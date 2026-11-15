#!/usr/bin/env python3
"""Haven v3 charging cradle: the DOCK BOARD (2026-11-14). Two layers, 1.6 mm, every part placed by JLCPCB.

What it is: a USB-C socket (power only), two 5.1 kohm resistors that tell a USB-C charger to give 5 V, one 10 uF
capacitor, and four bare gold pads (two per pod) that the pods' spring pins press on. Nothing else: each pod has its
own charging chip. Outline, pod holes, tongues, pad and screw positions come from
hardware/mechanical_cad/v3_slim/cradle_v3_layout.json (written by cradle_v3.py), so the board and the printed cradle
cannot drift apart.

    python3 tools/gen_cradle_v3_pcb.py   ->  kicad_v3_cradle/haven_v3_cradle.kicad_pcb, DRC report,
                                             fab/v3_cradle/haven_v3_cradle_{gerbers.zip,bom.csv,cpl.csv}

Only one of the socket's two VBUS pin pairs (A4/B9) is wired: in a USB-C plug all four VBUS contacts are one wire, so
either plug orientation works. Pod current is about 20 mA each. The other pair (A9/B4) is left on its own net,
VBUS_B, with no track: floating, not connected to anything.
LCSC numbers below are from memory and NOT checked against JLCPCB's library yet: check them at the quote.
NOT done: no schematic (board-only design, nets set here), no ESD part, no fuse (a coin across two pads shorts the
charger's 5 V; USB chargers limit that, cheap ones may not).
"""
import csv
import json
import os
import subprocess
import zipfile

import pcbnew
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
LAYOUT = os.path.join(ROOT, "..", "hardware", "mechanical_cad", "v3_slim", "cradle_v3_layout.json")
PRJ = os.path.join(ROOT, "kicad_v3_cradle")
PCB = os.path.join(PRJ, "haven_v3_cradle.kicad_pcb")
FAB = os.path.join(ROOT, "fab", "v3_cradle")
LIB = "/usr/share/kicad/footprints"
MM = pcbnew.FromMM
L = json.load(open(LAYOUT))
K = lambda X, Y: (100.0 + X, 100.0 - Y)            # cradle frame -> KiCad page


def P(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


os.makedirs(PRJ, exist_ok=True)
b = pcbnew.BOARD()
ds = b.GetDesignSettings()
ds.SetCopperLayerCount(2)
ds.m_TrackMinWidth, ds.m_MinClearance, ds.m_ViasMinSize, ds.m_MinThroughDrill = MM(0.15), MM(0.15), MM(0.5), MM(0.3)
ds.m_CopperEdgeClearance = MM(0.25)
ds.SetBoardThickness(MM(L["pcb_t"]))
nets = {}
for n in ("VBUS", "GND", "CC1", "CC2", "VBUS_B"):
    nets[n] = pcbnew.NETINFO_ITEM(b, n); b.Add(nets[n])

# ------------------------------------------------------------------ outline: rounded board minus a U-shaped hole per pod
X0, X1, Y0, Y1 = L["pcb"]
r = L["pcb_corner_r"]
outer = box(X0 + r, Y0 + r, X1 - r, Y1 - r).buffer(r, quad_segs=8)
cuts = []
for xj in L["pods"]:
    hw, (hy0, hy1) = L["hole_half_w"], L["hole_y"]
    hole = box(xj - hw + 1, hy0 + 1, xj + hw - 1, hy1 - 1).buffer(1.0, quad_segs=8)
    tongue = box(xj - L["tongue_half_w"], L["tongue_y0"], xj + L["tongue_half_w"], hy1 + 5).buffer(-0.5).buffer(0.5, quad_segs=6)
    cuts.append(hole.difference(tongue))                # a U: the tongue under the pins stays board
edge = b.GetLayerID("Edge.Cuts")


def ring(coords):
    pts = list(coords)
    for a, c in zip(pts, pts[1:]):
        s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(edge); s.SetWidth(MM(0.05))
        s.SetStart(P(*K(*a))); s.SetEnd(P(*K(*c))); b.Add(s)


ring(outer.exterior.coords)
for c in cuts:
    assert c.geom_type == "Polygon", c.geom_type
    ring(c.exterior.coords)
board_shape = outer.difference(unary_union(cuts))

# ------------------------------------------------------------------ parts
PARTS = []                                          # (ref, value, footprint name, LCSC, MPN)


def load(lib, name, ref, value, at, rot=0, lcsc="", mpn="", bom=True):
    fp = pcbnew.FootprintLoad(os.path.join(LIB, lib + ".pretty"), name)
    fp.SetReference(ref); fp.SetValue(value)
    fp.SetPosition(P(*at)); fp.SetOrientationDegrees(rot)
    fp.Reference().SetVisible(False)                    # parts sit under the cradle frame; refs only crowd the silk
    if not bom:
        fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    else:
        PARTS.append((ref, value, name, lcsc, mpn))
    b.Add(fp)
    return fp


def pad_at(fp, num):
    p = [q for q in fp.Pads() if q.GetNumber() == num][0].GetPosition()
    return pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)


def padnet(fp, num, net):
    for p in fp.Pads():
        if p.GetNumber() == num:
            p.SetNet(nets[net])


ux, uy = K(0.0, L["pcb"][2])                        # socket front flush with the board's -Y edge
usb = load("Connector_USB", "USB_C_Receptacle_HRO_TYPE-C-31-M-12", "J1", "USB-C power", (ux, uy - 3.7),
           lcsc="C165948", mpn="TYPE-C-31-M-12")
for num, net in (("A4", "VBUS"), ("B9", "VBUS"), ("A1", "GND"), ("B12", "GND"), ("B1", "GND"), ("A12", "GND"),
                 ("S1", "GND"), ("A5", "CC1"), ("B5", "CC2"), ("A9", "VBUS_B"), ("B4", "VBUS_B")):
    padnet(usb, num, net)
upos = {p.GetNumber(): (pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)) for p in usb.Pads() if p.GetNumber()}
r1 = load("Resistor_SMD", "R_0603_1608Metric", "R1", "5.1k", (106.8, 119.6), 0, "C23186", "0603WAF5101T5E")
r2 = load("Resistor_SMD", "R_0603_1608Metric", "R2", "5.1k", (106.8, 121.1), 0, "C23186", "0603WAF5101T5E")
c1 = load("Capacitor_SMD", "C_0603_1608Metric", "C1", "10uF 10V", (96.725, 119.5), 0, "C19702", "CL10A106KP8NNNC")
padnet(r1, "1", "CC1"); padnet(r1, "2", "GND"); padnet(r2, "1", "CC2"); padnet(r2, "2", "GND")
padnet(c1, "1", "GND"); padnet(c1, "2", "VBUS")
for i, (sx, sy) in enumerate(L["screws"]):
    load("MountingHole", "MountingHole_2.2mm_M2", f"H{i + 1}", "M2", K(sx, sy), bom=False)

# contact pads: bare, gold (ENIG), no paste, not parts
pads_k = []
for i, pd in enumerate(L["pads"]):
    fp = pcbnew.FOOTPRINT(b); fp.SetReference(f"CP{i + 1}"); fp.SetValue(pd["net"])
    fp.SetAttributes(pcbnew.FP_SMD | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    pad = pcbnew.PAD(fp); pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE); pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    pad.SetSize(pcbnew.VECTOR2I(MM(1.8), MM(1.8))); pad.SetNumber("1")
    ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.F_Mask); pad.SetLayerSet(ls)
    fp.Add(pad); fp.SetPosition(P(*K(pd["x"], pd["y"]))); b.Add(fp)
    fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    pad.SetNet(nets[pd["net"]])
    pads_k.append((K(pd["x"], pd["y"]), pd["net"]))


# ------------------------------------------------------------------ copper
def track(pts, net, w=0.5):
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(P(*a)); t.SetEnd(P(*c)); t.SetWidth(MM(w)); t.SetLayer(pcbnew.F_Cu)
        t.SetNet(nets[net]); b.Add(t)


def via(at, net):
    v = pcbnew.PCB_VIA(b); v.SetPosition(P(*at)); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3)); v.SetNet(nets[net]); b.Add(v)


a4, a5, b5 = upos["A4"], upos["A5"], upos["B5"]
TRUNK_X, TRUNK_TOP = 100.0, K(0, 11.5)[1]
track([a4, (a4[0], 119.5), (TRUNK_X, 117.5), (TRUNK_X, TRUNK_TOP)], "VBUS", 0.6)
vb = sorted(k for k, n in pads_k if n == "VBUS")
track([(vb[0][0], TRUNK_TOP), (vb[-1][0], TRUNK_TOP)], "VBUS", 0.6)
for (x, y), n in pads_k:
    if n == "VBUS":
        track([(x, TRUNK_TOP), (x, y)], "VBUS", 0.6)
    else:
        track([(x, y), (x, y - 1.75)], "GND", 0.6); via((x, y - 1.75), "GND")
track([a5, (a5[0], 119.6), (pad_at(r1, "1")[0], 119.6)], "CC1", 0.25)
track([b5, (b5[0], 121.1), (pad_at(r2, "1")[0], 121.1)], "CC2", 0.25)
for fp in (r1, r2):
    x, y = pad_at(fp, "2")
    track([(x, y), (x + 0.9, y)], "GND", 0.4); via((x + 0.9, y), "GND")
gx, gy = pad_at(c1, "1")
track([(gx, gy), (gx - 0.95, gy)], "GND", 0.4); via((gx - 0.95, gy), "GND")
s1 = sorted((pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)) for p in usb.Pads() if p.GetNumber() == "S1")
for g in ("A1", "A12"):                               # top GND pins to the nearest shell leg (shell legs reach the bottom pour)
    gp = upos[g]; leg = min(s1, key=lambda q: (q[0] - gp[0]) ** 2 + (q[1] - gp[1]) ** 2)
    track([gp, leg], "GND", 0.4)

# bottom-layer ground pour over the whole board
z = pcbnew.ZONE(b); z.SetLayer(pcbnew.B_Cu); z.SetNet(nets["GND"]); z.SetLocalClearance(MM(0.25)); z.SetMinThickness(MM(0.25))
ol = z.Outline(); ol.NewOutline()
for x, y in list(outer.exterior.coords)[:-1]:
    ol.Append(*[MM(v) for v in K(x, y)])
b.Add(z)

t = pcbnew.PCB_TEXT(b); t.SetText("HAVEN v3 cradle  2026-11-14"); t.SetLayer(pcbnew.B_SilkS); t.SetMirrored(True)
t.SetPosition(P(*K(0, -26.0))); t.SetTextSize(pcbnew.VECTOR2I(MM(1.0), MM(1.0))); b.Add(t)
for (x, y), n in pads_k:                              # mark the pads on the top silk: under the pods, for the assembler
    s = pcbnew.PCB_TEXT(b); s.SetText("+" if n == "VBUS" else "-"); s.SetLayer(pcbnew.F_SilkS)
    s.SetPosition(P(x, y - 1.6 if n == "VBUS" else y - 3.0)); s.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8))); b.Add(s)
b.Save(PCB)
b = pcbnew.LoadBoard(PCB)                            # the zone filler crashes on a board built in memory
b.BuildConnectivity()
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(PCB)

# ------------------------------------------------------------------ checks
rep = os.path.join(PRJ, "drc.json")
subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-all", "-o", rep, PCB], capture_output=True)
d = json.load(open(rep))
errs = [v for v in d.get("violations", []) if v["severity"] == "error"]
warns = [v for v in d.get("violations", []) if v["severity"] == "warning"]
print(f"DRC: {len(errs)} errors, {len(warns)} warnings, {len(d.get('unconnected_items', []))} unconnected")
for v in (errs + warns)[:20]:
    print("  ", v["severity"], v["type"], v["description"], [i.get("description", "")[:60] for i in v.get("items", [])])

# ------------------------------------------------------------------ fab files (JLCPCB column names)
gdir = os.path.join(FAB, "gerbers"); os.makedirs(gdir, exist_ok=True)
for f in os.listdir(gdir):
    os.remove(os.path.join(gdir, f))
bb = b.GetBoardEdgesBoundingBox()
origin = pcbnew.VECTOR2I(bb.GetLeft(), bb.GetBottom())
b.GetDesignSettings().SetAuxOrigin(origin); b.Save(PCB)
subprocess.run(["kicad-cli", "pcb", "export", "gerbers", "--layers", "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",
                "--use-drill-file-origin", "--subtract-soldermask", "-o", gdir + "/", PCB], check=True, capture_output=True)
subprocess.run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--drill-origin", "plot", "--excellon-separate-th",
                "-o", gdir + "/", PCB], check=True, capture_output=True)
with zipfile.ZipFile(os.path.join(FAB, "haven_v3_cradle_gerbers.zip"), "w", zipfile.ZIP_DEFLATED) as zf:
    for f in sorted(os.listdir(gdir)):
        zf.write(os.path.join(gdir, f), f)
groups = {}
for ref, val, fpn, lcsc, mpn in PARTS:
    groups.setdefault((val, fpn, mpn, lcsc), []).append(ref)
with open(os.path.join(FAB, "haven_v3_cradle_bom.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "Manufacturer Part", "LCSC Part #"])
    for (val, fpn, mpn, lcsc), refs in groups.items():
        w.writerow([val, ",".join(refs), fpn, mpn, lcsc])
with open(os.path.join(FAB, "haven_v3_cradle_cpl.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for fp in sorted(b.GetFootprints(), key=lambda q: q.GetReference()):
        if fp.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_POS_FILES:
            continue
        p = fp.GetPosition()
        w.writerow([fp.GetReference(), f"{pcbnew.ToMM(p.x - origin.x):.4f}mm", f"{pcbnew.ToMM(origin.y - p.y):.4f}mm", "Top",
                    f"{fp.GetOrientationDegrees() % 360:g}"])
print(f"board {pcbnew.ToMM(bb.GetWidth()):.1f} x {pcbnew.ToMM(bb.GetHeight()):.1f} mm; {len(PARTS)} placed parts; fab files in {FAB}")

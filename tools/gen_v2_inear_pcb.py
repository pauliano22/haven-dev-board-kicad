#!/usr/bin/env python3
"""Lay out the Haven v2 BTE in-ear board (kicad_v2_inear/haven_v2_inear.kicad_pcb).

6 x 6 mm, 2-layer, 0.6 mm, corner radius 0.8, origin = board centre. The outline matches
haven-hardware mechanical_cad/v2_bte/board_inear_outline.dxf.

Faces (as fitted in the shell):
  - Bottom (B.Cu, medial, facing the driver): SPH0641LU4H-1. It is bottom-port, so its
    sound port sits on a plated 0.4 mm hole at the board centre. Above it the hole lines up
    with the shell's mic hole. The two driver pads TP1/TP2 also go on this face.
  - Top (B.Cu's opposite, lateral, facing the shell's mic hole): the six cable pads W1..W6,
    C1 and R1. Nothing is placed inside the 1.4 mm gasket ring around the port hole.
KiCad Y points down. Superior (toward the cable boot) is -Y.

Run with the system python3 (KiCad 9 pcbnew):
    python3 tools/gen_v2_inear_pcb.py
then  kicad-cli pcb drc kicad_v2_inear/haven_v2_inear.kicad_pcb
"""
import json
import os
import re

import pcbnew

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PRJ = os.path.join(ROOT, "kicad_v2_inear")
LIB = os.path.join(PRJ, "footprints.pretty")
SCH = os.path.join(PRJ, "haven_v2_inear.kicad_sch")
PCB = os.path.join(PRJ, "haven_v2_inear.kicad_pcb")
NET = os.path.expanduser("~/.cache/haven_builds/inear_pcb/inear.net")

W, R_CORNER, THICK = 6.0, 0.8, 0.6
TRACK, CLR, VIA_D, VIA_DRILL = 0.15, 0.127, 0.55, 0.3
GASKET_R = 1.4
C0 = (100.0, 100.0)                                     # board centre on the sheet

# ref: (x, y, rot_deg, bottom)
PLACE = {
    "U13": (-0.814, 0.0, 270, True),                     # port hole lands on (0, 0); pins on the -X side
    "TP1": (2.05, -1.30, 0, True), "TP2": (2.05, 1.30, 0, True),
    "W5": (2.05, -1.30, 0, False), "W6": (2.05, 1.30, 0, False),
    "W1": (-2.074, -1.75, 0, False),                     # V_MIC, on its via
    "W3": (-0.95, -1.95, 0, False),                      # PDM_CLK, on its via
    "W2": (0.30, -2.30, 0, False),                       # GND
    "W4": (0.20, 2.30, 0, False),                        # PDM_DATA (after R1)
    "R1": (-1.20, 2.25, 0, False),
    "C1": (-2.30, -0.75, 270, False),                   # pad 1 (V_MIC) toward W1
}
VIAS = {"/V_MIC": [(-2.074, -1.75)], "/PDM_CLK": [(-0.95, -1.95)], "/MIC_DATA": [(-2.074, 1.75)],
        "/GND": [(0.30, -2.30), (1.2, 2.45)], "/SPK+": [(2.05, -1.30)], "/SPK-": [(2.05, 1.30)]}
# (net, layer, [points]); a point may be "Ref.pad" to snap to a pad centre
TRACKS = [
    ("/V_MIC", "B.Cu", ["U13.5", (-2.074, -1.75)]),
    ("/V_MIC", "F.Cu", [(-2.074, -1.75), "C1.1"]),
    ("/PDM_CLK", "B.Cu", ["U13.4", (-1.252, -1.55), (-0.95, -1.95)]),
    ("/MIC_DATA", "B.Cu", ["U13.1", (-2.074, 1.75)]),
    ("/MIC_DATA", "F.Cu", [(-2.074, 1.75), "R1.1"]),
    ("/PDM_DATA", "F.Cu", ["R1.2", "W4.1"]),
]


def mm(x, y):
    return pcbnew.VECTOR2I_MM(C0[0] + x, C0[1] + y)


def netlist():
    os.makedirs(os.path.dirname(NET), exist_ok=True)
    os.system(f'kicad-cli sch export netlist --format kicadsexpr -o "{NET}" "{SCH}" >/dev/null')
    s = open(NET).read()
    nets = {}
    for m in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]+)"\)(.*?)\)\)\s*(?=\(net |\)\s*\)\s*$)', s, re.S):
        for ref, pin in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2)):
            nets[(ref, pin)] = m.group(1)
    comps = dict(re.findall(r'\(comp \(ref "([^"]+)"\).*?\(footprint "[^:"]*:([^"]+)"\)', s, re.S))
    vals = dict(re.findall(r'\(comp \(ref "([^"]+)"\)\s*\(value "([^"]+)"\)', s, re.S))
    return nets, comps, vals


def outline(board):
    h, r = W / 2, R_CORNER
    k = h - r
    segs = [((-k, -h), (k, -h)), ((h, -k), (h, k)), ((k, h), (-k, h)), ((-h, k), (-h, -k))]
    for a, b in segs:
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(mm(*a)); s.SetEnd(mm(*b)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(pcbnew.FromMM(0.05))
        board.Add(s)
    for cx, cy, sx, sy in [(k, -k, k, -h), (k, k, h, k), (-k, k, -k, h), (-k, -k, -h, -k)]:
        a = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        a.SetCenter(mm(cx, cy)); a.SetStart(mm(sx, sy)); a.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T))
        a.SetLayer(pcbnew.Edge_Cuts); a.SetWidth(pcbnew.FromMM(0.05))
        board.Add(a)


def zone(board, net, layer, keepout=False):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    h = W / 2 - 0.25
    o = z.Outline(); o.NewOutline()
    for x, y in [(-h, -h), (h, -h), (h, h), (-h, h)]:
        o.Append(mm(x, y))
    z.SetNet(net)
    z.SetLocalClearance(pcbnew.FromMM(0.15))
    z.SetMinThickness(pcbnew.FromMM(0.15))
    z.SetThermalReliefGap(pcbnew.FromMM(0.15))
    z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    board.Add(z)
    return z


def gasket_keepout(board):
    """Component keep-out on the top face inside the gasket ring (copper is allowed)."""
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowFootprints(True)
    z.SetDoNotAllowTracks(False); z.SetDoNotAllowVias(True); z.SetDoNotAllowPads(False)
    z.SetDoNotAllowCopperPour(False)
    z.SetLayer(pcbnew.F_Cu)
    z.SetZoneName("GASKET_KEEPOUT")
    o = z.Outline(); o.NewOutline()
    import math
    for i in range(32):
        t = 2 * math.pi * i / 32
        o.Append(mm(GASKET_R * math.cos(t), GASKET_R * math.sin(t)))
    board.Add(z)


def project_rules():
    p = os.path.join(PRJ, "haven_v2_inear.kicad_pro")
    d = json.load(open(p))
    ds = d.setdefault("board", {}).setdefault("design_settings", {})
    rules = ds.setdefault("rules", {})
    rules.update(min_clearance=CLR, min_track_width=0.127, min_via_diameter=0.5, min_via_annular_width=0.1,
                 min_through_hole_diameter=0.3, min_hole_clearance=0.2, min_hole_to_hole=0.25,
                 min_copper_edge_clearance=0.25, min_connection=0.127)
    ns = d.setdefault("net_settings", {})
    cls = ns.setdefault("classes", [{"name": "Default"}])
    cls[0].update(clearance=CLR, track_width=TRACK, via_diameter=VIA_D, via_drill=VIA_DRILL)
    json.dump(d, open(p, "w"), indent=2)


def main():
    nets, comps, vals = netlist()
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    bds = board.GetDesignSettings()
    bds.SetBoardThickness(pcbnew.FromMM(THICK))
    netinfo = {}
    for n in sorted(set(nets.values())):
        ni = pcbnew.NETINFO_ITEM(board, n); board.Add(ni); netinfo[n] = ni
    outline(board)
    fps = {}
    for ref, fpname in comps.items():
        fp = pcbnew.FootprintLoad(LIB, fpname)
        fp.SetReference(ref); fp.SetValue(vals.get(ref, fpname))
        fp.SetFPID(pcbnew.LIB_ID("haven_v2_inear", fpname))
        board.Add(fp)
        x, y, rot, bottom = PLACE[ref]
        fp.SetPosition(mm(x, y)); fp.SetOrientationDegrees(rot)
        if bottom:
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        for pad in fp.Pads():
            n = nets.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(netinfo[n])
        for t in (fp.Reference(), fp.Value()):
            t.SetVisible(False)
        fps[ref] = fp

    def pt(p):
        if isinstance(p, str):
            ref, num = p.split(".")
            return next(q for q in fps[ref].Pads() if q.GetNumber() == num).GetPosition()
        return mm(*p)

    for net, layer, pts in TRACKS:
        P = [pt(p) for p in pts]
        for a, b in zip(P, P[1:]):
            t = pcbnew.PCB_TRACK(board); t.SetStart(a); t.SetEnd(b); t.SetWidth(pcbnew.FromMM(TRACK))
            t.SetLayer(board.GetLayerID(layer)); t.SetNet(netinfo[net]); board.Add(t)
    for net, pts in VIAS.items():
        for p in pts:
            v = pcbnew.PCB_VIA(board); v.SetPosition(mm(*p)); v.SetDrill(pcbnew.FromMM(VIA_DRILL))
            v.SetWidth(pcbnew.FromMM(VIA_D)); v.SetNet(netinfo[net]); board.Add(v)
    gasket_keepout(board)
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        zone(board, netinfo["/GND"], layer)
    board.Save(PCB)
    project_rules()                     # BOARD.Save rewrites the .kicad_pro; restore our rules before the fill
    # ZONE_FILLER segfaults on a board built in memory; it works on a freshly loaded one.
    board = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PCB)
    project_rules()                     # after saving: BOARD.Save rewrites the .kicad_pro
    print("wrote", PCB)


if __name__ == "__main__":
    main()

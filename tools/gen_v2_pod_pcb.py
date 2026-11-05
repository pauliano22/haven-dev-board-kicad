#!/usr/bin/env python3
"""Place the Haven v2 BTE pod board (kicad_v2_pod/haven_v2_pod.kicad_pcb), ready for routing.

13 x 27 mm, 6-layer, 0.8 mm, corner radius 1.5. Outline and keep-outs follow haven-hardware
mechanical_cad/v2_bte/board_pod_outline.dxf. Coordinates in this script are the DXF's: origin =
board centre, +Y = up (antenna end). KiCad's Y points down, so `kc()` flips Y.

Faces:
  - Top (F.Cu, lateral): CP1454 battery (keep-out circle, only its tab pads TP8/TP9 inside),
    MDBT53V-1M with its antenna end flush with the top edge, the six cable pads on the anterior
    edge, the status LED.
  - Bottom (B.Cu, head side): everything else, <= 1.0 mm tall.
Antenna: no copper on any layer for the top 3.8 mm (Raytac spec Ver.D), full board width.

Stackup: F.Cu sig | In1 GND plane | In2 sig | In3 sig | In4 sig + GND pour | B.Cu sig + GND pour. Rules match the
Rev A board, which JLCPCB quoted on its standard 6-layer process: 0.09 / 0.09 mm, 0.2 / 0.35 mm
routing vias, 0.15 / 0.25 mm vias in the BGA and WLCSP pads (epoxy-filled, capped).

    python3 tools/gen_v2_pod_pcb.py          # place, fan out, write the board
    python3 tools/route_v2_pod_pcb.py        # Freerouting, import, pour, DRC
"""
import json
import math
import os
import re

import pcbnew

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PRJ = os.path.join(ROOT, "kicad_v2_pod")
LIB = os.path.join(PRJ, "footprints.pretty")
SCH = os.path.join(PRJ, "haven_v2_pod.kicad_sch")
PCB = os.path.join(PRJ, "haven_v2_pod.kicad_pcb")
NET = os.path.expanduser("~/.cache/haven_builds/pod_pcb/pod.net")

W, L, R_CORNER, THICK = 13.0, 27.0, 1.5, 0.8
ANT_Y = 13.5 - 3.8                     # antenna keep-out below the top edge
BAT_C, BAT_R = (0.0, -6.45), 7.05      # CP1454 keep-out circle (top face)
MIC_PORT = (-4.9, 7.0)
GASKET_R = 1.4
EDGE = 0.3                             # part keep-back from the board edge
CLR, TRACK, VIA_D, VIA_DRILL = 0.10, 0.1, 0.35, 0.2   # 0.10: keeps tracks 0.15 mm from via holes
FAN_D, FAN_DRILL = 0.25, 0.15
SPACING = 0.22                         # courtyard-to-courtyard gap for auto-placed parts
C0 = (100.0, 100.0)

# Fixed placements: ref -> (x, y, rot, side). Side "F" top, "B" bottom.
FIXED = {
    "U1": (0.8, 7.3, 0, "F"),
    "W1": (5.65, 7.45, 0, "F"), "W3": (5.65, 6.30, 0, "F"), "W2": (5.65, 5.15, 0, "F"),
    "W4": (5.65, 4.00, 0, "F"), "W5": (5.65, 2.85, 0, "F"), "W6": (5.65, 1.70, 0, "F"),
    "TP8": (3.0, -0.6, 0, "F"), "TP9": (-3.0, -0.6, 0, "F"),
    "U4": (-5.0, 9.1, 0, "F"),
    "U15": (-2.4, -4.6, 0, "B"),            # codec in the open lower half, off the module
    "U2": (3.4, -5.6, 0, "B"),
    "U3": (-1.6, 0.9, 0, "B"),
    "X1": (2.6, 0.3, 0, "B"),
    "CRYSTAL1": (-4.6, -1.9, 0, "B"),
    "P1": (-3.6, -12.0, 0, "B"), "P2": (3.6, -12.0, 0, "B"),
    **{f"TP{i + 1}": (-4.5 + 1.5 * i, -10.1, 0, "B") for i in range(7)},
    **{f"D{i}": (5.0, y, 0, "B") for i, y in zip(range(2, 7), (7.45, 6.30, 4.00, 2.85, 1.70))},
}
DNP = {"L101", "L102"}                 # nRF DC/DC inductors, not fitted on the first build
# mic: port on MIC_PORT, body hanging down (away from the antenna)
MIC = ("U14", MIC_PORT, 180, "B")

NETCLASS = {"PWR": dict(nets=["/VBUS", "/VBAT", "/VSYS", "/SW", "/+1V8"], track=0.15),
            "AUDIO": dict(nets=["/SPK+", "/SPK-", "/V_LS"], track=0.12)}


def kc(x, y):
    return pcbnew.VECTOR2I_MM(C0[0] + x, C0[1] - y)


def dxf(v):
    return (pcbnew.ToMM(v.x) - C0[0], C0[1] - pcbnew.ToMM(v.y))


def netlist():
    os.makedirs(os.path.dirname(NET), exist_ok=True)
    os.system(f'kicad-cli sch export netlist --format kicadsexpr -o "{NET}" "{SCH}" >/dev/null')
    s = open(NET).read()
    nets = {}
    for m in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]+)"\)(.*?)\)\)\s*(?=\(net |\)\s*\)\s*$)', s, re.S):
        for ref, pin in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2)):
            nets[(ref, pin)] = m.group(1)
    comps = re.findall(r'\(comp \(ref "([^"]+)"\)\s*\(value "([^"]+)"\).*?\(footprint "[^:"]*:([^"]+)"\)', s, re.S)
    return nets, comps


def outline(board):
    h, v, r = W / 2, L / 2, R_CORNER
    for a, b in [((-h + r, -v), (h - r, -v)), ((h, -v + r), (h, v - r)), ((h - r, v), (-h + r, v)), ((-h, v - r), (-h, -v + r))]:
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(kc(*a)); s.SetEnd(kc(*b)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(pcbnew.FromMM(0.05)); board.Add(s)
    for cx, cy in [(h - r, v - r), (-h + r, v - r), (-h + r, -v + r), (h - r, -v + r)]:
        sx, sy = (1 if cx > 0 else -1), (1 if cy > 0 else -1)
        a = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        k = r / math.sqrt(2)
        a.SetArcGeometry(kc(cx + sx * r, cy), kc(cx + sx * k, cy + sy * k), kc(cx, cy + sy * r))
        a.SetLayer(pcbnew.Edge_Cuts); a.SetWidth(pcbnew.FromMM(0.05)); board.Add(a)


def poly_zone(board, pts, layer=None, layers=None, net=None, rule=None, name=""):
    z = pcbnew.ZONE(board)
    if layers:
        ls = pcbnew.LSET()
        for l in layers:
            ls.AddLayer(l)
        z.SetLayerSet(ls)
    else:
        z.SetLayer(layer)
    o = z.Outline(); o.NewOutline()
    for p in pts:
        o.Append(kc(*p))
    if rule:
        z.SetIsRuleArea(True)
        for k, v in rule.items():
            getattr(z, "SetDoNotAllow" + k)(v)
    if net is not None:
        z.SetNet(net)
        z.SetLocalClearance(pcbnew.FromMM(0.12))
        z.SetMinThickness(pcbnew.FromMM(0.1))
        z.SetThermalReliefGap(pcbnew.FromMM(0.12))
        z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.15))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    if name:
        z.SetZoneName(name)
    board.Add(z)
    return z


def circle_pts(c, r, n=40):
    return [(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def copper_layers():
    return [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu]


def project_rules():
    p = os.path.join(PRJ, "haven_v2_pod.kicad_pro")
    d = json.load(open(p))
    ds = d.setdefault("board", {}).setdefault("design_settings", {})
    ds.setdefault("rules", {}).update(
        min_clearance=CLR, min_track_width=0.09, min_via_diameter=FAN_D, min_via_annular_width=0.05,
        min_through_hole_diameter=FAN_DRILL, min_hole_clearance=0.15, min_hole_to_hole=0.2,
        min_copper_edge_clearance=0.2, min_connection=0.09, min_microvia_diameter=0.2, min_microvia_drill=0.1)
    ns = d.setdefault("net_settings", {})
    base = ns.setdefault("classes", [{"name": "Default"}])[0]
    base.update(clearance=CLR, track_width=TRACK, via_diameter=VIA_D, via_drill=VIA_DRILL)
    ns["classes"] = [base] + [dict(base, name=k, track_width=v["track"], priority=i) for i, (k, v) in enumerate(NETCLASS.items())]
    ns["netclass_patterns"] = [{"netclass": k, "pattern": n} for k, v in NETCLASS.items() for n in v["nets"]]
    json.dump(d, open(p, "w"), indent=2)


# ---------------------------------------------------------------- auto placement
class Occupancy:
    def __init__(self):
        self.rects = {"F": [], "B": []}

    def add(self, side, r):
        self.rects[side].append(r)

    def free(self, side, r):
        x0, y0, x1, y1 = r
        return all(x1 + SPACING <= a or x0 >= c + SPACING or y1 + SPACING <= b or y0 >= d + SPACING
                   for a, b, c, d in self.rects[side])


def allowed(side, r):
    x0, y0, x1, y1 = r
    h, v = W / 2 - EDGE, L / 2 - EDGE
    if x0 < -h or x1 > h or y0 < -v or y1 > ANT_Y - 0.2:
        return False
    # stay off the rounded corners
    for cx, cy in [(W / 2 - R_CORNER, L / 2 - R_CORNER), (-W / 2 + R_CORNER, L / 2 - R_CORNER),
                   (-W / 2 + R_CORNER, -L / 2 + R_CORNER), (W / 2 - R_CORNER, -L / 2 + R_CORNER)]:
        for px, py in [(x0, y0), (x0, y1), (x1, y0), (x1, y1)]:
            if (px - cx) * (1 if cx > 0 else -1) > 0 and (py - cy) * (1 if cy > 0 else -1) > 0 and \
                    math.hypot(px - cx, py - cy) > R_CORNER - EDGE:
                return False
    return True


def fp_rect(fp):
    """Part footprint in DXF coords: pad extent plus the body if a courtyard exists."""
    bb = fp.GetBoundingBox(False)              # pads + graphics, no text
    (x0, y1), (x1, y0) = dxf(pcbnew.VECTOR2I(bb.GetLeft(), bb.GetTop())), dxf(pcbnew.VECTOR2I(bb.GetRight(), bb.GetBottom()))
    return (x0, y0, x1, y1)


def place_at(fp, x, y, rot, side):
    if fp.IsFlipped() != (side == "B"):
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(kc(x, y))


def main():
    nets, comps = netlist()
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(6)
    board.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(THICK))
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)     # solid GND plane under the module
    # In4 is a signal layer (routing room around the BGA) that also gets a GND pour after routing
    ni = {}
    for n in sorted(set(nets.values())):
        x = pcbnew.NETINFO_ITEM(board, n); board.Add(x); ni[n] = x
    outline(board)

    fps = {}
    for ref, val, fpname in comps:
        fp = pcbnew.FootprintLoad(LIB, fpname)
        fp.SetReference(ref); fp.SetValue(val); fp.SetFPID(pcbnew.LIB_ID("haven_v2_pod", fpname))
        fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
        if ref in DNP:
            fp.SetDNP(True)
        board.Add(fp)
        for pad in fp.Pads():
            n = nets.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(ni[n])
        fps[ref] = fp

    occ = Occupancy()
    # keep-outs as occupancy: battery circle (top), module, mic, gasket ring (top)
    occ.add("F", (BAT_C[0] - BAT_R, BAT_C[1] - BAT_R, BAT_C[0] + BAT_R, BAT_C[1] + BAT_R))
    occ.add("F", (MIC_PORT[0] - GASKET_R, MIC_PORT[1] - GASKET_R, MIC_PORT[0] + GASKET_R, MIC_PORT[1] + GASKET_R))
    for ref, (x, y, rot, side) in FIXED.items():
        place_at(fps[ref], x, y, rot, side)
        occ.add(side, fp_rect(fps[ref]))
    # module inner-column pads (staggered behind the outer column): via-in-pad when connected, as on Rev A
    for pad in fps["U1"].Pads():
        n = pad.GetNetname()
        num = int(pad.GetNumber())
        if n and not n.startswith("unconnected") and (num in range(3, 18, 2) or num in range(28, 37, 2)):
            v = pcbnew.PCB_VIA(board); v.SetPosition(pad.GetPosition())
            v.SetDrill(pcbnew.FromMM(FAN_DRILL)); v.SetWidth(pcbnew.FromMM(FAN_D)); v.SetNet(pad.GetNet())
            board.Add(v)
            vx, vy = dxf(pad.GetPosition())
            occ.add("B", (vx - FAN_D / 2, vy - FAN_D / 2, vx + FAN_D / 2, vy + FAN_D / 2))

    # mic: rotate until its port pad lands on MIC_PORT
    mic = fps[MIC[0]]
    place_at(mic, 0, 0, MIC[2], MIC[3])
    port = next(p for p in mic.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH)
    px, py = dxf(port.GetPosition())
    place_at(mic, MIC_PORT[0] - px, MIC_PORT[1] - py, MIC[2], MIC[3])
    occ.add("B", fp_rect(mic))

    # passives: anchor each on the pad it serves, then spiral out to the nearest free spot
    anchors_used = {}
    big = {}
    for (ref, pin), n in nets.items():
        big.setdefault(n, []).append((ref, pin))
    ic = ("U15", "U2", "U1", "U14", "U3", "Q2", "X1", "CRYSTAL1", "U4", "P1", "W1", "W2", "W3", "W4", "W5", "W6")
    order = []
    for ref, val, fpname in comps:
        if ref in FIXED or ref == MIC[0]:
            continue
        sig = [n for (r, p), n in nets.items() if r == ref and n != "/GND"]
        sig.sort(key=lambda n: len(big[n]))
        order.append((len(big[sig[0]]) if sig else 99, ref, sig))
    order.sort()
    placed = set(FIXED) | {MIC[0]}
    for _, ref, sig in order:
        cands = []
        for n in sig:
            for r, p in big[n]:
                if r in placed and r != ref:
                    pad = next(q for q in fps[r].Pads() if q.GetNumber() == p)
                    cands.append((ic.index(r) if r in ic else 50, anchors_used.get((r, p), 0), r, p, pad))
            if cands:
                break
        if not cands:
            cands = [(0, 0, "U15", "", fps["U15"].Pads()[0])]
        cands.sort(key=lambda c: (c[1], c[0]))
        _, _, r, p, pad = cands[0]
        anchors_used[(r, p)] = anchors_used.get((r, p), 0) + 1
        ax, ay = dxf(pad.GetPosition())
        fp = fps[ref]
        done = False
        for k in range(1, 2000):
            rad = 0.15 * k ** 0.5 * 1.6
            ang = k * 2.39996
            x, y = ax + rad * math.cos(ang), ay + rad * math.sin(ang)
            for rot in (0, 90):
                place_at(fp, x, y, rot, "B")
                rr = fp_rect(fp)
                if allowed("B", rr) and occ.free("B", rr):
                    occ.add("B", rr); done = True
                    break
            if done:
                break
        if not done:
            raise SystemExit(f"no room for {ref}")
        placed.add(ref)

    # fan-out vias: every connected BGA / WLCSP ball gets a 0.15 / 0.25 mm via in its pad (filled and
    # capped at fab). Reserving them before autorouting keeps other nets from routing under a ball,
    # which is what left nets unroutable when only the inner balls were fanned out.
    for ref, rows, cols in (("U15", "ABCDEFG", range(1, 9)), ("U2", "ABCDE", range(1, 6))):
        for pad in fps[ref].Pads():
            n = pad.GetNetname()
            if not n or n.startswith("unconnected"):
                continue
            num = pad.GetNumber()
            r, c = num[0], int(num[1:])
            if True:
                v = pcbnew.PCB_VIA(board); v.SetPosition(pad.GetPosition())
                v.SetDrill(pcbnew.FromMM(FAN_DRILL)); v.SetWidth(pcbnew.FromMM(FAN_D)); v.SetNet(pad.GetNet())
                board.Add(v)

    # rule areas
    h, v = W / 2, L / 2
    poly_zone(board, [(-h, ANT_Y), (h, ANT_Y), (h, v), (-h, v)], layers=copper_layers(),
              rule=dict(Tracks=True, Vias=True, Pads=False, CopperPour=True, Footprints=False), name="ANTENNA_KEEPOUT")
    poly_zone(board, circle_pts(MIC_PORT, GASKET_R), layer=pcbnew.F_Cu,
              rule=dict(Footprints=True, Vias=True, Tracks=False, Pads=False, CopperPour=False), name="MIC_GASKET")
    # GND planes on In1/In4, GND pour on the outer layers, all stopping at the antenna keep-out
    for l in (pcbnew.In1_Cu, pcbnew.In4_Cu, pcbnew.B_Cu, pcbnew.F_Cu):
        poly_zone(board, [(-h + 0.2, -v + 0.2), (h - 0.2, -v + 0.2), (h - 0.2, ANT_Y), (-h + 0.2, ANT_Y)], layer=l, net=ni["/GND"])

    board.Save(PCB)
    project_rules()
    print("placed", len(fps), "parts; wrote", PCB)


if __name__ == "__main__":
    main()

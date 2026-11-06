#!/usr/bin/env python3
"""Lay out the Haven v2 BTE charging-case board (kicad_v2_case/haven_v2_case.kicad_pcb).

2 layers, 1.0 mm, all parts on the top face. Coordinates are the case frame from
haven-hardware mechanical_cad/v2_bte/case.json (X across, Y toward the back wall, mm); KiCad Y is
flipped. The board is the strip under the pods: the four spring pins sit exactly under the pods'
charge contacts, USB-C's mouth is flush with the back edge (case back-wall opening at x = USB_X),
the charge LED sits at the back edge behind a light hole, and the battery lead enters at the front.

    python3 tools/gen_v2_case_pcb.py        # place, outline, GND pours
    python3 tools/route_v2_pod_pcb.py ...   # not used: routing is done by route_v2_case_pcb.py
"""
import json
import os
import re

import pcbnew

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PRJ = os.path.join(ROOT, "kicad_v2_case")
LIB = os.path.join(PRJ, "footprints.pretty")
SCH = os.path.join(PRJ, "haven_v2_case.kicad_sch")
PCB = os.path.join(PRJ, "haven_v2_case.kicad_pcb")
NET = os.path.expanduser("~/.cache/haven_builds/case_pcb/case.net")
CASE_JSON = os.path.normpath(os.path.join(ROOT, "..", "hardware", "mechanical_cad", "v2_bte", "case.json"))

THICK = 1.0
CLR, TRACK, VIA_D, VIA_DRILL = 0.15, 0.25, 0.6, 0.3
USB_X = -2.0                  # J1 centre; the case's back-wall opening must match
USB_FRONT = 3.7               # HRO TYPE-C-31-M-12: mouth ~3.7 mm in front of the footprint origin
LED_X = -8.8


def kc(x, y):
    return pcbnew.VECTOR2I_MM(100.0 + x, 100.0 - y)


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


def place_table(case):
    by, bl = case["board_center_y"], case["board_mm"][1]
    back = by + bl / 2
    front = by - bl / 2
    c = case["contacts"]
    t = {
        # spring pins: exactly under the pod contacts
        "P1": (*c["L"]["vbus"], 0), "P2": (*c["L"]["gnd"], 0),
        "P3": (*c["R"]["vbus"], 0), "P4": (*c["R"]["gnd"], 0),
        # USB-C: rotated 180 so the mouth faces the back edge, flush with it
        "J1": (USB_X, back - USB_FRONT, 180),
        # USB support parts in the free strip in front of J1, between the two pods' pins
        "R1": (-5.6, front + 5.3, 0), "R2": (-3.2, front + 5.3, 0),
        "D1": (-0.6, front + 5.4, 0), "C1": (1.9, front + 3.6, 90),
        # charger cluster, left
        "U1": (-15.5, back - 4.5, 0), "R3": (-15.5, back - 7.6, 0), "C2": (-19.2, back - 4.5, 90),
        "R4": (-12.2, back - 1.4, 0), "D2": (LED_X, back - 0.9, 0),
        "J2": (-16.5, front + 3.4, 0),             # battery lead from the front
        "TP1": (-20.4, back - 8.0, 0),
        # boost cluster, right
        # boost: L1 turned so its SW pad sits straight above U2's SW pin (U2 rot 90: pins 4-6 face L1)
        "L1": (14.0, back - 1.9, 180), "U2": (12.925, back - 4.66, 90),
        "C3": (17.0, back - 4.6, 90),                 # VIN, right, next to L1's VBAT pad
        "C4": (10.2, back - 4.6, 90), "C5": (7.9, back - 4.6, 90),   # VOUT, left (U2's VOUT pin faces left)
        "R5": (11.4, back - 7.2, 0), "R6": (11.4, back - 8.4, 0),
        "D3": (9.0, front + 2.2, 90), "TP2": (19.6, front + 2.2, 0), "TP3": (16.6, front + 2.2, 0),
    }
    return t


def outline(board, x0, y0, x1, y1, r):
    for a, b in [((x0 + r, y0), (x1 - r, y0)), ((x1, y0 + r), (x1, y1 - r)), ((x1 - r, y1), (x0 + r, y1)), ((x0, y1 - r), (x0, y0 + r))]:
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(kc(*a)); s.SetEnd(kc(*b)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(pcbnew.FromMM(0.05)); board.Add(s)
    k = 0.70710678
    for sx, sy in [(1, -1), (1, 1), (-1, 1), (-1, -1)]:                 # corner directions
        cx, cy = (x1 - r if sx > 0 else x0 + r), (y1 - r if sy > 0 else y0 + r)
        a = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        a.SetArcGeometry(kc(cx + sx * r, cy), kc(cx + sx * r * k, cy + sy * r * k), kc(cx, cy + sy * r))
        a.SetLayer(pcbnew.Edge_Cuts); a.SetWidth(pcbnew.FromMM(0.05)); board.Add(a)


def zone(board, net, layer, x0, y0, x1, y1):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    o = z.Outline(); o.NewOutline()
    for x, y in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
        o.Append(kc(x, y))
    z.SetNet(net)
    z.SetLocalClearance(pcbnew.FromMM(0.25))
    z.SetMinThickness(pcbnew.FromMM(0.2))
    z.SetThermalReliefGap(pcbnew.FromMM(0.25))
    z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.3))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    board.Add(z)


def project_rules():
    p = os.path.join(PRJ, "haven_v2_case.kicad_pro")
    d = json.load(open(p))
    ds = d.setdefault("board", {}).setdefault("design_settings", {})
    ds.setdefault("rules", {}).update(min_clearance=CLR, min_track_width=0.15, min_via_diameter=0.5,
                                      min_via_annular_width=0.13, min_through_hole_diameter=0.3,
                                      min_hole_clearance=0.25, min_hole_to_hole=0.25,
                                      min_copper_edge_clearance=0.3, min_connection=0.15)
    ns = d.setdefault("net_settings", {})
    cls = ns.setdefault("classes", [{"name": "Default"}])
    cls[0].update(clearance=CLR, track_width=TRACK, via_diameter=VIA_D, via_drill=VIA_DRILL)
    names = [c["name"] for c in cls]
    if "PWR" not in names:
        cls.append(dict(cls[0], name="PWR", track_width=0.5))
    ns["netclass_patterns"] = [{"netclass": "PWR", "pattern": n} for n in ("/VUSB", "/VBAT", "/V5", "/SW", "/GND")]
    json.dump(d, open(p, "w"), indent=2)


def main():
    case = json.load(open(CASE_JSON))
    nets, comps, vals = netlist()
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    board.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(THICK))
    netinfo = {}
    for n in sorted(set(nets.values())):
        ni = pcbnew.NETINFO_ITEM(board, n); board.Add(ni); netinfo[n] = ni
    by, (bw, bl) = case["board_center_y"], case["board_mm"]
    x0, x1, y0, y1 = -bw / 2, bw / 2, by - bl / 2, by + bl / 2
    outline(board, x0, y0, x1, y1, 1.0)
    PLACE = place_table(case)
    for ref, fpname in comps.items():
        fp = pcbnew.FootprintLoad(LIB, fpname)
        fp.SetReference(ref); fp.SetValue(vals.get(ref, fpname))
        fp.SetFPID(pcbnew.LIB_ID("haven_v2_case", fpname))
        board.Add(fp)
        x, y, rot = PLACE[ref]
        fp.SetPosition(kc(x, y)); fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            n = nets.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(netinfo[n])
        fp.Value().SetVisible(False)
        fp.Reference().SetVisible(False)              # no room for silk refs between 0402s; refs are in the fab drawing
    # SW node, hand-placed: U2 pin 5 straight up to L1's SW pad (shortest switching loop)
    pad = {(f.GetReference(), p.GetNumber()): p for f in board.GetFootprints() for p in f.Pads()}
    a_, b_ = pad[("U2", "5")].GetPosition(), pad[("L1", "2")].GetPosition()
    assert abs(a_.x - b_.x) < pcbnew.FromMM(0.01), "U2 SW pin is not under L1's SW pad"
    t = pcbnew.PCB_TRACK(board); t.SetStart(a_); t.SetEnd(b_); t.SetWidth(pcbnew.FromMM(0.35))
    t.SetLayer(pcbnew.F_Cu); t.SetNet(netinfo["/SW"]); board.Add(t)
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        zone(board, netinfo["/GND"], layer, x0 + 0.3, y0 + 0.3, x1 - 0.3, y1 - 0.3)
    t = pcbnew.PCB_TEXT(board)
    t.SetText("HAVEN v2 CASE"); t.SetPosition(kc(0, y0 + 1.6)); t.SetLayer(pcbnew.B_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I_MM(1.0, 1.0)); t.SetMirrored(True); board.Add(t)
    board.Save(PCB)
    project_rules()
    board = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PCB)
    project_rules()
    print("wrote", PCB)


if __name__ == "__main__":
    main()

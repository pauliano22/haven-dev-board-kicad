#!/usr/bin/env python3
"""Place the Haven v3 slim pod board (kicad_v3_pod/haven_v3_pod.kicad_pcb). PLACEMENT ONLY, not routed.

9.6 x 27 mm, 6 layers, 0.8 mm (JLCPCB's thinnest 6-layer; the shell check assumed 0.6, so the pod is 0.2 mm
thicker than DESIGN_BRIEF_SHELL_V3.md says). Every part is on the top (lateral) face. The pouch cell lies on
the bottom face from the bottom edge up to y = +3.5 (17 mm cell); its two lead pads (TP8/TP9) are on the bottom face just
above it. Coordinates: origin = board centre, +Y up (antenna end), as in gen_v2_pod_pcb.py, whose helpers
this script reuses.

    python3 tools/gen_v3_pod_pcb.py

WARNING (2026-11-14): the board in the repo is ROUTED and was finished by hand-directed patches (see the README).
This script would overwrite it with an unrouted attempt-6 placement. It refuses to run unless HAVEN_FORCE_REGEN=1
and HAVEN_PCB points somewhere else or you really mean it.
"""
import json
import math
import os
import sys

import pcbnew

import gen_v2_pod_pcb as b

b.PRJ = os.path.join(b.ROOT, "kicad_v3_pod")
b.LIB = os.path.join(b.PRJ, "footprints.pretty")
b.SCH = os.path.join(b.PRJ, "haven_v3_pod.kicad_sch")
b.PCB = os.path.join(b.PRJ, "haven_v3_pod.kicad_pcb")
b.NET = os.path.expanduser("~/.cache/haven_builds/v3_pod_pcb/pod.net")
b.W, b.L, b.R_CORNER, b.THICK = 9.6, 27.0, 1.0, 0.8
b.ANT_Y = 13.5 - 3.8
MOD_BOTTOM = 13.5 - 12.4
CELL_TOP = -13.5 + 20.0          # 20 mm cell (TinyCircuits ASR00072, nominal 3.5 x 8 x 20): bottom face is free from y = 6.5 up to the antenna keep-out

b.SPACING = 0.15
CRYSTAL_XY = tuple(float(v) for v in os.environ.get("HAVEN_XTAL", "2.6,-2.85").split(","))
FIXED = {
    "U1": (0.0, 7.3, 0, "F"),
    "W5": (3.9, 0.3, 0, "F"), "W6": (2.6, 0.3, 0, "F"),        # speaker wires, just below the module
    "U14": (-2.72, -1.85, 0, "F"),         # mic, top port, under the shell's mic hole
    "U15": (1.2, -5.3, 0, "F"),            # audio chip, with room on three sides for its capacitors
    "CRYSTAL1": (CRYSTAL_XY[0], CRYSTAL_XY[1], 0, "F"),   # above the chip's top-right corner, where XTALI / XTALO leave (attempt 4 had it on the left: unroutable)
    "U2": (2.9, -10.2, 0, "F"),             # power chip
    "L2": (-0.3, -11.3, 90, "F"),
    # bottom face, in the 3.2 mm strip between the cell end (y = 6.5) and the antenna keep-out (under the module):
    "TP9": (-3.6, 8.65, 0, "B"), "P1": (-1.3, 8.65, 0, "B"), "P2": (1.3, 8.65, 0, "B"), "TP8": (3.6, 8.65, 0, "B"),
    **{f"TP{i + 1}": (-3.75 + 1.25 * i, 7.3, 0, "B") for i in range(7)},
}
SIDE_B = set()
IC_ORDER = ("U15", "U2", "U1", "U14", "U3", "Q2", "X1", "CRYSTAL1", "U4", "P1", "W5", "W6")


# ---- audio chip (U15, 0.35 mm pitch) escape plan, 2026-11-11 ------------------------------------------------
# With a 0.25 mm via in every ball there is only 0.10 mm between neighbouring vias: no track fits, on any layer.
# A signal on an inner ball can only leave through positions that have NO via: unused balls, or balls listed in
# U15_NO_VIA. Three autorouter attempts left the same inner signals stranded, so the escapes are drawn here by hand
# and locked; the autorouter continues from the stub ends. Ball map (row A at the top, column 1 at the left):
#   A GND  V_LS DVDD GND  -     -     -     -        B DOUT BCLK  DVDD GND    V_LS   XTALO XTALI -
#   C DIN  LRCLK -   PDMCLK PDMDIN SDA1 SCL1 -       D V_LS -     -    -      -      GND   GND   -
#   E V_LS -    -    DAC_EN -     GND   -    -       F GND  SPK+  V_LS -      -      -     V_LS  -
#   G SPK- V_LS GND  CM   -     -     GND   -
# Outer-ring signals B1, C1, G1 leave on the top layer and need no via. F1 (GND) gets its via just outside the
# chip. D6 (GND) joins its neighbour D7 on the top layer. That opens the left side and the D6 position.
# Everything bound for the bottom edge has to pass the single gap at E5-F5 (one track per layer), hence one net each
# on In2, In3, In4 and the bottom layer. V_LS inner balls (B5, F3, F7) connect through a V_LS pour on In4.
U15_NO_VIA = {"B1", "C1", "G1", "F1", "D6"}
# Attempt 5 lesson: stubs on different layers that END at the same x/y block each other's vias. Each escape now has a
# first straight stub (mm) and then a diagonal tail (dx, dy in mm on the board, x right, y down) so that every end
# is at least 0.45 mm from every other end and from every other escape track.
U15_ESCAPES = [   # ball, layer, positions passed through, exit direction (ball pitches), stub mm, tail (dx, dy) mm or None
    ("B6", "In2", ["A6"], (0, -1), 0.6, None), ("B7", "In2", ["A7"], (0, -1), 0.6, None),      # crystal, out of the top
    ("C7", "In2", ["C8"], (1, 0), 0.6, None),                                                     # SCL1, out of the right
    ("B2", "In2", ["B1"], (-1, 0), 0.25, (-0.6, -0.6)),                                           # BCLK: left, then up-left
    ("C2", "In2", ["C1"], (-1, 0), 0.25, (-0.6, 0.6)),                                            # LRCLK: left, then down-left
    ("F2", "In2", ["F1"], (-1, 0), 0.25, (-0.6, 0.6)),                                            # SPK+: left, then down-left
    ("C5", "In2", ["D5", "E5", "F5", "G5"], (0, 1), 0.3, (-0.5, 0.5)),                            # PDMDIN: bottom, fans left
    ("C6", "In3", ["D6", "D5", "E5", "F5", "G5"], (0, 1), 0.8, None),                             # SDA1: straight down
    ("C4", "In4", ["D4", "D5", "E5", "F5", "F6", "G6"], (0, 1), 0.3, (0.65, 0.5)),                # PDMCLK: fans far right
    ("E4", "B", ["E5", "F5", "G5"], (0, 1), 0.3, (0.5, 0.5)),                                     # DAC_ENABLE: fans right
]
U15_TOP = [("B1", (-1, 0), 0.9), ("C1", (-1, 0), 0.9), ("G1", (-1, 0), 0.6), ("F1", (-1, 0), 0.6)]   # top-layer stubs (mm)
PITCH = 0.35
U2_STRIP = float(os.environ.get("HAVEN_U2_STRIP", "0.7"))     # part-free strip below the power chip, mm
# Power chip (U2, 0.4 mm pitch, a via in every ball): inner control balls D3 (SHPHLD) and D4 (SHIP_EN) are boxed in on
# every layer. They leave on In2 under the bottom-row balls E3 / E4, which therefore get no via and leave on the top face.
U2_NO_VIA = {"E3", "E4"}
U2_ESCAPES = [("D3", "In2", ["E3"], (0, 1), 0.3, (-0.4, 0.4)), ("D4", "In2", ["E4"], (0, 1), 0.3, (0.4, 0.4))]


def escape_tracks(board, fp, escapes, pitch):
    """Locked escape tracks for one chip: through the listed ball positions, a straight stub, then a diagonal tail."""
    pos = {p.GetNumber(): p.GetPosition() for p in fp.Pads()}
    net = {p.GetNumber(): p.GetNet() for p in fp.Pads()}
    layer = {"In2": pcbnew.In2_Cu, "In3": pcbnew.In3_Cu, "In4": pcbnew.In4_Cu, "B": pcbnew.B_Cu, "F": pcbnew.F_Cu}
    for ball, lay, through, d, stub, tail in escapes:
        pts = [pos[ball]] + [pos[q] for q in through]
        pts.append(pcbnew.VECTOR2I(int(pts[-1].x + pcbnew.FromMM(stub) * d[0]), int(pts[-1].y + pcbnew.FromMM(stub) * d[1])))
        if tail:
            pts.append(pcbnew.VECTOR2I(int(pts[-1].x + pcbnew.FromMM(tail[0])), int(pts[-1].y + pcbnew.FromMM(tail[1]))))
        for a, c in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board); t.SetStart(a); t.SetEnd(c); t.SetLayer(layer[lay]); t.SetWidth(pcbnew.FromMM(0.09))
            t.SetNet(net[ball]); t.SetLocked(True); board.Add(t)


def u15_escapes(board, fp, ni):
    pos = {p.GetNumber(): p.GetPosition() for p in fp.Pads()}
    net = {p.GetNumber(): p.GetNet() for p in fp.Pads()}
    ex = pcbnew.VECTOR2I(pos["A2"].x - pos["A1"].x, pos["A2"].y - pos["A1"].y)      # one pitch along a row
    ey = pcbnew.VECTOR2I(pos["B1"].x - pos["A1"].x, pos["B1"].y - pos["A1"].y)      # one pitch down a column
    layer = {"In2": pcbnew.In2_Cu, "In3": pcbnew.In3_Cu, "In4": pcbnew.In4_Cu, "B": pcbnew.B_Cu, "F": pcbnew.F_Cu}

    def off(p, d, k):
        return pcbnew.VECTOR2I(int(p.x + (ex.x * d[0] + ey.x * d[1]) * k), int(p.y + (ex.y * d[0] + ey.y * d[1]) * k))

    def track(a, c, lay, n, w=0.09):
        t = pcbnew.PCB_TRACK(board); t.SetStart(a); t.SetEnd(c); t.SetLayer(layer[lay]); t.SetWidth(pcbnew.FromMM(w))
        t.SetNet(n); t.SetLocked(True); board.Add(t)

    escape_tracks(board, fp, U15_ESCAPES, PITCH)
    for ball, d, stub in U15_TOP:
        end = off(pos[ball], d, stub / PITCH)
        track(pos[ball], end, "F", net[ball])
        if ball == "F1":                                  # ground via outside the chip, clear of the SPK+ stub end below it
            end2 = off(pos[ball], d, 1.15 / PITCH)
            track(end, end2, "F", net[ball]); end = end2
            via = pcbnew.PCB_VIA(board); via.SetPosition(end); via.SetNet(net[ball]); via.SetLocked(True)
            via.SetDrill(pcbnew.FromMM(b.FAN_DRILL)); via.SetWidth(pcbnew.FromMM(b.FAN_D)); board.Add(via)
    track(pos["D6"], pos["D7"], "F", net["D6"])           # D6 shares D7's ground via
    track(pos["B3"], pos["A3"], "F", net["B3"])           # the two DVDD balls
    # V_LS pour on In4 under and around the chip: the inner V_LS balls and the nearby capacitors tie into it
    c = fp.GetPosition(); cx, cy = b.dxf(c)
    # Every other V_LS pad (capacitors, load switch, mic supply) gets a filled via in the pad down to the same pour,
    # and the pour is sized to reach them all. Attempts 1-4 left V_LS in fragments when this was left to the router.
    xs, ys = [cx - 2.6, cx + 2.6], [cy - 2.4, cy + 2.4]
    for f in board.GetFootprints():
        if f.GetReference() == fp.GetReference():
            continue
        for pad in f.Pads():
            if pad.GetNetname() == "/V_LS":
                px, py = b.dxf(pad.GetPosition())
                xs += [px - 0.5, px + 0.5]; ys += [py - 0.5, py + 0.5]
                if max(pad.GetSize().x, pad.GetSize().y) < pcbnew.FromMM(0.45):
                    continue          # attempt 5 lesson: a via in every small pad walls the chip in on all layers
                via = pcbnew.PCB_VIA(board); via.SetPosition(pad.GetPosition()); via.SetNet(pad.GetNet())
                via.SetDrill(pcbnew.FromMM(b.FAN_DRILL)); via.SetWidth(pcbnew.FromMM(b.FAN_D)); board.Add(via)
    h, v = b.W / 2 - 0.2, b.L / 2 - 0.2
    x0, x1, y0, y1 = max(min(xs), -h), min(max(xs), h), max(min(ys), -v), min(max(ys), MOD_BOTTOM - 0.2)
    z = b.poly_zone(board, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                    layer=pcbnew.In4_Cu, net=ni["/V_LS"], name="V_LS_UNDER_CODEC")
    z.SetAssignedPriority(5)
    print(f"V_LS pour on In4: x {x0:.1f}..{x1:.1f}, y {y0:.1f}..{y1:.1f} (board-centre mm)")


def main():
    nets, comps = b.netlist()
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(6)
    board.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(b.THICK))
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    ni = {}
    for n in sorted(set(nets.values())):
        x = pcbnew.NETINFO_ITEM(board, n); board.Add(x); ni[n] = x
    b.outline(board)
    fps = {}
    for ref, val, fpname in comps:
        fp = pcbnew.FootprintLoad(b.LIB, fpname)
        fp.SetReference(ref); fp.SetValue(val); fp.SetFPID(pcbnew.LIB_ID("haven_v3_pod", fpname))
        fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
        board.Add(fp)
        for pad in fp.Pads():
            n = nets.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(ni[n])
        fps[ref] = fp

    occ = b.Occupancy()
    for ref, (x, y, rot, side) in FIXED.items():
        b.place_at(fps[ref], x, y, rot, side)
        occ.add(side, b.fp_rect(fps[ref]))
    # keep small parts off the audio chip's top-layer escape stubs, which all leave to the left (the other
    # escapes are on inner layers and do not care what sits above them)
    x0, y0, x1, y1 = b.fp_rect(fps["U15"])
    occ.add("F", (x0 - 1.45, y0, x1, y1))
    # same idea below the power chip: its bottom-row balls E3 / E4 leave on the top face (attempt 5 lesson)
    x0, y0, x1, y1 = b.fp_rect(fps["U2"])
    occ.add("F", (x0, y0 - U2_STRIP, x1, y1))
    # nothing between the module's bottom edge and its body; keep the strips beside the module clear too
    occ.add("F", (-b.W / 2, MOD_BOTTOM, b.W / 2, b.L / 2))

    big = {}
    for (ref, pin), n in nets.items():
        big.setdefault(n, []).append((ref, pin))
    order = []
    for ref, val, fpname in comps:
        if ref in FIXED:
            continue
        sig = sorted([n for (r, p), n in nets.items() if r == ref and n != "/GND"], key=lambda n: len(big[n]))
        order.append((len(big[sig[0]]) if sig else 99, ref, sig))
    PRIO = ("C114", "C112", "C113", "C111", "C110", "C33", "C34", "C41")   # power-path and bulk capacitors get the nearest spots
    order.sort(key=lambda o: (PRIO.index(o[1]) if o[1] in PRIO else 99, o[0], o[1]))
    placed, used, far, failed = set(FIXED), {}, [], []
    for _, ref, sig in order:
        cands = []
        for n in sig:
            for r, p in big[n]:
                if r in placed and r != ref and (r != "U1" or ref in SIDE_B):
                    pad = next(q for q in fps[r].Pads() if q.GetNumber() == p)
                    cands.append((IC_ORDER.index(r) if r in IC_ORDER else 50, used.get((r, p), 0), r, p, pad))
            if cands:
                break
        if not cands:
            cands = [(0, 0, "U15", "", fps["U15"].Pads()[0])]
        cands.sort(key=lambda c: (c[0] >= 50, c[1], c[0]))
        _, _, r, p, pad = cands[0]
        used[(r, p)] = used.get((r, p), 0) + 1
        ax, ay = b.dxf(pad.GetPosition())
        fp = fps[ref]
        for k in range(1, 6000):
            rad, ang = 0.15 * k ** 0.5 * 1.6, k * 2.39996
            x, y = ax + rad * math.cos(ang), ay + rad * math.sin(ang)
            ok = False
            for rot in (0, 90):
                side = "B" if ref in SIDE_B else "F"
                b.place_at(fp, x, y, rot, side)
                rr = b.fp_rect(fp)
                if b.allowed(side, rr) and occ.free(side, rr) and (side == "F" or rr[1] > CELL_TOP + 0.3):
                    occ.add(side, rr); ok = True
                    break
            if ok:
                break
        else:
            b.place_at(fp, 8.0 + 1.2 * (len(failed) % 3), -2.0 * (len(failed) // 3), 0, "F")   # parked off the board
            failed.append(ref)
            continue
        placed.add(ref)
        far.append((round(rad, 2), ref, r))

    # fan-out: a 0.15 / 0.25 mm via in every connected ball of the audio and power chips (filled and capped at fab),
    # except the audio-chip balls in U15_NO_VIA (see escape plan below)
    for ref in ("U15", "U2"):
        for pad in fps[ref].Pads():
            n = pad.GetNetname()
            if n and not n.startswith("unconnected") and not (ref == "U15" and pad.GetNumber() in U15_NO_VIA) \
                    and not (ref == "U2" and pad.GetNumber() in U2_NO_VIA):
                via = pcbnew.PCB_VIA(board); via.SetPosition(pad.GetPosition())
                via.SetDrill(pcbnew.FromMM(b.FAN_DRILL)); via.SetWidth(pcbnew.FromMM(b.FAN_D)); via.SetNet(pad.GetNet())
                board.Add(via)
    u15_escapes(board, fps["U15"], ni)
    escape_tracks(board, fps["U2"], U2_ESCAPES, 0.4)

    h, v = b.W / 2, b.L / 2
    for l in (pcbnew.In1_Cu, pcbnew.In4_Cu, pcbnew.B_Cu, pcbnew.F_Cu):
        gz = b.poly_zone(board, [(-h + 0.2, -v + 0.2), (h - 0.2, -v + 0.2), (h - 0.2, b.ANT_Y), (-h + 0.2, b.ANT_Y)], layer=l, net=ni["/GND"])
        gz.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    b.poly_zone(board, [(-h, b.ANT_Y), (h, b.ANT_Y), (h, v), (-h, v)], layers=b.copper_layers(),
                rule=dict(Tracks=True, Vias=True, Pads=False, CopperPour=True, Footprints=False), name="ANTENNA_KEEPOUT")
    b.poly_zone(board, [(-h, -v), (h, -v), (h, CELL_TOP), (-h, CELL_TOP)], layer=pcbnew.B_Cu,
                rule=dict(Footprints=True, Vias=False, Tracks=False, Pads=False, CopperPour=False), name="CELL_AREA_NO_PARTS")
    board.Save(b.PCB)

    p = os.path.join(b.PRJ, "haven_v3_pod.kicad_pro")
    d = json.load(open(p))
    ds = d.setdefault("board", {}).setdefault("design_settings", {})
    ds.setdefault("rules", {}).update(
        min_clearance=b.CLR, min_track_width=0.09, min_via_diameter=b.FAN_D, min_via_annular_width=0.05,
        min_through_hole_diameter=b.FAN_DRILL, min_hole_clearance=0.15, min_hole_to_hole=0.2,
        min_copper_edge_clearance=0.2, min_connection=0.09)
    ns = d.setdefault("net_settings", {})
    base = ns.setdefault("classes", [{"name": "Default"}])[0]
    base.update(clearance=b.CLR, track_width=b.TRACK, via_diameter=b.VIA_D, via_drill=b.VIA_DRILL)
    ns["classes"] = [base] + [dict(base, name=k, track_width=v_["track"], priority=i) for i, (k, v_) in enumerate(b.NETCLASS.items())]
    ns["netclass_patterns"] = [{"netclass": k, "pattern": n} for k, v_ in b.NETCLASS.items() for n in v_["nets"]]
    json.dump(d, open(p, "w"), indent=2)
    far.sort(reverse=True)
    area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in occ.rects["F"][:-1] if r[1] < MOD_BOTTOM)
    free = (b.W - 2 * b.EDGE) * (MOD_BOTTOM - b.EDGE + b.L / 2 - b.EDGE)
    print(f"placed {len(fps) - len(failed)} of {len(fps)} parts; NO ROOM for {failed}; wrote", b.PCB)
    print(f"footprint area on the top face below the module: {area:.0f} mm2 of {free:.0f} mm2")
    print("furthest from the pad they serve (mm, part, anchor):", far[:8])


if __name__ == "__main__":
    if os.environ.get("HAVEN_FORCE_REGEN") != "1":
        sys.exit("refusing to overwrite the routed v3 board: set HAVEN_FORCE_REGEN=1 (read the docstring first)")
    main()

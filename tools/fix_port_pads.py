"""Correct two defects in the EasyEDA->KiCad port's pads (extracted/gen_pcb.py).

1. Pad shapes were never rotated: neither the pad's own angle nor the
   component's rotation was applied, so rectangular/oval pads on parts at
   90/270 degrees pointed the wrong way.
2. Back-layer parts were never mirrored. EasyEDA mirrors a bottom-side
   footprint across its local X axis before rotating; the port skipped that,
   so asymmetric bottom parts (charger, mic, USB-C, crystal...) had pads in
   the wrong places. Verified against routed copper: front 329/0 pad/track
   net matches before and after, back 156/95 before.

Sets absolute pad positions/orientations from the source footprints, so it
is safe to re-run. Usage: python3 tools/fix_port_pads.py <board.kicad_pcb>
"""
import json, math, os, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
EX = os.path.join(HERE, "..", "extracted")
MM = 0.0254  # source units are mil

placement = json.load(open(os.path.join(EX, "pcb_placement.json")))
bom = json.load(open(os.path.join(EX, "bom.json")))


def source_pads(fp_uuid):
    pads = []
    for line in open(os.path.join(EX, "stock_openearable", "FOOTPRINT", f"{fp_uuid}.efoo")):
        line = line.strip()
        if not line.startswith('["PAD"'):
            continue
        d = json.loads(line)
        _, _pid, _flag, _net, _layer, number, x, y, rot, _hole, shape, *_ = d
        pads.append((str(number), x, y, rot or 0, shape[0]))
    return pads


def rot(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


board = pcbnew.LoadBoard(sys.argv[1])
moved = rotated = 0
for fp in board.GetFootprints():
    ref = fp.GetReference()
    if ref not in placement:
        continue
    comp = placement[ref]
    uuid = bom.get(ref, {}).get("footprint") or comp.get("footprint")
    src = source_pads(uuid)
    kpads = list(fp.Pads())
    back = comp["layer"] == 2
    r = comp["rot"] or 0
    c = fp.GetPosition()
    # KiCad sorts pads by number on load, so pair by number; a repeated
    # number (e.g. several GND pads) pairs with the nearest candidate,
    # whichever transform (pre- or post-mirror) it currently sits under.
    pairs = []
    remaining = list(src)
    for pad in kpads:
        cands = [s for s in remaining if s[0] == pad.GetNumber()]
        if not cands:
            break
        dx = pcbnew.ToMM(pad.GetPosition().x - c.x)
        dy = pcbnew.ToMM(pad.GetPosition().y - c.y)
        def dist(s):
            opts = [rot(s[1] * MM, s[2] * MM, r), rot(s[1] * MM, -s[2] * MM, r)]
            return min(math.hypot(dx - ox, dy - oy) for ox, oy in opts)
        best = min(cands, key=dist)
        remaining.remove(best)
        pairs.append((best, pad))
    if len(pairs) != len(kpads) or remaining:
        print(f"skip {ref}: pad numbers differ from source")
        continue
    for (num, x, y, prot, kind), pad in pairs:
        ly = -y if back else y
        a = (r - prot) if back else (r + prot)
        if back:
            X, Y = rot(x * MM, ly * MM, r)
            pad.SetPosition(pcbnew.VECTOR2I(c.x + pcbnew.FromMM(X), c.y + pcbnew.FromMM(Y)))
            moved += 1
        # the port's frame is y-down with math-positive angles, which is
        # clockwise on screen; KiCad orientations are counterclockwise.
        target = (-a) % 360
        if kind != "ELLIPSE" or pad.GetShape() == pcbnew.PAD_SHAPE_OVAL:
            if abs(pad.GetOrientationDegrees() % 360 - target) > 1e-6:
                rotated += 1
            pad.SetOrientationDegrees(target)
pcbnew.SaveBoard(sys.argv[1], board)
print(f"back-side pads moved: {moved}, pad orientations changed: {rotated}")

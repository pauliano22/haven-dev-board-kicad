"""2026-11-18 review fixes (Vector / Claude review of the v3 pod board):
remove two dead-end stubs, enlarge U2/U3 pads to 0.25 mm, add BAT+/BAT- silk labels, add courtyards to
footprints that had none. Usage: python3 review_fix.py IN.kicad_pcb OUT.kicad_pcb"""
import sys, pcbnew
IN, OUT = sys.argv[1], sys.argv[2]
b = pcbnew.LoadBoard(IN)
MM = pcbnew.FromMM
# 1. dead-end stubs (far ends touch nothing; checked 2026-11-18)
for net, lay, a, c in (("/SCL1", "In2.Cu", (102.425, 104.95), (102.425, 102.627)),
                       ("/XTALO", "F.Cu", (102.584, 100.943), (103.179, 100.347))):
    L = b.GetLayerID(lay); hit = None
    for t in b.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetNetname() == net and t.GetLayer() == L:
            s, e = (t.GetStart().x / 1e6, t.GetStart().y / 1e6), (t.GetEnd().x / 1e6, t.GetEnd().y / 1e6)
            if {tuple(round(v, 2) for v in s), tuple(round(v, 2) for v in e)} == {tuple(round(v, 2) for v in a), tuple(round(v, 2) for v in c)}:
                hit = t
    assert hit is not None, net
    b.Remove(hit)
# 1b. the rest of the dead XTALO branch: after the stub above goes, the run from (102.584, 100.943) down to the
#     junction at (103.201, 104.381) leads nowhere (XTALO only joins R28.2 and U15.B6). Shorter oscillator net.
dead = [((102.5836,100.9428),(102.5836,101.5428)),((102.5836,101.5428),(102.6336,101.5928)),((102.6336,101.5928),(102.6336,101.7928)),
        ((102.6336,101.7928),(102.6836,101.8428)),((102.6836,101.8428),(102.6836,102.7928)),((102.6836,102.7928),(102.7336,102.8428)),
        ((102.7336,102.8428),(102.7336,102.8928)),((102.7336,102.8928),(102.6836,102.9428)),((102.6836,102.9428),(102.6836,103.8928)),
        ((102.6836,103.8928),(103.1836,104.3928)),((103.1836,104.3928),(103.201,104.381))]
key = lambda a, c: frozenset({(round(a[0], 3), round(a[1], 3)), (round(c[0], 3), round(c[1], 3))})
want = {key(a, c) for a, c in dead}
gone = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() == "/XTALO" and
        key((t.GetStart().x / 1e6, t.GetStart().y / 1e6), (t.GetEnd().x / 1e6, t.GetEnd().y / 1e6)) in want]
assert len(gone) == len(dead), len(gone)
for t in gone:
    b.Remove(t)
# 2. U2 (nPM1100, ball 0.195-0.255) and U3 (AP22916, Diodes suggests 0.24) pads to 0.25 mm
for ref in ("U2", "U3"):
    for p in b.FindFootprintByReference(ref).Pads():
        p.SetSize(pcbnew.VECTOR2I(MM(0.25), MM(0.25)))
# 2b. U3's bigger A2 pad came 0.073 mm from the SENSORS_ENABLE via (rule 0.10): move that via 0.05 mm away diagonally and
#     carry its track ends with it.
old = pcbnew.VECTOR2I_MM(104.15, 107.75); new = pcbnew.VECTOR2I_MM(104.20, 107.80)   # still inside its own pad B2 (ON), >= 0.12 mm from A2 and B1
for t in b.GetTracks():
    if t.GetNetname() != "/SENSORS_ENABLE":
        continue
    if t.GetClass() == "PCB_VIA" and (t.GetPosition() - old).EuclideanNorm() < 2000:
        t.SetPosition(new)
    elif t.GetClass() == "PCB_TRACK":
        if (t.GetStart() - old).EuclideanNorm() < 2000: t.SetStart(new)
        if (t.GetEnd() - old).EuclideanNorm() < 2000: t.SetEnd(new)
# 2c. two 0201 pad gaps under JLCPCB's 0.15 mm guideline (C32.2-C114.1 0.142, R5.1-C114.1 0.144): trim the small
#     pad 0.02 mm on the facing side (size -0.02, centre 0.01 away) -> 0.162 / 0.164 mm. Tracks still end inside.
for ref, num, axis, sign in (("C32", "2", "x", -1), ("R5", "1", "y", -1)):
    p = [q for q in b.FindFootprintByReference(ref).Pads() if q.GetNumber() == num][0]
    sz = p.GetSize(); rot = round(p.GetOrientationDegrees()) % 180
    local_x = (axis == "x") == (rot == 0)          # which local size axis lies along the board axis
    p.SetSize(pcbnew.VECTOR2I(sz.x - MM(0.02), sz.y) if local_x else pcbnew.VECTOR2I(sz.x, sz.y - MM(0.02)))
    pos = p.GetPosition()
    p.SetPosition(pcbnew.VECTOR2I(pos.x + sign * MM(0.01), pos.y) if axis == "x" else pcbnew.VECTOR2I(pos.x, pos.y + sign * MM(0.01)))
# 2d. L2's courtyard was body + 0.25 mm; use body + 0.10 like the rest (body 2.0 x 1.6, same extent as its pads).
l2 = b.FindFootprintByReference("L2"); c = l2.GetPosition()
for g in list(l2.GraphicalItems()):
    if g.GetLayer() in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
        l2.Remove(g)
r2 = pcbnew.PCB_SHAPE(l2); r2.SetShape(pcbnew.SHAPE_T_RECT); r2.SetLayer(pcbnew.F_CrtYd); r2.SetWidth(MM(0.05))
r2.SetStart(pcbnew.VECTOR2I(c.x - MM(1.1), c.y - MM(0.9))); r2.SetEnd(pcbnew.VECTOR2I(c.x + MM(1.1), c.y + MM(0.9)))
r2.thisown = 0; l2.Add(r2)
# 3. battery polarity on the bottom silk, above TP8 (VBAT) / TP9 (GND)
for ref, txt, dx in (("TP8", "BAT+", -0.35), ("TP9", "BAT-", 0.35)):
    f = b.FindFootprintByReference(ref); p = f.GetPosition()
    t = pcbnew.PCB_TEXT(b); t.SetText(txt); t.SetLayer(pcbnew.B_SilkS); t.SetMirrored(True)
    t.SetTextSize(pcbnew.VECTOR2I(MM(0.65), MM(0.8))); t.SetTextThickness(MM(0.15))
    t.SetPosition(pcbnew.VECTOR2I(p.x + MM(dx), p.y - MM(1.45))); b.Add(t)
# 4. courtyards: pad (and fab body) bounding box + 0.05 mm, on the footprint's side
added = []; keep = []
fps = list(b.GetFootprints())
need = [f for f in fps if f.Pads() and not any(g.GetLayer() in (pcbnew.F_CrtYd, pcbnew.B_CrtYd) for g in f.GraphicalItems())]
for f in need:
    boxes = [p.GetBoundingBox() for p in f.Pads()]
    fab = pcbnew.F_Fab if f.GetLayer() == pcbnew.F_Cu else pcbnew.B_Fab
    boxes += [g.GetBoundingBox() for g in f.GraphicalItems() if g.GetLayer() == fab and g.GetClass() == "PCB_SHAPE"]
    x0 = min(q.GetLeft() for q in boxes); x1 = max(q.GetRight() for q in boxes)
    y0 = min(q.GetTop() for q in boxes); y1 = max(q.GetBottom() for q in boxes)
    assert x1 - x0 < MM(15) and y1 - y0 < MM(15), f.GetReference()
    m = MM(0.05)
    r = pcbnew.PCB_SHAPE(f); r.SetShape(pcbnew.SHAPE_T_RECT)
    r.SetLayer(pcbnew.F_CrtYd if f.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd); r.SetWidth(MM(0.05))
    r.SetStart(pcbnew.VECTOR2I(x0 - m, y0 - m)); r.SetEnd(pcbnew.VECTOR2I(x1 + m, y1 + m))
    r.thisown = 0; f.Add(r); keep.append(r); added.append(f.GetReference())
# zones are refilled afterwards by kicad-cli (in-script fill/connectivity crashes after Remove)
b.Save(OUT)
print("courtyards added:", len(added))

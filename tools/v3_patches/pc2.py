"""Stage 1b: drop the blind vias, nudge R5, add vias-in-pad only where they clear every layer."""
import os, sys, math, pcbnew
P = os.environ["HAVEN_PCB"]; MM = pcbnew.FromMM; F = pcbnew.F_Cu
b = pcbnew.LoadBoard(P)
pad = lambda ref, num: next(p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num)
blind = [("C114", "2"), ("C110", "2"), ("C113", "2"), ("R115", "2"), ("C32", "2"), ("R9", "1"), ("R9", "2")]
for ref, num in blind:
    q = pad(ref, num).GetPosition()
    for t in list(b.GetTracks()):
        if t.GetClass() == "PCB_VIA" and (t.GetPosition() - q).EuclideanNorm() < MM(0.02): b.Remove(t)
r5 = b.FindFootprintByReference("R5"); o = pad("R5", "1").GetPosition()
for t in list(b.GetTracks()):
    if t.GetClass() == "PCB_VIA" and t.GetNetname() == "/V_LS" and (t.GetPosition() - o).EuclideanNorm() < MM(0.05): b.Remove(t)
    if t.GetClass() == "PCB_TRACK" and t.GetNetname() == "/SDA1" and t.GetLayer() == F: pass
r5.SetPosition(pcbnew.VECTOR2I(r5.GetPosition().x - MM(0.10), r5.GetPosition().y))

def seg_d(p, a, c):
    dx, dy = c.x - a.x, c.y - a.y; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / L))
    return math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy))
def ok(q, net, r=MM(0.125), hole=MM(0.075), clr=MM(0.105)):
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            d = (t.GetPosition() - q).EuclideanNorm()
            if d < MM(0.01): return False
            if d < hole + t.GetDrill() / 2 + MM(0.2): return False
            if t.GetNetname() != net and d < r + t.GetWidth(F) / 2 + clr: return False
        elif t.GetNetname() != net and seg_d(q, t.GetStart(), t.GetEnd()) - t.GetWidth() / 2 < max(r + clr, hole + MM(0.15)): return False
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net: continue
            bb = p.GetBoundingBox(); dx = max(bb.GetLeft() - q.x, 0, q.x - bb.GetRight()); dy = max(bb.GetTop() - q.y, 0, q.y - bb.GetBottom())
            if math.hypot(dx, dy) < max(r + clr, hole + MM(0.15)): return False
    return True
for ref, num in blind + [("R5", "1"), ("R114", "1"), ("C113", "1"), ("C110", "1"), ("C114", "1")]:
    p = pad(ref, num); net = p.GetNetname(); bb = p.GetBoundingBox(); c = p.GetPosition(); best = None
    for ix in range(-12, 13):
        for iy in range(-12, 13):
            q = pcbnew.VECTOR2I(c.x + ix * MM(0.03), c.y + iy * MM(0.03))
            if not (bb.GetLeft() + MM(0.02) <= q.x <= bb.GetRight() - MM(0.02) and bb.GetTop() + MM(0.02) <= q.y <= bb.GetBottom() - MM(0.02)): continue
            if ok(q, net) and (best is None or abs(ix) + abs(iy) < best[0]): best = (abs(ix) + abs(iy), q)
    if best and not (ref in ("R114", "C113", "C110", "C114") and num == "1"):
        v = pcbnew.PCB_VIA(b); v.SetPosition(best[1]); v.SetDrill(MM(0.15)); v.SetWidth(MM(0.25)); v.SetNet(p.GetNet()); b.Add(v)
    print(ref, num, net, "via spot" if best else "NO via spot", (round(best[1].x / 1e6, 3), round(best[1].y / 1e6, 3)) if best else "", flush=True)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.Save(P); sys.stdout.flush(); os._exit(0)

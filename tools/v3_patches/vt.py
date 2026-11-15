import os, sys, math, pcbnew
MM = pcbnew.FromMM; F = pcbnew.F_Cu
def seg_d(p, a, c):
    dx, dy = c.x - a.x, c.y - a.y; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / L))
    return math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy))
def blockers(b, x, y, net, r=0.125, hole=0.075, clr=0.105):
    q = pcbnew.VECTOR2I(MM(x), MM(y)); out = []
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            d = (t.GetPosition() - q).EuclideanNorm() / 1e6
            if d < 0.01: continue
            if d < hole + t.GetDrill() / 2e6 + 0.2: out.append(("hole", t.GetNetname(), round(d, 3)))
            elif t.GetNetname() != net and d < r + t.GetWidth(F) / 2e6 + clr: out.append(("via", t.GetNetname(), round(d, 3)))
        elif t.GetNetname() != net:
            d = seg_d(q, t.GetStart(), t.GetEnd()) / 1e6 - t.GetWidth() / 2e6
            if d < max(r + clr, hole + 0.15): out.append(("trk", t.GetNetname(), t.GetLayerName(), round(d, 3)))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net: continue
            bb = p.GetBoundingBox(); dx = max(bb.GetLeft() - q.x, 0, q.x - bb.GetRight()); dy = max(bb.GetTop() - q.y, 0, q.y - bb.GetBottom())
            d = math.hypot(dx, dy) / 1e6
            if d < max(r + clr, hole + 0.15): out.append(("pad", fp.GetReference() + "." + p.GetNumber(), round(d, 3)))
    return out
if __name__ == "__main__":
    b = pcbnew.LoadBoard(os.environ["HAVEN_PCB"])
    net = sys.argv[1]
    for a in sys.argv[2:]:
        x, y = map(float, a.split(","))
        print(a, blockers(b, x, y, net))
    sys.stdout.flush(); os._exit(0)

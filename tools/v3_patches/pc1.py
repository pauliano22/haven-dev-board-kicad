"""Power-corner re-placement, stage 1 (2026-11-14): move parts, rip what is in the way, hand-route SW and the L2-C114 link."""
import os, sys, math, re, subprocess, pcbnew
sys.path.insert(0, os.path.expanduser("~/projects/active/haven_workspace/hardware_kicad/tools"))
import fix_v2_pod_pcb as fx
P = os.environ["HAVEN_PCB"]; W = os.environ["HAVEN_WORK"]; MM = pcbnew.FromMM
b = pcbnew.LoadBoard(P)
F = pcbnew.F_Cu
MOVES = {  # ref: (x, y, rot or None)
    "L2": (102.40, 107.95, 180), "R9": (103.02, 106.79, None), "C114": (100.88, 108.52, None), "C32": (100.01, 107.65, None),
    "R115": (100.03, 108.54, None), "R114": (100.25, 109.35, None), "C110": (101.33, 110.65, None), "C113": (100.25, 110.85, None),
}
WANT_TOP = {"C114": "1", "C110": "1", "C113": "1"}      # pad that must be at the top (smaller y)
old = {}
for ref, (x, y, rot) in MOVES.items():
    fp = b.FindFootprintByReference(ref)
    old[ref] = [(p.GetNumber(), p.GetNetname(), pcbnew.VECTOR2I(p.GetPosition()), p.GetBoundingBox()) for p in fp.Pads()]
    fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    if rot is not None: fp.SetOrientationDegrees(rot)
    if ref in WANT_TOP:
        fp.SetOrientationDegrees(90)
        pd = {p.GetNumber(): p for p in fp.Pads()}
        other = [k for k in pd if k != WANT_TOP[ref]][0]
        if pd[WANT_TOP[ref]].GetPosition().y > pd[other].GetPosition().y: fp.SetOrientationDegrees(270)
    print(ref, [(p.GetNumber(), p.GetNetname(), round(p.GetPosition().x / 1e6, 3), round(p.GetPosition().y / 1e6, 3)) for p in fp.Pads()], flush=True)
l2 = b.FindFootprintByReference("L2")
for g in l2.GraphicalItems():
    if g.GetLayer() == pcbnew.F_CrtYd and g.GetClass() == "PCB_SHAPE":
        c = l2.GetPosition(); g.SetStart(pcbnew.VECTOR2I(c.x - MM(1.25), c.y - MM(1.0))); g.SetEnd(pcbnew.VECTOR2I(c.x + MM(1.25), c.y + MM(1.0)))

def rect_dist(q, bb):
    dx = max(bb.GetLeft() - q.x, 0, q.x - bb.GetRight()); dy = max(bb.GetTop() - q.y, 0, q.y - bb.GetBottom())
    return math.hypot(dx, dy)
def seg_rect(a, c, bb):          # sampled distance from a segment to a rectangle
    n = max(2, int((a - c).EuclideanNorm() / MM(0.03)) + 1)
    return min(rect_dist(pcbnew.VECTOR2I(int(a.x + (c.x - a.x) * i / n), int(a.y + (c.y - a.y) * i / n)), bb) for i in range(n + 1))
newpads = [(p, p.GetBoundingBox()) for ref in MOVES for p in b.FindFootprintByReference(ref).Pads()]
rm = set(); why = {}
def kill(t, r):
    rm.add(t.m_Uuid.AsString()); why.setdefault(r, []).append((t.GetNetname(), t.GetClass()))
RIPNETS = {"/SW", "/VBUS_DET"}
win = lambda p: p.x / 1e6 >= 98.4 and p.y / 1e6 >= 106.4
for t in b.GetTracks():
    net = t.GetNetname(); via = t.GetClass() == "PCB_VIA"
    pts = [t.GetPosition()] if via else [t.GetStart(), t.GetEnd()]
    if net in RIPNETS and any(win(q) for q in pts): kill(t, "ripnet"); continue
    if net == "/+1V8" and any(win(q) for q in pts) and (not via or t.GetWidth(F) < MM(0.3)) and (via or t.GetLayer() == F):
        # top-layer +1V8 copper and small vias in the corner (inner-layer web stays); via-in-ball B5 is kept below
        if not (via and abs(pts[0].x / 1e6 - 103.7) < .02 and abs(pts[0].y / 1e6 - 109.8) < .02): kill(t, "1v8 top"); continue
    # touches an old pad of a moved part
    for ref, pads in old.items():
        for num, pnet, pos, bb in pads:
            if pnet == net and ((via and rect_dist(pts[0], bb) < MM(0.01)) or (not via and t.GetLayer() == F and any(rect_dist(q, bb) < MM(0.01) for q in pts))):
                kill(t, "old pad")
    # collides with a new pad
    for p, bb in newpads:
        if via:
            d = rect_dist(pts[0], bb) - t.GetWidth(F) / 2
            if p.GetNetname() != net and d < MM(0.11): kill(t, "new pad clash")
        elif t.GetLayer() == F:
            d = seg_rect(pts[0], pts[1], bb) - t.GetWidth() / 2
            if p.GetNetname() != net and d < MM(0.11): kill(t, "new pad clash")
# explicit
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        q = (round(t.GetPosition().x / 1e6, 2), round(t.GetPosition().y / 1e6, 2))
        if (t.GetNetname(), q) in {("/VBUS", (99.88, 109.42)), ("/DEC", (101.19, 109.45)), ("/V_LS", (102.78, 107.14)), ("/SCL1", (102.78, 107.6))}: kill(t, "explicit")
    elif t.GetNetname() in ("/VBAT", "/VBUS", "/DEC", "/SCL1", "/V_LS") and t.GetLayer() == F and all(win(q) for q in (t.GetStart(), t.GetEnd())) and t.GetStart().x / 1e6 < 103.5:
        kill(t, "explicit F")
n = 0
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString() in rm: b.Remove(t); n += 1
print("removed", n, {k: len(v) for k, v in why.items()}, flush=True)

def track(net, pts, w, layer=F):
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1]))); t.SetEnd(pcbnew.VECTOR2I(MM(c[0]), MM(c[1])))
        t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNet(b.FindNet(net)); b.Add(t)
def via(net, x, y, small=True):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); v.SetDrill(MM(0.15 if small else 0.2)); v.SetWidth(MM(0.25 if small else 0.35))
    v.SetNet(b.FindNet(net)); b.Add(v)
pp = lambda ref, num: next(p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num).GetPosition()
xy = lambda q: (q.x / 1e6, q.y / 1e6)
a4 = xy(pp("U2", "A4")); l1 = xy(pp("L2", "1")); l22 = xy(pp("L2", "2")); c1 = xy(pp("C114", "1")); b1 = xy(pp("U2", "B1")); v1 = xy(pp("C110", "1"))
track("/SW", [a4, (a4[0], 108.55)], 0.2)
track("/+1V8", [l22, (c1[0], l22[1])], 0.5)
track("/VBUS", [b1, (v1[0], b1[1])], 0.2)
# vias in the pads of moved parts
for ref, num, net in (("C114", "2", "/GND"), ("C110", "2", "/GND"), ("C113", "2", "/GND"), ("R115", "2", "/GND"), ("C32", "2", "/GND"), ("R9", "1", "/V_LS"), ("R9", "2", "/SCL1")):
    q = xy(pp(ref, num)); via(net, q[0], q[1])
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.Save(P)
sys.stdout.flush(); os._exit(0)

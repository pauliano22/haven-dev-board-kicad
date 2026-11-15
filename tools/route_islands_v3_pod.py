#!/usr/bin/env python3
"""Finish open connections that route_rest_v2_pod.py cannot, by trying other attachment points.

route_rest only tries the one pair of points DRC names for each open connection. On a dense board that
point is often boxed in while another pad, via or track end of the SAME piece of copper is free. This script
collects every attachment point of the two disconnected pieces and tries the closest pairs in turn.

    HAVEN_PCB=... HAVEN_WORK=... HAVEN_HEUR_W=2.0 python3 tools/route_islands_v3_pod.py [/NET ...]
"""
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402

import fix_v2_pod_pcb as fx  # noqa: E402
import multilayer_route as mr  # noqa: E402
import route_rest_v2_pod as rr  # noqa: E402

TOL = pcbnew.FromMM(0.01)
MAX_TRIES = int(os.environ.get("HAVEN_TRIES", "14"))


def mm(p):
    return (round(pcbnew.ToMM(p.x), 4), round(pcbnew.ToMM(p.y), 4))


def seg_dist(p, a, c):
    ax, ay, cx, cy, px, py = a.x, a.y, c.x, c.y, p.x, p.y
    dx, dy = cx - ax, cy - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


class Net:
    """Pads, vias and tracks of one net, grouped into pieces of touching copper (zones ignored)."""

    def __init__(self, b, net):
        self.items = []          # (kind, obj)
        for fp in b.GetFootprints():
            for p in fp.Pads():
                if p.GetNetname() == net:
                    self.items.append(("pad", p))
        for t in b.GetTracks():
            if t.GetNetname() == net:
                self.items.append(("via" if t.GetClass() == "PCB_VIA" else "track", t))
        n = len(self.items)
        self.parent = list(range(n))
        for i in range(n):
            for j in range(i + 1, n):
                if self.touch(self.items[i], self.items[j]):
                    self.union(i, j)

    def find(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, i, j):
        self.parent[self.find(i)] = self.find(j)

    @staticmethod
    def on_layer(item, layer):
        kind, o = item
        if kind == "via":
            return True
        if kind == "pad":
            return o.IsOnLayer(layer)
        return o.GetLayer() == layer

    def touch(self, x, y):
        (kx, a), (ky, c) = x, y
        if kx == "track" and ky == "track":
            if a.GetLayer() != c.GetLayer():
                return False
            w = (a.GetWidth() + c.GetWidth()) / 2
            return any(seg_dist(p, c.GetStart(), c.GetEnd()) < w / 2 + TOL for p in (a.GetStart(), a.GetEnd())) or \
                any(seg_dist(p, a.GetStart(), a.GetEnd()) < w / 2 + TOL for p in (c.GetStart(), c.GetEnd()))
        if kx == "track" or ky == "track":
            t, other = (x, y) if kx == "track" else (y, x)
            if not self.on_layer(other, t[1].GetLayer()):
                return False
            o = other[1]
            if other[0] == "via":
                return seg_dist(o.GetPosition(), t[1].GetStart(), t[1].GetEnd()) < pcbnew.FromMM(0.125) + TOL
            return o.HitTest(t[1].GetStart()) or o.HitTest(t[1].GetEnd())
        if kx == "via" and ky == "via":
            return (a.GetPosition() - c.GetPosition()).EuclideanNorm() < pcbnew.FromMM(0.2)
        v, p = (a, c) if kx == "via" else (c, a)
        if kx == ky:        # two pads
            return False
        return p.HitTest(v.GetPosition())

    def piece_of(self, pt, layer):
        """Index of the piece owning the item DRC named by position pt (mm) on layer (None = via)."""
        q = pcbnew.VECTOR2I_MM(*pt)
        best = None
        for i, (kind, o) in enumerate(self.items):
            if kind == "track":
                d = min((o.GetStart() - q).EuclideanNorm(), (o.GetEnd() - q).EuclideanNorm())
                ok = layer is not None and o.GetLayer() == layer
            elif kind == "via":
                d = (o.GetPosition() - q).EuclideanNorm(); ok = True
            else:
                d = 0 if o.HitTest(q) else (o.GetPosition() - q).EuclideanNorm(); ok = layer is None or o.IsOnLayer(layer)
            if ok and d < pcbnew.FromMM(0.05) and (best is None or d < best[0]):
                best = (d, i)
        return None if best is None else self.find(best[1])

    def points(self, piece):
        """Attachment points of a piece: (xy mm, layers or None for any)."""
        out = {}
        has_via = set()
        for i, (kind, o) in enumerate(self.items):
            if self.find(i) == piece and kind == "via":
                has_via.add(mm(o.GetPosition()))
        for i, (kind, o) in enumerate(self.items):
            if self.find(i) != piece:
                continue
            if kind == "via":
                out[mm(o.GetPosition())] = None
            elif kind == "pad":
                p = mm(o.GetPosition())
                if p not in has_via:
                    out.setdefault(p, [pcbnew.B_Cu if o.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu])
            else:
                for e in (o.GetStart(), o.GetEnd()):
                    p = mm(e)
                    if p not in has_via and out.get(p, 0) is not None:
                        out.setdefault(p, [o.GetLayer()])
        return list(out.items())


def main():
    rep = rr.drc()
    todo = rr.pairs(rep)
    want = sys.argv[1:]
    if want:
        todo = sorted((t for t in todo if t[0] in want), key=lambda t: want.index(t[0]))    # route in the order given
    b = pcbnew.LoadBoard(rr.PCB)
    print(len(todo), "pairs:", " ".join(t[0] for t in todo), flush=True)
    failed = []
    for net, s, e, son, eon in todo:
        nn = Net(b, net)                       # rebuilt each time: earlier routes change the pieces
        ps = nn.piece_of(s, son[0] if son else None)
        pe = nn.piece_of(e, eon[0] if eon else None)
        if ps is None or pe is None:
            print("  skip", net, "cannot find the copper DRC named", flush=True); failed.append(net); continue
        if ps == pe:
            print("  already joined", net, flush=True); continue
        S, E = nn.points(ps), nn.points(pe)
        combos = sorted(((math.hypot(a[0][0] - c[0][0], a[0][1] - c[0][1]), a, c) for a in S for c in E), key=lambda t: t[0])
        done = False
        for k, (d, (a, la), (c, lc)) in enumerate(combos[:MAX_TRIES]):
            margin = 1.5 if d < 6 else 2.5
            path, why = mr.multilayer_astar(b, net, a, c, rr.CLR_MM, cell=0.05, margin=margin,
                                            max_iters=400000 if d < 6 else 1500000, start_on=la, end_on=lc)
            if path is not None:
                rr.commit(b, net, path, a, c)
                print(f"  routed {net} try {k + 1} of {len(combos)}: {a} -> {c}, {d:.1f} mm apart", flush=True)
                done = True
                break
        if not done:
            # boxed-in pads: drill a filled 0.15 / 0.25 via into the pad and leave on an inner layer
            added = []
            for pts in (S, E):
                for i, (xy, lay) in enumerate(pts):
                    if lay is None:
                        continue
                    pad = rr.pad_at(b, net, xy)
                    if pad is not None and mm(pad.GetPosition()) == xy and fx.Obstacles(b).via_ok(pad.GetPosition(), pad):
                        v = pcbnew.PCB_VIA(b); v.SetPosition(pad.GetPosition()); v.SetDrill(pcbnew.FromMM(0.15))
                        v.SetWidth(pcbnew.FromMM(0.25)); v.SetNet(b.FindNet(net)); b.Add(v)
                        added.append((v, xy)); pts[i] = (xy, None)
            if added:
                combos = sorted(((math.hypot(a[0][0] - c[0][0], a[0][1] - c[0][1]), a, c) for a in S for c in E
                                 if a[1] is None or c[1] is None), key=lambda t: t[0])
                for k, (d, (a, la), (c, lc)) in enumerate(combos[:MAX_TRIES]):
                    path, why = mr.multilayer_astar(b, net, a, c, rr.CLR_MM, cell=0.05, margin=1.5 if d < 6 else 2.5,
                                                    max_iters=400000 if d < 6 else 1500000, start_on=la, end_on=lc)
                    if path is not None:
                        rr.commit(b, net, path, a, c)
                        print(f"  routed {net} with via-in-pad: {a} -> {c}, {d:.1f} mm apart", flush=True)
                        done = True
                        for v, xy in added:          # keep only the vias the route uses
                            if xy not in (a, c):
                                b.Remove(v)
                        break
                if not done:
                    for v, _ in added:
                        b.Remove(v)
        if not done:
            print(f"  FAIL {net}: {min(MAX_TRIES, len(combos))} point pairs tried ({len(S)} x {len(E)} available), last: {why}", flush=True)
            failed.append(net)
    b.Save(rr.PCB)
    b = pcbnew.LoadBoard(rr.PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(rr.PCB)
    kinds = {}
    for m in re.findall(r"^\[(\w+)\]", rr.drc(), re.M):
        kinds[m] = kinds.get(m, 0) + 1
    print("DRC now:", kinds, "| not routed:", failed, flush=True)
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()

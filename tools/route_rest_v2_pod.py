#!/usr/bin/env python3
"""Route the connections Freerouting left open on the pod board, one at a time.

Reads the unconnected pairs from the latest DRC report, runs the multi-layer A* in
multilayer_route.py (F.Cu, In2, In3, In4, B.Cu; In1 stays a solid GND plane) with this board's
rules, writes tracks and vias, then refills and re-runs DRC. Pairs it can't route are listed.

    python3 tools/route_rest_v2_pod.py
"""
import math
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402

import fix_v2_pod_pcb as fx  # noqa: E402
import multilayer_route as mr  # noqa: E402
import route_lib as rl  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PCB = os.path.join(ROOT, "kicad_v2_pod", "haven_v2_pod.kicad_pcb")
WORK = os.path.expanduser("~/.cache/haven_builds/pod_pcb")

mr.LAYERS = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu]
mr.VIA_R_MM = 0.175                 # 0.35 mm routing via
rl.VIA_DRILL_R_MM = 0.10            # 0.2 mm drill
rl.MIN_HOLE_EDGE_MM = 0.2           # hole-to-hole
TRACK_MM, CLR_MM = 0.09, 0.105
LAYER_ID = {"F.Cu": pcbnew.F_Cu, "In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu, "In3.Cu": pcbnew.In3_Cu,
            "In4.Cu": pcbnew.In4_Cu, "B.Cu": pcbnew.B_Cu}      # a hair over the 0.10 rule, for rounding


def drc():
    rpt = os.path.join(WORK, "drc.rpt")
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "--severity-warning", "-o", rpt, PCB],
                   check=False, stdout=subprocess.DEVNULL)
    return open(rpt).read()


def pairs(rep):
    out = []
    for block in rep.split("\n[")[1:]:
        if not block.startswith("unconnected_items"):
            continue
        pts = re.findall(r"@\(([-\d.]+) mm, ([-\d.]+) mm\): (\w+).*?\[(/[^\]]+)\](?: of \S+)? on ([\w.]+)( - [\w.]+)?", block)
        if len(pts) == 2 and pts[0][3] == pts[1][3] and pts[0][3] != "/GND":
            on = [None if p[5] else [LAYER_ID[p[4]]] for p in pts]   # a via ("F.Cu - B.Cu") works on any layer
            out.append((pts[0][3], (float(pts[0][0]), float(pts[0][1])), (float(pts[1][0]), float(pts[1][1])), on[0], on[1]))
    return out


def pad_at(b, net, pt):
    q = pcbnew.VECTOR2I_MM(*pt)
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net and p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD and p.HitTest(q):
                return p
    return None


def commit(b, net, path, s, e):
    ni = b.FindNet(net)
    pts = [(p["pt"], p["layer"]) for p in path]
    # the A* works on a grid; pin both ends to the exact pad / track-end points
    pts = [(tuple(s), pts[0][1])] + pts + [(tuple(e), pts[-1][1])]
    # collapse collinear runs on the same layer
    simp = [pts[0]]
    for i in range(1, len(pts) - 1):
        (a, la), (c, lc), (d, ld) = simp[-1], pts[i], pts[i + 1]
        if la == lc == ld and abs((c[0] - a[0]) * (d[1] - a[1]) - (c[1] - a[1]) * (d[0] - a[0])) < 1e-6:
            continue
        simp.append(pts[i])
    simp.append(pts[-1])
    for (a, la), (c, lc) in zip(simp, simp[1:]):
        if la != lc:
            v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I_MM(*a))
            v.SetDrill(pcbnew.FromMM(0.2)); v.SetWidth(pcbnew.FromMM(0.35)); v.SetNet(ni); b.Add(v)
            if a != c:
                pass
            continue
        if a == c:
            continue
        t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I_MM(*a)); t.SetEnd(pcbnew.VECTOR2I_MM(*c))
        t.SetWidth(pcbnew.FromMM(TRACK_MM)); t.SetLayer(mr.LAYERS[la]); t.SetNet(ni); b.Add(t)


def main():
    todo = pairs(drc())
    first = sys.argv[1:]                # nets to route first, e.g. /SDA1 /SHPHLD
    todo.sort(key=lambda t: first.index(t[0]) if t[0] in first else len(first))
    if os.environ.get("ROUTE_ONLY"):           # route just the listed nets
        todo = [t for t in todo if t[0] in first]
    b = pcbnew.LoadBoard(PCB)
    print(len(todo), "signal pairs open:", " ".join(t[0] for t in todo))
    failed = []
    def via_at(net, pt):
        q = pcbnew.VECTOR2I_MM(*pt)
        return any(v.GetClass() == "PCB_VIA" and v.GetNetname() == net
                   and (v.GetPosition() - q).EuclideanNorm() < pcbnew.FromMM(0.05) for v in b.GetTracks())

    def track_end(net, pt, other, layer):
        # DRC names a track by its start point; attach at whichever end of it faces the other item
        q = pcbnew.VECTOR2I_MM(*pt)
        for t in b.GetTracks():
            if (t.GetClass() == "PCB_TRACK" and t.GetNetname() == net and t.GetLayer() == layer
                    and (t.GetStart() - q).EuclideanNorm() < pcbnew.FromMM(0.002)):
                o = pcbnew.VECTOR2I_MM(*other)
                end = min((t.GetStart(), t.GetEnd()), key=lambda p: (p - o).EuclideanNorm())
                return (pcbnew.ToMM(end.x), pcbnew.ToMM(end.y))
        return pt

    todo = [(net, track_end(net, s, e, son[0]) if son and pad_at(b, net, s) is None else s,
             track_end(net, e, s, eon[0]) if eon and pad_at(b, net, e) is None else e, son, eon)
            for net, s, e, son, eon in todo]
    for net, s, e, son, eon in todo:
        # a pad with a via already in it can be left on any layer
        kw = dict(start_on=None if via_at(net, s) else son, end_on=None if via_at(net, e) else eon)
        path, why = mr.multilayer_astar(b, net, s, e, CLR_MM, cell=0.05, margin=1.5, max_iters=900000, **kw)
        if path is None:
            # a boxed-in SMD pad: drill a filled 0.15 / 0.25 via into it and start from the via instead
            for end_pt, key in ((s, "start_on"), (e, "end_on")):
                if kw[key] is None:
                    continue
                pad = pad_at(b, net, end_pt)
                if pad is not None and fx.Obstacles(b).via_ok(pad.GetPosition(), pad):
                    v = pcbnew.PCB_VIA(b); v.SetPosition(pad.GetPosition()); v.SetDrill(pcbnew.FromMM(0.15))
                    v.SetWidth(pcbnew.FromMM(0.25)); v.SetNet(b.FindNet(net)); b.Add(v)
                    kw[key] = None
                    print("  via-in-pad", pad.GetParentFootprint().GetReference(), pad.GetNumber(), flush=True)
            path, why = mr.multilayer_astar(b, net, s, e, CLR_MM, cell=0.05, margin=1.5, max_iters=900000, **kw)
        if path is None:
            path, why = mr.multilayer_astar(b, net, s, e, CLR_MM, cell=0.05, margin=3.5, max_iters=2500000, **kw)
        if path is None:
            failed.append(f"{net} ({why})"); print("  fail", net, why, flush=True); continue
        commit(b, net, path, s, e)
        print("  routed", net, f"{len(path)} steps", flush=True)
    b.Save(PCB)
    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(PCB)
    rep = drc()
    kinds = {}
    for m in re.findall(r"^\[(\w+)\]", rep, re.M):
        kinds[m] = kinds.get(m, 0) + 1
    print("DRC now:", kinds)
    if failed:
        print("could not route:", "; ".join(failed))


if __name__ == "__main__":
    main()

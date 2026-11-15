#!/usr/bin/env python3
"""Widen power and speaker tracks on the v3 pod board wherever the clearance rules allow it.

The autorouter and the finishing tools lay every track at the 0.09 mm minimum. This pass tries each segment of the
listed nets at wider sizes, largest first, and keeps the widest that still clears every other net's copper on that
layer by CLR and stays EDGE away from the board edge. Segments that cannot grow (under the chips) stay as they are.
Zones are refilled and DRC re-run at the end; the board is restored if DRC shows any new error.

    HAVEN_PCB=... HAVEN_WORK=... python3 tools/widen_v3_pod.py
"""
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402

import route_lib as rl  # noqa: E402

PCB = os.environ["HAVEN_PCB"]
WORK = os.environ["HAVEN_WORK"]
CLR, EDGE = 0.105, 0.2
TARGETS = {"/SW": [0.3, 0.25, 0.2, 0.15, 0.12], "/VBUS": [0.25, 0.2, 0.15, 0.12], "/VBAT": [0.25, 0.2, 0.15, 0.12],
           "/VSYS": [0.25, 0.2, 0.15, 0.12], "/+1V8": [0.25, 0.2, 0.15, 0.12], "/V_LS": [0.25, 0.2, 0.15, 0.12],
           "/SPK+": [0.2, 0.15, 0.12], "/SPK-": [0.2, 0.15, 0.12], "/DVDD": [0.2, 0.15, 0.12], "/DEC": [0.2, 0.15, 0.12]}


def drc_counts():
    rpt = os.path.join(WORK, "drc_widen.rpt")
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "--severity-warning", "-o", rpt, PCB], stdout=subprocess.DEVNULL)
    k = {}
    for m in re.findall(r"^\[(\w+)\]", open(rpt).read(), re.M):
        k[m] = k.get(m, 0) + 1
    return k


def main():
    before = drc_counts()
    shutil.copy(PCB, PCB + ".prewiden")
    b = pcbnew.LoadBoard(PCB)
    bb = b.GetBoardEdgesBoundingBox()
    x0, x1, y0, y1 = [pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetRight(), bb.GetTop(), bb.GetBottom())]
    rl.set_clearance(CLR)
    obs_cache = {}
    stats = {}
    for t in b.GetTracks():
        net = t.GetNetname()
        if t.GetClass() != "PCB_TRACK" or net not in TARGETS:
            continue
        lay = t.GetLayer()
        if (net, lay) not in obs_cache:
            obs_cache[(net, lay)] = rl.collect_obstacles(b, lay, net, x0, x1, y0, y1)
        st = stats.setdefault(net, [0.0, 0.0, 0.0])          # length total, length widened, sum(width * length)
        L = pcbnew.ToMM(t.GetLength()); st[0] += L
        cur = pcbnew.ToMM(t.GetWidth()); best = cur
        for w in TARGETS[net]:
            if w <= cur:
                break
            h = w / 2 + EDGE
            pts = [(pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)) for p in (t.GetStart(), t.GetEnd())]
            if any(not (x0 + h <= px <= x1 - h and y0 + h <= py <= y1 - h) for px, py in pts):
                continue
            seg = pcbnew.SHAPE_SEGMENT(t.GetStart(), t.GetEnd(), pcbnew.FromMM(w))
            if any(o.Collide(seg, rl.CLEARANCE_IU) for o in obs_cache[(net, lay)]):
                continue
            best = w
            break
        if best > cur:
            t.SetWidth(pcbnew.FromMM(best)); st[1] += L
        st[2] += best * L
    b.Save(PCB)
    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(PCB)
    after = drc_counts()
    bad = lambda k: sum(v for n, v in k.items() if n not in ("track_dangling", "via_dangling"))
    for net, (tot, wid, wl) in sorted(stats.items()):
        print(f"  {net}: {tot:.1f} mm, {100 * wid / max(tot, 1e-9):.0f} % widened, average width {wl / max(tot, 1e-9):.3f} mm")
    print("DRC before", before, "after", after)
    if bad(after) > bad(before):
        shutil.copy(PCB + ".prewiden", PCB)
        print("NEW ERRORS: board restored, nothing widened")
    os.remove(PCB + ".prewiden")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()

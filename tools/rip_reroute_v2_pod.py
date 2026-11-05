#!/usr/bin/env python3
"""Rip-up and reroute for a pod-board connection the plain router can't finish.

    python3 tools/rip_reroute_v2_pod.py /SDA1 U15.C6 [radius_mm]

For each other net with copper within `radius_mm` of the stuck pad (nearest first): rip up that
net's tracks near the pad (and its routing vias there; vias-in-pad stay), run
route_rest_v2_pod.py with the stuck net first and the ripped net second, and keep the result only
if the open-connection count dropped and DRC shows no new violations. Otherwise restore the board
and try the next net. Dangling vias left behind are removed at the end.
"""
import os
import re
import shutil
import subprocess
import sys

import pcbnew

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PCB = os.path.join(ROOT, "kicad_v2_pod", "haven_v2_pod.kicad_pcb")
WORK = os.path.expanduser("~/.cache/haven_builds/pod_pcb")
MM = pcbnew.FromMM


def drc_counts():
    rpt = os.path.join(WORK, "drc_rr.rpt")
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "--severity-warning", "-o", rpt, PCB],
                   check=False, stdout=subprocess.DEVNULL)
    rep = open(rpt).read()
    kinds = {}
    for m in re.findall(r"^\[(\w+)\]", rep, re.M):
        kinds[m] = kinds.get(m, 0) + 1
    return kinds, rep


def near(p, q, r):
    return (p - q).EuclideanNorm() < r


def candidates(b, net, q, r):
    d = {}
    for t in b.GetTracks():
        n = t.GetNetname()
        if n in (net, "/GND"):
            continue
        if t.GetClass() == "PCB_VIA":
            dist = (t.GetPosition() - q).EuclideanNorm()
        else:
            import fix_v2_pod_pcb as fx
            dist = fx.seg_dist(q, t.GetStart(), t.GetEnd())
        if dist < r:
            d[n] = min(d.get(n, dist), dist)
    return sorted(d, key=d.get)


def rip(b, net, q, r):
    pad_pts = [p.GetPosition() for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname() == net]
    n = 0
    for t in list(b.GetTracks()):
        if t.GetNetname() != net:
            continue
        if t.GetClass() == "PCB_VIA":
            if near(t.GetPosition(), q, r) and not any(near(t.GetPosition(), p, MM(0.05)) for p in pad_pts):
                b.Remove(t); n += 1
        elif __import__("fix_v2_pod_pcb").seg_dist(q, t.GetStart(), t.GetEnd()) < r:
            b.Remove(t); n += 1
    return n


def remove_dangling():
    _, rep = drc_counts()
    pts = [(float(x), float(y)) for x, y in
           re.findall(r"^\[via_dangling\].*?\n.*?\n\s*@\(([-\d.]+) mm, ([-\d.]+) mm\)", rep, re.M)]
    tpts = [(float(x), float(y)) for x, y in
            re.findall(r"^\[track_dangling\].*?\n.*?\n\s*@\(([-\d.]+) mm, ([-\d.]+) mm\)", rep, re.M)]
    if not pts and not tpts:
        return 0
    b = pcbnew.LoadBoard(PCB)
    n = 0
    for v in list(b.GetTracks()):
        P = lambda x, y: pcbnew.VECTOR2I_MM(x, y)
        if v.GetClass() == "PCB_VIA" and any(near(v.GetPosition(), P(x, y), MM(0.01)) for x, y in pts):
            b.Remove(v); n += 1
        elif v.GetClass() == "PCB_TRACK" and any(near(v.GetStart(), P(x, y), MM(0.01)) or near(v.GetEnd(), P(x, y), MM(0.01))
                                                 for x, y in tpts):
            b.Remove(v); n += 1
    b.Save(PCB)
    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(PCB)
    return n


def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    net, padref = sys.argv[1], sys.argv[2]
    r = MM(float(sys.argv[3]) if len(sys.argv) > 3 else 1.2)
    ref, num = padref.split(".")
    b = pcbnew.LoadBoard(PCB)
    q = next(p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num).GetPosition()
    base, _ = drc_counts()
    base_open = base.get("unconnected_items", 0)
    base_bad = sum(v for k, v in base.items() if k not in ("unconnected_items", "via_dangling", "track_dangling"))
    backup = os.path.join(WORK, "rr_backup.kicad_pcb")
    shutil.copy(PCB, backup)
    cands = candidates(b, net, q, r)
    print(f"{net} at {padref}: {base_open} open now; candidates to rip: {' '.join(cands)}", flush=True)
    for c in cands:
        shutil.copy(backup, PCB)
        b = pcbnew.LoadBoard(PCB)
        n = rip(b, c, q, r)
        b.Save(PCB)
        out = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "route_rest_v2_pod.py"), net, c],
                             capture_output=True, text=True, env=dict(os.environ, ROUTE_ONLY="1")).stdout
        kinds, _ = drc_counts()
        opn = kinds.get("unconnected_items", 0)
        bad = sum(v for k, v in kinds.items() if k not in ("unconnected_items", "via_dangling", "track_dangling"))
        print(f"  rip {c} ({n} items): open {opn}, violations {bad}", flush=True)
        if opn < base_open and bad <= base_bad:
            print(f"  kept. dangling items removed: {remove_dangling_safe()}", flush=True)
            print("  DRC now:", drc_counts()[0])
            return
    shutil.copy(backup, PCB)
    print("  no single rip-up worked; board restored")


if __name__ == "__main__":
    main()


def gnd_via_with_rip(padref, r_mm=0.8):
    """Put a GND via-in-pad on `padref`, ripping and rerouting whichever net blocks it."""
    import fix_v2_pod_pcb as fx
    ref, num = padref.split(".")
    base, _ = drc_counts()
    base_open = base.get("unconnected_items", 0)
    backup = os.path.join(WORK, "rr_backup.kicad_pcb")
    shutil.copy(PCB, backup)
    b = pcbnew.LoadBoard(PCB)
    pad = next(p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num)
    q = pad.GetPosition()
    blockers = []
    for t in b.GetTracks():
        n = t.GetNetname()
        if n == "/GND" or n in blockers:
            continue
        d = (t.GetPosition() - q).EuclideanNorm() if t.GetClass() == "PCB_VIA" else fx.seg_dist(q, t.GetStart(), t.GetEnd())
        if d - (t.GetWidth(pcbnew.F_Cu) if t.GetClass() == "PCB_VIA" else t.GetWidth()) / 2 < MM(0.25):
            blockers.append(n)
    print(f"{padref}: {base_open} open; blockers {' '.join(blockers)}", flush=True)
    b = pcbnew.LoadBoard(PCB)
    pad = next(p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num)
    for n in blockers:
        rip(b, n, q, MM(r_mm))
    if not fx.Obstacles(b).via_ok(q, pad):
        print("  still no room for a via after ripping; restored"); shutil.copy(backup, PCB); return False
    v = pcbnew.PCB_VIA(b); v.SetPosition(q); v.SetDrill(MM(0.15)); v.SetWidth(MM(0.25)); v.SetNet(b.FindNet("/GND")); b.Add(v)
    b.Save(PCB)
    subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "route_rest_v2_pod.py"), *blockers],
                   capture_output=True, text=True, env=dict(os.environ, ROUTE_ONLY="1"))
    remove_dangling_safe()
    kinds, _ = drc_counts()
    opn = kinds.get("unconnected_items", 0)
    bad = sum(v for k, v in kinds.items() if k not in ("unconnected_items",))
    print(f"  open {opn}, other DRC {bad}", flush=True)
    if opn < base_open and bad == 0:
        return True
    shutil.copy(backup, PCB); print("  restored"); return False


def remove_dangling_safe(max_items=40):
    """Delete dangling vias / track stubs one at a time; undo any deletion that opens a connection."""
    removed = 0
    for _ in range(max_items):
        kinds, rep = drc_counts()
        opn = kinds.get("unconnected_items", 0)
        items = re.findall(r"^\[(via|track)_dangling\].*?\n.*?\n\s*@\(([-\d.]+) mm, ([-\d.]+) mm\): (\w+) \[([^\]]+)\]", rep, re.M)
        progress = False
        for kind, x, y, _, net in items:
            shutil.copy(PCB, os.path.join(WORK, "dangle_undo.kicad_pcb"))
            b = pcbnew.LoadBoard(PCB)
            q = pcbnew.VECTOR2I_MM(float(x), float(y))
            hit = None
            for t in b.GetTracks():
                if t.GetNetname() != net:
                    continue
                if kind == "via" and t.GetClass() == "PCB_VIA" and near(t.GetPosition(), q, MM(0.002)):
                    hit = t; break
                if kind == "track" and t.GetClass() == "PCB_TRACK" and (near(t.GetStart(), q, MM(0.002)) or near(t.GetEnd(), q, MM(0.002))):
                    hit = t; break
            if hit is None:
                continue
            b.Remove(hit); b.Save(PCB)
            if drc_counts()[0].get("unconnected_items", 0) > opn:
                shutil.copy(os.path.join(WORK, "dangle_undo.kicad_pcb"), PCB)
                continue
            removed += 1; progress = True
            break
        if not progress:
            break
    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(PCB)
    return removed

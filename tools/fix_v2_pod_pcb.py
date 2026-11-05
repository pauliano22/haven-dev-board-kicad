#!/usr/bin/env python3
"""Post-route clean-up for the pod board, run after each Freerouting pass.

1. Widens every track Freerouting necked down below 0.09 mm (the fab minimum) to 0.09 mm.
2. Every GND pad of a passive, ESD diode or crystal with no GND via within 0.5 mm gets a 0.15 / 0.25 mm via in its pad, which
   ties it to the In1/In4 GND planes (filled and capped at fab, like the BGA fan-out).
Then refills the zones and re-runs DRC.

    python3 tools/fix_v2_pod_pcb.py
"""
import math
import os
import re
import subprocess

import pcbnew

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PCB = os.path.join(ROOT, "kicad_v2_pod", "haven_v2_pod.kicad_pcb")
WORK = os.path.expanduser("~/.cache/haven_builds/pod_pcb")
MIN_W = 0.09


MM = pcbnew.FromMM
TOL = MM(0.002)                     # rounding slack on exact-minimum spacings (0.35 mm BGA grid)


def seg_dist(p, a, b):
    ax, ay, bx, by, px, py = a.x, a.y, b.x, b.y, p.x, p.y
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


class Obstacles:
    """Copper and holes of every net, for checking a through via (all layers) and a short track."""
    VIA_R, HOLE_R = MM(0.125), MM(0.075)

    def __init__(self, b):
        self.b = b
        self.tracks = [(t.GetStart(), t.GetEnd(), t.GetWidth() / 2, t.GetNetname(), t.GetLayer())
                       for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
        self.vias = [(v.GetPosition(), v.GetWidth() / 2, v.GetNetname()) for v in b.GetTracks() if v.GetClass() == "PCB_VIA"]
        self.pads = []
        for fp in b.GetFootprints():
            for p in fp.Pads():
                bb = p.GetBoundingBox()
                self.pads.append((bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom(), p.GetNetname(),
                                  p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH, p.IsOnLayer(pcbnew.F_Cu), p))
        e = b.GetBoardEdgesBoundingBox()
        self.edge = (e.GetLeft(), e.GetTop(), e.GetRight(), e.GetBottom())

    def add_via(self, q):
        self.vias.append((q, self.VIA_R, "/GND"))

    def add_track(self, t):
        self.tracks.append((t.GetStart(), t.GetEnd(), t.GetWidth() / 2, "/GND", t.GetLayer()))

    def gnd_via_near(self, q, r_mm):
        return any(n == "/GND" and math.hypot(p.x - q.x, p.y - q.y) < MM(r_mm) for p, _, n in self.vias)

    def via_ok(self, q, own_pad):
        x0, y0, x1, y1 = self.edge
        m = MM(0.45)
        if not (x0 + m < q.x < x1 - m and y0 + m < q.y < y1 - m):
            return False
        for a, c, hw, n, _ in self.tracks:            # copper 0.10 and hole 0.15 to other nets
            if n != "/GND" and seg_dist(q, a, c) - hw < max(self.VIA_R + MM(0.10), self.HOLE_R + MM(0.15)) - TOL:
                return False
        for p, r, n in self.vias:                      # hole-to-hole 0.2 for every via
            d = math.hypot(p.x - q.x, p.y - q.y)
            if d < 2 * self.HOLE_R + MM(0.2) - TOL or (n != "/GND" and d < r + self.VIA_R + MM(0.10) - TOL):
                return False
        for l, t, r, bt, n, pth, _, pad in self.pads:
            if pad.m_Uuid.AsString() == own_pad.m_Uuid.AsString():
                continue
            dx = max(l - q.x, 0, q.x - r); dy = max(t - q.y, 0, q.y - bt)
            d = math.hypot(dx, dy)
            if n != "/GND" and d < max(self.VIA_R + MM(0.10), self.HOLE_R + MM(0.15)) - TOL:
                return False
            if n == "/GND" and pth and d < MM(0.2):
                return False
        return True

    def track_ok(self, a, c, layer, own_pad):
        for s, e, hw, n, lay in self.tracks:
            if n != "/GND" and lay == layer:
                for k in range(21):
                    p = pcbnew.VECTOR2I(int(a.x + (c.x - a.x) * k / 20), int(a.y + (c.y - a.y) * k / 20))
                    if seg_dist(p, s, e) - hw < MM(0.05 + 0.10):
                        return False
        for l, t, r, bt, n, pth, onf, pad in self.pads:
            if n == "/GND" or pad.m_Uuid.AsString() == own_pad.m_Uuid.AsString() or (onf != (layer == pcbnew.F_Cu) and not pth):
                continue
            for k in range(11):                         # sample the track against the pad box
                x = a.x + (c.x - a.x) * k / 10; y = a.y + (c.y - a.y) * k / 10
                dx = max(l - x, 0, x - r); dy = max(t - y, 0, y - bt)
                if math.hypot(dx, dy) < MM(0.05 + 0.10):
                    return False
        return True

    def find_via_spot(self, pad):
        q = pad.GetPosition()
        if self.via_ok(q, pad):
            return q
        layer = pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
        for r in (0.35, 0.45, 0.55, 0.7, 0.85):
            for k in range(16):
                a = 2 * math.pi * k / 16
                c = pcbnew.VECTOR2I(int(q.x + MM(r) * math.cos(a)), int(q.y + MM(r) * math.sin(a)))
                if self.via_ok(c, pad) and self.track_ok(q, c, layer, pad):
                    return c
        return None


def drc(name):
    rpt = os.path.join(WORK, name)
    subprocess.run(["kicad-cli", "pcb", "drc", "--schematic-parity", "--severity-error", "--severity-warning",
                    "-o", rpt, PCB], check=False, stdout=subprocess.DEVNULL)
    return open(rpt).read()


def main():
    rep = drc("drc_pre_fix.rpt")
    gnd_pads = set()
    for block in rep.split("\n[")[1:]:
        if block.startswith("unconnected_items"):
            for ref_pad in re.findall(r"Pad (\S+) \[/GND\] of (\S+) on", block):
                gnd_pads.add((ref_pad[1], ref_pad[0]))
    b = pcbnew.LoadBoard(PCB)
    widened = 0
    for t in b.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetWidth() < pcbnew.FromMM(MIN_W):
            t.SetWidth(pcbnew.FromMM(MIN_W)); widened += 1
    gnd = b.FindNet("/GND")
    added, failed = 0, []
    obst = Obstacles(b)
    for fp in b.GetFootprints():
        if fp.GetReference()[0] not in "CRDLX" or fp.IsDNP():
            continue
        for pad in fp.Pads():
            if pad.GetNetname() != "/GND" or pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            q = pad.GetPosition()
            if obst.gnd_via_near(q, 0.5):
                continue
            spot = obst.find_via_spot(pad)
            if spot is None:
                failed.append(fp.GetReference() + "." + pad.GetNumber()); continue
            v = pcbnew.PCB_VIA(b); v.SetPosition(spot)
            v.SetDrill(pcbnew.FromMM(0.15)); v.SetWidth(pcbnew.FromMM(0.25)); v.SetNet(gnd); b.Add(v)
            if spot != q:
                t = pcbnew.PCB_TRACK(b); t.SetStart(q); t.SetEnd(spot); t.SetWidth(pcbnew.FromMM(0.1))
                t.SetLayer(pad.GetLayer() if pad.IsOnLayer(pcbnew.B_Cu) is False else pcbnew.B_Cu)
                t.SetLayer(pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu)
                t.SetNet(gnd); b.Add(t); obst.add_track(t)
            obst.add_via(spot)
            added += 1
    if failed:
        print("no legal GND via spot for:", " ".join(failed))
    for z in b.Zones():
        if not z.GetIsRuleArea():
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    for fp in b.GetFootprints():
        if fp.IsDNP():
            fp.SetExcludedFromBOM(False); fp.SetExcludedFromPosFiles(False)
    b.Save(PCB)
    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(PCB)
    rep = drc("drc.rpt")
    kinds = {}
    for m in re.findall(r"^\[(\w+)\]", rep, re.M):
        kinds[m] = kinds.get(m, 0) + 1
    print(f"widened {widened} tracks, added {added} GND vias-in-pad; DRC now: {kinds}")


if __name__ == "__main__":
    main()

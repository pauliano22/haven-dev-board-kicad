#!/usr/bin/env python3
"""Add GND stitching vias to the routed case board: a 1.6 mm grid of 0.6/0.3 vias wherever both
GND pours are present at the point, then drop any via that DRC flags. Ties the F.Cu and B.Cu pours
together so no GND copper is left floating.

    python3 tools/stitch_v2_case_pcb.py
"""
import os
import re
import subprocess

import pcbnew

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PCB = os.path.join(ROOT, "kicad_v2_case", "haven_v2_case.kicad_pcb")
RPT = os.path.expanduser("~/.cache/haven_builds/case_pcb/stitch_drc.rpt")


def drc():
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "--severity-warning", "-o", RPT, PCB],
                   check=False, stdout=subprocess.DEVNULL)
    return open(RPT).read()


def refill(b):
    b.Save(PCB)
    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(PCB)
    return pcbnew.LoadBoard(PCB)


def main():
    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    gnd = b.FindNet("/GND")
    zones = {z.GetLayer(): z for z in b.Zones() if z.GetNetname() == "/GND"}
    bb = b.GetBoardEdgesBoundingBox()
    x0, y0, x1, y1 = [pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())]
    added = []
    y = y0 + 1.0
    while y < y1 - 0.9:
        x = x0 + 1.0
        while x < x1 - 0.9:
            q = pcbnew.VECTOR2I_MM(x, y)
            # both pours must cover a 0.45 mm radius around the point (via pad 0.3 + 0.15)
            ok = True
            for lay in (pcbnew.F_Cu, pcbnew.B_Cu):
                fill = zones[lay].GetFilledPolysList(lay)
                for dx, dy in ((0, 0), (0.45, 0), (-0.45, 0), (0, 0.45), (0, -0.45)):
                    if not fill.Contains(pcbnew.VECTOR2I_MM(x + dx, y + dy)):
                        ok = False
            if ok:
                v = pcbnew.PCB_VIA(b); v.SetPosition(q); v.SetDrill(pcbnew.FromMM(0.3)); v.SetWidth(pcbnew.FromMM(0.6))
                v.SetNet(gnd); b.Add(v); added.append(v)
            x += 1.6
        y += 1.6
    b = refill(b)
    for _ in range(3):
        rep = drc()
        bad = set()
        for blk in rep.split("\n[")[1:]:
            if blk.startswith(("unconnected_items", "via_dangling")):
                continue
            for xx, yy, kind in re.findall(r"@\(([-\d.]+) mm, ([-\d.]+) mm\): (Via)", blk):
                bad.add((round(float(xx), 3), round(float(yy), 3)))
        if not bad:
            break
        for v in list(b.GetTracks()):
            if v.GetClass() == "PCB_VIA" and v.GetNetname() == "/GND":
                p = (round(pcbnew.ToMM(v.GetPosition().x), 3), round(pcbnew.ToMM(v.GetPosition().y), 3))
                if p in bad:
                    b.Remove(v)
        b = refill(b)
    n = sum(1 for v in b.GetTracks() if v.GetClass() == "PCB_VIA" and v.GetNetname() == "/GND")
    kinds = {}
    for m in re.findall(r"^\[(\w+)\]", drc(), re.M):
        kinds[m] = kinds.get(m, 0) + 1
    print(f"{n} GND vias; DRC: {kinds}")


if __name__ == "__main__":
    main()

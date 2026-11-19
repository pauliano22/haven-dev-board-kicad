#!/usr/bin/env python3
"""Make the ASSEMBLY version of the v3 pod board: the same board with two break-off rails (2026-11-14).

Why: JLCPCB refuses assembly on boards under 10 x 10 mm ("PCB assembly requires a minimum size of 10x10mm", quote of
2026-11-14); the pod is 9.6 mm wide. Rather than widen the pod, this adds a 5 mm rail on each long side, held by two
2.5 mm tabs per side with a row of 0.5 mm break holes just OUTSIDE the board edge. The board itself is unchanged:
copper, parts and outline are copied from kicad_v3_pod/haven_v3_pod.kicad_pcb every time this runs.

    python3 tools/make_v3_pod_panel.py     ->  kicad_v3_pod/panel/haven_v3_pod_panel.kicad_pcb
    python3 tools/export_v2_fab.py v3podpanel   ->  fab/v3_pod_panel/

After assembly: cut the tabs with flush cutters (do not snap them: C117 and R111 sit about 1.3 mm from a tab) and file
the four nibs flush; the shell is sized for the 9.6 mm board.
"""
import os
import shutil
import sys

import pcbnew
from shapely.geometry import Point, box
from shapely.ops import unary_union

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC = os.path.join(ROOT, "kicad_v3_pod", "haven_v3_pod.kicad_pcb")
OUT_DIR = os.path.join(ROOT, "kicad_v3_pod", "panel")
OUT = os.path.join(OUT_DIR, "haven_v3_pod_panel.kicad_pcb")
MM = pcbnew.FromMM
X0, X1, Y0, Y1, R = 95.2, 104.8, 86.5, 113.5, 1.0       # board outline (rounded rectangle), from the board file
GAP, RAIL = 2.0, 5.0
TABS = {"L": [(93.5, 96.0), (109.7, 112.2)], "R": [(93.5, 96.0), (109.2, 111.7)]}     # y ranges, clear of parts near the edge
HOLE_D, HOLE_PITCH, HOLE_OUT = 0.5, 0.8, 0.25            # break holes: centre this far outside the board edge

os.makedirs(OUT_DIR, exist_ok=True)
shutil.copy(SRC, OUT)
for ext in (".kicad_pro",):
    shutil.copy(SRC.replace(".kicad_pcb", ext), OUT.replace(".kicad_pcb", ext))
import json
_pro = OUT.replace(".kicad_pcb", ".kicad_pro"); _d = json.load(open(_pro))
# the panel's break holes and fiducials are mechanical marks with no courtyard; the board itself is checked in its own project
_d["board"]["design_settings"]["rule_severities"]["missing_courtyard"] = "ignore"; json.dump(_d, open(_pro, "w"), indent=2)
open(os.path.join(OUT_DIR, "fp-lib-table"), "w").write(open(os.path.join(os.path.dirname(SRC), "fp-lib-table")).read().replace("${KIPRJMOD}/", "${KIPRJMOD}/../"))
b = pcbnew.LoadBoard(OUT)
edge = b.GetLayerID("Edge.Cuts")
got = b.GetBoardEdgesBoundingBox()
assert abs(got.GetLeft() / 1e6 - X0) < 0.05 and abs(got.GetRight() / 1e6 - X1) < 0.05 and abs(got.GetTop() / 1e6 - Y0) < 0.05 \
    and abs(got.GetBottom() / 1e6 - Y1) < 0.05, "board outline changed: update X0..Y1"
for d in list(b.GetDrawings()):
    if d.GetLayer() == edge:
        b.Remove(d)

board = box(X0 + R, Y0 + R, X1 - R, Y1 - R).buffer(R, quad_segs=12)
pieces = [board, box(X0 - GAP - RAIL, Y0, X0 - GAP, Y1).buffer(-0.5).buffer(0.5, quad_segs=8),
          box(X1 + GAP, Y0, X1 + GAP + RAIL, Y1).buffer(-0.5).buffer(0.5, quad_segs=8)]
for side, tabs in TABS.items():
    for y0, y1 in tabs:
        pieces.append(box(X0 - GAP - 0.01, y0, X0 + 0.01, y1) if side == "L" else box(X1 - 0.01, y0, X1 + GAP + 0.01, y1))
panel = unary_union(pieces)
assert panel.geom_type == "Polygon"
for ring in [panel.exterior, *panel.interiors]:          # the slot between each pair of tabs is an inner cut-out
    pts = list(ring.simplify(0.002).coords)
    for a, c in zip(pts, pts[1:]):
        s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(edge); s.SetWidth(MM(0.05))
        s.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1]))); s.SetEnd(pcbnew.VECTOR2I(MM(c[0]), MM(c[1]))); b.Add(s)


def board_only(ref, value):
    fp = pcbnew.FOOTPRINT(b); fp.SetReference(ref); fp.SetValue(value)
    fp.SetAttributes(pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    return fp


n = 0
for side, tabs in TABS.items():
    x = X0 - HOLE_OUT if side == "L" else X1 + HOLE_OUT
    for y0, y1 in tabs:
        k = int((y1 - y0 - 0.6) / HOLE_PITCH) + 1
        for i in range(k):
            y = (y0 + y1) / 2 + (i - (k - 1) / 2) * HOLE_PITCH
            n += 1
            fp = board_only(f"MB{n}", "break hole"); fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
            p = pcbnew.PAD(fp); p.SetAttribute(pcbnew.PAD_ATTRIB_NPTH); p.SetShape(pcbnew.F_Cu, pcbnew.PAD_SHAPE_CIRCLE)
            p.SetSize(pcbnew.F_Cu, pcbnew.VECTOR2I(MM(HOLE_D), MM(HOLE_D))); p.SetDrillSize(pcbnew.VECTOR2I(MM(HOLE_D), MM(HOLE_D)))
            p.SetLayerSet(pcbnew.PAD.UnplatedHoleMask()); p.SetPosition(fp.GetPosition()); p.SetNumber("")
            fp.Add(p); b.Add(fp)
for i, (x, y) in enumerate(((X0 - GAP - RAIL / 2, Y0 + 3.0), (X0 - GAP - RAIL / 2, Y1 - 3.0), (X1 + GAP + RAIL / 2, Y0 + 5.0)), 1):
    fp = board_only(f"FID{i}", "fiducial"); fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    p = pcbnew.PAD(fp); p.SetAttribute(pcbnew.PAD_ATTRIB_SMD); p.SetShape(pcbnew.F_Cu, pcbnew.PAD_SHAPE_CIRCLE)
    p.SetSize(pcbnew.F_Cu, pcbnew.VECTOR2I(MM(1.0), MM(1.0))); ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.F_Mask)
    p.SetLayerSet(ls); p.SetLocalSolderMaskMargin(MM(0.5)); p.SetPosition(fp.GetPosition()); p.SetNumber("")
    fp.Add(p); b.Add(fp)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(OUT)
bb = pcbnew.LoadBoard(OUT).GetBoardEdgesBoundingBox()
print(f"panel {bb.GetWidth() / 1e6:.1f} x {bb.GetHeight() / 1e6:.1f} mm, {n} break holes, 3 fiducials -> {OUT}")
sys.stdout.flush(); os._exit(0)

#!/usr/bin/env python3
"""Layout and schematic PDFs of the v3 pod for outside design reviews (Raytac, Nordic), 2026-11-19.

    python3 tools/export_v3_review_pdfs.py   ->  fab/v3_review/haven_v3_pod_layout.pdf, haven_v3_pod_schematic.pdf

The layout PDF has one page per layer, scaled to fill the page (the board is only 9.6 x 27 mm), each with the board
outline and part outlines, and the layer named in the title block. Everything is drawn as seen from the TOP of the board.
Contains design files only, no personal or health information.
"""
import os
import shutil
import subprocess
import tempfile
import textwrap

import pcbnew

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PCB = os.path.join(ROOT, "kicad_v3_pod", "haven_v3_pod.kicad_pcb")
SCH = os.path.join(ROOT, "kicad_v3_pod", "haven_v3_pod.kicad_sch")
OUT = os.path.join(ROOT, "fab", "v3_review")
os.makedirs(OUT, exist_ok=True)

PAGES = [  # (file stem, layers on the page, title-block note)
    ("01_top_parts", ["F.Fab", "F.SilkS", "Edge.Cuts", "Dwgs.User", "Eco1.User"], "Top side parts (F.Fab outlines, references). Radio module U1 at the top, antenna end at the board edge."),
    ("02_F_Cu", ["F.Cu", "Edge.Cuts", "F.Fab", "Eco1.User"], "Layer 1 of 6: F.Cu (top copper; ground pour + signals)"),
    ("03_In1_Cu", ["In1.Cu", "Edge.Cuts"], "Layer 2 of 6: In1.Cu (solid ground plane)"),
    ("04_In2_Cu", ["In2.Cu", "Edge.Cuts"], "Layer 3 of 6: In2.Cu (signals, VBUS)"),
    ("05_In3_Cu", ["In3.Cu", "Edge.Cuts"], "Layer 4 of 6: In3.Cu (signals, VBAT)"),
    ("06_In4_Cu", ["In4.Cu", "Edge.Cuts"], "Layer 5 of 6: In4.Cu (ground + V_LS codec supply pours)"),
    ("07_B_Cu", ["B.Cu", "Edge.Cuts", "B.Fab", "Eco2.User"], "Layer 6 of 6: B.Cu (bottom copper, seen from the top). The pouch cell lies under the lower part"),
    ("08_bottom_parts", ["B.Fab", "B.SilkS", "Edge.Cuts", "Eco2.User"], "Bottom side (seen from the top): spring-pin charge contacts P1/P2, test pads, cell pads TP8/TP9"),
]

b = pcbnew.LoadBoard(PCB)
tb = b.GetTitleBlock()
tb.SetTitle("Haven v3 pod (9.6 x 27 mm, 6 layers, 0.8 mm) - layout for review")
tb.SetDate("2026-11-19")
tmp = tempfile.mkdtemp()
pc = pcbnew.PLOT_CONTROLLER(b)
po = pc.GetPlotOptions()
po.SetOutputDirectory(tmp)
po.SetPlotFrameRef(False)          # with auto-scale the frame is scaled too and fills the page; a text label is used instead
po.SetAutoScale(False)            # auto-scale put the drawing off the page (KiCad 9 Python); a fixed scale is centred
po.SetScale(6.5)
po.SetMirror(False)
po.SetPlotReference(True)
po.SetPlotValue(False)
po.SetSketchPadsOnFabLayers(True)
po.SetPlotPadNumbers(True)
po.SetDrillMarksType(pcbnew.DRILL_MARKS_SMALL_DRILL_SHAPE)
pc.SetColorMode(True)
files = []
edge = b.GetBoardEdgesBoundingBox()
# Part references are hidden on this tiny board; for the review PDF put each one at its part's centre, on Eco1.User (top
# parts) or Eco2.User (bottom parts, written unmirrored so they read in the top view). Not saved to the board.
for fp in b.GetFootprints():
    bb = fp.GetCourtyard(fp.GetLayer()).BBox() if not fp.GetCourtyard(fp.GetLayer()).IsEmpty() else fp.GetBoundingBox(False)
    ref = fp.GetReference()
    size = max(0.12, min(0.4, 0.9 * pcbnew.ToMM(min(bb.GetWidth(), bb.GetHeight())), 1.4 * pcbnew.ToMM(bb.GetWidth()) / len(ref)))
    t = pcbnew.PCB_TEXT(b)
    t.SetLayer(pcbnew.Eco1_User if fp.GetLayer() == pcbnew.F_Cu else pcbnew.Eco2_User)
    t.SetText(ref)
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
    t.SetTextThickness(pcbnew.FromMM(size * 0.12))
    t.SetPosition(bb.GetCenter())
    b.Add(t)
for stem, layers, note in PAGES:
    # page label: a text on Cmts.User above the board, plotted with the page's layers, removed afterwards
    label = pcbnew.PCB_TEXT(b)
    label.SetLayer(pcbnew.Cmts_User)
    label.SetText("\n".join(textwrap.wrap("Haven v3 pod, 9.6 x 27 mm, 6 layers, 0.8 mm, scale 6.5:1. View from TOP. " + note, 64)))
    label.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.3), pcbnew.FromMM(0.3)))
    label.SetTextThickness(pcbnew.FromMM(0.04))
    label.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    label.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_BOTTOM)
    label.SetPosition(pcbnew.VECTOR2I(edge.GetLeft() - pcbnew.FromMM(3), edge.GetTop() - pcbnew.FromMM(0.6)))
    b.Add(label)
    seq = pcbnew.LSEQ()
    for name in layers + ["Cmts.User"]:
        seq.push_back(b.GetLayerID(name))
    pc.OpenPlotfile(stem, pcbnew.PLOT_FORMAT_PDF, note)
    pc.PlotLayers(seq)
    pc.ClosePlot()
    files.append(pc.GetPlotFileName())
    b.Remove(label)
layout = os.path.join(OUT, "haven_v3_pod_layout.pdf")
subprocess.run(["pdfunite", *files, layout], check=True)
shutil.rmtree(tmp)
sch_pdf = os.path.join(OUT, "haven_v3_pod_schematic.pdf")
subprocess.run(["kicad-cli", "sch", "export", "pdf", "-o", sch_pdf, SCH], check=True, capture_output=True)
for f in (layout, sch_pdf):
    print(f, f"{os.path.getsize(f) / 1e6:.2f} MB")

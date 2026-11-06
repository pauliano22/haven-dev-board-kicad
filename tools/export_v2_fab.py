#!/usr/bin/env python3
"""Export JLCPCB fab files for the v2 BTE boards into fab/v2_<board>/.

    python3 tools/export_v2_fab.py [pod] [inear] [case]     (default: all three)

Per board: gerbers + drill (zip), BOM (JLC columns, from the schematic's MPN / LCSC fields) and
CPL (from the footprints' real positions and orientations, relative to the board's bottom-left,
which is also the gerber/drill origin). Parts with no LCSC number are listed: JLC can't place
them from stock (consign, hand-solder, or pick a part in JLC's search).
Check every rotation in JLC's placement preview: JLC's zero orientation differs from KiCad's for
some packages (SOT-23, SOT-563, the USB-C, the WLCSPs).
"""
import csv
import os
import re
import subprocess
import sys
import zipfile

import pcbnew

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BOARDS = {"pod": 6, "inear": 2, "case": 2}


def sch_parts(sch):
    """ref -> (value, footprint, mpn, lcsc, dnp) from the schematic."""
    tmp = os.path.expanduser(f"~/.cache/haven_builds/fab_{os.path.basename(sch)}.csv")
    subprocess.run(["kicad-cli", "sch", "export", "bom", "-o", tmp,
                    "--fields", "Reference,Value,Footprint,MPN,LCSC,${DNP}", "--group-by", "", sch],
                   check=True, capture_output=True)
    out = {}
    for r in csv.DictReader(open(tmp)):
        for ref in r["Reference"].split(","):
            out[ref.strip()] = (r["Value"], r["Footprint"].split(":")[-1], r["MPN"], r["LCSC"], bool(r.get("DNP")))
    return out


def export(name, layers_n):
    prj = os.path.join(ROOT, f"kicad_v2_{name}")
    pcb = os.path.join(prj, f"haven_v2_{name}.kicad_pcb")
    sch = os.path.join(prj, f"haven_v2_{name}.kicad_sch")
    out = os.path.join(ROOT, "fab", f"v2_{name}")
    gdir = os.path.join(out, "gerbers")
    os.makedirs(gdir, exist_ok=True)
    for f in os.listdir(gdir):
        os.remove(os.path.join(gdir, f))

    board = pcbnew.LoadBoard(pcb)
    bb = board.GetBoardEdgesBoundingBox()
    origin = pcbnew.VECTOR2I(bb.GetLeft(), bb.GetBottom())
    ds = board.GetDesignSettings()
    if ds.GetAuxOrigin() != origin:
        ds.SetAuxOrigin(origin)
        board.Save(pcb)

    inner = [f"In{i}.Cu" for i in range(1, layers_n - 1)]
    layers = ",".join(["F.Cu", *inner, "B.Cu", "F.Paste", "B.Paste", "F.SilkS", "B.SilkS", "F.Mask", "B.Mask", "Edge.Cuts"])
    subprocess.run(["kicad-cli", "pcb", "export", "gerbers", "--layers", layers, "--use-drill-file-origin",
                    "--subtract-soldermask", "-o", gdir + "/", pcb], check=True, capture_output=True)
    subprocess.run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--drill-origin", "plot",
                    "--excellon-separate-th", "--generate-map", "--map-format", "gerberx2", "-o", gdir + "/", pcb],
                   check=True, capture_output=True)
    with zipfile.ZipFile(os.path.join(out, f"haven_v2_{name}_gerbers.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(gdir)):
            z.write(os.path.join(gdir, f), f)

    parts = sch_parts(sch)
    groups, cpl, skipped = {}, [], []
    for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
        ref = fp.GetReference()
        val, fpn, mpn, lcsc, dnp = parts.get(ref, (fp.GetValue(), "", "", "", False))
        if dnp or fp.IsDNP():
            skipped.append(f"{ref} (DNP)")
            continue
        if not fp.Pads() or all(p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD and re.match(r"(TP|W|P)\d", ref) and not mpn
                                for p in fp.Pads()):
            skipped.append(f"{ref} (pad only)")       # test / wire / pogo pads are copper, not parts
            continue
        groups.setdefault((val, str(fp.GetFPID().GetLibItemName()), mpn, lcsc), []).append(ref)
        p = fp.GetPosition()
        cpl.append([ref, f"{pcbnew.ToMM(p.x - origin.x):.4f}mm", f"{pcbnew.ToMM(origin.y - p.y):.4f}mm",
                    "Bottom" if fp.GetLayer() == pcbnew.B_Cu else "Top", f"{fp.GetOrientationDegrees() % 360:g}"])
    with open(os.path.join(out, f"haven_v2_{name}_bom.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "Manufacturer Part", "LCSC Part #"])
        for (val, fpn, mpn, lcsc), refs in groups.items():
            w.writerow([val, ",".join(refs), fpn, mpn, lcsc])
    with open(os.path.join(out, f"haven_v2_{name}_cpl.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        w.writerows(cpl)
    no_lcsc = [r for (v, fpn, m, l), refs in groups.items() if not l for r in refs]
    size = (pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()))
    print(f"{name}: {size[0]:.1f} x {size[1]:.1f} mm, {layers_n} layers; {len(groups)} BOM lines, {len(cpl)} placements; "
          f"no LCSC #: {' '.join(no_lcsc) or '-'}; not placed: {' '.join(skipped) or '-'}")


if __name__ == "__main__":
    for n in (sys.argv[1:] or list(BOARDS)):
        export(n, BOARDS[n])

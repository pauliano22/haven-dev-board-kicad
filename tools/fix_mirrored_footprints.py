#!/usr/bin/env python3
"""One-off repair: un-mirror the library footprints that were converted from EasyEDA (.efoo) files.

extracted/gen_footprints.py copied EasyEDA's y-up pad coordinates into KiCad's y-down files, so every
such footprint was a top-to-bottom mirror image (DESIGN_REVIEW_2026-11.md, finding 1). This negates each
pad's y and retags the file so it cannot be applied twice. Pad rotation angles stay as they are: a
counter-clockwise angle in a y-up drawing is the same visual angle in KiCad once y is flipped.

It changes LIBRARY files only. Boards keep their embedded (mirrored) footprints until they are re-laid.

    python3 tools/fix_mirrored_footprints.py kicad_v2_pod kicad_v2_inear
"""
import glob
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PAD_AT = re.compile(r'(\(pad "[^"]*" \w+ \w+ \(at )(-?[\d.]+) (-?[\d.]+)')


def fix(path):
    s = open(path).read()
    if "(generator haven_kicad_port)" not in s:
        return False
    s = PAD_AT.sub(lambda m: f"{m.group(1)}{m.group(2)} {(-float(m.group(3)) + 0.0):.4f}", s)
    s = s.replace("(generator haven_kicad_port)", "(generator haven_kicad_port_yfix)")
    open(path, "w").write(s)
    return True


for d in sys.argv[1:]:
    for f in sorted(glob.glob(os.path.join(ROOT, d, "footprints.pretty", "*.kicad_mod"))):
        print(("fixed   " if fix(f) else "skipped ") + os.path.relpath(f, ROOT))

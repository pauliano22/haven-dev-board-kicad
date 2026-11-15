#!/usr/bin/env python3
"""Check that asymmetric parts sit on the board with the handedness their datasheet's TOP VIEW shows.

Why: footprints converted from the EasyEDA files were mirror images (y axis not flipped), which DRC and
schematic parity cannot see. Found 2026-11-11, see DESIGN_REVIEW_2026-11.md.

Each entry names three pads a, b, c such that, in the datasheet's top view of the part (or the land
pattern's top view), b is to the RIGHT of a and c is BELOW a. For a part on the front that means the
cross product (b-a) x (c-a) is positive in KiCad's y-down coordinates; for a part on the back it must be
negative (the board is seen through from the front). Rotation does not change the sign, a mirror does.

    python3 tools/check_footprint_handedness.py [pod] [inear]      exit code 1 if any part is mirrored
"""
import os
import sys

import pcbnew

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CHECKS = {
    "pod": [
        ("U15", "A1", "A8", "G1", "ADAU1860 data sheet Rev C, Figure 8 (top view)"),
        ("U2", "A1", "A5", "E1", "nPM1100 PS v1.5, Figure 35"),
        ("U1", "1", "39", "17", "Raytac MDBT53V-1M spec, section 2.2 (top view)"),
        ("U14", "1", "5", "2", "Knowles SPH0641LU4H-1, example land pattern"),
    ],
    "inear": [("U13", "1", "5", "2", "Knowles SPH0641LU4H-1, example land pattern")],
    "v3pod": [
        ("U15", "A1", "A8", "G1", "ADAU1860 data sheet Rev C, Figure 8 (top view)"),
        ("U2", "A1", "A5", "E1", "nPM1100 PS v1.5, Figure 35"),
        ("U1", "1", "39", "17", "Raytac MDBT53V-1M spec, section 2.2 (top view)"),
        ("U14", "2", "3", "1", "SPK0641HT4H-1 Rev D-1 page 7, example land pattern"),
        ("U3", "A1", "A2", "B1", "AP22916 DS44758 Rev 2-2 page 1, Pin Assignments (top view): A1 VOUT, A2 VIN, B1 GND, B2 ON (read 2026-11-14)"),
    ],
}
PATHS = {"v3pod": ("kicad_v3_pod", "haven_v3_pod.kicad_pcb")}


def pad_xy(fp, number):
    for p in fp.Pads():
        if p.GetNumber() == number:
            q = p.GetPosition()
            return pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)
    raise KeyError(number)


def main():
    boards = sys.argv[1:] or ["pod", "inear"]
    bad = 0
    for name in boards:
        d, f = PATHS.get(name, (f"kicad_v2_{name}", f"haven_v2_{name}.kicad_pcb"))
        board = pcbnew.LoadBoard(os.path.join(ROOT, d, f))
        for ref, a, b, c, source in CHECKS[name]:
            fp = board.FindFootprintByReference(ref)
            if fp is None:
                print(f"   {name} {ref}: not on the board"); bad += 1; continue
            A, B, C = pad_xy(fp, a), pad_xy(fp, b), pad_xy(fp, c)
            cross = (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0])
            ok = (cross > 0) != fp.IsFlipped()
            bad += 0 if ok else 1
            print(f"   {name} {ref} ({'back' if fp.IsFlipped() else 'front'}): {'ok' if ok else 'MIRRORED'}   [{source}]")
    print("RESULT:", "all parts have the datasheet's handedness" if not bad else f"{bad} part(s) MIRRORED: do not order")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

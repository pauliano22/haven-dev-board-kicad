"""
Refine the rough placement from place_pcb_footprints_v2.py using this
project's own established collision-avoidance search (placement_lib.py's
find_spot, already used successfully across many past routing sessions).
The initial placement was arbitrary (no collision-checking at all) and
produced 37 real shorts + 503 clearance violations -- this pass finds a
genuinely free spot for each new footprint near its rough starting point.

Run from kicad/ directory, after place_pcb_footprints_v2.py.
"""
import sys
sys.path.insert(0, "../tools")
import pcbnew
import placement_lib as pl

PCB_PATH = "haven_dev_board.kicad_pcb"

NEW_REFS = ["U15", "MIC1", "U16", "R29", "C50", "C51", "C52", "C53",
            "C54", "R30", "R31", "C55", "C56", "L1", "D1"]


def main():
    board = pcbnew.LoadBoard(PCB_PATH)
    moved, stuck = [], []
    for ref in NEW_REFS:
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            print(f"{ref}: NOT FOUND, skipping")
            continue
        pos = fp.GetPosition()
        anchor = (pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y))
        cands, total = pl.find_spot(board, ref, "F.Cu", anchor,
                                     radius=15.0, step=0.5,
                                     exclude_refs=set(NEW_REFS), limit=1)
        if not cands:
            print(f"{ref}: NO clear spot found within 15mm of {anchor} ({total} candidates total)")
            stuck.append(ref)
            continue
        d, x, y, rot = cands[0]
        pl.move(board, ref, x, y, rot, "F.Cu")
        print(f"{ref}: moved to ({x}, {y}) rot={rot}, {d}mm from original")
        moved.append(ref)

    pcbnew.SaveBoard(PCB_PATH, board)
    print(f"\nMoved {len(moved)}/{len(NEW_REFS)}. Stuck: {stuck}")


if __name__ == "__main__":
    main()

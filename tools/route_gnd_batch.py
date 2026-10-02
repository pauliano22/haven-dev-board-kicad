"""
Close the GND "missing connection" gaps between the new components and
the board's existing GND copper -- all short distances (0.1-9mm), mostly
direct same-layer connections. Each segment is verified with seg_ok
before placing (this project's own established discipline), and the
whole board is re-checked with real DRC after, not assumed clean from
the per-segment check alone.

Run from kicad/ directory.
"""
import sys
sys.path.insert(0, "../tools")
import pcbnew
import route_lib as rl
import placement_lib as pl

PCB_PATH = "haven_dev_board.kicad_pcb"

# (p1, p2, layer) -- same-F.Cu-layer pairs only this pass; cross-layer
# pairs (B.Cu <-> F.Cu) need a via and are handled separately.
SAME_LAYER_PAIRS = [
    ((44.5703, 106.0201), (45.545, 105.0001), "F.Cu"),
    ((55.615, 115.448), (57.5525, 115.198), "F.Cu"),
    ((55.615, 115.448), (53.665, 117.298), "F.Cu"),
    ((55.615, 115.448), (53.665, 113.598), "F.Cu"),
    ((57.5525, 115.198), (57.565, 117.298), "F.Cu"),
    ((58.578094, 113.323), (57.565, 113.598), "F.Cu"),
    ((58.278094, 113.843442), (57.5525, 115.198), "F.Cu"),
    ((58.4404, 112.2719), (58.4404, 112.6219), "F.Cu"),
    ((62.2603, 123.1518), (60.545, 122.0001), "F.Cu"),
    ((68.545, 108.0001), (72.8625, 107.5), "F.Cu"),
    ((72.8625, 107.5), (76.2895, 105.5154), "F.Cu"),
]

# (f_cu_point, b_cu_point) -- needs a via at the F.Cu point, then a track
# on B.Cu from there to the existing B.Cu item.
CROSS_LAYER_PAIRS = [
    ((59.1404, 111.4479), (60.366, 110.8817)),
    ((85.4327, 127.9999), (79.2898, 126.9901)),
    ((85.0001, 107.455), (84.9414, 110.7776)),
]

# C52's existing-side point is on In4.Cu specifically -- needs a via.
VIA_NEEDED_PAIRS = [
    ((45.545, 118.0001), (47.9298, 117.7295)),  # C52 pad2 (F.Cu) -> In4.Cu track
]


def main():
    board = pcbnew.LoadBoard(PCB_PATH)
    placed, skipped = 0, []

    for p1, p2, layer in SAME_LAYER_PAIRS:
        if pl.seg_ok(board, "GND", layer, p1, p2, 0.2):
            pl.add_seg(board, "GND", layer, p1, p2, 0.2)
            placed += 1
        else:
            skipped.append((p1, p2, layer, "seg blocked"))

    for f_pt, b_pt in CROSS_LAYER_PAIRS:
        via_ok, why = pl.via_ok(board, "GND", f_pt)
        if not via_ok:
            skipped.append((f_pt, b_pt, "via", f"via blocked: {why}"))
            continue
        pl.add_via(board, "GND", f_pt)
        if pl.seg_ok(board, "GND", "B.Cu", f_pt, b_pt, 0.2):
            pl.add_seg(board, "GND", "B.Cu", f_pt, b_pt, 0.2)
            placed += 1
        else:
            skipped.append((f_pt, b_pt, "B.Cu", "seg blocked after via"))

    for f_pt, in4_pt in VIA_NEEDED_PAIRS:
        via_ok, why = pl.via_ok(board, "GND", f_pt)
        if not via_ok:
            skipped.append((f_pt, in4_pt, "via", f"via blocked: {why}"))
            continue
        pl.add_via(board, "GND", f_pt)
        if pl.seg_ok(board, "GND", "In4.Cu", f_pt, in4_pt, 0.2):
            pl.add_seg(board, "GND", "In4.Cu", f_pt, in4_pt, 0.2)
            placed += 1
        else:
            skipped.append((f_pt, in4_pt, "In4.Cu", "seg blocked after via"))

    rl.refill_zones(board)
    pcbnew.SaveBoard(PCB_PATH, board)
    print(f"Placed {placed} connections. Skipped {len(skipped)}:")
    for s in skipped:
        print(" ", s)


if __name__ == "__main__":
    main()

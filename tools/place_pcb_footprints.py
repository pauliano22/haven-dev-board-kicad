"""
Place ALL new footprints on the real PCB (codec, mic, boost converter IC,
and every new passive from schematic stages 1-3), with correct per-pad
net assignments, and remove the old ADAU1860 + PDM mic footprints.

FOOTPRINT PLACEMENT ONLY -- no routing. Expect DRC to report many
unrouted/unconnected nets after this; that's the honest, expected state
for this stage, not a bug.

Footprint choices, matching this project's own existing conventions
(reusing its R0402/C0402 rather than inventing new-but-equivalent ones):
  R0402, C0402: this project's own existing footprints (already used
    throughout the rest of the board)
  L_1210_3225Metric: a real power-inductor-sized footprint (0402/L0402 is
    far too small for a 10uH boost inductor's current handling)
  D_SOD-123, SOT-23-5: standard KiCad library footprints, vendored into
    this project's local footprints.pretty to match its self-contained,
    single-fp-lib-table convention
  TAC5301-Q1, CMA-4544PF-W: custom-built this session (see
    build_pcb_footprints.py)

Run from kicad/ directory, after build_pcb_footprints.py.
"""
from kiutils.board import Board
from kiutils.footprint import Footprint
from kiutils.items.common import Position, Net

PCB_PATH = "haven_dev_board.kicad_pcb"

NEW_NETS = [
    "MIC_P", "MIC_BIAS", "MIC_BIAS_NODE", "SW_NODE", "FB_NODE",
    "HVDD", "DREG_DECOUPLE", "VREF_DECOUPLE",
]

TAC5301_PAD_NETS = {
    "2": "BCLK", "3": "LRCLK", "5": "DIN", "4": "DOUT",
    "7": "SCL1", "8": "SDA1",
    "15": "MIC_P", "16": "GND",
    "19": "DAC_N", "20": "DAC_P",
    "1": "DREG_DECOUPLE", "6": "3V3", "11": "3V3", "23": "3V3",
    "13": "HVDD", "14": "MIC_BIAS", "24": "VREF_DECOUPLE",
    "A1": "GND", "A2": "GND", "A3": "GND", "A4": "GND",
    "25": "GND",
}
MIC_PAD_NETS = {"1": "MIC_BIAS_NODE", "2": "GND"}
TPS61040_PAD_NETS = {"1": "SW_NODE", "2": "GND", "3": "FB_NODE", "4": "V_BAT", "5": "V_BAT"}

# (ref, footprint_lib_entry, value, x, y, {pad1: net1, pad2: net2})
PASSIVES = [
    ("R29", "R0402", "2.2k",    45.0, 130.0, {"1": "MIC_BIAS", "2": "MIC_BIAS_NODE"}),
    ("C50", "C0402", "1uF",     50.0, 130.0, {"1": "MIC_BIAS_NODE", "2": "MIC_P"}),
    ("C51", "C0402", "0.1uF",   45.0, 105.0, {"1": "DREG_DECOUPLE", "2": "GND"}),
    ("C52", "C0402", "1uF",     45.0, 118.0, {"1": "VREF_DECOUPLE", "2": "GND"}),
    ("C53", "C0402", "4.7uF",   68.0, 108.0, {"1": "V_BAT", "2": "GND"}),
    ("C54", "C0402", "1uF",     85.0, 108.0, {"1": "HVDD", "2": "GND"}),
    ("R30", "R0402", "1.0M",    85.0, 118.0, {"1": "HVDD", "2": "FB_NODE"}),
    ("R31", "R0402", "160k",    85.0, 128.0, {"1": "FB_NODE", "2": "GND"}),
    ("C55", "C0402", "22pF",    90.0, 118.0, {"1": "HVDD", "2": "FB_NODE"}),
    ("C56", "C0402", "1uF 35V", 60.0, 140.0, {"1": "MIC_BIAS", "2": "GND"}),
    ("L1",  "L_1210_3225Metric", "10uH", 68.0, 118.0, {"1": "V_BAT", "2": "SW_NODE"}),
    ("D1",  "D_SOD-123", "MBR0530T1G", 78.0, 118.0, {"1": "SW_NODE", "2": "HVDD"}),
]


def get_or_create_net(board, name):
    for n in board.nets:
        if n.name == name:
            return n.number
    new_number = max(n.number for n in board.nets) + 1
    board.nets.append(Net(number=new_number, name=name))
    return new_number


def set_pad_nets(footprint, board, pad_net_map):
    for pad in footprint.pads:
        if pad.number in pad_net_map:
            name = pad_net_map[pad.number]
            number = get_or_create_net(board, name)
            pad.net = Net(number=number, name=name)


def place_footprint(board, lib_entry, ref, value, x, y, pad_net_map, rotation=0):
    fp = Footprint.from_file(f"footprints.pretty/{lib_entry}.kicad_mod")
    fp.libraryNickname = "haven_footprints"
    fp.position = Position(X=x, Y=y, angle=rotation)
    fp.properties["Reference"] = ref
    fp.properties["Value"] = value
    set_pad_nets(fp, board, pad_net_map)
    board.footprints.append(fp)
    return fp


def main():
    board = Board.from_file(PCB_PATH)

    for name in NEW_NETS:
        get_or_create_net(board, name)

    old_u15 = [f for f in board.footprints if f.properties.get("Reference") == "U15"]
    assert len(old_u15) == 1, f"expected exactly 1 U15 footprint, found {len(old_u15)}"
    board.footprints.remove(old_u15[0])
    print("Removed old ADAU1860 footprint")

    old_mic = [f for f in board.footprints if "SPH0641" in f.properties.get("Value", "")]
    for f in old_mic:
        board.footprints.remove(f)
    print(f"Removed {len(old_mic)} old PDM mic footprint(s)")

    place_footprint(board, "TAC5301-Q1", "U15", "TAC5301QRGERQ1",
                     58.6153, 111.4477, TAC5301_PAD_NETS)
    place_footprint(board, "CMA-4544PF-W", "MIC1", "CMA-4544PF-W",
                     58.6153, 90.0, MIC_PAD_NETS)
    place_footprint(board, "SOT-23-5", "U16", "TPS61040DBVR",
                     75.0, 108.0, TPS61040_PAD_NETS)

    for ref, lib_entry, value, x, y, pad_nets in PASSIVES:
        place_footprint(board, lib_entry, ref, value, x, y, pad_nets)

    board.to_file(PCB_PATH)
    print("Wrote", PCB_PATH, f"-- placed {3 + len(PASSIVES)} new footprints")


if __name__ == "__main__":
    main()

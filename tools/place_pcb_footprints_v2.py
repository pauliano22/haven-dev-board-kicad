"""
Place the new footprints on the real PCB using pcbnew's own API directly
(NOT kiutils) -- this project's own established convention for PCB-level
work (see route_lib.py's header comment), and for a real, hard reason
found this session: removing a footprint via kiutils' plain Python list
.remove() doesn't update KiCad's internal connectivity/zone bookkeeping,
and segfaults pcbnew on save. board.Remove(footprint) (the real API) does
it correctly -- verified by testing both, isolated, before touching the
real project file.

Run from the kicad/ directory, on the real project file in place.
"""
import pcbnew

PCB_PATH = "haven_dev_board.kicad_pcb"
FP_LIB = "footprints.pretty"

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

NEW_NET_NAMES = sorted(set(
    list(TAC5301_PAD_NETS.values()) + list(MIC_PAD_NETS.values()) +
    list(TPS61040_PAD_NETS.values()) +
    [n for _, _, _, _, _, pads in PASSIVES for n in pads.values()]
))


def get_or_create_net(board, name):
    existing = board.FindNet(name)
    if existing is not None:
        return existing
    net = pcbnew.NETINFO_ITEM(board, name)
    board.Add(net)
    return net


def place_footprint(board, lib_entry, ref, value, x, y, pad_net_map, rotation=0):
    fp = pcbnew.FootprintLoad(FP_LIB, lib_entry)
    assert fp is not None, f"could not load footprint {lib_entry}"
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    if rotation:
        fp.SetOrientationDegrees(rotation)
    fp.SetReference(ref)
    fp.SetValue(value)
    for pad in fp.Pads():
        num = pad.GetNumber()
        if num in pad_net_map:
            net = get_or_create_net(board, pad_net_map[num])
            pad.SetNet(net)
    board.Add(fp)
    return fp


def main():
    board = pcbnew.LoadBoard(PCB_PATH)

    for name in NEW_NET_NAMES:
        get_or_create_net(board, name)

    u15_list = [fp for fp in board.GetFootprints() if fp.GetReference() == "U15"]
    assert len(u15_list) == 1, f"expected exactly 1 U15 footprint, found {len(u15_list)}"
    board.Remove(u15_list[0])
    print("Removed old ADAU1860 footprint")

    mic_list = [fp for fp in board.GetFootprints() if "SPH0641" in fp.GetValue()]
    for fp in mic_list:
        board.Remove(fp)
    print(f"Removed {len(mic_list)} old PDM mic footprint(s)")

    place_footprint(board, "TAC5301-Q1", "U15", "TAC5301QRGERQ1", 58.6153, 111.4477, TAC5301_PAD_NETS)
    place_footprint(board, "CMA-4544PF-W", "MIC1", "CMA-4544PF-W", 58.6153, 90.0, MIC_PAD_NETS)
    place_footprint(board, "SOT-23-5", "U16", "TPS61040DBVR", 75.0, 108.0, TPS61040_PAD_NETS)
    for ref, lib_entry, value, x, y, pad_nets in PASSIVES:
        place_footprint(board, lib_entry, ref, value, x, y, pad_nets)

    pcbnew.SaveBoard(PCB_PATH, board)
    print(f"Wrote {PCB_PATH} -- placed {3 + len(PASSIVES)} new footprints via pcbnew API")


if __name__ == "__main__":
    main()

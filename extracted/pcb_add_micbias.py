"""
Fill a real gap found this tick: R_MICBIAS and C_MICIN (the mic-bias
network from the codec/mic schematic redesign) were never actually placed
on the PCB -- only the codec and mic footprints themselves were. Adding
them now, using the same real 0402/C0402 footprints already used
elsewhere on this board.
"""
import pcbnew

PCB_PATH = "/home/paul22iac/projects/active/haven_dev_board_kicad/kicad/haven_dev_board.kicad_pcb"
FP_LIB = "/home/paul22iac/projects/active/haven_dev_board_kicad/kicad/footprints.pretty"

board = pcbnew.LoadBoard(PCB_PATH)


def mm(v):
    return pcbnew.VECTOR2I(int(v[0] * 1e6), int(v[1] * 1e6))


def get_or_create_net(name):
    net = board.GetNetInfo().GetNetItem(name)
    if net is not None and net.GetNetCode() != 0:
        return net
    new_net = pcbnew.NETINFO_ITEM(board, name)
    board.Add(new_net)
    return new_net


def place(fp, ref, value, pos_mm, pad_nets):
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(mm(pos_mm))
    for pad in fp.Pads():
        num = pad.GetNumber()
        net_name = pad_nets.get(num)
        if net_name:
            pad.SetNet(get_or_create_net(net_name))
    board.Add(fp)


r_fp = pcbnew.FootprintLoad(FP_LIB, "R0402")
place(r_fp, "R_MICBIAS", "2.2k", (90.0, -13.0), {'1': 'MICBIAS', '2': 'MIC_IN'})

c_fp = pcbnew.FootprintLoad(FP_LIB, "C0402")
place(c_fp, "C_MICIN", "1uF", (94.0, -13.0), {'1': 'MIC_IN', '2': 'MIC_IN_AC'})

board.Save(PCB_PATH)
filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())
board.Save(PCB_PATH)
print("Saved", PCB_PATH)

"""
Place TLV320AIC3100 (codec) and CMA-4544PF-W (mic) footprints on the real
PCB, following the schematic-side codec/mic redesign already committed.

TLV320AIC3100 footprint: Texas_RHB0032M_VQFN-32-1EP_5x5mm_P0.5mm -- this
is TI's own real footprint for this EXACT part (RHB is the datasheet's
own package designator, confirmed against its pin-diagram page), copied
from KiCad's official library, not hand-derived. Pad 33 is the exposed
thermal pad; tied to GND (no explicit datasheet guidance against it, and
tying an unlabeled thermal pad to ground is the standard default).

CMA-4544PF-W footprint: no official KiCad library footprint exists for
this part (it's a plain round electret capsule, not a standard IC
package), so this builds one from the datasheet's own mechanical drawing:
2 through-hole pins (Term.1/Term.2) on a 2.54mm pitch, silkscreen circle
approximating the real 9.7mm body diameter. The datasheet's own spec
sheet explicitly says "terminal: pin type (hand soldering only)" --
through-hole, not SMD, so this deliberately does NOT use SMD pads.
Exact pin-to-body-center offset wasn't pixel-verified from the drawing
(flagged, not hidden) -- centering the body circle between the two pins
is a reasonable first approximation for placement/DRC purposes, not a
manufacturing-ready footprint.

Placement: found via a real courtyard-and-copper scan (same discipline
as the charger placement fix earlier this session, after that one caught
a real short from skipping the copper check).
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


def load_fp(lib_path, name):
    fp = pcbnew.FootprintLoad(lib_path, name)
    if fp is None:
        raise RuntimeError(f"could not load footprint {name}")
    return fp


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
    return fp


def remove_fp(ref):
    for fp in list(board.GetFootprints()):
        if fp.GetReference() == ref:
            board.Remove(fp)
            print(f"Removed old {ref} footprint")
            return
    print(f"WARNING: {ref} not found")


def make_mic_capsule_footprint():
    """2-pin THT footprint approximating CMA-4544PF-W's real capsule package."""
    fp = pcbnew.FOOTPRINT(board)
    # Empty library nickname, matching how every other footprint on this
    # board is referenced (checked directly: FootprintLoad-sourced parts
    # like U15/U_BUCK1 all end up with a blank nickname too) -- an
    # earlier attempt used a real-looking but unregistered "footprints"
    # nickname, which DRC correctly flagged as lib_footprint_issues.
    fp.SetFPID(pcbnew.LIB_ID("", "CMA-4544PF-W"))

    PIN_PITCH = 2.54
    PAD_DRILL = 0.9
    PAD_DIA = 1.6
    BODY_DIA = 9.7

    for num, x in (("1", -PIN_PITCH / 2), ("2", PIN_PITCH / 2)):
        pad = pcbnew.PAD(fp)
        pad.SetNumber(num)
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE if num == "2" else pcbnew.PAD_SHAPE_RECT)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        pad.SetSize(pcbnew.VECTOR2I(int(PAD_DIA * 1e6), int(PAD_DIA * 1e6)))
        pad.SetDrillSize(pcbnew.VECTOR2I(int(PAD_DRILL * 1e6), int(PAD_DRILL * 1e6)))
        pad.SetLayerSet(pcbnew.LSET.AllCuMask())
        pad.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), 0))
        fp.Add(pad)

    circle = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_CIRCLE)
    circle.SetLayer(pcbnew.F_SilkS)
    circle.SetCenter(pcbnew.VECTOR2I(0, 0))
    circle.SetEnd(pcbnew.VECTOR2I(int(BODY_DIA / 2 * 1e6), 0))
    circle.SetWidth(int(0.15 * 1e6))
    fp.Add(circle)

    ref_field = fp.Reference()
    ref_field.SetPosition(pcbnew.VECTOR2I(0, int(-BODY_DIA / 2 * 1e6 - 1.5e6)))
    return fp


# ---- Remove old parts ----
remove_fp('U15')  # old ADAU1860
remove_fp('U13')  # old PDM mic

# ---- Place TLV320AIC3100 ----
# Position re-derived after the first attempt's mic placement turned out to
# overhang a real notch cut into the board outline (found via DRC: a
# copper_edge_clearance + silk_edge_clearance violation) -- a plain
# bounding-box free-space scan missed it because this board's outline
# isn't a simple rectangle. Re-scanned using the real board polygon
# (BOARD.GetBoardPolygonOutlines) instead of just its bounding box.
codec_fp = load_fp(FP_LIB, "Texas_RHB0032M_VQFN-32-1EP_5x5mm_P0.5mm_EP2.1x2.1mm")
place(codec_fp, "U15", "TLV320AIC3100", (48.38, -0.72), {
    '1': 'GND', '2': '3V3', '3': '+1.8V', '4': 'DOUT',
    '5': 'DIN', '6': 'LRCLK', '7': 'BCLK', '8': 'BCLK',
    '9': 'SDA1', '10': 'SCL1', '11': 'GND', '12': 'MICBIAS',
    '13': 'MIC_IN_AC', '14': 'GND', '15': 'GND', '16': 'GND',
    '17': 'V_LS', '18': 'GND', '19': None, '20': None,
    '21': None, '22': None, '23': None, '24': None,
    '25': None, '26': None, '27': 'DAC_P', '28': 'V_LS',
    '29': 'GND', '30': 'DAC_N', '31': '3V3', '32': None,
    '33': 'GND',  # exposed thermal pad
})

# ---- Place CMA-4544PF-W ----
mic_fp = make_mic_capsule_footprint()
place(mic_fp, "U13", "CMA-4544PF-W", (82.88, -10.22), {
    '1': 'MIC_IN',
    '2': 'GND',
})

board.Save(PCB_PATH)
print("Saved", PCB_PATH)

# Refill copper zones -- skipping this after adding new through-hole pads
# left stale hole_clearance violations against zones that hadn't been
# recomputed around the new holes (found via DRC on the first attempt).
filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())
board.Save(PCB_PATH)
print("Refilled zones and re-saved", PCB_PATH)

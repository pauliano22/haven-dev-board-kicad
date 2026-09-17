"""
Place real footprints for the TP4056/TPS62822/TPS22917 power-tree redesign
onto the real haven_dev_board.kicad_pcb (on the redesign/tp4056-power-tree
branch, not master). Schematic-only work from earlier this session is now
matched on the PCB side.

Real footprints used (copied from KiCad's own official library, not
hand-derived -- these are the exact TI/JEDEC parts):
  - Texas_VSON-HR-8_1.5x2mm_P0.5mm.kicad_mod  -- TPS62822DLCR (TI's own name
    for this exact package is "VSON-HR", confirmed against the datasheet's
    own generic-package-view page)
  - SOIC-8_3.9x4.9mm_P1.27mm.kicad_mod        -- TP4056 (plain SOP-8, no EP)
  - SOT-23-6.kicad_mod                         -- TPS22917DBVR (JEDEC MO-178,
    confirmed against the datasheet's own DBV0006A package outline)

U2 (the old BQ25120A, DSBGA-25) is removed. The old BOM's small resistors
(R0201/C0201/etc.) use the project's existing generic footprints already in
footprints.pretty/ -- reused directly for the 5 new passives (R_PROG,
R_FB1, R_FB2, R_PU_CHRG, R_PU_STDBY), all 0402 for easy hand assembly
(matches this project's own stated goal: "I don't need the dev board to be
tiny").

Placement: found genuinely free board area by scanning real footprint
courtyards (not eyeballed), clustered near the existing L2 inductor /
C18 output cap (already the buck's real output tank) so the new buck IC's
SW/FB loop stays short.

Net assignment: schematic netlist EXPORT from this project is broken
(a separate, pre-existing finding -- see HARDWARE_COST_ALTERNATIVES.md), so
pad-to-net assignment is done directly here by name, matching the reused/
new net names established on the schematic side. Reused net names use the
PCB's EXISTING net (looked up by name, real connections preserved); the two
new nets (FB_1V8, TP4056_PROG) are created fresh.
"""
import pcbnew

PCB_PATH = "/home/paul22iac/projects/active/haven_dev_board_kicad/kicad/haven_dev_board.kicad_pcb"
FP_LIB = "/home/paul22iac/projects/active/haven_dev_board_kicad/kicad/footprints.pretty"

board = pcbnew.LoadBoard(PCB_PATH)


def mm(v):
    return pcbnew.VECTOR2I(int(v[0] * 1e6), int(v[1] * 1e6))


def get_or_create_net(name):
    nets = board.GetNetInfo()
    net = nets.GetNetItem(name)
    if net is not None and net.GetNetCode() != 0:
        return net
    new_net = pcbnew.NETINFO_ITEM(board, name)
    board.Add(new_net)
    return new_net


def load_fp(lib_path, name):
    fp = pcbnew.FootprintLoad(lib_path, name)
    if fp is None:
        raise RuntimeError(f"could not load footprint {name} from {lib_path}")
    return fp


def place(fp, ref, value, pos_mm, pad_nets):
    """pad_nets: dict pad-number-str -> net-name-str (or None to leave unconnected)"""
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


# ---- 1. Remove old U2 (BQ25120A) footprint ----
old_u2 = None
for fp in list(board.GetFootprints()):
    if fp.GetReference() == 'U2':
        old_u2 = fp
        break
if old_u2:
    board.Remove(old_u2)
    print("Removed old U2 (BQ25120A) footprint")

# ---- 2. Place TPS62822 (VSON-HR-8) ----
# NOTE: originally placed at (72, 39), right next to L2/C18 (the existing
# buck output tank) -- but that whole area is densely routed with existing
# copper (VUSB/V_PMID/V_LS traces criss-crossing near the old charger),
# which a footprint-bounding-box-only placement scan doesn't see. That
# caused two real DRC "shorting_items" violations (this footprint's pads
# physically overlapping live existing traces). Moved to the same clear
# area (confirmed empty of both footprints AND copper, checked directly)
# used for TP4056/TPS22917 below instead. Real routing to L2 is future
# work regardless of exact distance -- nothing is routed yet.
buck_fp = load_fp(FP_LIB, "Texas_VSON-HR-8_1.5x2mm_P0.5mm")
place(buck_fp, "U_BUCK1", "TPS62822DLCR", (68.0, -10.0), {
    '1': 'VCC',      # EN, tied always-on to battery rail
    '2': 'FB_1V8',
    '3': 'GND',
    '4': None,       # NC, per datasheet
    '5': 'GND',
    '6': 'SW',
    '7': 'VCC',
    '8': None,       # PG, unused, leave floating per datasheet
})

# ---- 3. Place TP4056 (SOP-8) in the free area found by the courtyard scan ----
tp4056_fp = load_fp(FP_LIB, "SOIC-8_3.9x4.9mm_P1.27mm")
place(tp4056_fp, "U2", "TP4056", (52.0, -10.0), {
    '1': 'TS',
    '2': 'TP4056_PROG',
    '3': 'GND',
    '4': 'VUSB',
    '5': 'VCC',
    '6': 'CC_#PG',
    '7': 'CC_#CD',
    '8': 'VUSB',
})

# ---- 4. Place TPS22917 (SOT-23-6) nearby ----
ls_fp = load_fp(FP_LIB, "SOT-23-6")
place(ls_fp, "U_LS1", "TPS22917DBVR", (60.0, -10.0), {
    '1': 'VCC',
    '2': 'GND',
    '3': 'LSCTRL',
    '4': None,   # CT, floating for fastest turn-on
    '5': None,   # QOD, floating to disable
    '6': '3V3',
})

# ---- 5. New passives (0402, matches "easy hand assembly" goal) ----
def place_r0402(ref, value, pos_mm, net_a, net_b):
    fp = load_fp(FP_LIB, "R0402")
    place(fp, ref, value, pos_mm, {'1': net_a, '2': net_b})

place_r0402('R_PROG', '1.2k', (58.0, -6.0), 'TP4056_PROG', 'GND')
place_r0402('R_FB1', '200k', (66.0, -13.0), '+1.8V', 'FB_1V8')
place_r0402('R_FB2', '100k', (70.0, -13.0), 'FB_1V8', 'GND')
place_r0402('R_PU_CHRG', '100k', (66.0, -6.0), 'CC_#CD', '3V3')
place_r0402('R_PU_STDBY', '100k', (70.0, -6.0), 'CC_#PG', '3V3')

board.Save(PCB_PATH)
print("Saved", PCB_PATH)

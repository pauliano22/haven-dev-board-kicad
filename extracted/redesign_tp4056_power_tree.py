"""
Haven dev board power-tree redesign, take 2 (scratchpad regenerated after the
prior session's tmp files were cleared).

Replaces U2 (BQ25120AYFPR charger/PMIC) with three real, currently-stocked,
datasheet-verified parts:
  - TP4056 (linear Li-Ion charger, SOP-8)      -- replaces the charger half
  - TPS62822DLC (adjustable buck, VQFN-8)      -- replaces SYS's 1.8V rail
  - TPS22917 (load switch, SOT-23-6)           -- replaces LS/LDO's 3V3 rail
      (LS/LDO's real default mode was a plain load switch, not true LDO
       regulation -- confirmed from the BQ25120A datasheet last session --
       so a load switch is a faithful replacement, not a downgrade.)

All three pinouts below were pulled from real datasheets this session, not
guessed:
  - TP4056: sparkfun-hosted TP4056.pdf (NanJing Top Power ASIC's own doc)
  - TPS62822: ti.com/lit/ds/symlink/tps62822.pdf, SLVSDV6C
  - TPS22917: ti.com/lit/ds/symlink/tps22917.pdf, SLVSDW8B

Net-reuse findings from inspecting the REAL schematic before writing this
(see HARDWARE_COST_ALTERNATIVES.md for the full trace):
  - L2 (2.2uH inductor) pin 1 is already on a label named "SW", pin 2 is
    already on "+1.8V", with 4 existing decoupling caps on +1.8V already
    (C1, C4, C18, C20) -- this is genuinely the buck's existing output tank,
    left over from BQ25120A's SYS pin. No new output cap needed.
  - "3V3" already has 4 decoupling caps (C5, C17, C29, C48) from other
    consumers on that rail -- no new output cap needed for the load switch
    either.
  - "TS" (battery thermistor sense) already has a real 2-resistor divider
    (R6, R13) wired at the battery -- reuse this net for TP4056's TEMP pin
    instead of inventing new resistors (the prior attempt's mistake).
  - "LSCTRL" is already driven by a real MCU GPIO (MDBT531 pin 27) -- reuse
    directly for TPS22917's ON pin.
  - "VUSB" is the real 5V USB input rail (already has D2/C22/R27 on it) --
    TP4056's VCC feeds from here, and TP4056's CE (must not float) is tied
    to this same rail (standard "always enabled when powered" wiring).
  - "VCC" is this board's odd but consistent name for the *battery* rail
    (U2's old BAT pins were on it) -- TP4056's BAT, TPS62822's VIN, and
    TPS22917's VIN all land here.
  - CD#/PG# (old BQ25120A status flags, push-pull) fed two real MCU GPIOs
    directly with NO pull-up anywhere on either net. TP4056's CHRG/STDBY
    are open-drain -- reusing those nets as-is would leave the GPIOs
    floating whenever the pin is deasserted. Fixed by adding two new 100k
    pull-ups to 3V3 (not VUSB/5V -- these feed a 3.3V-domain MCU input,
    pulling to 5V would over-volt the pin).

Net new nets introduced: only FB_1V8 (buck feedback midpoint) and
TP4056_PROG (charge-current-set resistor node). Down from 3 in the prior
attempt to 2, by reusing TS and VUSB instead of inventing TP4056_TEMP and a
separate CE net. If the same kiutils/kicad-cli dangling-label anomaly shows
up again, it's now scoped to just these two.
"""
import copy
import uuid
from kiutils.schematic import Schematic
from kiutils.items.common import Position, Effects, Font, Justify, Property
from kiutils.items.schitems import SchematicSymbol
from kiutils.symbol import Symbol, SymbolPin

SRC = "/home/paul22iac/projects/active/haven_dev_board_kicad/kicad/haven_dev_board.kicad_sch"
OUT = "/tmp/claude-1000/-home-paul22iac/de6df91d-5626-4f43-95cb-adf67fb0294d/scratchpad/haven_dev_board_sch_V3.kicad_sch"

PROJ = "haven_dev_board"


def new_uuid():
    return str(uuid.uuid4())


def eff(justify=None):
    return Effects(font=Font(height=1.27, width=1.27), justify=justify or Justify())


def make_box_symbol(lib_id, ref_prefix, value, left_pins, right_pins, box_h=None, box_w=15.24):
    """left_pins/right_pins: list of (number, name), top-to-bottom as drawn."""
    n_rows = max(len(left_pins), len(right_pins))
    if box_h is None:
        box_h = (n_rows - 1) * 2.54 + 5.08
    half_h = box_h / 2

    top_y = half_h - 2.54  # first pin row, matching U2's style (pins start inset from top edge)

    graphics_unit = Symbol(entryName=lib_id, unitId=0, styleId=1, extends=None)
    from kiutils.items.syitems import SyRect
    from kiutils.items.common import Stroke, Fill
    graphics_unit.graphicItems.append(SyRect(
        start=Position(X=-box_w / 2, Y=-half_h, angle=None),
        end=Position(X=box_w / 2, Y=half_h, angle=None),
        stroke=Stroke(width=0.254, type='default'),
        fill=Fill(type='background'),
    ))

    pins_unit = Symbol(entryName=lib_id, unitId=1, styleId=1, extends=None)
    for i, (num, name) in enumerate(left_pins):
        y = top_y - i * 2.54
        p = SymbolPin(
            electricalType='passive', graphicalStyle='line',
            position=Position(X=-box_w / 2 - 2.54, Y=y, angle=0),
            length=2.54, name=name, number=num,
            nameEffects=eff(), numberEffects=eff(),
        )
        pins_unit.pins.append(p)
    for i, (num, name) in enumerate(right_pins):
        y = top_y - i * 2.54
        p = SymbolPin(
            electricalType='passive', graphicalStyle='line',
            position=Position(X=box_w / 2 + 2.54, Y=y, angle=180),
            length=2.54, name=name, number=num,
            nameEffects=eff(), numberEffects=eff(),
        )
        pins_unit.pins.append(p)

    top = Symbol(entryName=lib_id, extends=None, inBom=True, onBoard=True)
    top.properties = [
        Property(key='Reference', value=ref_prefix,
                  position=Position(X=-box_w / 2, Y=half_h + 2.54, angle=0), effects=eff()),
        Property(key='Value', value=value,
                  position=Position(X=-box_w / 2, Y=-half_h - 2.54, angle=0), effects=eff()),
    ]
    top.units = [graphics_unit, pins_unit]
    return top


def make_instance(ref, lib_id, value, x, y):
    inst = SchematicSymbol()
    inst.libId = f'{PROJ}:{lib_id}'
    inst.position = Position(X=x, Y=y, angle=0)
    inst.unit = 1
    inst.inBom = True
    inst.onBoard = True
    inst.uuid = new_uuid()
    inst.properties = [
        Property(key='Reference', value=ref, position=Position(X=x, Y=y - 12, angle=0), effects=eff()),
        Property(key='Value', value=value, position=Position(X=x, Y=y + 12, angle=0), effects=eff()),
    ]
    return inst


def add_label(sch, text, x, y):
    lbl_cls = type(sch.labels[0])
    lbl = lbl_cls(text=text, position=Position(X=x, Y=y, angle=0),
                  effects=eff(Justify(horizontally='left')), uuid=new_uuid())
    sch.labels.append(lbl)


RESISTOR_BOX_W = 5.08  # matches the real R28 symbol's own box width exactly


def make_resistor_symbol(lib_id, value):
    return make_box_symbol(lib_id, 'R', value, [('1', '1')], [('2', '2')],
                            box_h=5.08, box_w=RESISTOR_BOX_W)


def add_resistor(sch, ref, value, x, y, pin1_label, pin2_label):
    lib_id = ref  # bare, matches R28-style convention (one symbol per instance)
    sch.libSymbols.append(make_resistor_symbol(lib_id, value))
    inst = make_instance(ref, lib_id, value, x, y)
    sch.schematicSymbols.append(inst)
    # pin X = +/-(box_w/2 + pin length), pin length is 2.54 (make_box_symbol's fixed stub length)
    pin_x = RESISTOR_BOX_W / 2 + 2.54
    add_label(sch, pin1_label, x - pin_x, y)
    add_label(sch, pin2_label, x + pin_x, y)


def main():
    sch = Schematic.from_file(SRC)

    # ---- 1. Remove U2 (BQ25120A) instance + its 25 pin labels ----
    u2_inst = next(i for i in sch.schematicSymbols
                   if next((p.value for p in i.properties if p.key == 'Reference'), '') == 'U2')
    u2_sym = next(s for s in sch.libSymbols if s.libId == 'U2')
    ox, oy = u2_inst.position.X, u2_inst.position.Y
    u2_pin_coords = []
    for unit in u2_sym.units:
        for p in unit.pins:
            u2_pin_coords.append((ox + p.position.X, oy + p.position.Y))

    removed = 0
    kept_labels = []
    for lbl in sch.labels:
        hit = any(abs(lbl.position.X - x) < 0.01 and abs(lbl.position.Y - y) < 0.01
                  for x, y in u2_pin_coords)
        if hit:
            removed += 1
        else:
            kept_labels.append(lbl)
    sch.labels = kept_labels
    print(f"Removed {removed} labels belonging to U2 (expected 25)")

    sch.schematicSymbols = [i for i in sch.schematicSymbols if i is not u2_inst]
    sch.libSymbols = [s for s in sch.libSymbols if s.libId != 'U2']
    print("Removed U2 instance + libSymbol")

    # ---- 2. TP4056 (new "U2") ----
    tp4056_left = [('1', 'TEMP'), ('2', 'PROG'), ('3', 'GND'), ('4', 'VCC')]
    tp4056_right = [('8', 'CE'), ('7', 'CHRG'), ('6', 'STDBY'), ('5', 'BAT')]
    sch.libSymbols.append(make_box_symbol('TP4056', 'U', 'TP4056', tp4056_left, tp4056_right))
    tp4056_x, tp4056_y = 300, 260
    tp4056_inst = make_instance('U2', 'TP4056', 'TP4056', tp4056_x, tp4056_y)
    sch.schematicSymbols.append(tp4056_inst)
    box_h = (4 - 1) * 2.54 + 5.08
    top_y = box_h / 2 - 2.54
    tp4056_pin_labels = {
        '1': 'TS', '2': 'TP4056_PROG', '3': 'GND', '4': 'VUSB',
        '8': 'VUSB', '7': 'CC_#CD', '6': 'CC_#PG', '5': 'VCC',
    }
    for i, (num, name) in enumerate(tp4056_left):
        y = tp4056_y + top_y - i * 2.54
        x = tp4056_x - 15.24 / 2 - 2.54
        add_label(sch, tp4056_pin_labels[num], x, y)
    for i, (num, name) in enumerate(tp4056_right):
        y = tp4056_y + top_y - i * 2.54
        x = tp4056_x + 15.24 / 2 + 2.54
        add_label(sch, tp4056_pin_labels[num], x, y)

    # ---- 3. TPS62822DLC (new "U_BUCK1") ----
    buck_left = [('1', 'EN'), ('2', 'FB'), ('3', 'AGND'), ('4', 'NC')]
    buck_right = [('8', 'PG'), ('7', 'VIN'), ('6', 'SW'), ('5', 'PGND')]
    sch.libSymbols.append(make_box_symbol('TPS62822DLC', 'U', 'TPS62822DLCR', buck_left, buck_right))
    buck_x, buck_y = 300, 300
    buck_inst = make_instance('U_BUCK1', 'TPS62822DLC', 'TPS62822DLCR', buck_x, buck_y)
    sch.schematicSymbols.append(buck_inst)
    buck_pin_labels = {'1': 'VCC', '2': 'FB_1V8', '3': 'GND', '4': None,
                        '8': None, '7': 'VCC', '6': 'SW', '5': 'GND'}
    for i, (num, name) in enumerate(buck_left):
        y = buck_y + top_y - i * 2.54
        x = buck_x - 15.24 / 2 - 2.54
        if buck_pin_labels[num]:
            add_label(sch, buck_pin_labels[num], x, y)
    for i, (num, name) in enumerate(buck_right):
        y = buck_y + top_y - i * 2.54
        x = buck_x + 15.24 / 2 + 2.54
        if buck_pin_labels[num]:
            add_label(sch, buck_pin_labels[num], x, y)

    # ---- 4. TPS22917 (new "U_LS1") ----
    ls_left = [('1', 'VIN'), ('2', 'GND'), ('3', 'ON')]
    ls_right = [('6', 'VOUT'), ('5', 'QOD'), ('4', 'CT')]
    sch.libSymbols.append(make_box_symbol('TPS22917', 'U', 'TPS22917DBVR', ls_left, ls_right))
    ls_x, ls_y = 300, 335
    ls_box_h = (3 - 1) * 2.54 + 5.08
    ls_top_y = ls_box_h / 2 - 2.54
    ls_inst = make_instance('U_LS1', 'TPS22917', 'TPS22917DBVR', ls_x, ls_y)
    sch.schematicSymbols.append(ls_inst)
    ls_pin_labels = {'1': 'VCC', '2': 'GND', '3': 'LSCTRL', '6': '3V3', '5': None, '4': None}
    for i, (num, name) in enumerate(ls_left):
        y = ls_y + ls_top_y - i * 2.54
        x = ls_x - 15.24 / 2 - 2.54
        if ls_pin_labels[num]:
            add_label(sch, ls_pin_labels[num], x, y)
    for i, (num, name) in enumerate(ls_right):
        y = ls_y + ls_top_y - i * 2.54
        x = ls_x + 15.24 / 2 + 2.54
        if ls_pin_labels[num]:
            add_label(sch, ls_pin_labels[num], x, y)

    # ---- 5. New passives ----
    add_resistor(sch, 'R_PROG', '1.2k', 260, 260, 'TP4056_PROG', 'GND')
    add_resistor(sch, 'R_FB1', '200k', 260, 295, 'FB_1V8', 'FBTOP_1V8')
    add_resistor(sch, 'R_FB2', '100k', 260, 305, 'FB_1V8', 'GND')
    # R_FB1 bridges +1.8V (the regulated output) <-> FB_1V8 (the FB pin node);
    # R_FB2 bridges that same FB_1V8 node <-> GND. FBTOP_1V8 is just this
    # script's placeholder name for R_FB1's outer pin before the rename below.
    for lbl in sch.labels:
        if lbl.text == 'FBTOP_1V8':
            lbl.text = '+1.8V'
    add_resistor(sch, 'R_PU_CHRG', '100k', 340, 250, 'CC_#CD', '3V3')
    add_resistor(sch, 'R_PU_STDBY', '100k', 340, 260, 'CC_#PG', '3V3')

    sch.to_file(OUT)
    print("Wrote", OUT)


if __name__ == '__main__':
    main()

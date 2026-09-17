"""
Haven dev board codec/mic redesign: replace the ADAU1860 (U15, BGA-56,
0.35mm pitch -- the single biggest real cost driver found this session)
with TLV320AIC3100 (QFN-32, TI) + replace the PDM mic (U13, SPH0641LU4H-1)
with CMA-4544PF-W (a plain 2-terminal analog electret capsule), since
TLV320AIC3100 has no clean PDM input (confirmed from its own datasheet:
mic inputs are analog PGA inputs MIC1LP/MIC1RP/MIC1LM, not PDM).

Real datasheet sources used this session (not guessed):
  - TLV320AIC3100: ti.com/lit/ds/symlink/tlv320aic3100.pdf, SLAS667C
    (pin table on its own page 6-7)
  - CMA-4544PF-W: sameskydevices.com/product/resource/cma-4544pf-w.pdf
    (2-terminal capsule, own "measurement circuit" diagram gives the real
    bias resistor (2.2k) and coupling cap (1uF) values used below)

Real net-reuse findings (traced from the actual schematic before writing
anything, same discipline as the charger redesign):
  - DIN/DOUT/BCLK/LRCLK: the real I2S bus, already wired to the MCU
    (MDBT531) with 2 owners each (ADAU1860 + MCU) -- reused directly.
  - SDA1/SCL1: the I2C control bus (4 owners each -- ADAU1860 plus other
    devices already sharing it) -- reused directly.
  - V_LS: the existing ~3.3V-ish switched analog rail that already fed
    ADAU1860's AVDD/HPVDD/IOVDD and the old PDM mic's VDD (38 total
    owners across the board) -- reused for the new codec's AVDD/HPVDD and
    unchanged for anything else already on it.
  - +1.8V: the SAME rail this session's charger redesign already
    established (TPS62822's regulated output) -- reused for the codec's
    DVDD, which needs 1.65-1.95V per its own datasheet. This only works
    because that redesign landed first.
  - DAC_N/DAC_P: ADAU1860's HPOUTN/HPOUTP were labeled with these but had
    only ONE owner each on this sheet (the chip itself) -- the real
    downstream receiver connection isn't modeled here, a pre-existing
    condition, not something this change creates or fixes. Preserved
    as-is: the new codec's HPL/HPR reuse the same two label names.
  - TCK/TMS/TDI/TDO: real JTAG debug pins with a second owner elsewhere
    (a debug header) -- TLV320AIC3100 has no JTAG at all (fixed-function
    codec, not a general DSP), so these simply lose their ADAU1860 end
    when it's removed. The header side is untouched and still valid for
    whatever else might be on that chain.

Real, deliberate simplifications (each flagged, not hidden):
  - MCLK (pin 8) is tied to the same net as BCLK (pin 7) rather than
    adding a dedicated crystal -- TLV320AIC3100's own datasheet explicitly
    says "normally MCLK is PLL input; however, BCLK, GPIO1, etc. can also
    be PLL input," so the PLL is configured (in firmware/register init,
    not modeled here) to use BCLK as its reference instead. Avoids needing
    a new crystal for a part that didn't need its own oscillator before.
  - VOL/MICDET (pin 11), MIC1RP (pin 14), MIC1LM (pin 15): all unused in
    this single-ended-mic configuration, tied directly to GND. MIC1LM
    tied straight to GND rather than through a matching bias/AC-ground
    network is a real simplification worth a second look before trusting
    it blind -- some reference designs bias the unused differential input
    pin to a DC midpoint instead of hard ground for better common-mode
    balance. Flagged here, not silently assumed correct.
  - RESET (pin 31) tied directly to 3V3 (permanently out of reset) rather
    than a firmware-controlled GPIO -- simplest safe default since nothing
    in the current firmware needs to assert a hardware reset. A future
    revision could free up an MCU pin for this instead.
  - Class-D speaker block (SPKP/SPKM x2, SPKVDD x2, SPKVSS x2) entirely
    unused -- this board drives its receiver from the headphone output
    (HPL/HPR), not the higher-power Class-D path, so these 6 pins are left
    genuinely unconnected, same as this project's existing convention for
    real unused pins (not fabricating a connection).
  - GPIO1 (pin 32) left floating -- genuinely optional per datasheet.

Genuinely new nets introduced: MICBIAS, MIC_IN, and MIC_IN_AC (3 -- the
mic bias network needs a real DC-biased node and a separate AC-coupled-
only node either side of the blocking cap, not one shorted net; caught
and fixed a real bug here where an earlier draft of this script shorted
both, which would have defeated the coupling cap entirely). Reused, not
new: GND, 3V3, +1.8V, V_LS, DOUT, DIN, LRCLK, BCLK, SDA1, SCL1, DAC_N,
DAC_P.
"""
import uuid
from kiutils.schematic import Schematic
from kiutils.items.common import Position, Effects, Font, Justify, Property
from kiutils.items.schitems import SchematicSymbol
from kiutils.symbol import Symbol, SymbolPin
from kiutils.items.syitems import SyRect
from kiutils.items.common import Stroke, Fill

SRC = "/home/paul22iac/projects/active/haven_dev_board_kicad/kicad/haven_dev_board.kicad_sch"
OUT = "/tmp/claude-1000/-home-paul22iac/de6df91d-5626-4f43-95cb-adf67fb0294d/scratchpad/haven_dev_board_sch_CODEC_V1.kicad_sch"
PROJ = "haven_dev_board"


def new_uuid():
    return str(uuid.uuid4())


def eff(justify=None):
    return Effects(font=Font(height=1.27, width=1.27), justify=justify or Justify())


def make_box_symbol(lib_id, ref_prefix, value, left_pins, right_pins, box_h=None, box_w=15.24):
    n_rows = max(len(left_pins), len(right_pins))
    if box_h is None:
        box_h = (n_rows - 1) * 2.54 + 5.08
    half_h = box_h / 2
    top_y = half_h - 2.54

    graphics_unit = Symbol(entryName=lib_id, unitId=0, styleId=1, extends=None)
    graphics_unit.graphicItems.append(SyRect(
        start=Position(X=-box_w / 2, Y=-half_h, angle=None),
        end=Position(X=box_w / 2, Y=half_h, angle=None),
        stroke=Stroke(width=0.254, type='default'),
        fill=Fill(type='background'),
    ))

    pins_unit = Symbol(entryName=lib_id, unitId=1, styleId=1, extends=None)
    for i, (num, name) in enumerate(left_pins):
        y = top_y - i * 2.54
        pins_unit.pins.append(SymbolPin(
            electricalType='passive', graphicalStyle='line',
            position=Position(X=-box_w / 2 - 2.54, Y=y, angle=0),
            length=2.54, name=name, number=num,
            nameEffects=eff(), numberEffects=eff(),
        ))
    for i, (num, name) in enumerate(right_pins):
        y = top_y - i * 2.54
        pins_unit.pins.append(SymbolPin(
            electricalType='passive', graphicalStyle='line',
            position=Position(X=box_w / 2 + 2.54, Y=y, angle=180),
            length=2.54, name=name, number=num,
            nameEffects=eff(), numberEffects=eff(),
        ))

    top = Symbol(entryName=lib_id, extends=None, inBom=True, onBoard=True)
    top.properties = [
        Property(key='Reference', value=ref_prefix,
                  position=Position(X=-box_w / 2, Y=half_h + 2.54, angle=0), effects=eff()),
        Property(key='Value', value=value,
                  position=Position(X=-box_w / 2, Y=-half_h - 2.54, angle=0), effects=eff()),
    ]
    top.units = [graphics_unit, pins_unit]
    return top, box_w, top_y


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
    sch.labels.append(lbl_cls(text=text, position=Position(X=x, Y=y, angle=0),
                               effects=eff(Justify(horizontally='left')), uuid=new_uuid()))


RESISTOR_BOX_W = 5.08


def add_two_pin(sch, ref, value, x, y, pin1_label, pin2_label, prefix='R'):
    lib_id = ref
    sym, box_w, _ = make_box_symbol(lib_id, prefix, value, [('1', '1')], [('2', '2')],
                                     box_h=5.08, box_w=RESISTOR_BOX_W)
    sch.libSymbols.append(sym)
    inst = make_instance(ref, lib_id, value, x, y)
    sch.schematicSymbols.append(inst)
    pin_x = RESISTOR_BOX_W / 2 + 2.54
    add_label(sch, pin1_label, x - pin_x, y)
    add_label(sch, pin2_label, x + pin_x, y)


def add_ic(sch, ref, lib_id, value, x, y, left_pins, right_pins, pin_labels):
    """left_pins/right_pins: [(num,name),...]; pin_labels: {num: label_text or None}"""
    sym, box_w, top_y = make_box_symbol(lib_id, 'U', value, left_pins, right_pins)
    sch.libSymbols.append(sym)
    inst = make_instance(ref, lib_id, value, x, y)
    sch.schematicSymbols.append(inst)
    for i, (num, name) in enumerate(left_pins):
        yy = y + top_y - i * 2.54
        xx = x - box_w / 2 - 2.54
        if pin_labels.get(num):
            add_label(sch, pin_labels[num], xx, yy)
    for i, (num, name) in enumerate(right_pins):
        yy = y + top_y - i * 2.54
        xx = x + box_w / 2 + 2.54
        if pin_labels.get(num):
            add_label(sch, pin_labels[num], xx, yy)


def remove_component(sch, ref):
    inst = next(i for i in sch.schematicSymbols
                if next((p.value for p in i.properties if p.key == 'Reference'), '') == ref)
    symname = inst.libId.split(':')[-1]
    sym = next(s for s in sch.libSymbols if s.libId == symname)
    ox, oy = inst.position.X, inst.position.Y
    coords = []
    for unit in sym.units:
        for p in unit.pins:
            coords.append((ox + p.position.X, oy + p.position.Y))
    removed = 0
    kept = []
    for lbl in sch.labels:
        hit = any(abs(lbl.position.X - x) < 0.01 and abs(lbl.position.Y - y) < 0.01 for x, y in coords)
        if hit:
            removed += 1
        else:
            kept.append(lbl)
    sch.labels = kept
    sch.schematicSymbols = [i for i in sch.schematicSymbols if i is not inst]
    sch.libSymbols = [s for s in sch.libSymbols if s.libId != symname]
    print(f"Removed {ref} ({symname}): {removed} labels, {len(coords)} pins expected")


def main():
    sch = Schematic.from_file(SRC)

    remove_component(sch, 'U15')  # ADAU1860
    remove_component(sch, 'U13')  # SPH0641LU4H-1 (old PDM mic)

    # ---- TLV320AIC3100 (new "U15") ----
    codec_left = [
        ('1', 'IOVSS'), ('2', 'IOVDD'), ('3', 'DVDD'), ('4', 'DOUT'),
        ('5', 'DIN'), ('6', 'WCLK'), ('7', 'BCLK'), ('8', 'MCLK'),
        ('9', 'SDA'), ('10', 'SCL'), ('11', 'VOL_MICDET'), ('12', 'MICBIAS'),
        ('13', 'MIC1LP'), ('14', 'MIC1RP'), ('15', 'MIC1LM'), ('16', 'AVSS'),
    ]
    codec_right = [
        ('17', 'AVDD'), ('18', 'DVSS'), ('19', 'SPKM_A'), ('20', 'SPKVSS_A'),
        ('21', 'SPKVDD_A'), ('22', 'SPKP_A'), ('23', 'SPKM_B'), ('24', 'SPKVDD_B'),
        ('25', 'SPKVSS_B'), ('26', 'SPKP_B'), ('27', 'HPL'), ('28', 'HPVDD'),
        ('29', 'HPVSS'), ('30', 'HPR'), ('31', 'RESET'), ('32', 'GPIO1'),
    ]
    codec_labels = {
        '1': 'GND', '2': '3V3', '3': '+1.8V', '4': 'DOUT',
        '5': 'DIN', '6': 'LRCLK', '7': 'BCLK', '8': 'BCLK',  # MCLK tied to BCLK, see module docstring
        '9': 'SDA1', '10': 'SCL1', '11': 'GND', '12': 'MICBIAS',
        '13': 'MIC_IN_AC', '14': 'GND', '15': 'GND', '16': 'GND',
        '17': 'V_LS', '18': 'GND', '19': None, '20': None,
        '21': None, '22': None, '23': None, '24': None,
        '25': None, '26': None, '27': 'DAC_P', '28': 'V_LS',
        '29': 'GND', '30': 'DAC_N', '31': '3V3', '32': None,
    }
    add_ic(sch, 'U15', 'TLV320AIC3100', 'TLV320AIC3100', 420, -20, codec_left, codec_right, codec_labels)

    # ---- CMA-4544PF-W (new "U13") ----
    mic_labels = {'1': 'MIC_IN', '2': 'GND'}
    add_ic(sch, 'U13', 'CMA-4544PF-W', 'CMA-4544PF-W', 380, -20,
           [('1', 'TERM1')], [('2', 'TERM2')], mic_labels)

    # ---- New passives: mic bias network (values from CUI's own measurement circuit) ----
    # Two distinct nets either side of the coupling cap, not one shorted net:
    # MICBIAS --[R_MICBIAS 2.2k]-- MIC_IN (mic's Term.1, DC-biased) --[C_MICIN
    # 1uF]-- MIC_IN_AC (codec's MIC1LP pin, AC-coupled only).
    add_two_pin(sch, 'R_MICBIAS', '2.2k', 400, -12, 'MICBIAS', 'MIC_IN')
    add_two_pin(sch, 'C_MICIN', '1uF', 400, -8, 'MIC_IN', 'MIC_IN_AC', prefix='C')

    sch.to_file(OUT)
    print("Wrote", OUT)


if __name__ == '__main__':
    main()

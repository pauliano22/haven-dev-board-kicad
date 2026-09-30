"""
Stage 3 of the TAC5301-Q1 codec swap: the HVDD boost converter.

Real reference design: TI TPS61040 datasheet (SLVS413L) Figure 7-1 "LCD
Bias Supply" -- an 18V-from-battery boost converter using exactly this
topology. Recomputed the feedback divider for Haven's actual 9V HVDD
target (mid-range of the datasheet's required 5.6-12V) instead of the
reference design's 18V, using the datasheet's own formula (Section
7.2.2.2, eq. 5): VOUT = 1.233V * (1 + R1/R2).

Kept R2 = 160kOhm (the reference design's own value, already inside the
datasheet's recommended <=200kOhm range) and solved for R1:
  9V / 1.233V = 7.299 = 1 + R1/160k  ->  R1 = 1.008 MOhm -> 1.0 MOhm (E96)
  Check: 1.233 * (1 + 1000/160) = 8.94V -- inside the 5.6-12V requirement
  with margin on both sides.

Every other component value (L1, D1, CFF, C1, C2) is the datasheet's own
reference design value, unmodified -- Haven's ~1.1mA HVDD load (per the
TAC5301-Q1 datasheet's own reference design) is far below the reference
design's 10mA target, so these are a safe, conservative choice, not
re-optimized for the lower current (deliberately -- no reason to shave
margin here).

BOM this stage:
  U_BOOST (TPS61040, SOT23-5)
  L1 (10uH, e.g. Sumida CR32-100 or equivalent)
  D1 (MBR0530 Schottky)
  R1 (1.0Mohm), R2 (160kOhm) -- feedback divider
  CFF (22pF) -- feedforward, across R1
  C1 (4.7uF) -- input cap
  C2 (1uF) -- output cap

NOT verified this stage (real open items, not silently skipped):
- Real inductor/diode part availability and JLC/LCSC stock
- PCB layout: this is a switching converter, loop area and SW-node
  copper matter a lot for EMI -- schematic-correct is not layout-correct
- EN tied directly to VIN (always-on) -- fine for this design's scope,
  but means HVDD boosts whenever the battery is connected, worth revisiting
  if standby power ever matters

Run from kicad/ directory, after stages 1 and 2.
"""
import uuid as uuidlib

from kiutils.schematic import Schematic
from kiutils.items.common import Position, Property, Effects, Font, Justify, Stroke, Fill
from kiutils.items.schitems import SchematicSymbol, LocalLabel, Rectangle
from kiutils.symbol import Symbol, SymbolPin

SCH_PATH = "haven_dev_board.kicad_sch"


def new_uuid():
    return str(uuidlib.uuid4())


def build_2pin_symbol(entry_name, value):
    top = Symbol(entryName=entry_name)
    top.properties = [
        Property(key="Reference", value=entry_name[0], position=Position(X=-2.54, Y=5.08, angle=0),
                  effects=Effects(font=Font(height=1.27, width=1.27))),
        Property(key="Value", value=value, position=Position(X=-2.54, Y=-5.08, angle=0),
                  effects=Effects(font=Font(height=1.27, width=1.27))),
    ]
    body = Symbol(entryName=entry_name, unitId=0, styleId=1)
    body.graphicItems = [Rectangle(
        start=Position(X=-2.54, Y=-2.54), end=Position(X=2.54, Y=2.54),
        stroke=Stroke(width=0.254, type="default"), fill=Fill(type="background"),
    )]
    pins_unit = Symbol(entryName=entry_name, unitId=1, styleId=1)
    pins_unit.pins = [
        SymbolPin(electricalType="passive", graphicalStyle="line",
                  position=Position(X=0, Y=5.08, angle=180), length=2.54,
                  name="1", number="1",
                  nameEffects=Effects(font=Font(height=1.27, width=1.27)),
                  numberEffects=Effects(font=Font(height=1.27, width=1.27)), hide=False),
        SymbolPin(electricalType="passive", graphicalStyle="line",
                  position=Position(X=0, Y=-5.08, angle=0), length=2.54,
                  name="2", number="2",
                  nameEffects=Effects(font=Font(height=1.27, width=1.27)),
                  numberEffects=Effects(font=Font(height=1.27, width=1.27)), hide=False),
    ]
    top.units = [body, pins_unit]
    return top


def place_2pin(sch, ref, entry_name, x, y, net1, net2):
    inst = SchematicSymbol(
        libraryNickname="haven_dev_board", entryName=entry_name,
        position=Position(X=x, Y=y, angle=0), unit=1, uuid=new_uuid(),
        properties=[
            Property(key="Reference", value=ref, position=Position(X=x - 2.54, Y=y + 5.08, angle=0),
                      effects=Effects(font=Font(height=1.27, width=1.27))),
            Property(key="Value", value=entry_name.split("_", 1)[1] if "_" in entry_name else "",
                      position=Position(X=x - 2.54, Y=y - 5.08, angle=0),
                      effects=Effects(font=Font(height=1.27, width=1.27))),
        ],
    )
    sch.schematicSymbols.append(inst)
    sch.labels.append(LocalLabel(text=net1, position=Position(X=x, Y=y + 5.08, angle=0),
                                  effects=Effects(font=Font(height=1.27, width=1.27), justify=Justify(horizontally="left")),
                                  uuid=new_uuid()))
    sch.labels.append(LocalLabel(text=net2, position=Position(X=x, Y=y - 5.08, angle=0),
                                  effects=Effects(font=Font(height=1.27, width=1.27), justify=Justify(horizontally="left")),
                                  uuid=new_uuid()))


def build_tps61040_symbol():
    top = Symbol(entryName="TPS61040")
    top.properties = [
        Property(key="Reference", value="U", position=Position(X=-7.62, Y=10.16, angle=0),
                  effects=Effects(font=Font(height=1.27, width=1.27))),
        Property(key="Value", value="TPS61040DBVR", position=Position(X=-7.62, Y=-10.16, angle=0),
                  effects=Effects(font=Font(height=1.27, width=1.27))),
    ]
    body = Symbol(entryName="TPS61040", unitId=0, styleId=1)
    body.graphicItems = [Rectangle(
        start=Position(X=-7.62, Y=7.62), end=Position(X=7.62, Y=-7.62),
        stroke=Stroke(width=0.254, type="default"), fill=Fill(type="background"),
    )]
    pins_unit = Symbol(entryName="TPS61040", unitId=1, styleId=1)
    # SOT23-5, DBV package (Figure 4-1): SW=1, GND=2, FB=3, EN=4, VIN=5
    pin_defs = [
        ("SW", "1", -10.16, 5.08, 0),
        ("GND", "2", -10.16, -5.08, 0),
        ("FB", "3", 10.16, -5.08, 180),
        ("EN", "4", 10.16, 0, 180),
        ("VIN", "5", 10.16, 5.08, 180),
    ]
    pins_unit.pins = [
        SymbolPin(electricalType="passive", graphicalStyle="line",
                  position=Position(X=x, Y=y, angle=angle), length=2.54,
                  name=name, number=num,
                  nameEffects=Effects(font=Font(height=1.27, width=1.27)),
                  numberEffects=Effects(font=Font(height=1.27, width=1.27)), hide=False)
        for name, num, x, y, angle in pin_defs
    ]
    top.units = [body, pins_unit]
    return top


def main():
    sch = Schematic.from_file(SCH_PATH)

    sch.libSymbols.append(build_tps61040_symbol())
    for entry_name, value in [
        ("L_10uH", "10uH"), ("D_MBR0530", "MBR0530"),
        ("R_1.0M", "1.0M"), ("R_160k", "160k"),
        ("C_22pF_ff", "22pF"), ("C_4.7uF_in", "4.7uF"), ("C_1uF_out", "1uF"),
    ]:
        sch.libSymbols.append(build_2pin_symbol(entry_name, value))

    ic_pos = Position(X=550.0, Y=140.0, angle=0)
    ic = SchematicSymbol(
        libraryNickname="haven_dev_board", entryName="TPS61040",
        position=ic_pos, unit=1, uuid=new_uuid(),
        properties=[
            Property(key="Reference", value="U16", position=Position(X=ic_pos.X, Y=ic_pos.Y - 12, angle=0),
                      effects=Effects(font=Font(height=1.27, width=1.27))),
            Property(key="Value", value="TPS61040DBVR", position=Position(X=ic_pos.X, Y=ic_pos.Y + 12, angle=0),
                      effects=Effects(font=Font(height=1.27, width=1.27))),
        ],
    )
    sch.schematicSymbols.append(ic)

    def lbl(text, x, y):
        sch.labels.append(LocalLabel(text=text, position=Position(X=x, Y=y, angle=0),
                                      effects=Effects(font=Font(height=1.27, width=1.27), justify=Justify(horizontally="left")),
                                      uuid=new_uuid()))

    # IC pins: SW(-10.16,5.08) GND(-10.16,-5.08) FB(10.16,-5.08) EN(10.16,0) VIN(10.16,5.08)
    lbl("SW_NODE", ic_pos.X - 10.16, ic_pos.Y + 5.08)
    lbl("GND", ic_pos.X - 10.16, ic_pos.Y - 5.08)
    lbl("FB_NODE", ic_pos.X + 10.16, ic_pos.Y - 5.08)
    lbl("V_BAT", ic_pos.X + 10.16, ic_pos.Y)       # EN tied to V_BAT: always enabled
    lbl("V_BAT", ic_pos.X + 10.16, ic_pos.Y + 5.08)  # VIN

    # L1: V_BAT -> SW_NODE
    place_2pin(sch, "L1", "L_10uH", 520.0, 110.0, "V_BAT", "SW_NODE")
    # D1: SW_NODE -> HVDD (anode at SW_NODE, cathode at HVDD -- polarity is a
    # real PCB-layout/footprint-orientation detail, not captured by this
    # generic 2-pin passive template; flagged for the layout stage)
    place_2pin(sch, "D1", "D_MBR0530", 560.0, 110.0, "SW_NODE", "HVDD")
    # C1: input cap, V_BAT -> GND, near the IC
    place_2pin(sch, "C53", "C_4.7uF_in", 535.0, 160.0, "V_BAT", "GND")
    # C2: output cap, HVDD -> GND
    place_2pin(sch, "C54", "C_1uF_out", 580.0, 140.0, "HVDD", "GND")
    # R1 (top of divider): HVDD -> FB_NODE
    place_2pin(sch, "R30", "R_1.0M", 580.0, 170.0, "HVDD", "FB_NODE")
    # R2 (bottom of divider): FB_NODE -> GND
    place_2pin(sch, "R31", "R_160k", 580.0, 200.0, "FB_NODE", "GND")
    # CFF: feedforward cap in parallel with R1, HVDD -> FB_NODE
    place_2pin(sch, "C55", "C_22pF_ff", 595.0, 170.0, "HVDD", "FB_NODE")

    # MICBIAS decoupling: 1uF/35V, value straight from the TAC5301-Q1
    # datasheet's own Figure 8-1 reference circuit (the ">25V rating"
    # layout guideline is for the chip's own full 3-10V MICBIAS range,
    # not specific to what we actually program it to -- using TI's own
    # cited value rather than re-deriving a lower rating for our case).
    sch.libSymbols.append(build_2pin_symbol("C_1uF_35V_micbias", "1uF 35V"))
    place_2pin(sch, "C56", "C_1uF_35V_micbias", 610.0, 140.0, "MIC_BIAS", "GND")

    sch.to_file(SCH_PATH)
    print("Wrote", SCH_PATH)


if __name__ == "__main__":
    main()

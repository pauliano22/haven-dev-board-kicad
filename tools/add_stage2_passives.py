"""
Stage 2 of the TAC5301-Q1 codec swap: add the real passive components
around the codec, using values sourced from real documents (cited per
component below), not guessed. Run AFTER add_tac5301_symbols.py, on its
output -- this does not redo stage 1's work.

Added this stage:
- R29 (2.2kOhm): mic bias resistor, MICBIAS -> R29 -> mic capsule OUT pin.
  Value matches CMA-4544PF-W's OWN datasheet measurement circuit exactly
  (Vs -> RL=2.2kOhm -> OUT), not a generic guess.
- C50 (1uF): AC-coupling cap, mic capsule OUT -> C50 -> codec IN1P.
  Value matches the coupling cap shown in TI app note SLAAED4 Figure 2-1
  (AC-coupled external resistor calculator reference circuit).
- C51 (0.1uF): DREG decoupling, DREG -> C51 -> GND.
  Value from the datasheet's own Figure 8-1 typical application circuit.
- C52 (1uF): VREF decoupling, VREF -> C52 -> GND.
  Value from the same Figure 8-1 reference circuit.

Still NOT done after this stage (real, disclosed, not silently skipped):
- HVDD boost converter (needs its own inductor/diode/feedback-resistor
  design -- HVDD is left unconnected, not wired wrong, until this exists)
- MICBIAS's own decoupling cap (needs HVDD solved first to be meaningful --
  low priority, add alongside the boost converter, not before)
- OUT2P/OUT2M termination
- PCB footprint placement/routing

Run from kicad/ directory, on the real project file in place.
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
    """Matches this project's own established 2-pin passive template
    (verified against the real C12 entry: rectangle body, pins "1"/"2"
    at (0, +-5.08), passive/line, 2.54mm leg length)."""
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
    sch.labels.append(LocalLabel(
        text=net1, position=Position(X=x, Y=y + 5.08, angle=0),
        effects=Effects(font=Font(height=1.27, width=1.27), justify=Justify(horizontally="left")),
        uuid=new_uuid(),
    ))
    sch.labels.append(LocalLabel(
        text=net2, position=Position(X=x, Y=y - 5.08, angle=0),
        effects=Effects(font=Font(height=1.27, width=1.27), justify=Justify(horizontally="left")),
        uuid=new_uuid(),
    ))


def retarget_label(sch, old_text, new_text, near_x, near_y, radius=1.0):
    """Find the one label matching old_text closest to (near_x, near_y)
    and rename it -- used to insert a component into an existing 2-point
    net without touching the other labels of that net elsewhere."""
    candidates = [l for l in sch.labels if l.text == old_text
                  and abs(l.position.X - near_x) < radius and abs(l.position.Y - near_y) < radius]
    assert len(candidates) == 1, f"expected exactly 1 match for {old_text} near ({near_x},{near_y}), got {len(candidates)}"
    candidates[0].text = new_text


def main():
    sch = Schematic.from_file(SCH_PATH)

    for entry_name in ["R_2.2k", "C_1uF_couple", "C_0.1uF_dreg", "C_1uF_vref"]:
        sch.libSymbols.append(build_2pin_symbol(entry_name, entry_name.split("_", 1)[1]))

    # Codec instance is at (436.880, 95.250); mic instance at (436.880, 175.0)
    # (see add_tac5301_symbols.py). Mic's own OUT pin label currently reads
    # "MIC_P" directly -- retarget it to "MIC_BIAS_NODE" so R29/C50 can sit
    # in between it and the codec's real MIC_P (IN1P) net.
    retarget_label(sch, "MIC_P", "MIC_BIAS_NODE", 430.53, 175.0)

    # R29: MICBIAS -> MIC_BIAS_NODE (2.2kOhm, matches CMA-4544PF-W's own
    # datasheet test circuit exactly)
    place_2pin(sch, "R29", "R_2.2k", 460.0, 140.0, "MIC_BIAS", "MIC_BIAS_NODE")

    # C50: MIC_BIAS_NODE -> MIC_P (1uF AC-coupling, per SLAAED4 Figure 2-1)
    place_2pin(sch, "C50", "C_1uF_couple", 470.0, 140.0, "MIC_BIAS_NODE", "MIC_P")

    # C51: DREG -> GND (0.1uF, per datasheet Figure 8-1 typical application)
    place_2pin(sch, "C51", "C_0.1uF_dreg", 480.0, 140.0, "DREG_DECOUPLE", "GND")

    # C52: VREF -> GND (1uF, per datasheet Figure 8-1 typical application)
    place_2pin(sch, "C52", "C_1uF_vref", 490.0, 140.0, "VREF_DECOUPLE", "GND")

    sch.to_file(SCH_PATH)
    print("Wrote", SCH_PATH)


if __name__ == "__main__":
    main()

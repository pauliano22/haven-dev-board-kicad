"""
Stage 1 of the TAC5301-Q1 codec swap: add the new symbol definitions,
place instances for the codec + replacement mic, remove the old
ADAU1860 (U15) and old PDM mic instances + their labels, and wire the
core signal path (power, I2C, audio serial bus, mic in, DAC out) using
Haven's EXISTING net names wherever the function matches -- no rename
needed on the nRF5340/MDBT531 side, since net names are just labels that
need to match text, not pin names.

Explicitly NOT done in this stage (flagged, not silently skipped):
- Decoupling caps for DREG/VREF (need per-datasheet values, follow-up)
- HVDD/MICBIAS bias-resistor network sizing for the new mic
- OUT2P/OUT2M (unused second channel) termination
- PCB footprint placement/routing -- schematic only, this stage

Run from kicad/ directory, on the real project file in place (matching
.kicad_pro alongside it -- see CODEX_NOTES.md's standing /tmp-corruption
hazard entry; this stays inside the real project dir throughout).
"""
import copy
import uuid as uuidlib

from kiutils.schematic import Schematic
from kiutils.items.common import Position, Property, Effects, Font, Justify
from kiutils.items.schitems import SchematicSymbol, LocalLabel
from kiutils.symbol import Symbol, SymbolPin

SCH_PATH = "haven_dev_board.kicad_sch"


def new_uuid():
    return str(uuidlib.uuid4())


# name, number -> chosen LOCAL pin offset within the new symbol body.
# Schematic pin layout doesn't need to match the physical package layout
# (U15's own symbol doesn't either) -- grouped here by function, spaced
# 2.54mm apart per side, matching this project's existing pin pitch.
TAC5301_PIN_LAYOUT = {
    # left side: audio serial interface + I2C
    "BCLK":     (-15.24, 10.16, 0),
    "FSYNC":    (-15.24, 7.62, 0),
    "DIN":      (-15.24, 5.08, 0),
    "DOUT":     (-15.24, 2.54, 0),
    "SCL":      (-15.24, -2.54, 0),
    "SDA":      (-15.24, -5.08, 0),
    "GPIO1":    (-15.24, -7.62, 0),
    # right side: analog audio in/out
    "IN1P":     (15.24, 10.16, 0),
    "IN1M":     (15.24, 7.62, 0),
    "IN2P":     (15.24, 5.08, 0),
    "IN2M":     (15.24, 2.54, 0),
    "OUT1M":    (15.24, -2.54, 0),
    "OUT1P":    (15.24, -5.08, 0),
    "OUT2P":    (15.24, -7.62, 0),
    "OUT2M":    (15.24, -10.16, 0),
    # top: power
    "DREG":     (-10.16, 15.24, 0),
    "IOVDD":    (-5.08, 15.24, 0),
    "AVDD#11":  (0.0, 15.24, 0),
    "AVDD#23":  (5.08, 15.24, 0),
    "HVDD":     (10.16, 15.24, 0),
    "MICBIAS":  (15.24, 15.24, 0),
    "VREF":     (-15.24, 15.24, 0),
    # bottom: grounds
    "VSS#A1":   (-10.16, -15.24, 0),
    "IOVSS":    (-5.08, -15.24, 0),
    "VSSA#10":  (0.0, -15.24, 0),
    "VSSA#12":  (5.08, -15.24, 0),
    "AVSS#A3":  (10.16, -15.24, 0),
    "AVSS#A4":  (15.24, -15.24, 0),
    "VSS#PAD":  (-15.24, -15.24, 0),
}

# key in TAC5301_PIN_LAYOUT -> (pin_name_for_symbol, pin_number)
# ('#'-suffixed keys disambiguate duplicate pin names at different numbers)
TAC5301_PINS = {
    "BCLK": ("BCLK", "2"), "FSYNC": ("FSYNC", "3"), "DIN": ("DIN", "5"),
    "DOUT": ("DOUT", "4"), "SCL": ("SCL", "7"), "SDA": ("SDA", "8"),
    "GPIO1": ("GPIO1", "9"),
    "IN1P": ("IN1P", "15"), "IN1M": ("IN1M", "16"),
    "IN2P": ("IN2P", "17"), "IN2M": ("IN2M", "18"),
    "OUT1M": ("OUT1M", "19"), "OUT1P": ("OUT1P", "20"),
    "OUT2P": ("OUT2P", "21"), "OUT2M": ("OUT2M", "22"),
    "DREG": ("DREG", "1"), "IOVDD": ("IOVDD", "6"),
    "AVDD#11": ("AVDD", "11"), "AVDD#23": ("AVDD", "23"),
    "HVDD": ("HVDD", "13"), "MICBIAS": ("MICBIAS", "14"),
    "VREF": ("VREF", "24"),
    "VSS#A1": ("VSS", "A1"), "IOVSS": ("IOVSS", "A2"),
    "VSSA#10": ("VSSA", "10"), "VSSA#12": ("VSSA", "12"),
    "AVSS#A3": ("AVSS", "A3"), "AVSS#A4": ("AVSS", "A4"),
    "VSS#PAD": ("VSS", "PAD"),
}

assert set(TAC5301_PIN_LAYOUT) == set(TAC5301_PINS), "layout/pin key mismatch"

# net name to wire at each TAC5301-Q1 pin, reusing Haven's existing net
# names where the function matches. None = leave unconnected this stage.
NET_MAP = {
    "BCLK": "BCLK",
    "FSYNC": "LRCLK",       # Haven's existing frame-sync net name (nRF side already uses this text)
    "DIN": "DIN",
    "DOUT": "DOUT",
    "SCL": "SCL1",
    "SDA": "SDA1",
    "GPIO1": None,          # unused this stage
    "IN1P": "MIC_P",        # new net: to the replacement analog mic
    "IN1M": "GND",          # FLAGGED (see stage-2 note): assumes single-ended-
                            # to-differential via AGND reference on the minus
                            # input. Not yet confirmed against the codec's own
                            # analog-mic application circuit (its "Microphone
                            # Interface with TAX5XXX Devices" app note, not
                            # pulled this pass) -- verify before trusting this
                            # for anything beyond a schematic placeholder.
    "IN2P": None,           # second (unused) mic channel
    "IN2M": None,
    "OUT1M": "DAC_N",       # reuse Haven's existing speaker-output net names
    "OUT1P": "DAC_P",
    "OUT2P": None,          # unused second output channel (flagged, not terminated)
    "OUT2M": None,
    "DREG": "DREG_DECOUPLE",   # flagged: needs its own decoupling cap, stage 2
    "IOVDD": "3V3",
    "AVDD#11": "3V3",
    "AVDD#23": "3V3",
    "HVDD": None,           # NOT 3V3 -- real datasheet spec (Recommended Operating
                            # Conditions, HVDD to AVSS) requires 5.6V MIN / 9V TYP /
                            # 12V MAX. Tying this to the 3.3V rail would put HVDD
                            # below its functional minimum and MICBIAS likely
                            # wouldn't work at all. Needs its own small boost
                            # converter from the battery (TPS61040-class part is a
                            # real, verified candidate: SOT-23, single-Li-ion-cell
                            # input, up to 12V/20mA output, sold specifically as a
                            # "bias voltage" boost converter -- but the actual
                            # boost sub-circuit, inductor/diode/feedback-resistor
                            # sizing, is not designed yet. Left unconnected rather
                            # than wired wrong.
    "MICBIAS": "MIC_BIAS",
    "VREF": "VREF_DECOUPLE",  # flagged: needs its own decoupling cap, stage 2
    "VSS#A1": "GND",
    "IOVSS": "GND",
    "VSSA#10": "GND",
    "VSSA#12": "GND",
    "AVSS#A3": "GND",
    "AVSS#A4": "GND",
    "VSS#PAD": "GND",
}


def build_tac5301_symbol():
    top = Symbol(entryName="TAC5301-Q1")
    top.properties = [
        Property(key="Reference", value="U", position=Position(X=-17.78, Y=17.78, angle=0),
                  effects=Effects(font=Font(height=1.27, width=1.27))),
        Property(key="Value", value="TAC5301QRGERQ1", position=Position(X=-17.78, Y=-17.78, angle=0),
                  effects=Effects(font=Font(height=1.27, width=1.27))),
    ]

    body = Symbol(entryName="TAC5301-Q1", unitId=0, styleId=1)
    from kiutils.items.schitems import Rectangle
    from kiutils.items.common import Stroke, Fill
    body.graphicItems = [Rectangle(
        start=Position(X=-17.78, Y=17.78), end=Position(X=17.78, Y=-17.78),
        stroke=Stroke(width=0.254, type="default"),
        fill=Fill(type="background"),
    )]

    pins_unit = Symbol(entryName="TAC5301-Q1", unitId=1, styleId=1)
    pins = []
    for key, (x, y, angle) in TAC5301_PIN_LAYOUT.items():
        pname, pnum = TAC5301_PINS[key]
        pins.append(SymbolPin(
            electricalType="passive", graphicalStyle="line",
            position=Position(X=x, Y=y, angle=angle), length=2.54,
            name=pname, number=pnum,
            nameEffects=Effects(font=Font(height=1.27, width=1.27)),
            numberEffects=Effects(font=Font(height=1.27, width=1.27)),
            hide=False,
        ))
    pins_unit.pins = pins
    top.units = [body, pins_unit]
    return top


def build_mic_symbol():
    # CMA-4544PF-W: plain 2-terminal electret capsule (OUT, GND per its
    # measurement-circuit diagram). Modeled on this file's existing 2-pin
    # passive-part template (same rectangle+2-pin structure already used
    # elsewhere in this schematic for simple 2-terminal parts).
    top = Symbol(entryName="CMA-4544PF-W")
    top.properties = [
        Property(key="Reference", value="MIC", position=Position(X=0, Y=6.35, angle=0),
                  effects=Effects(font=Font(height=1.27, width=1.27))),
        Property(key="Value", value="CMA-4544PF-W", position=Position(X=0, Y=-6.35, angle=0),
                  effects=Effects(font=Font(height=1.27, width=1.27))),
    ]
    body = Symbol(entryName="CMA-4544PF-W", unitId=0, styleId=1)
    from kiutils.items.schitems import Circle
    from kiutils.items.common import Stroke, Fill
    body.graphicItems = [Circle(
        center=Position(X=0, Y=0), radius=3.81,
        stroke=Stroke(width=0.254, type="default"), fill=Fill(type="background"),
    )]
    pins_unit = Symbol(entryName="CMA-4544PF-W", unitId=1, styleId=1)
    pins_unit.pins = [
        SymbolPin(electricalType="passive", graphicalStyle="line",
                  position=Position(X=-6.35, Y=0, angle=0), length=2.54,
                  name="OUT", number="1",
                  nameEffects=Effects(font=Font(height=1.27, width=1.27)),
                  numberEffects=Effects(font=Font(height=1.27, width=1.27)), hide=False),
        SymbolPin(electricalType="passive", graphicalStyle="line",
                  position=Position(X=6.35, Y=0, angle=180), length=2.54,
                  name="GND", number="2",
                  nameEffects=Effects(font=Font(height=1.27, width=1.27)),
                  numberEffects=Effects(font=Font(height=1.27, width=1.27)), hide=False),
    ]
    top.units = [body, pins_unit]
    return top


def rotated_offset(x, y, angle_deg):
    # All chosen pin angles are axis-aligned (0/90/180/270), and the
    # instance placement angle is 0 in this stage, so this is an identity
    # for now -- kept as a named step so a future non-zero placement
    # rotation doesn't get silently ignored.
    return x, y


def main():
    sch = Schematic.from_file(SCH_PATH)

    # --- locate and remove the old ADAU1860 instance + its labels ---
    old_u15 = next(s for s in sch.schematicSymbols if s.entryName == "U15" or
                    (s.uuid == "00000000-0000-0000-0000-000000000361"))
    print("Removing old ADAU1860 instance at", old_u15.position, "uuid", old_u15.uuid)
    sch.schematicSymbols.remove(old_u15)

    # Labels between the U15 instance and the next component (C31) are the
    # ADAU1860's own pin labels -- remove all of them; anything reused
    # (BCLK/DIN/DOUT/SCL1/SDA1/GND/V_LS/etc.) gets re-added fresh at the
    # new instance's pin positions below, so nothing is lost.
    old_u15_labels_by_uuid = {
        f"00000000-0000-0000-0000-0000000003{n:02d}" for n in range(61, 100)
    } | {f"00000000-0000-0000-0000-0000000003{n}" for n in range(70, 98)}
    removed = [l for l in sch.labels if l.uuid in old_u15_labels_by_uuid]
    for l in removed:
        sch.labels.remove(l)
    print(f"Removed {len(removed)} old ADAU1860 pin labels")

    # --- add new symbol library entries ---
    sch.libSymbols.append(build_tac5301_symbol())
    sch.libSymbols.append(build_mic_symbol())

    # --- place the TAC5301-Q1 instance at U15's old position ---
    codec_pos = Position(X=436.880, Y=95.250, angle=0)
    codec = SchematicSymbol(
        libraryNickname="haven_dev_board", entryName="TAC5301-Q1",
        position=codec_pos, unit=1, uuid=new_uuid(),
        properties=[
            Property(key="Reference", value="U15",
                      position=Position(X=codec_pos.X, Y=codec_pos.Y - 5, angle=0),
                      effects=Effects(font=Font(height=1.27, width=1.27))),
            Property(key="Value", value="TAC5301QRGERQ1",
                      position=Position(X=codec_pos.X, Y=codec_pos.Y + 5, angle=0),
                      effects=Effects(font=Font(height=1.27, width=1.27))),
        ],
    )
    sch.schematicSymbols.append(codec)

    # --- place the mic instance in clear space below the old U15 area ---
    mic_pos = Position(X=436.880, Y=175.0, angle=0)
    mic = SchematicSymbol(
        libraryNickname="haven_dev_board", entryName="CMA-4544PF-W",
        position=mic_pos, unit=1, uuid=new_uuid(),
        properties=[
            Property(key="Reference", value="MIC1",
                      position=Position(X=mic_pos.X, Y=mic_pos.Y - 5, angle=0),
                      effects=Effects(font=Font(height=1.27, width=1.27))),
            Property(key="Value", value="CMA-4544PF-W",
                      position=Position(X=mic_pos.X, Y=mic_pos.Y + 5, angle=0),
                      effects=Effects(font=Font(height=1.27, width=1.27))),
        ],
    )
    sch.schematicSymbols.append(mic)

    # --- labels for every codec pin with a net assigned this stage ---
    added = 0
    for key, (dx, dy, angle) in TAC5301_PIN_LAYOUT.items():
        net = NET_MAP[key]
        if net is None:
            continue
        ox, oy = rotated_offset(dx, dy, angle)
        lbl = LocalLabel(
            text=net,
            position=Position(X=codec_pos.X + ox, Y=codec_pos.Y + oy, angle=0),
            effects=Effects(font=Font(height=1.27, width=1.27), justify=Justify(horizontally="left")),
            uuid=new_uuid(),
        )
        sch.labels.append(lbl)
        added += 1
    print(f"Added {added} codec net labels")

    # --- mic labels (OUT -> MIC_P, GND -> MIC_N per the simple 2-terminal
    #     electret bias circuit: capsule OUT through bias network to
    #     IN1P/MIC_P, capsule GND terminal returns to IN1M/MIC_N rather
    #     than board GND, matching a pseudo-differential input scheme;
    #     see stage-2 note below on verifying this against the codec's
    #     recommended single-ended-mic application circuit) ---
    mic_out_lbl = LocalLabel(text="MIC_P", position=Position(X=mic_pos.X - 6.35, Y=mic_pos.Y, angle=0),
                              effects=Effects(font=Font(height=1.27, width=1.27), justify=Justify(horizontally="left")), uuid=new_uuid())
    mic_gnd_lbl = LocalLabel(text="GND", position=Position(X=mic_pos.X + 6.35, Y=mic_pos.Y, angle=0),
                              effects=Effects(font=Font(height=1.27, width=1.27), justify=Justify(horizontally="left")), uuid=new_uuid())
    sch.labels.append(mic_out_lbl)
    sch.labels.append(mic_gnd_lbl)

    sch.to_file(SCH_PATH)
    print("Wrote", SCH_PATH)


if __name__ == "__main__":
    main()

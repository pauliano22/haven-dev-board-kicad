"""
Build the two custom footprints needed for the TAC5301-Q1 redesign.

TAC5301-Q1: starts from KiCad's real, verified TI reference footprint
(Texas_RGE0024C_VQFN-24-1EP_4x4mm_P0.5mm_EP2.1x2.1mm -- ships in KiCad's
own standard library, and its 24-pad + thermal-pad geometry matches the
TAC5301-Q1 datasheet's own mechanical drawing exactly: 4x4mm body, 0.5mm
pitch, 2.1x2.1mm thermal pad). The TAC5301-Q1's real package (RGE0024R)
adds 4 small corner pads (A1-A4, all extra GND/shield connections per the
pin table, not unique signals) beyond the base RGE0024 -- added here at
the package's outer corner per the datasheet's "4X SQ 0.25 TYP" callout
and the 4.1/3.9mm body outline. Not pulled from an exact land-pattern
coordinate (TI's package drawing doesn't give one at text-extractable
precision) -- a reasonable, disclosed estimate for 4 pads that are all
redundant ground connections, not a unique signal, so a small placement
imprecision here is low-risk, unlike getting one of the 24 real signal
pins wrong.

CMA-4544PF-W: simple 2-pad through-hole footprint for the mic capsule
(9.7mm diameter body per its own datasheet, pin type/hand-soldering,
~2.54mm typical lead spacing for this class of electret capsule -- exact
lead spacing not given in the datasheet's own drawing at text-extractable
precision either; using a common, standard spacing for this capsule size,
flagged as needing a real caliper check against the actual part before
finalizing hole spacing).
"""
from kiutils.footprint import Footprint, Pad, DrillDefinition, Attributes
from kiutils.items.common import Position

TI_REF = "/usr/share/kicad/footprints/Package_DFN_QFN.pretty/Texas_RGE0024C_VQFN-24-1EP_4x4mm_P0.5mm_EP2.1x2.1mm.kicad_mod"


def build_tac5301q1_footprint():
    fp = Footprint.from_file(TI_REF)
    fp.entryName = "TAC5301-Q1"
    fp.properties["Value"] = "TAC5301-Q1"

    # Corner pads: package outline is 4.1/3.9mm (datasheet Fig., RGE0024R),
    # so half-span ~2.05/1.95mm; placing at the diagonal corner just inside
    # that per the "4X SQ 0.25 TYP" callout.
    corner_positions = {
        "A1": (-1.95, -1.85),
        "A2": (-1.95, 1.85),
        "A3": (1.95, 1.85),
        "A4": (1.95, -1.85),
    }
    for name, (x, y) in corner_positions.items():
        fp.pads.append(Pad(
            number=name, type="smd", shape="rect",
            position=Position(X=x, Y=y, angle=0),
            size=Position(X=0.25, Y=0.25),
            layers=["F.Cu", "F.Mask", "F.Paste"],
        ))
    return fp


def build_cma4544_footprint():
    fp = Footprint(entryName="CMA-4544PF-W")
    fp.layer = "F.Cu"
    fp.attributes = Attributes(type="through_hole")
    fp.pads = [
        Pad(number="1", type="thru_hole", shape="rect",
            position=Position(X=-1.27, Y=0, angle=0),
            size=Position(X=1.4, Y=1.4), drill=DrillDefinition(oval=False, diameter=0.8),
            layers=["*.Cu", "*.Mask"]),
        Pad(number="2", type="thru_hole", shape="circle",
            position=Position(X=1.27, Y=0, angle=0),
            size=Position(X=1.4, Y=1.4), drill=DrillDefinition(oval=False, diameter=0.8),
            layers=["*.Cu", "*.Mask"]),
    ]
    return fp


if __name__ == "__main__":
    tac = build_tac5301q1_footprint()
    print("TAC5301-Q1 footprint: ", len(tac.pads), "pads")
    tac.to_file("footprints.pretty/TAC5301-Q1.kicad_mod")

    mic = build_cma4544_footprint()
    print("CMA-4544PF-W footprint:", len(mic.pads), "pads")
    mic.to_file("footprints.pretty/CMA-4544PF-W.kicad_mod")

#!/usr/bin/env python3
"""Generate the Haven v2 BTE charging-case schematic (kicad_v2_case/).

Charge-only, no microcontroller:

  USB-C (5 V, CC 5.1k pull-downs) -> MCP73831 (or pin-compatible TP4054) 1-cell charger, 250 mA
  -> ~800 mAh 1S LiPo with its own protection board (PCM), on a JST-SH 2-pin
  -> TPS61023 boost to 5 V (always enabled; ~30 uA standby, true disconnect only when disabled,
     output short limited to ~350 mA by the IC, TI SLVSF14B 7.3.7)
  -> two pogo pins per pod (VBUS, GND), 5.0 mm apart = the pod shell's two charge contacts
     (haven-hardware v2_bte: PAD_PITCH 2.5 mm either side of the magnet).

Each pod's nPM1100 limits its own input to 100 mA, so the two pods together draw <= 200 mA from
the boost. The same TPD1E05U06 ESD diode as the pod protects every exposed pin.

Reuses the symbol/footprint writer from gen_v2_schematic.py. Stock KiCad footprints are copied
from /usr/share/kicad/footprints into the project's footprints.pretty.

    python3 tools/gen_v2_case_schematic.py
"""
import gen_v2_schematic as g

ROOT = g.ROOT
STOCK = "/usr/share/kicad/footprints"

# ---------------------------------------------------------------- footprints
STOCK_FPS = {
    "USB_C_Receptacle_HRO_TYPE-C-31-M-12": "Connector_USB",
    "SOT-23-5": "Package_TO_SOT_SMD",
    "SOT-563": "Package_TO_SOT_SMD",
    "JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal": "Connector_JST",
    "R_0402_1005Metric": "Resistor_SMD",
    "C_0402_1005Metric": "Capacitor_SMD",
    "C_0603_1608Metric": "Capacitor_SMD",
    "C_0805_2012Metric": "Capacitor_SMD",
    "L_1008_2520Metric": "Inductor_SMD",
    "LED_0603_1608Metric": "LED_SMD",
}
for _name, _lib in STOCK_FPS.items():
    g.NEW_FPS[_name] = (lambda n=_name, l=_lib: open(f"{STOCK}/{l}.pretty/{n}.kicad_mod").read().rstrip())


def pogo_fp():
    # Seat for an SMD spring pin, 2.0 mm base flange. The real part is still open (README):
    # check its land pattern before layout.
    out = g.fp_header("PogoPin_SMD_D2.0", "Seat for a 2.0 mm-base SMD spring (pogo) pin; part TBD, "
                      "check the land pattern before layout")
    out.append('  (pad "1" smd circle (at 0 0) (size 2.2 2.2) (layers "F.Cu" "F.Paste" "F.Mask"))')
    out.append(g.rect("F.CrtYd", -1.35, -1.35, 1.35, 1.35))
    out.append(")")
    return "\n".join(out)


g.NEW_FPS["PogoPin_SMD_D2.0"] = pogo_fp
g.NEW_FPS["D_SOD-523"] = __import__("gen_v2_bte_schematic").sod523_ti_fp

# ---------------------------------------------------------------- symbols
g.SYMBOLS["USB_C_PWR"] = dict(
    left=[("A4", "VBUS"), ("A9", "VBUS"), ("B4", "VBUS"), ("B9", "VBUS"), ("A5", "CC1"), ("B5", "CC2"),
          ("A6", "D+"), ("B6", "D+"), ("A7", "D-"), ("B7", "D-")],
    right=[("A1", "GND"), ("A12", "GND"), ("B1", "GND"), ("B12", "GND"), ("S1", "SHIELD"),
           ("A8", "SBU1"), ("B8", "SBU2")],
    ref="J", width=12.7)
# Microchip MCP73831 SOT-23-5 (DS20001984): 1 STAT, 2 VSS, 3 VBAT, 4 VDD, 5 PROG.
# TP4054 has the same pinout (1 CHRG, 2 GND, 3 BAT, 4 VCC, 5 PROG) and the same ~1000/R(kOhm) mA.
g.SYMBOLS["MCP73831"] = dict(left=[("4", "VDD"), ("5", "PROG")], right=[("3", "VBAT"), ("1", "STAT"), ("2", "VSS")],
                             ref="U", width=10.16)
# TI TPS61023 SOT-563 (SLVSF14B, Pin Functions): 1 FB, 2 EN, 3 VIN, 4 GND, 5 SW, 6 VOUT.
g.SYMBOLS["TPS61023"] = dict(left=[("3", "VIN"), ("2", "EN"), ("5", "SW")], right=[("6", "VOUT"), ("1", "FB"), ("4", "GND")],
                             ref="U", width=10.16)
g.SYMBOLS["BAT_JST2"] = dict(left=[("1", "+"), ("2", "-")], right=[("MP", "MP")], ref="J", width=7.62)

TVS = __import__("gen_v2_bte_schematic").TVS


def P(ref, sym, value, fp, nets, mpn="", lcsc="", note="", dnp=False):
    return dict(ref=ref, sym=sym, value=value, fp=fp, nets=nets, mpn=mpn, lcsc=lcsc, note=note, dnp=dnp)


def case_parts():
    p = []
    # USB-C, power only. D+/D- and SBU unused (no data); CC1/CC2 5.1k to GND = 5 V sink.
    p.append(P("J1", "USB_C_PWR", "USB-C 16P", "USB_C_Receptacle_HRO_TYPE-C-31-M-12",
               {"A4": "VUSB", "A9": "VUSB", "B4": "VUSB", "B9": "VUSB", "A5": "CC1", "B5": "CC2",
                "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND"},
               mpn="TYPE-C-31-M-12", lcsc="C165948", note="Korean Hroparts USB-C 16-pin receptacle; power only"))
    p.append(P("R1", "R", "5.1k", "R_0402_1005Metric", {"1": "CC1", "2": "GND"}, note="CC1 sink pull-down (USB-C 5 V / default current)"))
    p.append(P("R2", "R", "5.1k", "R_0402_1005Metric", {"1": "CC2", "2": "GND"}, note="CC2 sink pull-down"))
    p.append(P("D1", "TVS", "TPD1E05U06", "D_SOD-523", {"1": "VUSB", "2": "GND"}, mpn=TVS[0], lcsc=TVS[1],
               note="ESD on USB VBUS"))
    p.append(P("C1", "C", "4.7uF", "C_0603_1608Metric", {"1": "VUSB", "2": "GND"}, note="Charger input, 10 V X5R"))

    # Charger
    p.append(P("U1", "MCP73831", "MCP73831T-2ACI/OT", "SOT-23-5",
               {"4": "VUSB", "5": "PROG", "3": "VBAT", "1": "STAT", "2": "GND"},
               mpn="MCP73831T-2ACI/OT", lcsc="C424093",
               note="1-cell Li-ion charger, 4.20 V. TP4054 is a pin-compatible drop-in if stock is short "
                    "(one LCSC listing marks MCP73831 not-recommended-for-new-designs). Thermal regulation "
                    "will throttle 250 mA when hot; that is fine."))
    p.append(P("R3", "R", "4.02k 1%", "R_0402_1005Metric", {"1": "PROG", "2": "GND"},
               note="Charge current ~1000/R(kOhm) mA = ~250 mA (0.3C for 800 mAh)"))
    p.append(P("C2", "C", "4.7uF", "C_0603_1608Metric", {"1": "VBAT", "2": "GND"}, note="Charger output / battery, 10 V X5R"))
    p.append(P("R4", "R", "1k", "R_0402_1005Metric", {"1": "VUSB", "2": "LED_A"}, note="Charge LED current ~3 mA"))
    p.append(P("D2", "LED", "red", "LED_0603_1608Metric", {"1": "LED_A", "2": "STAT"},
               note="On while charging (STAT pulls low), off when full or unplugged"))

    # Battery
    p.append(P("J2", "BAT_JST2", "LiPo 1S ~800 mAh", "JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal",
               {"1": "VBAT", "2": "GND", "MP": "GND"},
               note="1S LiPo pouch WITH protection board (PCM), ~800 mAh (603040 class), JST-SH lead. "
                    "Pin 1 = +. Check the cell's lead polarity: it is not standardised."))

    # Boost 5 V (TI SLVSF14B Figure 8-1 values)
    p.append(P("U2", "TPS61023", "TPS61023DRLR", "SOT-563",
               {"3": "VBAT", "2": "VBAT", "5": "SW", "6": "V5", "1": "FB", "4": "GND"},
               mpn="TPS61023DRLR", lcsc="C1852149",
               note="Boost to 5.0 V for the pods. EN tied to VIN: always on (20-30 uA standby). "
                    "Output short: current folds back to ~350 mA and it restarts when released. "
                    "LCSC C1852149 is the DRLT reel variant: same part."))
    p.append(P("L1", "L", "1uH", "L_1008_2520Metric", {"1": "VBAT", "2": "SW"},
               note="1 uH, >= 1.5 A saturation, <= 80 mOhm, 2520. Pods draw <= 200 mA, so a small part is enough"))
    p.append(P("C3", "C", "10uF", "C_0805_2012Metric", {"1": "VBAT", "2": "GND"}, note="Boost input, 10 V X5R, at VIN"))
    p.append(P("C4", "C", "22uF", "C_0805_2012Metric", {"1": "V5", "2": "GND"}, note="Boost output, 10 V X5R"))
    p.append(P("C5", "C", "22uF", "C_0805_2012Metric", {"1": "V5", "2": "GND"}, note="Boost output, 10 V X5R"))
    p.append(P("R5", "R", "732k 1%", "R_0402_1005Metric", {"1": "V5", "2": "FB"}, note="FB top: VOUT = 0.595 V x (1 + 732k/100k) = 4.95 V"))
    p.append(P("R6", "R", "100k 1%", "R_0402_1005Metric", {"1": "FB", "2": "GND"}, note="FB bottom"))

    # Pogo pins: left pod and right pod, each VBUS + GND, with ESD on VBUS
    for side, n0 in (("L", 1), ("R", 3)):
        p.append(P(f"P{n0}", "PAD", f"POGO_{side}_VBUS", "PogoPin_SMD_D2.0", {"1": "V5"},
                   note=f"{side} pod VBUS spring pin, mates the pod shell contact wired to P1. 5.0 mm from P{n0 + 1}"))
        p.append(P(f"P{n0 + 1}", "PAD", f"POGO_{side}_GND", "PogoPin_SMD_D2.0", {"1": "GND"},
                   note=f"{side} pod GND spring pin, mates the shell contact wired to P2"))
    p.append(P("D3", "TVS", "TPD1E05U06", "D_SOD-523", {"1": "V5", "2": "GND"}, mpn=TVS[0], lcsc=TVS[1],
               note="ESD on the exposed pogo VBUS pins (both pods share V5)"))
    p.append(P("TP1", "PAD", "VBAT", "Pad_1.2", {"1": "VBAT"}, note="Test pad"))
    p.append(P("TP2", "PAD", "V5", "Pad_1.2", {"1": "V5"}, note="Test pad"))
    p.append(P("TP3", "PAD", "GND", "Pad_1.2", {"1": "GND"}, note="Test pad"))
    return p


if __name__ == "__main__":
    g.OUT = f"{ROOT}/kicad_v2_case"
    g.PROJECT = "haven_v2_case"
    g.LIB = "haven_v2_case"
    g.SHEET_UUID = "0b6c7a1e-5d2e-4c41-9f0a-2a1e9b7c3d03"
    g.PARTS = case_parts()
    g.build()
    sch = f"{g.OUT}/{g.PROJECT}.kicad_sch"
    txt = open(sch).read().replace('(title "Haven v2 earbud")', '(title "Haven v2 BTE charging case")', 1)
    txt = txt.replace("tools/gen_v2_schematic.py", "tools/gen_v2_case_schematic.py", 1)
    open(sch, "w").write(txt)

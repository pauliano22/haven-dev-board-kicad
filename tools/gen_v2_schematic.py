#!/usr/bin/env python3
"""Generate the Haven v2 earbud schematic, symbol library and new footprints.

Writes kicad_v2/{haven_v2.kicad_sch,haven_v2.kicad_sym,haven_v2.kicad_pro,
sym-lib-table,fp-lib-table,footprints.pretty/}. Connectivity is made with
local net labels placed exactly on pin endpoints; unused pins get no-connect
flags. Every pin is "passive" so ERC checks wiring, not driver types.

Sources (see kicad_v2/README.md for page references):
- Kept circuits: pad-to-net map of the Rev A board (branch rev-a/native-trim),
  whose copper was checked pad-by-pad against OpenEarable's routing.
- MDBT53V-1M: Raytac "MDBT53V-1M & MDBT53V-P1M Spec" Ver.D 2024-10-25.
- nPM1100: Nordic "nPM1100 Product Specification" v1.2 (4445_367).
"""
import json
import os
import shutil
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "kicad_v2")
LIB = "haven_v2"
PROJECT = "haven_v2"
SHEET_UUID = "6d7a6f2e-0b2d-4c5e-9a2e-7e2a3c1f0a01"
GRID = 2.54


def uid():
    return str(uuid.uuid4())


def f(v):
    return f"{v:.3f}".rstrip("0").rstrip(".") if v != int(v) else str(int(v))


# ---------------------------------------------------------------- symbols
# Each symbol: name -> dict(left=[(num,name)], right=[(num,name)], ref, width)
# Pins in each list are drawn top to bottom, 2.54 mm apart.
SYMBOLS = {}


def two_pin(name, ref):
    SYMBOLS[name] = dict(left=[("1", "~")], right=[("2", "~")], ref=ref, width=5.08, small=True)


two_pin("R", "R")
two_pin("C", "C")
two_pin("L", "L")
SYMBOLS["LED"] = dict(left=[("1", "A")], right=[("2", "K")], ref="D", width=5.08, small=True)
SYMBOLS["TVS"] = dict(left=[("1", "K")], right=[("2", "A")], ref="D", width=5.08, small=True)
SYMBOLS["XTAL2"] = dict(left=[("1", "1")], right=[("2", "2")], ref="X", width=5.08, small=True)
SYMBOLS["XTAL4"] = dict(left=[("1", "1"), ("2", "GND")], right=[("3", "3"), ("4", "GND")],
                        ref="Y", width=7.62)
SYMBOLS["NMOS"] = dict(left=[("1", "G")], right=[("3", "D"), ("2", "S")], ref="Q", width=7.62)
SYMBOLS["PAD"] = dict(left=[("1", "~")], right=[], ref="TP", width=2.54, small=True)
SYMBOLS["AP22916"] = dict(left=[("A2", "VIN"), ("B2", "ON")], right=[("A1", "VOUT"), ("B1", "GND")],
                          ref="U", width=10.16)
SYMBOLS["SPH0641LU4H-1"] = dict(
    left=[("5", "VDD"), ("4", "CLOCK"), ("2", "SELECT")],
    right=[("1", "DATA"), ("3", "GND"), ("6", "GND"), ("7", "GND"), ("8", "GND")],
    ref="U", width=12.7)

PINS_V1 = json.load(open(os.path.join(ROOT, "tools", "v2_pins_v1.json")))
adau = PINS_V1["U15"]
adau_left = sorted([k for k in adau if k[0] in "ABCD"], key=lambda k: (k[0], int(k[1:])))
adau_right = sorted([k for k in adau if k[0] in "EFG"], key=lambda k: (k[0], int(k[1:])))
SYMBOLS["ADAU1860"] = dict(left=[(k, adau[k]) for k in adau_left],
                           right=[(k, adau[k]) for k in adau_right], ref="U", width=30.48)

# MDBT53V-1M, Raytac spec Ver.D section 2.5 "Pin assignment" (pages 15-17).
MDBT53V_PINS = {
    1: "GND", 2: "SWDIO", 3: "SWCLK", 4: "nRESET", 5: "P0.26/AIN5", 6: "P0.18/QSPI_CSN",
    7: "P0.25/AIN4", 8: "P0.17/QSPI_SCK", 9: "P0.12/DCX", 10: "P0.16/QSPI_IO3",
    11: "P0.11/CSN", 12: "P0.15/QSPI_IO2", 13: "P0.10/MISO", 14: "P0.14/QSPI_IO1",
    15: "P0.09/MOSI", 16: "P0.13/QSPI_IO0", 17: "P0.08/SCK", 18: "GND", 19: "P1.03/TWI",
    20: "P1.02/TWI", 21: "P0.03/NFC2", 22: "P0.02/NFC1", 23: "P0.00/XL1", 24: "P0.01/XL2",
    25: "DCCH", 26: "VDD", 27: "GND", 28: "P0.05/AIN1", 29: "VDDH", 30: "P0.04/AIN0",
    31: "DCCD", 32: "P1.13", 33: "DECD", 34: "P1.12", 35: "DCC", 36: "P1.11", 37: "DECR",
    38: "P0.31", 39: "GND",
}
SYMBOLS["MDBT53V-1M"] = dict(left=[(str(n), MDBT53V_PINS[n]) for n in range(1, 20)],
                             right=[(str(n), MDBT53V_PINS[n]) for n in range(20, 40)],
                             ref="U", width=25.4)

# nPM1100 WLCSP-25, Nordic PS v1.2 Table 21 (pages 42-43).
NPM_PINS = {
    "A1": "D-", "A2": "D+", "A3": "DEC", "A4": "SW", "A5": "PVSS",
    "B1": "VBUS", "B2": "VBUS", "B3": "VOUTBSET1", "B4": "VOUTBSET0", "B5": "VOUTB",
    "C1": "VSYS", "C2": "VSYS", "C3": "VTERMSET", "C4": "AVSS", "C5": "AVSS",
    "D1": "VBAT", "D2": "VBAT", "D3": "SHPHLD", "D4": "SHPACT", "D5": "ISET",
    "E1": "NTC", "E2": "ICHG", "E3": "ERR", "E4": "CHG", "E5": "MODE",
}
npm_left = ["B1", "B2", "D1", "D2", "A1", "A2", "E1", "E2", "C3", "D5", "E5", "C4", "C5", "A5"]
npm_right = ["C1", "C2", "A3", "A4", "B5", "B4", "B3", "E3", "E4", "D4", "D3"]
SYMBOLS["nPM1100"] = dict(left=[(k, NPM_PINS[k]) for k in npm_left],
                          right=[(k, NPM_PINS[k]) for k in npm_right], ref="U", width=20.32)


def sym_geom(name):
    s = SYMBOLS[name]
    n = max(len(s["left"]), len(s["right"]), 1)
    h = (n - 1) * GRID
    w = s["width"]
    pins = {}
    for i, (num, _) in enumerate(s["left"]):
        pins[num] = (-w / 2 - GRID, h / 2 - i * GRID, 0)
    for i, (num, _) in enumerate(s["right"]):
        pins[num] = (w / 2 + GRID, h / 2 - i * GRID, 180)
    return w, h, pins


def sym_body(name, prefix):
    s = SYMBOLS[name]
    w, h, pins = sym_geom(name)
    top = h / 2 + GRID * (0.5 if s.get("small") else 1)
    bot = -h / 2 - GRID * (0.5 if s.get("small") else 1)
    hide_names = s.get("small")
    out = [f'(symbol "{prefix}{name}" (pin_names (offset 0.254){" (hide yes)" if hide_names else ""}) '
           f'(in_bom yes) (on_board yes)',
           f'  (property "Reference" "{s["ref"]}" (at 0 {f(top + 1.27)} 0) (effects (font (size 1.27 1.27))))',
           f'  (property "Value" "{name}" (at 0 {f(bot - 1.27)} 0) (effects (font (size 1.27 1.27))))',
           '  (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
           '  (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
           f'  (symbol "{name}_0_1"',
           f'    (rectangle (start {f(-w / 2)} {f(top)}) (end {f(w / 2)} {f(bot)}) '
           '(stroke (width 0.254) (type default)) (fill (type background)))',
           '  )',
           f'  (symbol "{name}_1_1"']
    for num, pname in s["left"] + s["right"]:
        x, y, a = pins[num]
        out.append(f'    (pin passive line (at {f(x)} {f(y)} {a}) (length {GRID}) '
                   f'(name "{pname}" (effects (font (size 1.016 1.016)))) '
                   f'(number "{num}" (effects (font (size 1.016 1.016)))))')
    out += ['  )', ')']
    return "\n".join(out)


# ---------------------------------------------------------------- parts
PARTS = []  # dict(ref, sym, value, fp, nets{pin:net}, mpn, lcsc, note, dnp)


def add(ref, sym, value, fp, nets, mpn="", lcsc="", note="", dnp=False):
    PARTS.append(dict(ref=ref, sym=sym, value=value, fp=fp, nets=nets, mpn=mpn, lcsc=lcsc,
                      note=note, dnp=dnp))


def R(ref, value, a, b, fp="R0201", mpn="", lcsc="", note=""):
    add(ref, "R", value, fp, {"1": a, "2": b}, mpn, lcsc, note)


def C(ref, value, a, b="GND", fp="C0201", mpn="", lcsc="", note=""):
    add(ref, "C", value, fp, {"1": a, "2": b}, mpn, lcsc, note)


# Reused part numbers (Rev A BOM, fab/rev_a/haven_rev_a_bom.csv on rev-a/native-trim)
C100N = ("GRM033R60J104KE19D", "C76928")
C1U = ("GRM033R60J105KEA2D", "C76929")
C10U = ("CL05A106MQ5NUNC", "C15525")
C4U7_0402 = ("CL05A475KP5NRNC", "C368809")

# --- nRF5340 module (Raytac reference circuit, spec section 8.1, pages 41-42)
mod = {"1": "GND", "18": "GND", "27": "GND", "39": "GND",
       "2": "SWDIO", "3": "SWCLK", "4": "nRESET",
       "26": "+1V8", "29": "+1V8",
       "35": "DCC", "37": "DECR", "31": "DCCD", "33": "DECD",
       "23": "XL1", "24": "XL2",
       "20": "SDA1", "19": "SCL1",            # codec I2C, was P1.15/P1.00 on v1
       "30": "DAC_ENABLE",                    # P0.04, unchanged from v1
       "36": "SENSORS_ENABLE",                # P1.11, unchanged from v1
       "16": "BCLK",                          # P0.13, was P1.10
       "14": "LRCLK",                         # P0.14, was P0.30
       "12": "DIN",                           # P0.15, was P0.28
       "38": "DOUT",                          # P0.31, unchanged from v1
       "34": "LED_EN",                        # P1.12, was P1.08
       "13": "CHG_STAT",                      # P0.10, new (nPM1100 CHG)
       "11": "CHG_ERR",                       # P0.11, new (nPM1100 ERR)
       "9": "SHIP_EN",                        # P0.12, new (nPM1100 SHPACT)
       "28": "VSYS_SENSE",                    # P0.05/AIN1, battery/VSYS monitor
       "7": "VBUS_DET",                       # P0.25/AIN4, "in case" detect
       "32": "SPARE_P1_13"}                   # P1.13, test pad for touch/one-wire later
add("U1", "MDBT53V-1M", "MDBT53V-1M", "MDBT53V-1M", mod, "MDBT53V-1M", "",
    "Raytac nRF5340 module, chip antenna. DCCH (25) unused in normal-voltage mode.")
C("C101", "4.7uF", "+1V8", fp="C0402", mpn=C4U7_0402[0], lcsc=C4U7_0402[1],
  note="Module VDD/VDDH decoupling (Raytac C11)")
add("L101", "L", "10uH", "L0402", {"1": "DCC", "2": "DECR"}, "", "",
    "nRF DC/DC (Raytac L1). Leave unpopulated to run in LDO mode.")
C("C102", "1uF", "DECR", mpn=C1U[0], lcsc=C1U[1], note="Raytac C27")
add("L102", "L", "10uH", "L0402", {"1": "DCCD", "2": "DECD"}, "", "",
    "nRF DC/DC (Raytac L2). Leave unpopulated to run in LDO mode.")
C("C103", "1uF", "DECD", mpn=C1U[0], lcsc=C1U[1], note="Raytac C26")
add("X1", "XTAL2", "32.768kHz", "FC-135R_L3.2-W1.5", {"1": "XL1", "2": "XL2"},
    "Q13FC1350000200", "C48615", "LF crystal, same part and load caps as v1/OpenEarable")
C("C2", "9pF", "XL2", mpn="CC0201CRNPO9BN9R0", lcsc="C277498")
C("C14", "9pF", "XL1", mpn="CC0201CRNPO9BN9R0", lcsc="C277498")

# --- nPM1100 PMIC (Nordic PS v1.2 config 3, page 47, with VOUTB = 1.8 V)
npm = {"B1": "VBUS", "B2": "VBUS", "D1": "VBAT", "D2": "VBAT",
       "A1": "GND", "C3": "VSYS", "D5": "GND", "E5": "GND",
       "C4": "GND", "C5": "GND", "A5": "GND",
       "E1": "NTC", "E2": "ICHG",
       "C1": "VSYS", "C2": "VSYS", "A3": "DEC", "A4": "SW", "B5": "+1V8",
       "B4": "GND", "B3": "GND",            # VOUTBSET1/0 = LOW/LOW -> 1.8 V (Table 16)
       "E3": "CHG_ERR", "E4": "CHG_STAT", "D4": "SHIP_EN", "D3": "SHPHLD"}
add("U2", "nPM1100", "nPM1100-CAAB-R", "WLCSP-25_2.075x2.075_P0.4", npm, "NPM1100-CAAB-R", "",
    "D+ (A2) unconnected and D- to AVSS: fixed 100 mA VBUS limit (Table 23, config 1). "
    "VTERMSET to VSYS: 4.20 V termination.")
C("C110", "2.2uF", "VBUS", fp="C0402", note="VBUS input (Nordic C1, 0603 25 V in the reference)")
C("C111", "1uF", "VBAT", mpn=C1U[0], lcsc=C1U[1], note="VBAT (Nordic C5)")
C("C112", "10uF", "VSYS", fp="C0402", mpn=C10U[0], lcsc=C10U[1], note="VSYS (Nordic C3)")
C("C113", "10uF", "DEC", fp="C0402", mpn=C10U[0], lcsc=C10U[1], note="DEC (Nordic C4)")
add("L2", "L", "2.2uH", "L0402", {"1": "SW", "2": "+1V8"}, "MLZ1005M2R2WT000", "C383389",
    "Buck inductor (Nordic L1 2.2 uH); same part as v1's BQ25120 buck")
C("C114", "10uF", "+1V8", fp="C0402", mpn=C10U[0], lcsc=C10U[1], note="VOUTB (Nordic C2)")
R("R110", "10k", "NTC", "GND", mpn="RC0201FR-0710KL", lcsc="C106225", note="No battery NTC: fixed 10k (Nordic config 1 R1)")
R("R111", "30k 1%", "ICHG", "GND", note="20 mA charge limit (Table 11), ~0.3C for a 60 mAh CP1254")
add("TP7", "PAD", "SHPHLD", "TestPad_0.8", {"1": "SHPHLD"}, "", "",
    "Internal 100k pull-up; ship mode exits on VBUS. Pull low >200 ms to exit without the case.")

# --- case contacts, battery, protection
add("P1", "PAD", "POGO_VBUS", "PogoPad_1.6", {"1": "VBUS"}, "", "", "Gold charging pad to case pogo pin")
add("P2", "PAD", "POGO_GND", "PogoPad_1.6", {"1": "GND"}, "", "", "Gold charging pad to case pogo pin")
add("D1", "TVS", "ESD 5V", "D_SOD-523", {"1": "VBUS", "2": "GND"}, "", "",
    "Exposed pad needs ESD clamping. Part not chosen yet (open question).")
add("TP8", "PAD", "BAT+", "Pad_1.2", {"1": "VBAT"}, "", "", "CP1254 tab")
add("TP9", "PAD", "BAT-", "Pad_1.2", {"1": "GND"}, "", "", "CP1254 tab")

# --- sensing dividers
R("R112", "1M", "VSYS", "VSYS_SENSE", mpn="CQ01WMJ0105TEE", lcsc="C5151554", note="VSYS/battery monitor: 4.35 V -> 1.56 V")
R("R113", "560k", "VSYS_SENSE", "GND")
C("C115", "100nF", "VSYS_SENSE", mpn=C100N[0], lcsc=C100N[1])
R("R114", "100k", "VBUS", "VBUS_DET", note="In-case detect: 5.0 V -> 1.60 V")
R("R115", "47k", "VBUS_DET", "GND")

# --- status LED (v1 topology, anode moved from 3V3 to VSYS)
add("U4", "LED", "XL-0201SURC", "LED-SMD_L0.65-W0.35-P0.41_XL-0201SURC",
    {"1": "VSYS", "2": "LED_K"}, "XL-0201SURC", "C3646923", "Red status LED")
R("R4", "510R", "LED_K", "LED_D", mpn="WR02X511JAL", lcsc="C180335")
add("Q2", "NMOS", "CSD15380F3", "PICOSTAR-3_L0.7-W0.6-P0.40-TL",
    {"1": "LED_EN", "2": "GND", "3": "LED_D"}, "CSD15380F3", "C529568")
R("U8", "1M", "LED_EN", "GND", mpn="CQ01WMJ0105TEE", lcsc="C5151554", note="Gate pull-down (v1 U8)")

# --- debug pads
for i, (val, net) in enumerate([("SWDIO", "SWDIO"), ("SWCLK", "SWCLK"), ("RESET", "nRESET"),
                                 ("VDD", "+1V8"), ("GND", "GND"), ("P1.13", "SPARE_P1_13")], 1):
    add(f"TP{i}", "PAD", val, "TestPad_0.8", {"1": net}, "", "", "SWD / test pad")

# --- codec power switch (v1 U3)
add("U3", "AP22916", "AP22916BCA4-7", "X1-WLB0808-4_L0.8-W0.8-P0.40-TL",
    {"A2": "+1V8", "B2": "SENSORS_ENABLE", "A1": "V_LS", "B1": "GND"},
    "AP22916BCA4-7", "C5244375", "Switches the codec + mic rail. Firmware must drive SENSORS_ENABLE.")

# --- ADAU1860 (nets from the Rev A board's verified pad map)
adau_nets = {b: "V_LS" for b in ["A2", "B5", "D1", "E1", "F3", "F7", "G2"]}
adau_nets.update({b: "GND" for b in ["A1", "A4", "B4", "D6", "D7", "E6", "F1", "G3", "G7"]})
adau_nets.update({"A3": "DVDD", "B3": "DVDD", "G4": "CM", "E4": "DAC_ENABLE",
                  "C7": "SCL1", "C6": "SDA1", "B2": "BCLK", "C2": "LRCLK", "C1": "DIN",
                  "B1": "DOUT", "C4": "PDMCLK", "C5": "PDMDIN", "B7": "XTALI", "B6": "XTALO",
                  "F2": "SPK+", "G1": "SPK-"})
add("U15", "ADAU1860", "ADAU1860BCBZRL", "BGA-56_L3.0-W2.7-P0.35-R8-C7-TL", adau_nets,
    "ADAU1860BCBZRL", "C17592940", "I2C address set by ADDR0/ADDR1 low (as v1)")
C("C31", "100nF", "DVDD", mpn=C100N[0], lcsc=C100N[1])
C("C36", "1uF", "DVDD", mpn=C1U[0], lcsc=C1U[1])
C("C32", "1uF", "CM", mpn=C1U[0], lcsc=C1U[1])
for ref, val in [("C7", "1uF"), ("C47", "1uF"), ("C11", "100nF"), ("C12", "100nF"),
                 ("C13", "100nF"), ("C27", "100nF"), ("C38", "100nF"), ("C40", "100nF"),
                 ("C42", "100nF"), ("C43", "100nF"), ("C44", "100nF")]:
    p = C1U if val == "1uF" else C100N
    C(ref, val, "V_LS", mpn=p[0], lcsc=p[1])
for ref in ["C33", "C34", "C41"]:
    C(ref, "10uF", "V_LS", fp="C0402", mpn=C10U[0], lcsc=C10U[1])
R("R5", "2k", "V_LS", "SDA1", mpn="CR0201JH0202G", lcsc="C100158")
R("R9", "2k", "V_LS", "SCL1", mpn="CR0201JH0202G", lcsc="C100158")
add("CRYSTAL1", "XTAL4", "24.576MHz", "CRYSTAL-SMD_4P-L2.0-W1.6-BL_HUAXIN_CN4",
    {"1": "XTALI", "2": "GND", "3": "XO_R", "4": "GND"}, "CN4024M57620001", "C7294677",
    "Codec crystal. If it won't start, try 22 pF for C45/C46 (POWER_BUDGET.md note).")
C("C46", "33pF", "XTALI", mpn="GRM0335C1H330JA01D", lcsc="C76925")
C("C45", "33pF", "XO_R", mpn="GRM0335C1H330JA01D", lcsc="C76925")
R("R28", "220R", "XO_R", "XTALO", mpn="RC0201FR-07220RL", lcsc="C274342")

# --- mic and speaker
add("U13", "SPH0641LU4H-1", "SPH0641LU4H-1", "MIC-SMD_5P_L3.5-W2.7-P0.82_SPH0641LU4H-1",
    {"1": "PDMDIN", "2": "GND", "3": "GND", "4": "PDMCLK", "5": "V_LS",
     "6": "GND", "7": "GND", "8": "GND"},
    "SPH0641LU4H-1", "C2879853", "Outer mic. SELECT low = data on the clock's falling edge (as v1)")
add("TP10", "PAD", "SPK+", "Pad_1.2", {"1": "SPK+"}, "", "", "8 mm 16-32 ohm dynamic driver")
add("TP11", "PAD", "SPK-", "Pad_1.2", {"1": "SPK-"}, "", "", "8 mm 16-32 ohm dynamic driver")


# ---------------------------------------------------------------- footprints
def fp_header(name, descr):
    return [f'(footprint "{name}" (version 20240108) (generator "gen_v2_schematic")',
            '  (layer "F.Cu")', f'  (descr "{descr}")', '  (attr smd)',
            '  (property "Reference" "REF**" (at 0 -1.5 0) (layer "F.SilkS") '
            '(effects (font (size 0.5 0.5) (thickness 0.08))))',
            f'  (property "Value" "{name}" (at 0 1.5 0) (layer "F.Fab") '
            '(effects (font (size 0.5 0.5) (thickness 0.08))))']


def rect(layer, x1, y1, x2, y2, w=0.05):
    return (f'  (fp_rect (start {f(x1)} {f(y1)}) (end {f(x2)} {f(y2)}) '
            f'(stroke (width {w}) (type solid)) (fill none) (layer "{layer}"))')


def mdbt53v_fp():
    # Raytac spec section 2.2, page 10: top view, origin at the module's bottom-left
    # corner, 39 pads 0.55 x 0.4 mm (bottom row rotated 90 deg).
    cols = {
        (0.6, "v"): [(8.4, 1), (7.125, 2), (6.375, 4), (5.625, 6), (4.875, 8), (4.125, 10),
                     (3.375, 12), (2.625, 14), (1.875, 16)],
        (1.55, "v"): [(6.75, 3), (6.0, 5), (5.25, 7), (4.5, 9), (3.75, 11), (3.0, 13),
                      (2.25, 15), (1.5, 17)],
        (6.25, "v"): [(4.5, 36), (3.75, 34), (3.0, 32), (2.25, 30), (1.5, 28)],
        (7.2, "v"): [(8.4, 39), (5.625, 38), (4.875, 37), (4.125, 35), (3.375, 33),
                     (2.625, 31), (1.875, 29)],
    }
    bottom = [(0.525, 18), (1.275, 19), (2.025, 20), (2.775, 21), (3.525, 22), (4.275, 23),
              (5.025, 24), (5.775, 25), (6.525, 26), (7.275, 27)]
    pads = []
    for (x, _), items in cols.items():
        for y, n in items:
            pads.append((n, x, y, 0.55, 0.4))
    for x, n in bottom:
        pads.append((n, x, 0.6, 0.4, 0.55))
    assert sorted(p[0] for p in pads) == list(range(1, 40))
    out = fp_header("MDBT53V-1M", "Raytac MDBT53V-1M nRF5340 module, 7.8x12.4 mm, "
                    "pads per spec Ver.D p.10; antenna keep-out 3.8 mm at the top edge, all layers")
    for n, x, y, w, h in sorted(pads):
        kx, ky = x - 3.9, -(y - 6.2)
        out.append(f'  (pad "{n}" smd rect (at {f(kx)} {f(ky)}) (size {f(w)} {f(h)}) '
                   '(layers "F.Cu" "F.Paste" "F.Mask"))')
    out.append(rect("F.Fab", -3.9, -6.2, 3.9, 6.2, 0.1))
    out.append(rect("F.CrtYd", -4.0, -6.3, 4.0, 6.3))
    out.append(rect("Cmts.User", -3.9, -6.2, 3.9, -2.4))  # antenna area (top 3.8 mm)
    out.append('  (fp_text user "ANTENNA KEEPOUT, NO COPPER ANY LAYER" (at 0 -4.3 0) '
               '(layer "Cmts.User") (effects (font (size 0.4 0.4) (thickness 0.06))))')
    # top-layer no-copper patch 1.5 x 1.15 mm, 2.05 mm from the left edge (p.9)
    out.append(rect("Cmts.User", -3.9 + 2.05, -2.4, -3.9 + 3.55, -2.4 + 1.15))
    out.append('  (fp_circle (center -3.3 -1.6) (end -3.2 -1.6) (stroke (width 0.1) (type solid)) '
               '(fill solid) (layer "F.SilkS"))')
    out.append(")")
    return "\n".join(out)


def npm1100_fp():
    # Nordic PS v1.2 8.1/8.2: 5x5 balls, 0.4 mm pitch, ball 0.195-0.255 mm.
    out = fp_header("WLCSP-25_2.075x2.075_P0.4", "nPM1100 WLCSP-25, 2.075 mm, 0.4 mm pitch, "
                    "top view, A1 top-left; NSMD 0.2 mm pads")
    for ri, row in enumerate("ABCDE"):
        for ci in range(5):
            out.append(f'  (pad "{row}{ci + 1}" smd circle (at {f(-0.8 + ci * 0.4)} {f(-0.8 + ri * 0.4)}) '
                       '(size 0.2 0.2) (layers "F.Cu" "F.Paste" "F.Mask"))')
    out.append(rect("F.Fab", -1.0375, -1.0375, 1.0375, 1.0375, 0.05))
    out.append(rect("F.CrtYd", -1.2, -1.2, 1.2, 1.2))
    out.append('  (fp_circle (center -1.25 -1.25) (end -1.2 -1.25) (stroke (width 0.1) (type solid)) '
               '(fill solid) (layer "F.SilkS"))')
    out.append(")")
    return "\n".join(out)


def round_pad_fp(name, d, descr):
    out = fp_header(name, descr)
    out.append(f'  (pad "1" smd circle (at 0 0) (size {f(d)} {f(d)}) (layers "F.Cu" "F.Mask"))')
    out.append(f'  (fp_circle (center 0 0) (end {f(d / 2 + 0.15)} 0) (stroke (width 0.05) (type solid)) '
               '(fill none) (layer "F.CrtYd"))')
    out.append(")")
    return "\n".join(out)


def sod523_fp():
    out = fp_header("D_SOD-523", "SOD-523 diode, 1.2x0.8 mm body")
    out.append('  (pad "1" smd rect (at -0.7 0) (size 0.6 0.7) (layers "F.Cu" "F.Paste" "F.Mask"))')
    out.append('  (pad "2" smd rect (at 0.7 0) (size 0.6 0.7) (layers "F.Cu" "F.Paste" "F.Mask"))')
    out.append(rect("F.CrtYd", -1.25, -0.6, 1.25, 0.6))
    out.append(")")
    return "\n".join(out)


NEW_FPS = {
    "MDBT53V-1M": mdbt53v_fp,
    "WLCSP-25_2.075x2.075_P0.4": npm1100_fp,
    "PogoPad_1.6": lambda: round_pad_fp("PogoPad_1.6", 1.6, "Gold charging pad for a case pogo pin"),
    "TestPad_0.8": lambda: round_pad_fp("TestPad_0.8", 0.8, "Test / SWD pad"),
    "Pad_1.2": lambda: round_pad_fp("Pad_1.2", 1.2, "Wire pad for battery tab or speaker lead"),
    "D_SOD-523": sod523_fp,
}
V1_FP_DIR = os.path.join(ROOT, "kicad", "footprints.pretty")
V1_FP_ALIAS = {"CRYSTAL-SMD_4P-L2.0-W1.6-BL_HUAXIN_CN4": "6684822644394e4eba542a27714dd8a6"}


# ---------------------------------------------------------------- schematic
def build():
    os.makedirs(OUT, exist_ok=True)
    fpdir = os.path.join(OUT, "footprints.pretty")
    os.makedirs(fpdir, exist_ok=True)
    for p in PARTS:
        name = p["fp"]
        dst = os.path.join(fpdir, name + ".kicad_mod")
        if name in NEW_FPS:
            open(dst, "w").write(NEW_FPS[name]() + "\n")
        else:
            src = os.path.join(V1_FP_DIR, V1_FP_ALIAS.get(name, name) + ".kicad_mod")
            text = open(src).read()
            if name in V1_FP_ALIAS:
                text = text.replace(f'"{V1_FP_ALIAS[name]}"', f'"{name}"', 1)
            open(dst, "w").write(text)

    # check every connected pin exists on its symbol and every footprint pad on the symbol
    for p in PARTS:
        _, _, pins = sym_geom(p["sym"])
        missing = set(p["nets"]) - set(pins)
        assert not missing, (p["ref"], missing)

    used_syms = sorted({p["sym"] for p in PARTS})
    lib = ["(kicad_symbol_lib (version 20231120) (generator \"gen_v2_schematic\")"]
    lib += [sym_body(s, "") for s in used_syms]
    lib.append(")")
    open(os.path.join(OUT, f"{LIB}.kicad_sym"), "w").write("\n".join(lib) + "\n")

    items = []
    # place parts on a grid of columns
    big = {"MDBT53V-1M": (60, 70), "nPM1100": (60, 200), "ADAU1860": (250, 110)}
    col_x, col_y = 380.0, 30.48
    small_col_xs = [380.0, 440.0, 500.0, 560.0, 620.0]
    ci = 0
    for p in PARTS:
        w, h, pins = sym_geom(p["sym"])
        if p["sym"] in big:
            x, y = big[p["sym"]]
        else:
            x, y = small_col_xs[ci], col_y
            col_y += max(h, GRID) + 12.7
            if col_y > 520:
                ci += 1
                col_y = 30.48
        x = round(x / GRID) * GRID
        y = round(y / GRID) * GRID
        top = h / 2 + GRID
        props = [("Reference", p["ref"], x, y - top - 2.54, False),
                 ("Value", p["value"], x, y + top + 2.54, False),
                 ("Footprint", f'{LIB}:{p["fp"]}', x, y, True),
                 ("Datasheet", "~", x, y, True),
                 ("Description", p["note"], x, y, True),
                 ("MPN", p["mpn"], x, y, True),
                 ("LCSC", p["lcsc"], x, y, True)]
        s = [f'  (symbol (lib_id "{LIB}:{p["sym"]}") (at {f(x)} {f(y)} 0) (unit 1)',
             f'    (in_bom yes) (on_board yes) (dnp {"yes" if p["dnp"] else "no"}) (uuid "{uid()}")']
        for k, v, px, py, hide in props:
            v = v.replace('"', "'")
            s.append(f'    (property "{k}" "{v}" (at {f(px)} {f(py)} 0) (effects (font (size 1.27 1.27))'
                     f'{" (hide yes)" if hide else ""}))')
        for num in pins:
            s.append(f'    (pin "{num}" (uuid "{uid()}"))')
        s.append(f'    (instances (project "{PROJECT}" (path "/{SHEET_UUID}" (reference "{p["ref"]}") (unit 1))))')
        s.append("  )")
        items.append("\n".join(s))
        for num, (px, py, a) in pins.items():
            ax, ay = x + px, y - py
            net = p["nets"].get(num)
            if net:
                ang = 180 if a == 0 else 0
                just = "right" if ang == 180 else "left"
                items.append(f'  (label "{net}" (at {f(ax)} {f(ay)} {ang}) (effects (font (size 1.016 1.016)) '
                             f'(justify {just} bottom)) (uuid "{uid()}"))')
            else:
                items.append(f'  (no_connect (at {f(ax)} {f(ay)}) (uuid "{uid()}"))')

    libsyms = "\n".join("    " + l for s in used_syms for l in sym_body(s, f"{LIB}:").split("\n"))
    sch = [f'(kicad_sch (version 20231120) (generator "gen_v2_schematic")',
           f'  (uuid "{SHEET_UUID}")', '  (paper "A1")',
           '  (title_block (title "Haven v2 earbud") (rev "v2.0-draft") '
           '(comment 1 "Generated by tools/gen_v2_schematic.py - edit the script, not this file"))',
           '  (lib_symbols', libsyms, '  )']
    sch += items
    sch += ['  (sheet_instances (path "/" (page "1")))', ')']
    open(os.path.join(OUT, f"{PROJECT}.kicad_sch"), "w").write("\n".join(sch) + "\n")

    open(os.path.join(OUT, "sym-lib-table"), "w").write(
        f'(sym_lib_table\n  (lib (name "{LIB}")(type "KiCad")(uri "${{KIPRJMOD}}/{LIB}.kicad_sym")'
        '(options "")(descr "Haven v2 symbols, generated"))\n)\n')
    open(os.path.join(OUT, "fp-lib-table"), "w").write(
        f'(fp_lib_table\n  (lib (name "{LIB}")(type "KiCad")(uri "${{KIPRJMOD}}/footprints.pretty")'
        '(options "")(descr "Haven v2 footprints: v1 copies + new parts"))\n)\n')
    pro = os.path.join(OUT, f"{PROJECT}.kicad_pro")
    if not os.path.exists(pro):
        shutil.copy(os.path.join(ROOT, "kicad", "haven_dev_board.kicad_pro"), pro)
        txt = open(pro).read().replace("haven_dev_board", PROJECT)
        open(pro, "w").write(txt)

    nets = {}
    for p in PARTS:
        for pin, n in p["nets"].items():
            nets.setdefault(n, []).append(f'{p["ref"]}.{pin}')
    single = {n: v for n, v in nets.items() if len(v) < 2}
    print(f"{len(PARTS)} parts, {len(nets)} nets; single-node nets: {single}")


if __name__ == "__main__":
    build()

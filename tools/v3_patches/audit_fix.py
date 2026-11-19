"""2026-11-19 fixes from the pin-by-pin datasheet audit (kicad_v3_pod/AUDIT_2026-11-19.md).

1. U2 part number: nPM1100-CAAB-R is the HIGH-VTERM variant (PS v1.5 Table 33: function variant AB = high VTERM), which
   with VTERMSET tied to VSYS charges to 4.35 V (Table 12). The cell is a standard 3.7 V / 4.2 V LiPo. Now
   nPM1100-CAAA-E-R (AA = standard VTERM): 4.20 V with the same wiring. Same package and footprint; no copper change.
2. U4 LED polarity: the Xinglight XL-0201SURC datasheet (page 7) numbers the cathode 1 and the anode 2; our symbol had
   1 = anode. Symbol pins renumbered (1 = K, 2 = A) and the footprint turned 180 degrees so its pad 1 (cathode) sits on
   the existing LED_K copper and pad 2 on VSYS. No copper change.
3. Raytac MDBT53V-1M spec section 2.2 asks for a "toplayer no ground pad" area, 1.5 x 1.15 mm, 2.05 mm from the module's
   left edge, right below the 3.8 mm antenna area. The board had top-layer ground pour there. Adds an F.Cu rule area that
   forbids copper pour (a VBUS via's top ring stays inside it; it is not ground).

Usage:  python3 audit_fix.py SCH SYM IN.kicad_pcb OUT.kicad_pcb
        then refill zones in a fresh process (see the README) and run DRC with schematic parity.
"""
import re
import sys

import pcbnew

SCH, SYM, IN, OUT = sys.argv[1:5]


def sub_once(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


def renumber_led(text):
    """Swap the LED symbol's pin numbers inside its definition only: A becomes 2, K becomes 1."""
    m = re.search(r'\(symbol "(haven_v3_pod:)?LED" .*?\n\s*\)\n\s*\)\n', text, re.S)
    assert m, "LED symbol not found"
    blk = m.group(0)
    a_old = re.search(r'\(name "A" [^\n]*?\(number "1"', blk)
    k_old = re.search(r'\(name "K" [^\n]*?\(number "2"', blk)
    assert a_old and k_old, "LED pins not as expected (already fixed?)"
    blk2 = blk.replace(a_old.group(0), a_old.group(0)[:-3] + '"2"').replace(k_old.group(0), k_old.group(0)[:-3] + '"1"')
    return text.replace(blk, blk2)


# --- schematic and symbol library (text edits; the generator gives new random UUIDs, so it is not re-run)
sch = open(SCH).read()
sch = renumber_led(sch)
sch = sub_once(sch, '(property "Value" "nPM1100-CAAB-R"', '(property "Value" "nPM1100-CAAA-E-R"')
sch = sub_once(sch, '(property "MPN" "NPM1100-CAAB-R"', '(property "MPN" "NPM1100-CAAA-E-R"')
sch = sub_once(sch, '(property "LCSC" "C7016010"', '(property "LCSC" "C5200749"')
sch = sub_once(sch, 'VTERMSET to VSYS: 4.20 V termination."',
               'VTERMSET to VSYS: 4.20 V termination ONLY on the standard-VTERM part (CAAA); CAAB would give 4.35 V."')
sch = sub_once(sch, '(property "Description" "Red status LED"',
               '(property "Description" "Red status LED. Pin 1 = cathode (Xinglight datasheet p.7)"')
open(SCH, "w").write(sch)
sym = open(SYM).read()
open(SYM, "w").write(renumber_led(sym))

# --- board
b = pcbnew.LoadBoard(IN)
MM = pcbnew.FromMM

u2 = b.FindFootprintByReference("U2")
u2.SetValue("nPM1100-CAAA-E-R")
for f in u2.GetFields():
    if f.GetName() == "MPN":
        f.SetText("NPM1100-CAAA-E-R")
    elif f.GetName() == "LCSC":
        f.SetText("C5200749")

u4 = b.FindFootprintByReference("U4")
assert round(u4.GetOrientationDegrees()) % 360 == 0, u4.GetOrientationDegrees()
pads = {p.GetNumber(): p for p in u4.Pads()}
assert pads["1"].GetNetname() == "/VSYS" and pads["2"].GetNetname() == "/LED_K"
old_pos = {n: pcbnew.VECTOR2I(p.GetPosition()) for n, p in pads.items()}
u4.SetOrientation(pcbnew.EDA_ANGLE(180, pcbnew.DEGREES_T))
pads["1"].SetNet(b.FindNet("/LED_K")); pads["1"].SetPinFunction("K")
pads["2"].SetNet(b.FindNet("/VSYS")); pads["2"].SetPinFunction("A")
# pad 1 now sits where pad 2 was (LED_K copper) and the other way round
assert (pads["1"].GetPosition() - old_pos["2"]).EuclideanNorm() < MM(0.002)
assert (pads["2"].GetPosition() - old_pos["1"]).EuclideanNorm() < MM(0.002)
desc = [f for f in u4.GetFields() if f.GetName() == "Description"]
if desc:
    desc[0].SetText("Red status LED. Pin 1 = cathode (Xinglight datasheet p.7)")

# Raytac top-layer no-ground area. Module centred on x = 100.0 (pads 96.625..103.375), 7.8 mm wide -> left edge 96.1.
# Module top edge = board edge 86.475; antenna area 3.8 mm -> 90.275. Box 2.05..3.55 mm from the left edge, 1.15 tall;
# drawn 0.05 mm larger on each side.
x0, x1, y0, y1 = 96.1 + 2.05 - 0.05, 96.1 + 3.55 + 0.05, 86.475 + 3.8 - 0.05, 86.475 + 3.8 + 1.15 + 0.05
z = pcbnew.ZONE(b)
z.SetIsRuleArea(True)
z.SetLayer(pcbnew.F_Cu)
z.SetZoneName("RAYTAC_TOP_NO_GROUND")
z.SetDoNotAllowCopperPour(True)
z.SetDoNotAllowTracks(False)
z.SetDoNotAllowVias(False)
z.SetDoNotAllowPads(False)
z.SetDoNotAllowFootprints(False)
ol = z.Outline()
ol.NewOutline()
for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
    ol.Append(MM(x), MM(y))
b.Add(z)
z.thisown = 0
print(f"rule area x {x0:.3f}..{x1:.3f}, y {y0:.3f}..{y1:.3f}")

b.Save(OUT)
print("saved", OUT)

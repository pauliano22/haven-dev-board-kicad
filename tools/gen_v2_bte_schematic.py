#!/usr/bin/env python3
"""Generate the Haven v2 behind-the-ear (BTE) schematics: pod board + in-ear unit.

Reuses the parts, symbols, footprints and writer from gen_v2_schematic.py and
splits the design into two KiCad projects, one per physical board:

- kicad_v2_pod/   battery, radio, PMIC, codec, LED, charge pads, SWD pads,
                  cable ESD and the cable solder pads.
- kicad_v2_inear/ SPH0641 PDM mic, its decoupling and series resistor, cable
                  pads and speaker pads.

The two boards are joined by a fixed 6-conductor cable. Net names at the cable
pads match on both boards (see kicad_v2_pod/README.md for the harness table).
"""
import copy

import gen_v2_schematic as g

ROOT = g.ROOT

# ---------------------------------------------------------------- footprints
# TI TPD1E05U06DYAR, SOD-523 (DYA0002A land pattern example, SLVSBO7O rev O
# 2024: pads 0.4 x 0.67 mm, 1.48 mm overall). Pin 1 = I/O, pin 2 = GND.
def sod523_ti_fp():
    out = g.fp_header("D_SOD-523", "SOD-523 (TI DYA0002A land pattern example), pads 0.4x0.67, "
                      "1.48 mm overall. Pin 1 I/O, pin 2 GND for TPD1E05U06DYAR")
    out.append('  (pad "1" smd rect (at -0.54 0) (size 0.4 0.67) (layers "F.Cu" "F.Paste" "F.Mask"))')
    out.append('  (pad "2" smd rect (at 0.54 0) (size 0.4 0.67) (layers "F.Cu" "F.Paste" "F.Mask"))')
    out.append(g.rect("F.CrtYd", -0.95, -0.55, 0.95, 0.55))
    out.append(")")
    return "\n".join(out)


g.NEW_FPS["D_SOD-523"] = sod523_ti_fp
g.NEW_FPS["WirePad_0.8"] = lambda: g.round_pad_fp(
    "WirePad_0.8", 0.8, "Solder pad for one 38-40 AWG cable conductor")

TVS = ("TPD1E05U06DYAR", "")   # LCSC number not confirmed; check at JLCPCB upload
R33 = ("ERJ1GNF33R0C", "C717007")
C100N = g.C100N

# Harness: one entry per cable conductor. (pod net, in-ear net, label)
CABLE = [
    ("V_LS", "V_MIC", "Mic supply (1.8 V, switched by U3)"),
    ("GND", "GND", "Ground / return; route next to PDM_CLK and PDM_DATA"),
    ("CBL_PDMCLK", "PDM_CLK", "PDM clock, codec -> mic, 33 ohm series at the pod"),
    ("PDMDIN", "PDM_DATA", "PDM data, mic -> codec, 33 ohm series at the mic"),
    ("SPK+", "SPK+", "Speaker +, twisted with SPK-"),
    ("SPK-", "SPK-", "Speaker -, twisted with SPK+"),
]


def by_ref(parts):
    return {p["ref"]: p for p in parts}


def pod_parts():
    base = copy.deepcopy(g.PARTS)
    keep = [p for p in base if p["ref"] not in ("U13", "TP10", "TP11")]
    refs = by_ref(keep)

    # CP1454 (85-108 mAh) instead of CP1254: ~40 mA charge.
    r111 = refs["R111"]
    r111.update(value="15k 1%", mpn="0201WMF1502TEE", lcsc="C473452",
                note="~40 mA charge (I ~ 600 V / R; 30k = 20 mA, 12k = 50 mA in Nordic's tables): "
                     "0.37C for a 108 mAh CP1454, 0.47C for the 85 mAh version")
    refs["TP8"]["note"] = "CP1454 + tab"
    refs["TP9"]["note"] = "CP1454 - tab"

    # Gaps from the v2 schematic, filled.
    refs["C110"].update(mpn="CL05A225KA5NUNC", lcsc="C307418",
                        note="VBUS input 2.2 uF 25 V X5R 0402 (Nordic C1)")
    refs["R113"].update(mpn="RC0201FR-07560KL", lcsc="C295807")
    refs["R114"].update(mpn="RC0201FR-07100KL", lcsc="C106224")
    refs["R115"].update(mpn="RC0201FR-0747KL", lcsc="C138139")
    refs["D1"].update(value="TPD1E05U06", mpn=TVS[0], lcsc=TVS[1],
                      note="ESD on the exposed VBUS charge pad. 5.5 V stand-off, 0.42 pF. "
                           "TI SLVSBO7O: pin 1 I/O, pin 2 GND")
    for ref in ("L101", "L102"):
        refs[ref].update(dnp=True, note="nRF DC/DC inductor, NOT fitted on the first build "
                                        "(module runs in LDO mode). Fit a 10 uH 0402 later to save current.")

    # PDM clock leaves the board: series termination at its source (the codec).
    for p in keep:
        if p["ref"] == "U15":
            assert p["nets"]["C4"] == "PDMCLK"
    g_parts = keep
    g_parts.append(dict(ref="R120", sym="R", value="33R", fp="R0201",
                        nets={"1": "PDMCLK", "2": "CBL_PDMCLK"}, mpn=R33[0], lcsc=R33[1],
                        note="PDM clock series termination at the source", dnp=False))

    # ESD on every cable line that leaves the pod (GND excepted).
    for i, (net, _, label) in enumerate([c for c in CABLE if c[0] != "GND"], 2):
        g_parts.append(dict(ref=f"D{i}", sym="TVS", value="TPD1E05U06", fp="D_SOD-523",
                            nets={"1": net, "2": "GND"}, mpn=TVS[0], lcsc=TVS[1],
                            note=f"Cable ESD: {label}", dnp=False))

    # Cable solder pads W1..W6.
    for i, (net, _, label) in enumerate(CABLE, 1):
        g_parts.append(dict(ref=f"W{i}", sym="PAD", value=f"CBL_{net}", fp="WirePad_0.8",
                            nets={"1": net}, mpn="", lcsc="", note=f"Cable conductor {i}: {label}",
                            dnp=False))
    return g_parts


def inear_parts():
    parts = []
    parts.append(dict(ref="U13", sym="SPH0641LU4H-1", value="SPH0641LU4H-1",
                      fp="MIC-SMD_5P_L3.5-W2.7-P0.82_SPH0641LU4H-1",
                      nets={"1": "MIC_DATA", "2": "GND", "3": "GND", "4": "PDM_CLK", "5": "V_MIC",
                            "6": "GND", "7": "GND", "8": "GND"},
                      mpn="SPH0641LU4H-1", lcsc="C2879853",
                      note="Outer mic, bottom port: needs a 0.5-0.8 mm hole through this board "
                           "under the port. SELECT low = data on the clock's falling edge (as v1)",
                      dnp=False))
    parts.append(dict(ref="C1", sym="C", value="100nF", fp="C0201", nets={"1": "V_MIC", "2": "GND"},
                      mpn=C100N[0], lcsc=C100N[1], note="Mic decoupling, at the VDD pin", dnp=False))
    parts.append(dict(ref="R1", sym="R", value="33R", fp="R0201",
                      nets={"1": "MIC_DATA", "2": "PDM_DATA"}, mpn=R33[0], lcsc=R33[1],
                      note="PDM data series termination at the source (the mic)", dnp=False))
    for i, (_, net, label) in enumerate(CABLE, 1):
        parts.append(dict(ref=f"W{i}", sym="PAD", value=f"CBL_{net}", fp="WirePad_0.8",
                          nets={"1": net}, mpn="", lcsc="", note=f"Cable conductor {i}: {label}",
                          dnp=False))
    for i, net in enumerate(["SPK+", "SPK-"], 1):
        parts.append(dict(ref=f"TP{i}", sym="PAD", value=net, fp="Pad_1.2", nets={"1": net},
                          mpn="", lcsc="", note="Lead to the 8 mm 16-32 ohm driver", dnp=False))
    return parts


def build_one(out_dir, project, lib, sheet_uuid, title, parts):
    g.OUT = f"{ROOT}/{out_dir}"
    g.PROJECT = project
    g.LIB = lib
    g.SHEET_UUID = sheet_uuid
    g.PARTS = parts
    g.build()
    # title block
    sch = f"{g.OUT}/{project}.kicad_sch"
    txt = open(sch).read().replace('(title "Haven v2 earbud")', f'(title "{title}")', 1)
    txt = txt.replace("tools/gen_v2_schematic.py", "tools/gen_v2_bte_schematic.py", 1)
    open(sch, "w").write(txt)


if __name__ == "__main__":
    build_one("kicad_v2_pod", "haven_v2_pod", "haven_v2_pod",
              "0b6c7a1e-5d2e-4c41-9f0a-2a1e9b7c3d01", "Haven v2 BTE pod", pod_parts())
    build_one("kicad_v2_inear", "haven_v2_inear", "haven_v2_inear",
              "0b6c7a1e-5d2e-4c41-9f0a-2a1e9b7c3d02", "Haven v2 BTE in-ear unit", inear_parts())

#!/usr/bin/env python3
"""Generate the Haven v3 slim pod schematic (kicad_v3_pod/). Decision: Paul, 2026-11-11, concept A of
DESIGN_BRIEF_SHELL_V3.md with the microphone on the pod (in-ear piece = speaker + 2 wires, no board).

Starts from the v2 pod part list (gen_v2_bte_schematic.pod_parts) and applies:
  design review fixes (DESIGN_REVIEW_2026-11.md)
    - footprints come from kicad_v2_pod/footprints.pretty, the un-mirrored library (finding 1)
    - L2: real power inductor, 2.0 x 1.6 mm (finding 2; nPM1100 PS Table 20: DCR <= 400 mohm, Isat >= 350 mA)
    - U3: AP22916C, the slow-turn-on version, same pinout (finding 3). Firmware supply-delay must be ~6000 us.
    - L101, L102, C102, C103 removed: Raytac's LDO-mode reference leaves DCC/DECR/DECD unconnected (finding 5)
  v3 changes
    - no cable microphone: W1-W4, their ESD diodes and the cable clock resistor R120 go. Cable = SPK+ / SPK-.
    - pod mic U14 is the only mic: top-port SPK0641HT4H-1 (the battery now covers the board's other face, so a
      bottom-port mic has nowhere to listen). SELECT to ground = data on the falling clock edge = DMIC0, the
      channel the firmware already uses (datasheet Rev D-1 Table 7).
    - R111 30 k: 20 mA charge, 0.5C for the 40 mAh cell (TinyCircuits ASR00072: 3.5 x 8 x 20 mm nominal, 1C max charge and discharge).
    - 32.768 kHz crystal X1 and C2/C14 removed (no room beside a 20 mm cell); internal RC oscillator instead.
Not yet chosen / not verified: the pouch cell, R111 and L2 LCSC numbers, the L2 land pattern (generic 2016).
"""
import gen_v2_schematic as g
import gen_v2_bte_schematic as bte

import os

g.V1_FP_DIR = os.path.join(g.ROOT, "kicad_v2_pod", "footprints.pretty")
g.V1_FP_ALIAS = {}

g.SYMBOLS["SPK0641HT4H-1"] = dict(
    left=[("4", "VDD"), ("2", "CLOCK"), ("3", "SELECT")],
    right=[("1", "DATA"), ("5", "GND"), ("6", "GND"), ("7", "GND"), ("8", "GND")],
    ref="U", width=12.7)


def spk0641_fp():
    """Syntiant/Knowles SPK0641HT4H-1 Rev D-1 page 7 "Example Land Pattern", drawn as seen from above the
    board (KiCad F.Cu view, y down). Body 4.00 x 3.00 x 1.00. Row 1: pin 2 left, pin 3 right. Row 2: pin 1 left,
    pin 4 right. Ground bars: 7 top, 5 bottom, 6 left, 8 right. Sound port (top of the part) is 0.97 mm above
    centre on the pin-7 side, ASSUMING the top view and the land pattern are drawn the same way up."""
    out = g.fp_header("MIC_SPK0641HT4H-1", "SPK0641HT4H-1 top-port PDM mic, 4.0x3.0x1.0, datasheet Rev D-1 land pattern")
    L = '(layers "F.Cu" "F.Paste" "F.Mask")'
    for num, x, y in (("2", -0.425, -0.675), ("3", 0.425, -0.675), ("1", -0.425, 0.675), ("4", 0.425, 0.675)):
        out.append(f'  (pad "{num}" smd rect (at {x} {y}) (size 0.45 0.95) {L})')
    out.append(f'  (pad "7" smd rect (at 0 -1.7125) (size 1.3 0.325) {L})')
    out.append(f'  (pad "5" smd rect (at 0 1.7125) (size 1.3 0.325) {L})')
    out.append(f'  (pad "6" smd rect (at -1.2125 0) (size 0.325 2.3) {L})')
    out.append(f'  (pad "8" smd rect (at 1.2125 0) (size 0.325 2.3) {L})')
    out.append(g.rect("F.Fab", -1.5, -2.0, 1.5, 2.0))
    out.append(g.rect("F.CrtYd", -1.75, -2.25, 1.75, 2.25))
    out.append('  (fp_circle (center 0 -0.97) (end 0.25 -0.97) (stroke (width 0.05) (type solid)) (fill none) (layer "F.Fab"))')
    out.append(")")
    return "\n".join(out)


def l2016_fp():
    out = g.fp_header("L_2016", "2.0x1.6 mm power inductor, Murata DFE201610E recommended pattern (pads 0.55 x 1.6, gap 0.9, overall 2.0)")
    out.append('  (pad "1" smd rect (at -0.725 0) (size 0.55 1.6) (layers "F.Cu" "F.Paste" "F.Mask"))')
    out.append('  (pad "2" smd rect (at 0.725 0) (size 0.55 1.6) (layers "F.Cu" "F.Paste" "F.Mask"))')
    out.append(g.rect("F.CrtYd", -1.25, -1.0, 1.25, 1.0))      # 0.15 mm margin (was 0.25): lets L2 sit next to U2, 2026-11-14
    out.append(")")
    return "\n".join(out)


g.NEW_FPS["MIC_SPK0641HT4H-1"] = spk0641_fp
g.NEW_FPS["L_2016"] = l2016_fp

# 2026-11-19 audit: the Xinglight XL-0201SURC datasheet (page 7) numbers the cathode 1 and the anode 2. Pin positions
# unchanged (anode left, cathode right), numbers swapped. On the board U4 is turned 180 degrees to match.
g.SYMBOLS["LED"] = dict(left=[("2", "A")], right=[("1", "K")], ref="D", width=5.08, small=True)


def pod_parts():
    parts = bte.pod_parts()
    cable_mic_nets = {"CBL_PDMCLK"}
    # X1, C2, C14: the 32.768 kHz crystal and its capacitors. Removed 2026-11-11: with the 20 mm cell there is no room
    # for it. The radio uses its internal RC oscillator instead (firmware built with -DFILE_SUFFIX=lfrc).
    drop = {"W1", "W2", "W3", "W4", "R120", "L101", "L102", "C102", "C103", "U14", "X1", "C2", "C14"}
    # ESD diodes on the removed cable lines (V_LS, clock, data); the speaker and charge-pad diodes stay
    for p in parts:
        if p["sym"] == "TVS" and p["nets"]["1"] in ("V_LS", "CBL_PDMCLK", "PDMDIN"):
            drop.add(p["ref"])
    parts = [p for p in parts if p["ref"] not in drop]
    refs = bte.by_ref(parts)
    assert not any(n in cable_mic_nets for p in parts for n in p["nets"].values())

    # 2026-11-19 audit: CAAB is the high-VTERM variant (PS v1.5 Table 33) and with VTERMSET to VSYS charges to 4.35 V
    # (Table 12). The cell is a 4.2 V LiPo: use the standard-VTERM part, same package.
    refs["U2"].update(value="nPM1100-CAAA-E-R", mpn="NPM1100-CAAA-E-R", lcsc="C5200749",
                      note="D+ (A2) unconnected and D- to AVSS: fixed 100 mA VBUS limit (Table 23, config 1). VTERMSET to "
                           "VSYS: 4.20 V termination ONLY on the standard-VTERM part (CAAA); CAAB would give 4.35 V.")
    refs["U4"]["nets"] = {"1": "LED_K", "2": "VSYS"}
    refs["U4"]["note"] = "Red status LED. Pin 1 = cathode (Xinglight datasheet p.7)"
    refs["U3"].update(value="AP22916CCA4-7", mpn="AP22916CCA4-7", lcsc="C3246319",
                      note="Switches the codec + mic rail. C version: 1 mV/us turn-on, about 30 mA inrush "
                           "(the B version's 0.3-0.4 A could brown out the radio). Firmware supply-delay ~6000 us.")
    refs["L2"].update(fp="L_2016", mpn="DFE201610E-2R2M=P2", lcsc="C337891",
                      note="Buck inductor. Must meet nPM1100 PS Table 20: 2.2 uH, DCR <= 400 mohm, Isat >= 350 mA. "
                           "Distributor data for this part: DCR 140 mohm max, Isat 1.9-2.4 A. LCSC C337891 (listing read 2026-11-13; do not confuse with DFE201610P, C237554).")
    refs["R111"].update(value="30k 1%", mpn="RC0201FR-0730KL", lcsc="C138153",
                        note="20 mA charge (Nordic table: 30k = 20 mA): 0.5C for the 40 mAh TinyCircuits ASR00072 cell, "
                             "whose page gives 40 mA (1C) as the maximum charge current.")
    for r in ("P1", "P2"):
        refs[r]["fp"] = "SpringPin_2.0"    # 2026-11-14: land for a spring pin with a 2.0 mm base (see README "Spring pin")
        refs[r]["note"] = ("Charge contact: surface-mount spring pin, 2.0 mm base, 1.5 mm barrel, hand-soldered after assembly. "
                           "Candidates: Xinyangze YZ160615045R-01 (LCSC C5157428) or Kinghelm KH-PG204505-DZ (C2842924), "
                           "both 4.5 mm free / 3.5 mm working. Final length waits on the measured cell thickness.")
    for r in ("TP3", "TP5"):
        refs[r]["fp"] = "TestPad_0.6"      # shrunk and moved 0.3 mm toward the cell to clear the spring-pin lands
    refs["TP8"]["note"] = "Pouch cell + lead (cell has its own protection board)"
    refs["TP9"]["note"] = "Pouch cell - lead"
    # module DC/DC pins: left unconnected, as in Raytac's LDO-mode reference
    for pin, net in list(refs["U1"]["nets"].items()):
        if net in ("DCC", "DECR", "DCCD", "DECD", "XL1", "XL2"):
            del refs["U1"]["nets"][pin]
    for r in ("W5", "W6"):
        refs[r]["note"] += " (v3: the only cable conductors)"

    parts.append(dict(ref="U14", sym="SPK0641HT4H-1", value="SPK0641HT4H-1", fp="MIC_SPK0641HT4H-1",
                      nets={"1": "MIC2_DATA", "2": "PDMCLK", "3": "GND", "4": "V_LS",
                            "5": "GND", "6": "GND", "7": "GND", "8": "GND"},
                      mpn="SPK0641HT4H-1", lcsc="C5159510",
                      note="The only mic. Top port, faces the shell's mic hole through a gasket. "
                           "SELECT low = falling-edge data = DMIC0.", dnp=False))
    # 2026-11-13 layout review: Raytac's reference circuit has 4.7 uF at the module's VDD. C101 (4.7 uF) ended up 12 mm
    # away, and nothing larger than an 0201 fits beside the module, so a 1 uF sits right at VDD pad 29 and C101 stays as bulk.
    c = dict(refs["C47"]); c.update(ref="C117", nets={"1": "+1V8", "2": "GND"},
                                    note="Radio module VDD, local: beside pad 29. C101 (4.7 uF) is the bulk capacitor.")
    assert c["value"] == "1uF", c["value"]
    parts.append(c)
    return parts


if __name__ == "__main__":
    parts = pod_parts()
    bte.build_one("kicad_v3_pod", "haven_v3_pod", "haven_v3_pod",
                  "0b6c7a1e-5d2e-4c41-9f0a-2a1e9b7c3d03", "Haven v3 slim pod", parts)
    print(len(parts), "parts")

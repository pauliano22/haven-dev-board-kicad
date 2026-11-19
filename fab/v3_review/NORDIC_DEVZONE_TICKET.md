Title: Design review request: nPM1100 + nRF5340 (Raytac MDBT53V-1M) in a small wearable, schematic and layout

Hello,

Could you review the nPM1100 and nRF5340 parts of our board before we order the first prototypes? This is a personal, non-commercial project: Haven, a behind-the-ear hearing-comfort device (2 prototypes). Board 9.6 x 27 mm, 6 layers, 0.8 mm.

Attached:
- haven_v3_pod_pinmap.pdf: circuit summary, then every pin of each chip with its net and the parts on that net. Please start here; the generated schematic connects everything by net labels.
- haven_v3_pod_schematic.pdf: the KiCad schematic
- haven_v3_pod_layout.pdf: every copper layer and the part outlines, drawn 6.5:1 as seen from the top
- haven_v3_pod_gerbers.zip

nPM1100 (nPM1100-CAAA-E-R, WLCSP):
- Fixed 100 mA VBUS limit (ISET = D- = AVSS, D+ open); VTERMSET = VSYS (4.20 V); ICHG 30 k (20 mA) for a 40 mAh cell; NTC pin to a 10 k resistor; VOUTBSET = 00 (1.8 V); SHPACT to a GPIO; SHPHLD to a test pad.
- Capacitors as in Figure 34: VBUS 2.2 uF, VSYS 10 uF, DEC 10 uF, VBAT 1 uF, VOUTB 10 uF. Inductor: Murata DFE201610E-2R2M (2.2 uH, 140 mohm).

nRF5340 (inside the Raytac MDBT53V-1M): normal-voltage mode, VDD = VDDH = 1.8 V from VOUTB; LDO mode (DCC, DECR, DCCD, DECD and DCCH unconnected); no 32.768 kHz crystal (LFRC on both cores).

Questions:
1. Is the nPM1100 configuration right for a 4.2 V, 40 mAh LiPo with its own protection board?
2. MODE is tied to AVSS. Our load stays under 30 mA, so the buck stays in hysteretic mode (up to 80 mV p-p ripple). The same 1.8 V rail feeds an audio codec (ADAU1860) and a PDM microphone through a load switch. Would you tie MODE high (forced PWM) instead? What does that cost in quiescent current?
3. Output capacitance: VOUTB has about 11 uF effective directly, plus about 23 uF behind the load switch when the codec is on. That is roughly 34 uF after DC-bias derating, above the 6-20 uF in Table 21. Is that a problem in automatic mode, and should we reduce it?
4. Buck layout: L2's SW pad is 0.5 mm from ball A4 (one 0.85 mm top-layer track), and the output capacitor C114 sits 0.15 mm from L2. Would you change anything? (U2 and L2 are near the bottom right in the layout PDF.)
5. Is LFRC without a 32.768 kHz crystal a concern for a BLE peripheral's connection stability or current?
6. Anything else you see.

Thank you!
Paul

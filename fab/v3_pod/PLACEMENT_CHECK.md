# v3 pod: rotation check sheet for JLCPCB's placement preview

**For the version with break-off rails (`fab/v3_pod_panel/`, the one to upload for assembly) add 7.00 mm to every x
position below.** Rotations and pin-1 directions are the same.

Made 2026-11-14 from `kicad_v3_pod/haven_v3_pod.kicad_pcb` (snapshot `v3_pod_FINAL5_2026-11-14`); U4 row updated
2026-11-19 (snapshot `v3_pod_FINAL7_audit_2026-11-19`). Positions unchanged since. Re-make it if the board changes.

**Why:** the placement file gives each part's rotation as KiCad has it. JLCPCB's own parts library can have a different
"zero" for the same part, and their preview then shows the part turned 90 or 180 degrees. Nothing offline can prove the
two agree. The check is visual, in JLCPCB's preview, before paying. Parts with two identical ends (capacitors,
resistors, the inductor) cannot be wrong; only the ten parts below can.

**How to read it:** hold the board with the antenna end (the module) at the top, parts facing you. "Position" is
millimetres from the bottom-left corner, as in the placement file. "Pin 1 is" says which way pin 1 (or ball A1) lies
from the part's centre. In JLCPCB's preview, the pin-1 dot on each part must be on that side.

| Part | What | Position (x, y) | Rotation in file | Pin 1 is | Footprint source |
|---|---|---|---|---|---|
| U2 | power chip, ball A1 | 7.73, 3.33 | 0 | upper left | drawn by us (`WLCSP-25`), checked against Nordic's figure |
| U15 | audio chip, ball A1 | 6.03, 8.23 | 0 | upper left | LCSC / EasyEDA footprint |
| U3 | load switch, ball A1 | 8.79, 5.95 | 0 | upper left | LCSC / EasyEDA footprint; ball order checked against the Diodes datasheet page 1 (A1 VOUT, A2 VIN, B1 GND, B2 ON) |
| U14 | microphone, pin 1 | 2.11, 11.68 | 0 | lower left | drawn by us from the datasheet land pattern |
| U4 | LED, pad 1 = cathode (to LED_K) | 5.82, 11.65 | 180 | left | LCSC / EasyEDA footprint. Settled 2026-11-19: the Xinglight datasheet (page 7) numbers the cathode 1; the symbol now says so and the footprint is turned 180 degrees, so pad 1 (cathode) is on the LEFT, the LED_K side toward Q2. Copper unchanged. In the preview the LED's cathode mark must be on the LEFT. If it is wrong the light stays dark; nothing is damaged |
| D1 | ESD diode, pad 1 (VBUS) | 1.06, 7.10 | 90 | below centre | drawn by us (`D_SOD-523`) |
| D5 | ESD diode, pad 1 (SPK+) | 2.45, 7.36 | 90 | below centre | same |
| D6 | ESD diode, pad 1 (SPK-) | 3.65, 5.12 | 90 | below centre | same |
| Q2 | LED transistor, pad 1 (gate) | 5.03, 10.61 | 0 | upper left | LCSC / EasyEDA footprint |
| CRYSTAL1 | crystal, pad 1 | 7.42, 10.68 | 0 | lower left | LCSC / EasyEDA footprint (turned the wrong way it still works: pads 1/3 are the crystal, 2/4 ground) |

Risk ranking: the four parts drawn by us (U2, U14, D1/D5/D6) are the likely ones to disagree with JLCPCB's library,
because their zero rotation was our choice. The LCSC / EasyEDA footprints normally match JLCPCB as they are.

Also confirm in the preview:
- U1 (the radio module) is NOT placed by JLCPCB: it has no LCSC number on purpose and is hand-soldered.
- P1 / P2 (spring pins), the test pads and the two speaker-wire pads are bare pads, not parts.
- C117 sits 0.29 mm from the module outline and 0.29 mm from the board edge: ask whether they accept it.
- Seven pad-to-pad gaps between neighbouring parts are 0.13-0.15 mm (around L2, C114, R5, R9, C110): their design
  check may flag these.

JLCPCB placement preview, 2026-11-15 (signed-in quote, low-resolution viewer; screenshots in the bridge folder
`files/haven_v3_pod_panel_2026-11-14/`): U2, U3, Q2, CRYSTAL1 pin-1 dot as this sheet says; U15 probably (dot on its
upper-left side); D1/D5/D6 show their "IO" pad (pad 1) below and "GND" above, as this sheet says; U4 too small to read;
U1 and U14 were not placed in that quote.

U4 settled 2026-11-19 (see its row); its rotation in the file is now 180.

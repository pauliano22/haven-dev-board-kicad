# PCBWay website inquiry: what to enter (2026-11-19)

On 2026-11-19 PCBWay (Yoyo, sales03@pcbway.com) asked Paul to register on pcbway.com and submit the request through the
"Submit Inquiry" (PCB assembly) form. Their engineer then reviews the Gerbers and BOM and quotes Option B (full turnkey).
This replaces emailing the files: the form gets the **2026-11-19 files** (correct charger chip nPM1100-CAAA-E-R).

Files, Windows: `C:\Users\pmi\claude-bridge\files\haven_pcbway_portal_2026-11-19\`

## Inquiry 1: pod board (the main one)
- Service: turnkey PCB assembly (PCBWay makes the board and buys all parts).
- Board: one design supplied with break-off rails, 23.6 x 27.1 mm. Quantity: **5 boards made, 2 assembled.**
- 6 layers, 0.8 mm, ENIG, min track / space 0.09 / 0.10 mm (3.5 / 4 mil), min hole 0.15 mm, vias epoxy-filled and
  capped, green mask, white silkscreen.
- Assembly: top side only, SMD only. 26 unique parts, 52 placements. Fine pitch: U15 0.35 mm WLCSP-56, U2 0.4 mm
  WLCSP-25, U3 0.4 mm WLCSP-4; U1 is an LGA radio module (Raytac MDBT53V-1M, no LCSC number, buy from DigiKey/Raytac).
- Uploads: `haven_v3_pod_panel_gerbers.zip`, `haven_v3_pod_panel_bom.csv`, `haven_v3_pod_panel_cpl.csv`, plus the full
  package `haven_v3_box_build_2026-11-19.zip` (9.1 MB) if the form takes another file.
- Remarks (paste):
  > Box-build quote requested by email with Yoyo (sales03@pcbway.com), Option B: you make and assemble both boards (this
  > pod board and a small 2-layer cradle board), source all parts, 3D-print the housings, assemble 2 units and 1
  > cradle, program the firmware and ship to the USA. Everything is in haven_v3_box_build_2026-11-19.zip, with step-by-
  > step instructions in BUILD_INSTRUCTIONS.md (version 2026-11-19; it replaces the files in my first email). Please
  > X-ray U1, U15, U2 and U3. U2 must be nPM1100-CAAA-E-R (not CAAB). LED U4: cathode on the left (LED_K side).
  > Development prototypes for bench testing, not for sale.

## Inquiry 2: cradle board (only if the form takes one board per inquiry)
- 41.0 x 51.5 mm, 2 layers, 1.6 mm, **ENIG required** (four bare round pads are the charge contacts), min track 0.25 mm.
  Quantity: 5 boards made, 1 assembled.
- Parts: 4 (USB-C J1 TYPE-C-31-M-12 with 4 through-hole shell legs, R1/R2 5.1 k 0603, C1 10 uF 0603).
- Uploads: `haven_v3_cradle_gerbers.zip`, `haven_v3_cradle_bom.csv`, `haven_v3_cradle_cpl.csv`.
- Remarks: "Cradle board for the same box-build quote as my pod-board inquiry (Yoyo, sales03@pcbway.com)."

Nothing is ordered by submitting an inquiry. Do not pay or confirm an order without Paul.

# Haven v3: build instructions for a turnkey (box build) order

Version 2026-11-15. Prototype quantity: **2 finished pods with their in-ear pieces, and 1 charging cradle.**
This is a development prototype, not a consumer product. It is not to be worn: every test below is on the bench.

Everything referenced here is in this package (`haven_v3_box_build_<date>.zip`). Dimensions in mm.

## 1. What is being built

| Item | Qty | Made of |
|---|---|---|
| Pod (behind-the-ear unit) | 2, identical | pod circuit board (assembled), 40 mAh LiPo cell, 2 spring pins, printed two-part shell |
| In-ear piece | 2, identical | 4.9 mm speaker, 220 ohm resistor, printed two-part capsule, ear tip |
| Cable, pod to in-ear piece | 2 | 2-conductor thin cable, 60 mm cut length |
| Charging cradle | 1 | cradle circuit board (assembled), printed base / frame / lid, 8 magnets, 4 screws |

## 2. Circuit boards

### 2a. Pod board: `pcb/pod_panel/`
- 6 layers, 0.8 mm thick, ENIG, min via 0.15 mm hole / 0.25-0.3 mm pad, epoxy-filled and capped vias.
- Supplied as a single board with two 5 mm break-off rails (23.6 x 27.1 mm), because the board itself is 9.6 mm wide.
- **Fabricate 5, assemble 2.**
- Assemble ALL parts in the BOM, **including U1 (Raytac MDBT53V-1M radio module, LGA pads underneath)**; it has
  no LCSC number because it is sourced from DigiKey / Raytac. Fine-pitch parts: U15 (0.35 mm BGA), U2 (0.4 mm WLCSP),
  U3 (0.4 mm WLCSP). **X-ray U1, U15, U2 and U3.**
- Orientation: please check the polarised parts against `PLACEMENT_CHECK.md` (pin-1 side of each, as seen in the
  file). Add 7.00 mm to the X positions in that sheet for the railed board. **U4 (LED): the cathode mark must be on
  the LEFT (the LED_K side).** A reversed LED does no damage but stays dark.
- Remove the rails by **cutting the tabs with flush cutters, not snapping** (C117 and R111 sit about 1.3 mm from a
  tab), then file the four nibs flush. The shell is sized for the 9.6 mm board.
- Do not populate anything not in the BOM. P1, P2, TP1-TP9, W5, W6 are bare pads.

### 2b. Cradle board: `pcb/cradle/`
- 2 layers, 1.6 mm, **ENIG required** (the four round pads are the charge contacts). 41.0 x 51.5 mm with two inner
  cut-outs (milled). **Fabricate 5, assemble 1.**
- 4 parts: J1 USB-C (TYPE-C-31-M-12), R1/R2 5.1 kohm 0603, C1 10 uF 0603. The four round pads CP1-CP4 stay bare:
  no solder, no paste, keep them clean.

## 3. Bought parts (not on the boards)

See `BOM_bought_parts.csv`. Summary: 3 LiPo cells (TinyCircuits ASR00072, one spare), 2 speakers (Ole Wolff
OWR-0504T-16), 4 spring pins (Xinyangze YZ160615045R-01, LCSC C5157428, or the same-drawing Kinghelm
KH-PG204505-DZ, C2842924; 4.5 mm free height), 2 resistors 220 ohm 0402, about 150 mm of 2-conductor cable (outer
diameter 1.1 mm max), 2 ear tips for a 5.4 mm nozzle / 4.5 mm bore, 8 disc magnets 5 x 2 mm N52, 4 screws M2 x 8
self-tapping with a head no wider than 4 mm.

## 4. Printed parts: `print/`

| File | Qty | Note |
|---|---|---|
| `pod_v3_shell_tray_R.stl` | 2 | head side of the pod; has the flat contact land and 2 holes for the spring pins |
| `pod_v3_shell_lid_R.stl` | 2 | outer side of the pod |
| `inear_v3_body.stl` (+ `.step`) | 2 | speaker cup and nozzle |
| `inear_v3_cap.stl` (+ `.step`) | 2 | back cap with the cable stub |
| `cradle_v3_base.stl`, `cradle_v3_frame.stl`, `cradle_v3_lid.stl` | 1 each | |

Material: a tough or standard resin (SLA/DLP), 0.05 mm layers if possible; walls are 0.8 mm. **Hold the pod and
in-ear prints until step 5.1**: the pod shell is drawn around the cell's nominal size, and the cell supplier gives
wide tolerances. We send updated files within a day if the cell is bigger.

## 5. Assembly, in this order

### 5.1 Measure the cells (before printing the pod shells)
Measure one cell with calipers: thickness, width, length (including its protection board and the folded tabs).
Nominal design size is **3.5 x 8.0 x 20.0**. If any figure is larger than 3.8 x 8.0 x 20.0, send us the three
numbers before printing; we return adjusted shell (and matching cradle) files.

### 5.2 Spring pins (pod board, bottom face)
Solder one spring pin on P1 and one on P2 (2.0 mm round lands on the bottom face, near the module end). Pins
**perpendicular to the board**, plunger pointing away from the board. P1 is the + charge input (VBUS), P2 is ground.

### 5.3 Cell
- Cut the cell's connector off, leaving the wires as short as fits. **Never let the two wires touch.**
- Red (+) to **TP8 (VBAT)**, black (-) to **TP9 (GND)**. Both are on the bottom face, either side of the spring pins.
- The cell lies flat against the bottom face, from the board's far end (away from the spring pins) toward the pins,
  wires at the pin end. Kapton tape between cell and board.

### 5.4 Program the firmware
- SWD test pads on the bottom face: **TP1 SWDIO, TP2 SWCLK, TP3 nRESET, TP4 +1V8 (target voltage reference),
  TP5 GND.** 0.6-0.8 mm pads; a pogo fixture or fine wires.
- The cell powers the board. Then, with a J-Link and Nordic's nrfjprog (or `nrfutil device` equivalents):
  ```
  nrfjprog --recover
  nrfjprog --program firmware/haven_net_core.hex --coprocessor CP_NETWORK --sectorerase --verify
  nrfjprog --program firmware/haven_app_core.hex --sectorerase --verify
  nrfjprog --reset
  ```
- **Check:** a phone running the free "nRF Connect" app finds a Bluetooth device named **Haven**.

### 5.5 Speaker cable and in-ear piece
- Cable, 60 mm. At the pod: conductor A to **W5 (SPK+)**, conductor B to **W6 (SPK-)**, both on the top face.
  The cable leaves through the hole in the top end of the pod shell.
- At the in-ear end: the cable goes through the cap's stub. Conductor A to the speaker's + tab **through the 220 ohm
  resistor** (resistor soldered directly between wire and tab, insulated with kapton); conductor B straight to the
  speaker's - tab. **The resistor is required**: it limits the maximum loudness in hardware.
- Speaker into the body, sound face toward the nozzle. Glue the cap on with a thin bead at the rim (keep glue out of
  the sound path). Fit the ear tip on the nozzle.

### 5.6 Close the pod
Cell in the tray, board on top (module side up, spring pins through the two holes in the tray), lid over the tray's
lip. A small amount of glue on the lip. **Check:** each spring-pin tip stands about 0.5 mm proud of the flat land
on the tray, and moves freely.

### 5.7 Cradle
- Assembled cradle board into the base, frame on top, 4 screws through frame and board into the base.
- 4 magnets glued into the frame's top pockets, 4 into the lid's pockets. **Test the polarity before gluing:** each
  lid magnet must attract the frame magnet under it.

## 6. Final tests (bench only; nothing in or near an ear)

1. Both pods in the cradle, lid closed, cradle on any USB-C phone charger: after 1 hour, each cell reads higher than
   before (TP8 to TP9, or the app's battery figure).
2. Each pod is found as "Haven" in nRF Connect and connects.
3. With the speaker held in free air at arm's length, the Haven app's test tone at its lowest level is audible.

Please report: X-ray result for U1 / U15 / U2 / U3, the cell measurements from 5.1, and the results of section 6.

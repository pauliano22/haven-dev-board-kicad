# Haven v3 slim pod: schematic (2026-11-11)

**Decision (Paul, 2026-11-11):** build concept A of `DESIGN_BRIEF_SHELL_V3.md` with the microphone on the pod.
The in-ear piece becomes a small speaker on two wires, with no circuit board.

**Generated** by `tools/gen_v3_pod_schematic.py` from the v2 pod part list. Edit the script, not the `.kicad_sch`.

## Status
- 67 parts, 43 nets (v2 pod: 79 parts). `kicad-cli sch erc --severity-all`: **0 violations**.
- **Decision (Paul, 2026-11-11): 17 mm cell** (about 40 mAh; about 13 h quiet / 6 h loud by datasheet estimate). The first
  attempt with a 22 mm cell fitted only 50 of 67 parts on one face (`placement_attempt_2026-11-11.png`); the shorter cell
  frees the bottom face between y = +3.5 mm and the antenna keep-out for the test pads, charge pads, cell pads and the 32 kHz crystal.
- **Board: all 67 parts placed, routing NOT finished.** `haven_v3_pod.kicad_pcb` after `tools/gen_v3_pod_pcb.py`,
  `tools/route_v3_pod_pcb.py 40` (Freerouting), then `fix_v2_pod_pcb.py` and `route_rest_v2_pod.py` run with
  `HAVEN_PCB` / `HAVEN_WORK` pointing at v3.
  - Attempt 1 (audio chip at the right edge): 12 unconnected, 7 copper-to-edge, 11 dangling vias; capacitors up to 10 mm from
    their pins. Saved as `~/.cache/haven_builds/v3_pod_pcb/after_route_rest.kicad_pcb`.
  - Attempt 2 (audio chip moved to (1.2, -5.3), capacitors anchored on chip pins, worst about 6 mm): **16 unconnected,
    5 copper-to-edge, 15 dangling vias. This is the file in the repo.** Six of the failures are audio-chip balls whose
    fan-out via is boxed in at once (BCLK, PDMDIN, SDA1, SHPHLD, XO_R, XTALO): they need `rip_reroute_v2_pod.py` per net
    or hand-placed escapes, as v2 did.
  - Attempt 3 (20 mm cell, no 32 kHz crystal, 64 parts): **16 unconnected, 5 copper-to-edge, 18 dangling vias. This is the
    file in the repo now** (also `~/.cache/haven_builds/v3_pod_pcb/after_route_rest3.kicad_pcb`). Open: BCLK, LED_EN, PDMDIN,
    SCL1, SDA1 (2), SENSORS_ENABLE, SHIP_EN, SHPHLD, SPK+ (2), V_LS (2), XTALI (2), XTALO. Three attempts have all ended at
    12-16 open, mostly audio-chip balls boxed in at the chip. More autorouter passes will not fix this; it needs
    hand-planned escapes for the audio chip (which ball leaves on which layer), then the autorouter for the rest.
  - Attempt 4 (hand-planned, locked escapes for the audio chip in `gen_v3_pod_pcb.py`: `U15_ESCAPES`, five balls without
    vias, V_LS pour on In4 under the chip): **13 unconnected, 0 copper-to-edge, 8 dangling vias, 8 dangling tracks.
    This is the file in the repo now** (`after_route_rest4.kicad_pcb`). The stranded audio-chip signals (PDMDIN, SDA1,
    SCL1, XTALI, LRCLK) are now routed. Still open: BCLK, SHIP_EN, SENSORS_ENABLE (long runs to the module), SHPHLD to its
    test pad, SPK- to its wire pad, XTALO and XO_R (the crystal sits left of the chip while its signals leave from the
    top and its resistor is on the right: move CRYSTAL1 and R28 to the top-right of U15), and five V_LS fragments
    (enlarge the V_LS pour or give the capacitors vias into it).
  - 2026-11-12, what the layer pictures showed: In2 and In3 are nearly empty on the attempt-4 board. The open
    connections are not a lack of room overall. Their end points are boxed in on the top face (parts 0.15 mm apart leave
    no gap a 0.09 mm track can pass with 0.1 mm clearance, and a via in the pad is too close to neighbouring tracks).
    Tools added: `multilayer_route.HEUR_W` (greedier search, env `HAVEN_HEUR_W=2.0`, makes long routes findable) and
    `tools/route_islands_v3_pod.py` (tries every pad, via and track end of the two disconnected pieces, then a
    via-in-pad). On the attempt-4 board they closed 2 more (11 open); the rest needed a placement change.
  - Attempt 5 (2026-11-12): CRYSTAL1 moved above the audio chip's top-right corner (`HAVEN_XTAL`, default 2.6,-2.85),
    a filled via in every V_LS pad before routing, V_LS pour on In4 enlarged to cover all of them (it now replaces
    ground on In4 below the module; In1 stays solid ground). 64 of 64 placed, no shorts or clearance errors before
    routing. Known cost: D1 (charge-pad ESD diode) landed 15 mm from its pad.
    **Result, 2026-11-13: 3 signals open (DOUT at the audio chip's B1 ball, CHG_ERR at the power chip's E3 ball,
    LED_EN at the module's pad 34), plus one ground-fill island on the top face at the bottom-left corner. No
    clearance, short or hole errors. 3 "connection too narrow" pour necks, 10 dangling stubs, 4 dangling vias to tidy.
    This is the file in the repo** (copy: `~/.cache/haven_builds/v3_pod_pcb/attempt5_final_3open.kicad_pcb`).
    How it got there: Freerouting left 37 open; `fix` + `route_rest` got to 13; `route_islands` 11; `rip_reroute` 7;
    hand-planned In2 exits for the power chip's inner balls D3/D4 through E3/E4 closed SHIP_EN and SHPHLD; a hand-placed
    0.15/0.25 via closed the SDA1 pull-up; CHG_STAT, ICHG, VBAT re-routed around them.
  - Why the last three are stuck (seen in zoomed layer pictures, `zoom.py` / `viamap.py` in the cache folder):
    - DOUT: ball B1 has no via (BCLK's In2 exit passes under it). On the top face it is in a pocket closed by the SPK-
      track (x = 98.92), the C33 pad above and the DIN track below; every via spot in the pocket is taken on In2-In4.
    - CHG_ERR: ball E3 has no via (SHPHLD's In2 exit passes under it). The 0.6 mm channel between the chip's bottom row
      and C112 is closed at both ends and has tracks under it on every layer.
    - LED_EN: long run from the module's inner pad; not looked at closely yet.
  - Lessons for the generator before any attempt 6:
    1. A via in every V_LS pad plus the fix script's ground vias makes a wall of through-vias around the audio chip on
       all layers. Put vias only in the 10 uF pads and let small capacitors share them on the top face.
    2. The hand-planned exits end stacked at the same x/y on different layers (G5: In2, In3 and B; B1/C1: top and
       In2), so no via can be placed at any stub end. Fan the ends apart by at least 0.3 mm.
    3. Keep a 0.8 mm part-free strip below the power chip (as already done left of the audio chip) and plan D3/D4 exits
       in the generator (`U2` balls E3/E4 without vias, as patched by hand here).
    4. CHG_ERR is not used by firmware. Leaving it unconnected is an option (the nPM1100 pin is an open-drain output)
       but it removes charger-fault reporting; not done, Paul's call.
  - **2026-11-13, later: ALL CONNECTIONS ROUTED.** `kicad-cli pcb drc --schematic-parity`: 0 unconnected, 0 errors,
    0 schematic parity issues, 2 warnings (dead-end stubs on SCL1 and XTALO that are part of in-use tracks). Mirror
    check passes on all five chips. 1909 track segments, 185 vias (132 are the 0.15/0.25 filled size). Snapshot:
    `~/.cache/haven_builds/v3_pod_pcb/v3_pod_ROUTED_CLEAN_2026-11-13.kicad_pcb`. This is the file in the repo.
    - Attempt 6 (generator with the lessons below) was NOT better: 6 open + 22 copper-to-edge errors after the same
      stages. Snapshot `attempt6_final_6open_22edge.kicad_pcb`. The repo board is attempt 5, finished by targeted fixes.
      **The generator in `tools/gen_v3_pod_pcb.py` now produces the attempt-6 placement, not the repo board. Do not
      regenerate over the routed board.** The routed board's placement is in `placed5_unrouted.kicad_pcb`.
    - How the last ones closed: LED_EN by a small via beside Q2 after moving an unfinished CHG_ERR track; DOUT's real
      blockage was at the module (pad 38 walled in by the SPARE_P1_13 track), fixed by pulling up SPK- and SPARE,
      routing DOUT end to end, then re-routing those two; C40's ground pad got its own via after re-routing an SDA1
      segment; CHG_ERR by pulling up SHIP_EN and CHG_STAT near the power chip, routing it first, then those two.
      Scripts used are in the cache folder (`dout_direct.py`, `chgerr.py`, `join_pours.py`, `prune.py`).
    - V_LS fill minimum width raised to 0.15 mm so nothing depends on a 0.05 mm neck; the audio chip's V_LS balls
      that relied on such necks got tracks.
  - **This is a board that passes the rule check, not a reviewed layout. Known weak spots to fix or accept before any order:**
    1. Every power track is the minimum 0.09 mm (VBAT 24 mm, VSYS 19 mm, +1V8 44 mm, V_LS 31 mm, VBUS 30 mm, SW 6 mm,
       SPK+/SPK- 18 mm each). Resistance is tolerable at these currents on paper (about 0.13-0.5 ohm per rail), but
       the buck's SW node and input loop should be short and wide. Needs a widening pass; the fix script widened none.
    2. Audio-chip supply balls D1/E1 reach V_LS through a 6 mm long 0.09 mm track. Should be short and wide.
    3. Decoupling capacitors are up to 6-8 mm from the pins they serve; the charge-pad ESD diode D1 is 15 mm from its pad.
    4. Buck layout (U2, L2, C110-C114) has not been compared with Nordic's reference layout.
    5. Crystal tracks (XTALI/XTALO/XO_R) route length and what runs beside them not reviewed.
    6. Cell tolerances, spring-pin land pattern on P1/P2 (decision 2026-11-13), U3 handedness by convention only.
  - **2026-11-13, widening and review pass:**
    - `tools/widen_v3_pod.py` widened power and speaker segments wherever 0.1 mm clearance allowed, no new rule
      errors. Share of length widened / average width: +1V8 75 % / 0.19 mm, SW 77 % / 0.14, VSYS 58 % / 0.14,
      VBUS 25 % / 0.16, VBAT 16 % / 0.16, V_LS 51 % / 0.13, SPK+ 69 % / 0.15, SPK- 83 % / 0.17, DVDD 49 % / 0.13.
      The parts that stayed 0.09 mm are under and between the chips.
    - Measured on the board (straight-line distances):
      - Audio chip: every V_LS ball has a 10 uF within 0.9-2.0 mm. DVDD's capacitors are 3.2-3.5 mm away. CM 1.7 mm.
      - Power chip: VBUS 1.5 mm, VSYS 1.8-2.1 mm, VBAT 2.3-2.5 mm, +1V8 1.7 mm, DEC 1.8 mm. Acceptable for a prototype.
      - **Buck switching node: 5.7 mm of track with 2 vias through the bottom layer; the inductor is 4.5 mm from
        the SW ball.** Nordic's reference keeps it adjacent. Expect more radiated noise and ripple; measure.
      - **Radio module supply: Raytac's reference circuit (spec section 8.1.1, read as an image) shows 4.7 uF on VDD.
        Ours (C101) is 12 mm from the VDD pads 26/29; the nearest capacitor of any kind is 10 mm away.** Cause: the
        placer was told not to anchor parts on the module. No free spot for an 0402 within 2 mm was found on the
        routed board. Fix in the next layout pass (move W5/W6 down about 0.6 mm and fit a capacitor between them and
        the module), or accept for the first boards and check the module's supply ripple on the bench.
      - Crystal: XTALI 5.0 mm / 3 vias, XTALO 7.2 mm / 2 vias, XO_R 5.4 mm. Long for a crystal; adds roughly 1 pF
        per node (estimate). Start-up and frequency to be checked on the bench.
      - I2C runs are 18-20 mm; fine at 400 kHz with the 2 kohm pull-ups.
    - Factory files exported: `fab/v3_pod/` (gerbers zip, BOM, placement file; `tools/export_v2_fab.py v3pod`).
      BOM: every part has a JLCPCB/LCSC number except the radio module (blank on purpose, as on v2). Added
      L2 = C337891 (Murata DFE201610E-2R2M=P2) and R111 = C138153 (Yageo RC0201FR-0730KL), from LCSC listings via search.
      **Not yet done: JLCPCB quote and their DFM check, placement-preview rotation check, 13 hand-soldered pads
      (wires, test pads, charge pads) are not in the placement file by design.**
    - Final state: 0 unconnected, 0 errors, 0 parity issues, 2 warnings. Snapshot `v3_pod_FINAL_2026-11-13.kicad_pcb`.
  - **2026-11-13, the two review fixes (Paul: "go ahead and fix those two"):**
    - Module supply: new **C117, 1 uF 0201** (same part as the other 1 uF, LCSC C76929), in the 0.9 mm strip right of
      the module at (104.35, 97.55), 1.1 mm from VDD pad 29, ground via in its pad. It is 0.29 mm from the module's
      body edge and 0.29 mm from the board edge: tight for assembly, check JLCPCB's DFM. C101 (4.7 uF) stays where it
      is as bulk. This is NOT Raytac's 4.7 uF at the pin: no stocked 0201 4.7 uF was confirmed (Samsung
      CL03A475MQ3CRNC exists but no LCSC number found) and nothing larger fits. 65 parts now.
    - Buck: L2 turned 180 degrees so its SW pad faces the chip; SW re-routed. **SW: 5.7 mm -> 4.4 mm, still 2 vias
      (the one in ball A4 plus one at the inductor), widths up to 0.3 mm, 72 % of it widened.** Inductor SW pad is
      3.8 mm from ball A4; its output pad is 4.9 mm from the output capacitor C114. A modest gain. Putting the
      inductor and C114 next to the chip as in Nordic's reference means re-placing the whole power corner (about 12
      parts) and re-routing it: not done. Measure +1V8 ripple and audio noise on the first boards.
    - After both: 0 unconnected, 0 errors, 0 parity issues, 2 warnings; mirror check passes; fab files re-exported
      (52 placements). Snapshot `v3_pod_FINAL2_2026-11-13.kicad_pcb`.
  - **2026-11-14: spring-pin lands and power corner re-laid (Paul: "do everything you can without me").**
    Snapshots in `~/.cache/haven_builds/v3_pod_pcb/`: `v3_pod_PINS_2026-11-14` (pins only), `v3_pod_FINAL3_2026-11-14`, `v3_pod_FINAL4_2026-11-14`, **`v3_pod_FINAL5_2026-11-14`**
    (current board). Patch scripts kept in `tools/v3_patches/` (`pc1.py` move + rip, `pc2.py` checked vias, `vt.py`
    "what blocks a via here", `prune.py`, `win.py`, `zoom.py`); they are one-off records, not re-runnable generators.
    - **Spring pin.** Datasheets read (saved in `~/.cache/haven_datasheets/pogo/`): Xinyangze YZ160615045R-01 (LCSC
      C5157428) and Kinghelm KH-PG204505-DZ (LCSC C2842924) are the same shape: **2.0 mm base, 0.5 mm thick; 1.5 mm
      barrel to 3.0 mm; 1.0 mm (0.9 mm Kinghelm) plunger; 4.5 mm free, 3.5 mm working, 3.1-3.4 mm fully pressed; 1 A;
      brass, gold over nickel (3 u" / 1 u": thin)**. Mill-Max 0900 (2.39 mm base) does not fit between the pads.
      Stock, price and the 4.0 mm-long variant were NOT confirmed. Length is chosen after the cell is measured: with
      the shell as drawn (4.0 mm board-to-outside) a 4.5 mm pin stands 0.5 mm proud against the head; a 4.0 mm pin
      is flush. Nickel under thin gold against skin is a materials question (`MATERIALS_AND_ASSEMBLY.md`).
    - Board: P1 / P2 are now 2.0 mm lands (`SpringPin_2.0`); TP3 (RESET) and TP5 (GND) shrunk to 0.6 mm and moved
      0.3 mm toward the cell (`TestPad_0.6`) to clear them; SWCLK, SWDIO, nRESET and one +1V8 link re-routed. The
      pins are hand-soldered after assembly (bottom face, not in the placement file). **Not checked: two 3 mm brass
      posts sit 1 mm below the antenna keep-out; range must be measured on the first boards.**
    - **Power corner.** L2 now lies directly above U2 with its SW pad 0.5 mm from ball A4: **SW is one 0.85 mm,
      0.3 mm wide top-layer track with no via (was 4.4 mm, 2 vias; before that 5.7 mm).** C114 (output) is 0.15 mm
      from L2's output pad (was 4.9 mm). C110 (VBUS) is 0.4 mm from balls B1/B2 on the top layer. Moved: L2, C114,
      C110, C113, C32, R114, R115, R9, R5 (0.1 mm). L2's courtyard margin was cut 0.25 -> 0.15 mm to allow it.
      Costs: C113 (DEC) is now 2.3 mm from ball A3 (was about 1.4); C111 (VBAT, 1 uF) is reached through 3 vias and
      a bottom-layer track; SCL1's pull-up R9 connects through a via under the inductor body; seven pad-to-pad gaps
      between different parts are now 0.13-0.15 mm (none were under 0.15 before, apart from same-net pads). The
      inductor now sits 0.5 mm below the audio chip's last ball row and about 1.3 mm from the crystal's load cap
      C46: **the switching line is far shorter, but the inductor is closer to the codec clock. Net effect on audio
      noise is not known; measure +1V8 ripple and the codec noise floor on the first boards.**
    - D1 (VBUS ESD diode) NOT moved. Traced: VBUS runs pad -> In2 -> balls B1/B2 -> C110, with D1 on a stub after
      the chip. A strike is taken by C110 (2.2 uF: 8 kV from 150 pF moves it about 0.5 V), so moving D1 buys little
      and there is no room at the pad end. Left as is, by judgement, not by test.
    - Ground check after the move (which pour each moved capacitor sits in, nearest ground via): C114's ground pad
      had no via and sat in a 3.8 mm2 top-layer island, nearest via 2.2 mm away. Added a ground via at the pad's
      edge (101.13, 109.05) and one at R115 (100.44, 108.54). **C110's ground pad still has no via of its own**
      (inner-layer tracks under it; nearest ground via 1.1 mm away through the main pour). Snapshot
      **`v3_pod_FINAL4_2026-11-14`** is the current board; fab files re-exported from it. The bridge folder for the JLCPCB quote task was refreshed with these
      FINAL4 files at 01:26, before the browser session had logged any step on it.
    - Series resistor for the speaker (passive loudness limit, see `DESIGN_BRIEF_SHELL_V3.md` "Worst-case loudness"):
      looked for a board position between W6 and W5; none is legal (VBUS on In2 and VBAT on In3 run down x = 103.32
      under the gap, and the SPK+ via sits inside W5). Not added. Recommended at the speaker tab instead.
    - L2 land pattern checked against Murata's DFE201610E sheet (copy in `~/.cache/haven_datasheets/inductor/`,
      "Recommended patterns": pads 0.55 x 1.6 mm, 0.9 mm apart, 2.0 mm overall). Ours was 0.7 x 1.7, 0.8 apart, 2.2
      overall. Changed to Murata's in the generator, the library and the board; gaps from L2 to R5, C114 and U3 are
      now about 0.25 mm. Snapshot **`v3_pod_FINAL5_2026-11-14`** is the current board; fab files and the quote
      folder were refreshed from it. (A 0.06 mm nudge of C114 was tried and reverted: it broke a clearance.)
    - LED polarity: a second attempt to read the LCSC library entry was blocked by the site. Still unsettled.
    - **JLCPCB quote, 2026-11-14 02:29, not signed in, nothing ordered** (full text:
      `claude-bridge/done/2026-11-14-0122-haven-v3-jlcpcb-quote.md`). Bare board, 5 pieces, 6 layers, 0.8 mm, ENIG,
      epoxy filled and capped vias, 0.15 / 0.25 mm vias: **$101.82, 7-8 days, shipping $26.08 (UPS, default option)**.
      Of that, $33.15 is for the 0.15 mm vias and $16.56 for the electrical test they force with them. The site
      forced Tg155 material and "specify stackup". No design warnings on the quote page (their real check comes
      after an order). **Assembly was refused: "PCB assembly requires a minimum size of 10x10mm"; the board is
      9.6 mm wide.** Parts matching and the placement preview were therefore not reached.
    - **Fix: an assembly version with break-off rails**, `tools/make_v3_pod_panel.py` ->
      `kicad_v3_pod/panel/haven_v3_pod_panel.kicad_pcb` (23.6 x 27.1 mm): the unchanged board, a 5 mm rail on each
      long side across a 2 mm slot, two 2.5 mm tabs per side with 0.5 mm break holes just outside the board edge,
      three fiducials on the rails. DRC: 0 errors. Fab files: `python3 tools/export_v2_fab.py v3podpanel` ->
      `fab/v3_pod_panel/` (positions are the plain board's plus 7.00 mm in x). The pod and shell stay 9.6 mm.
      Re-run the panel script after ANY change to the board. After assembly cut the tabs with flush cutters and
      file the nibs. A second quote-only task for this version was queued at 12:5x.
    - Result: 65 parts, 0 unconnected, 0 errors, 0 parity issues, 2 warnings (same two in-use dead-end tracks);
      mirror check passes; fab files re-exported (26 BOM lines, 52 placements).
    - Lesson: a via placed "in the pad" without checking the four inner layers shorted 6 nets at once; `vt.py`
      lists the blockers for a candidate via and found legal spots in minutes.
  - Next: measure a real cell, pick the pin length, then a JLCPCB quote and DFM check.
    Nothing is to be ordered without Paul's say-so.
  - Tools changed 2026-11-12/13: `multilayer_route.HEUR_W`, via-check cache; `route_rest_v2_pod.py` env
    `HAVEN_HEUR_W`, `HAVEN_SMALL_VIA`; new `route_islands_v3_pod.py`; `rip_reroute_v2_pod.py` crash fixed
    (`remove_dangling_safe` was defined after the main guard) and env `HAVEN_ROUTER`. v2 defaults unchanged.
- **Old note, superseded:** The cell choice is moving to a 3.5 x 8 x 20 mm cell (see battery table),
  which changes the bottom-face strip, so placement has to change once more first. Fix the cell size, re-place, then route.
- Handedness check (`tools/check_footprint_handedness.py v3pod`): audio chip, power chip, module, mic and load switch correct.
- Shell with this cell and a 0.8 mm board: 32.4 x 13.0 x 9.2 mm (`hardware/mechanical_cad/v3_slim/pod_v3.py A 0.8 0.25`).

## Cell chosen for layout (2026-11-11): TinyCircuits ASR00072, from the product page Paul pasted
- 3.7 V, 40 mAh, **3.5 +-0.5 x 8.0 +-2.0 x 20.0 +-3.0 mm**, 1.1 g, $3.49, protection circuit, JST SH lead 34 mm.
  Max charge 40 mA (1C), **max discharge 40 mA (1C)**. Certificates listed: UL1642, UN38.3, IEC62133 (documents not opened).
- The tolerances are wide (up to 10 mm wide, 23 mm long). The board is laid out for the NOMINAL size: cell bay 20 mm,
  bottom-face strip 3.2 mm. **Measure a real cell with calipers before ordering boards.**
- **2026-11-14 (night): the cell size does NOT gate the board order.** The cell sits under the board between
  y = -13.5 (the board's end) and +6.5; the bottom-face parts, the cell pads and the spring pins are all at y > 6.5. A
  longer cell overhangs past the board's end into the shell nose (moving the pod's end magnet), a thicker or wider one
  only grows the shell. So a different cell changes the printed shell (about $1 to reprint, regenerated by script, and
  the cradle pockets follow automatically), never the board. Cells with a maker's MAXIMUM size found: SparkFun 40 mAh
  (Data Power DTP301120, datasheet in `~/.cache/haven_datasheets/cell/`: T <= 3.0, W <= 11.0, L <= 20.0 bare cell,
  pack with protection board and JST-PH not drawn) and VCELL VP350820 (product page: 3.7 x 8.5 x 22.5 mm max, 40 mAh;
  no datasheet seen). **Decision (Paul, 2026-11-15): keep TinyCircuits ASR00072 for the first pair; buy 3; print the
  shells only after the cells are in hand; the builder checks the cell size during assembly, Paul does not measure.**
- 40 mA discharge limit: Haven's estimated average draw is 3-7 mA, but start-up and radio peaks are not measured. Check
  on the bench (bring-up plan stage 1-2) that peaks stay under 40 mA or that the cell tolerates them.
- **Peak current estimate (2026-11-15, calculated, not measured).** Everything except the charger runs from the
  nPM1100's 1.8 V buck, so the cell sees roughly I(1.8 V) x 1.8 / (3.5 V x 0.9 efficiency) = about 0.57 x the 1.8 V
  current. Worst case at 1.8 V with everything on at once: app CPU at 64 MHz in LDO mode about 6 mA + network core
  and radio transmitting at 0 dBm (LDO mode) about 9 mA + ADAU1860 with signal into a load about 11 mA (datasheet
  Table 7: AVDD+HPVDD 7.87, DVDD 3.06, IOVDD 0.32 mA) + mic and the rest about 1 mA = about 27 mA, so **about 15 mA
  from the cell, against its 40 mA limit (about 2.5 x margin)**. The nRF5340 figures are from memory of Nordic's
  product spec (the Raytac PDF's tables are images); the ADAU1860 one is from its datasheet. Speaker current through
  the 220 ohm series resistor is a few mA at most. The one real spike is the codec load switch's turn-on (about
  30 mA inrush, already slowed with `supply-delay-us` 6000) and the buck's start-up; the bench check in
  `BRINGUP_PLAN.md` (v3 section, row 1) measures both. Firmware already keeps the draw down: radio 0 dBm, app core at
  its 64 MHz default, logging over RTT only (no UART). No firmware change made.
- Consequences applied: R111 = 30 kohm (20 mA charge, 0.5C); 32.768 kHz crystal X1 and C2/C14 removed (no room), firmware
  variant `boards/haven_v2_nrf5340_cpuapp_lfrc.conf` runs the radio's clock from its internal oscillator (builds with
  `-DFILE_SUFFIX=lfrc`, both cores confirmed on RC in `.config`; extra current not measured); charge contacts P1/P2 are
  1.2 mm wire pads; all bottom-face pads sit in two rows between the cell end and the antenna keep-out. 64 parts, 0 ERC.
- Known weak spot: the charge-pad ESD diode D1 is about 9 mm from its pad.

## Battery candidates (2026-11-11, none ordered, none verified beyond the listed source)
| Cell | Size (mm) | Capacity | Protection | Source | Fit |
|---|---|---|---|---|---|
| TinyCircuits ASR00072 pouch | 3.5 x 8 x 20 (tolerances +-0.5 / 2 / 3) | 40 mAh | yes | US seller; lists UL1642, UN38.3, IEC62133 documents (search extract; page not opened) | 3 mm longer than the 17 mm cell bay: check whether it can overhang the board's bottom end inside the shell |
| Generic "401017"-class pouch | 4 x 10 x 17 | about 40 mAh | usually | marketplace sellers, no trustworthy datasheet found | fits as designed |
| VARTA CP9440 A4 coin | 9.4 dia x 4.0 | 29-30 mAh | none | Texim (VARTA distributor) | fits; about 10 h quiet / 4 h loud; needs tags and board-side protection |
| VARTA CP1240 A4X coin | 12.1 dia x 4.0 | 51 mAh | none | Texim datasheet | 2 mm too wide: pod grows to about 15 mm |
| Custom pouch (Grepow and similar) | to order | 40-50 mAh | yes | minimum order quantities; not asked | best fit, not for a first prototype |

## What changed from the v2 pod
| Change | Why |
|---|---|
| Footprints taken from the un-mirrored library | Review finding 1 |
| L2: 2.0 x 1.6 mm power inductor (Murata DFE201610E-2R2M=P2) | Review finding 2. Distributor data: DCR 140 mohm max, saturation 1.9-2.4 A. LCSC number not looked up. Land pattern is generic: check against Murata's |
| U3: AP22916CCA4-7 (LCSC C3246319) | Review finding 3: slow turn-on, about 30 mA inrush. Firmware `supply-delay-us` raised 300 -> 6000 in `haven_v2_nrf5340_cpuapp.dts` (v2 firmware rebuilt, builds) |
| L101, L102, C102, C103 removed; module pins DCC, DECR, DCCD, DECD unconnected | Raytac's LDO-mode reference (review finding 5) |
| Cable pads W1-W4, R120 and three ESD diodes removed | No microphone in the ear; cable is SPK+ / SPK- only |
| U14: SPK0641HT4H-1, top port, 4.0 x 3.0 x 1.0 mm (LCSC C5159510) | The cell covers the board's other face, so a bottom-port mic cannot hear. Pins from datasheet Rev D-1 page 7: 1 DATA, 2 CLOCK, 3 SELECT, 4 VDD, 5-8 GND. SELECT to ground = data on the falling clock edge (Table 7) = DMIC0, which the firmware uses |
| R111: 22 kohm | About 27 mA charge for a 55 mAh cell. Re-check when the cell is chosen |

## Open before layout is final
- The cell: no trustworthy seller found for a 4 x 10 x 22 mm protected pouch cell. Its real size sets the board length.
- Mic footprint was drawn by hand from the datasheet figure (`~/.cache/haven_datasheets/spk0641ht4h.pdf`). It must be added
  to `tools/check_footprint_handedness.py` (pins 2, 3, 1: pin 3 is right of pin 2, pin 1 is below pin 2 in the board view)
  when the board exists. The sound-port position (0.97 mm from centre toward pin 7) assumes the datasheet's top view and
  land pattern are drawn the same way up.
- Firmware low-battery shutdown is still missing (review finding 4). The pouch cell's own protection is a backstop, not a plan.
- The speaker (Ole Wolff OWR-0504T-16, 4.9 mm) is unmeasured in a sealed ear.

## Review fixes (2026-11-18, after an outside AI review run in Vector)
Snapshot before: `~/.cache/haven_builds/v3_pod_pcb/v3_pod_before_review_fixes_2026-11-18.kicad_pcb`; after:
`v3_pod_FINAL6_review_fixes_2026-11-18.kicad_pcb`. Script: `tools/v3_patches/review_fix.py`.
- **Battery polarity on the board:** "BAT+" / "BAT-" on the bottom silk above TP8 (VBAT) and TP9 (GND).
- **Courtyards:** 45 footprints had none and the project ignored "missing courtyard", so "0 errors" never covered
  parts crowding each other. Added pad-and-body + 0.05 mm courtyards (L2 tightened to body + 0.10 mm), turned the
  check on (error). Library footprints in `footprints.pretty` updated to match (old copies in
  `~/.cache/haven_builds/v3_review_fix/footprints.pretty.before`).
- **U2 / U3 pads 0.20 / 0.18 -> 0.25 mm:** Diodes suggests 0.24 mm for the AP22916 (DS44758 p.31); the nPM1100's
  balls are 0.195-0.255 mm (PS v1.5 table 25); 0.25 also meets JLCPCB's minimum. The SENSORS_ENABLE via in U3's B2
  (ON) pad moved 0.05 mm diagonally so it stays >= 0.12 mm from A2 and B1.
- **Tight pads:** C32.2 and R5.1 trimmed 0.02 mm on the side facing C114 (gaps 0.142 / 0.144 -> 0.162 / 0.165 mm).
  Smallest pad gap between parts on the board is now 0.153 mm (R9-U15). These two are the only "footprint differs
  from library" notes in DRC, on purpose.
- **Dead track removed:** the SCL1 stub on In2 (2.3 mm) and the whole dead XTALO branch on F.Cu (about 4.3 mm, it
  ran toward the inductor); XTALO now only joins R28 and U15.B6. The earlier prune had removed the wrong segment.
- Result: DRC 0 errors, 0 unconnected, schematic parity clean; handedness check passes; railed panel DRC 0; fab
  files and the box-build package re-exported.
- Not changed (known, accepted): parts near the edge / tabs, 0.15 mm vias, thin supply tracks, L2 near U15, D1 far
  from P1, LED polarity, U15 mask web 0.10 mm.

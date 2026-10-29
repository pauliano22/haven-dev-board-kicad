# Rev A: OpenEarable's earbud board, trimmed for Haven

Branch `rev-a/native-trim`. Decision record: `haven-workspace/PROJECT_STATUS.md`, 2026-10-28.

Rev A is OpenEarable main 2.0 at its real size with the parts Haven doesn't use deleted.
It keeps the ADAU1860 codec and OpenEarable's own routing. Nothing was autorouted.

## Read this first: the KiCad port had four conversion bugs

Every board in this repo comes from `extracted/gen_pcb.py`, a script that converted
OpenEarable's EasyEDA Pro file to KiCad. Checking each pad against the copper routed to it
showed four defects. Earlier DRC passes reported their symptoms but never isolated the causes.

| Defect | Effect | Fix |
|---|---|---|
| Bottom-side parts never mirrored | Every asymmetric bottom part had pins in the wrong places: the charger U2, mic U13, USB-C U12, codec crystal and SWD J1. On B.Cu, 156 pads matched their copper and 95 didn't (F.Cu was 329/0). | `tools/fix_port_pads.py` |
| Pad shapes never rotated | Rectangular and oval pads on parts rotated 90/270° pointed the wrong way. Commit `73d9548` had hand-fixed two parts of this class. | `tools/fix_port_pads.py` |
| Multi-segment traces dropped | 61 traces stored as copper POLY records, 166 segments, were never converted. | `tools/add_port_polyline_tracks.py` |
| Standalone pads dropped | The battery pads (V_BAT, GND), speaker pads (DAC_P, DAC_N) and four I2S test pads were missing, so the battery and speaker had nothing to solder to. | `tools/add_port_free_pads.py` |

Design rules were also KiCad's 0.2 mm defaults. They're now OpenEarable's own: 0.09 mm
clearance, 0.0889 mm track, 0.1 mm pours.

**The other boards inherit all four bugs.** The 5× bench board on `master` and the TAC5301
redesign (`redesign/tac5301-codec-swap`, PR #11) were built from the same port output. As
drawn, their bottom-side charger, USB-C and mic footprints don't match the real parts, and
they have no battery or speaker pads. Don't fabricate either one without redoing them from
the corrected 1× board.

Corrected 1× board before any deletions, zones filled: DRC went from 933 violations to 99,
unconnected items from 187 to 0, shorts from 83 to 0. Every pad matches its copper
(F 402/0, B 327/0).

## What Rev A changes

Removed, 20 parts:
- **microSD:** CARD1, U10 level shifter, U9 load switch, Q3/R1 card detect, R15/R20
  pull-ups, and the V_SD decoupling C6/C8/C26/C28.
- **Flash:** U14. Firmware never uses it, and the nRF5340 has 1 MB internal.
- **IMU:** U1, plus its SCL2/SDA2 pull-ups R10/R11.
- **Fuel gauge:** U6, with R17, C23 and R19. Battery voltage can be read by the nRF5340's ADC.
- **Flex-board connector:** CN1, a Hirose part with a 112-week lead time. The sensor flex
  board isn't used.

Changed:
- **R21 becomes a 0R jumper.** It was the fuel gauge's 10 mΩ sense resistor in series with
  the battery, so it can't simply be removed.
- **J1 (Samtec SWD/JTAG) becomes do-not-populate.** Its pads stay wired to SWDIO, SWCLK,
  RESETN, +1.8V and GND, so they work as programming test pads with pogo pins or soldered
  wires. A Tag-Connect footprint would have meant new routing on an earbud-scale board.

Kept: the MDBT53 module, ADAU1860 with its 24.576 MHz crystal, SPH0641 mic, speaker pads,
BQ25120 charger and inductor, USB-C with ESD protection, button, RGB LED with KTD2026,
32.768 kHz crystal, and U3.

**Firmware note:** U3 switches V_LS, which powers the ADAU1860 and the mic. The firmware
must drive SENSORS_ENABLE high before the codec or mic will work.

Copper: 23 nets with fewer than two pads left lost all their tracks and vias. Affected
nets that stay alive lost only the stubs KiCad's connectivity engine reported dangling.
In total, 347 segments and 54 vias were removed (`tools/rev_a_trim.py`,
`tools/rev_a_schematic.py`).

## Size

**14.73 × 32.33 mm, unchanged.** The remaining copper at the old CN1 end (C48, the codec's
I2C SDA1/SCL1, and the mic's PDM lines) reaches 76.47 mm against a 77.41 mm edge. Trimming
gains less than 0.6 mm and would break the fit with OpenEarable's enclosure. The removed
parts were scattered across the board, not grouped at one end, so a smaller board needs
parts re-placed (Rev B), not just deleted.

## Checks (zones filled, `kicad-cli` 9.0.9)

DRC: **0 unconnected, 0 shorts, 0 dangling tracks.** 82 entries remain:
- **61 lib_footprint_mismatch + 8 lib_footprint_issues.** Expected: the pads were edited in
  place, and the 8 new free-pad footprints have no library entry.
- **8 via_dangling.** Five of these are vias where two tracks on the same layer meet
  (removing the PDMCLK one breaks the mic clock), so they stay. The other three were already
  present on the converted board: a no-net via next to MDBT53 pad 28, a `#ERROR`-net via,
  and one V_LS via.
- **3 clearance.** TMS and TDO are 0.0886 mm apart against a 0.09 mm rule. That's
  OpenEarable's original routing, and these are the codec's unused JTAG lines.
- **1 solder_mask_bridge + 1 hole_clearance.** A no-net via against MDBT53 pad 28, which is
  unconnected. It was already present on the converted board.

ERC: 163, all `pin_not_connected`/`label_dangling`/off-grid. The generator placed net
labels near pins rather than on them. Board connectivity comes from OpenEarable's per-pad
data, so fabrication isn't affected. Until the labels are snapped to pins, though, the
schematic is documentation, not a source of connectivity. Separately, the schematic
wouldn't load at all before this branch: its library symbol names were wrong. That's now
fixed by `tools/repair_schematic.py`, and BOM export works.

## Fabrication

`fab/rev_a/` holds `haven_rev_a_gerbers.zip`, `haven_rev_a_bom.csv` and
`haven_rev_a_cpl.csv`, all in JLCPCB format and generated by `tools/export_rev_a_fab.py`.

Board requirements, checked against JLCPCB's published 6-layer capabilities:

| Requirement | This board | JLCPCB 6-layer |
|---|---|---|
| Trace / space | 0.09 / 0.09 mm | 0.09 / 0.09 mm (inner layers not clearly stated) |
| Vias | 206 through vias, 0.15 mm drill / 0.25–0.30 mm pad, no microvias | 0.15 / 0.25 mm minimum |
| Via-in-pad | 130, including 19 under the ADAU1860 BGA and 22 under the MDBT53 | Epoxy-filled and capped (POFV) included free on 6+ layers |
| BGA | ADAU1860, 0.35 mm pitch, 0.25 mm pads | 0.25 mm minimum BGA pad |

So it should fit JLCPCB's standard 6-layer process with free POFV, not an HDI/advanced
tier. One flag for the quote: JLCPCB's BGA guide recommends 0.35 mm pads when vias are in
the pads, and ours are 0.25 mm. Expect a DFM question there.

Sourcing: 68 placed parts on 39 BOM lines. Every line except one has an LCSC number,
mostly taken from OpenEarable's own BOM, which was designed for JLCPCB assembly.
- **MDBT53 (Raytac):** not in LCSC's catalog. Either ship it to JLCPCB (consignment) or
  hand-place it.
- **ADAU1860 (LCSC C17592940):** stock wasn't checked here. DigiKey lists about a 10-week
  lead time.

Placement file: the port puts every footprint at 0° with rotation baked into its pads, so
`kicad-cli pos` would report 0° for everything. The CPL takes rotation from the source
placement data instead. Bottom-side rotation conventions vary between tools, so **check
every bottom part in JLCPCB's placement preview** before paying.

## Still needs a person

1. Upload the three files to JLCPCB for a real quote: 6 layers, POFV, assembly. Then check
   the placement preview, especially the bottom side and the 0.25 mm BGA via-in-pad DFM note.
2. Decide how the MDBT53 gets on the board (consignment or hand-placed), and confirm
   ADAU1860 stock.
3. Optionally, snap the schematic labels to pins so the schematic matches the board.

# Placement fix: crystals and decoupling back next to their chips

Fixes the finding in `HAVEN_HARDWARE_REVIEW.md` §0.7 / issue #4: the 5×
rescale left both crystals and every decoupling cap 8–50 mm from the part
they serve. Nine placement-only stages, each DRC-gated (zero new violation
identities by type+description, unconnected count not worse) before commit.

Tooling: KiCad **9.0.8** (`kicad-cli pcb drc --format json --severity-all
--all-track-errors`), pcbnew Python from the same install, the project's
`tools/route_lib.py` / `multilayer_route.py` / `placement_lib.py`, plus two
new tools written for this work: `tools/move_two_terminal.py` (generic
two-terminal relocation with DRC-clean routing) and `tools/stage.sh` (one
gated stage per run; restores the board unless the diff is clean).
`tools/measure_placement.py` produces the distance table.

## Result

`.kicad_pcb` header unchanged from master (`version 20241229`,
`generator_version "9.0"`).

### DRC, before and after (kicad-cli 9.0.8)

| | violations | by type | unconnected |
|---|---|---|---|
| master `1e7c6d2` (baseline.json) | 219 | clearance 99, lib_footprint_mismatch 78, solder_mask_bridge 33, track_dangling 9 | 2 |
| this branch (after_i.json) | **219** | **identical multiset** | **2** (the same two cosmetic U15 same-net pairs) |

`tools/drc_diff.py baseline.json after_i.json` → 0 new violation identities,
0 new unconnected. Per-stage reports `after_a.json` … `after_i.json` are in
this directory.

### Distances — footprint centres (`tools/measure_placement.py`)

| pair | master | this PR |
|---|---|---|
| X1 (32.768 kHz) ↔ MDBT531 | 30.4 mm | 8.9 mm (module centre; see pad table) |
| X1 ↔ C2 / C14 (9 pF) | 10.9 / 10.9 mm | 1.8 / 1.8 mm |
| CRYSTAL1 (24.576 MHz) ↔ U15 | 13.8 mm | 5.2 mm |
| CRYSTAL1 ↔ C45 / C46 (33 pF) | 8.1 / 9.7 mm | 1.7 / 2.1 mm |
| R28 (220 Ω, XTALO) ↔ U15 | 21.8 mm | 3.9 mm |
| U15 ↔ C33 (V_LS 10 µF) | 10.0 mm | 2.5 mm |
| U15 ↔ C31 (100 nF, `$1N151`) | 13.1 mm | 1.9 mm |
| MDBT531 ↔ C1 (+1.8V 1 µF) | 25.9 mm | 7.6 mm (module centre; see pad table) |
| U2 ↔ L2 (buck inductor) | 12.9 mm | 2.9 mm |
| U2 ↔ C16 / C18 / C22 | 13.3 / 12.7 / 10.7 mm | 2.4 / 1.8 / 1.5 mm |
| U6 ↔ C21 | 8.3 mm | 8.3 mm (not moved) |

### Distances — pad to pin (what actually matters electrically)

| connection | master | this PR |
|---|---|---|
| X1.1 (XL1) ↔ MDBT531 pin 34 | 23.8 mm | **2.4 mm** |
| X1.2 (XL2) ↔ MDBT531 pin 36 | 24.0 mm | **2.5 mm** |
| CRYSTAL1.1 (XTALI) ↔ U15 ball B7 | 13.6 mm | **6.0 mm** |
| R28.2 (XTALO) ↔ U15 ball B6 | 21.1 mm | **4.5 mm** |
| C33.2 (V_LS) ↔ nearest U15 V_LS ball | 8.8 mm | **1.5 mm** |
| C31.1 (`$1N151`) ↔ U15 ball A3 | 12.0 mm | **1.4 mm** |
| C1.2 (+1.8V) ↔ MDBT531 pin 38 | 23.5 mm | **1.0 mm** |
| C22.1 (VUSB) ↔ U2 ball A2 | 10.2 mm | **0.9 mm** |
| C16.2 (V_PMID) ↔ U2 ball A3 | 13.6 mm | **1.5 mm** |
| C18.1 (+1.8V) ↔ U2 ball B5 | 12.8 mm | **1.1 mm** |
| L2.1 (SW) ↔ U2 ball A4 | 11.7 mm | **2.2 mm** |

### Honest notes on what was and wasn't achieved

- **Codec crystal: 6.0 mm pad-to-ball, not ~3 mm.** The XTALI/XTALO escapes
  from the 0.35 mm BGA are the constraint: the two escape vias kept from the
  original routing sit in a B.Cu pocket walled off by the TDO / SDA1 / DOUT
  diagonals, so the crystal had to go just east of TDO, with each net hopping
  over TDO on F.Cu through one new via. Total XTALI path ≈ 6 mm, load caps
  1.7/2.1 mm from the crystal, GND returns on their own vias — a large
  improvement over 13.6 mm + 8–10 mm caps, and as close as the fan-out allows
  without re-doing the BGA escape itself. If the oscillator still misbehaves
  on hardware, the next lever is the crystal's load-cap values, not placement.
- **32.768 kHz crystal: 2.4 mm to the module pins**, caps 1.8 mm. Done.
- **C31 is a codec cap, not U14's.** The §0.7 table listed U14 ↔ C31; the
  netlist puts C31 on `$1N151` = U15 balls A3/B3. It is now 1.4 mm from A3.
  U14 (QSPI flash, V_LS balls D2/H4) has **no dedicated decoupling cap on
  this BOM** — worth adding on the next revision; not something placement can
  fix.
- **U15 has no +1.8V ball**; its supply is V_LS (C33). C1 is the *module's*
  +1.8V cap and now sits 1.0 mm from pin 38. The §0.7 row "U15 ↔ C1" was
  therefore the wrong pairing; it is left in the centre table for
  traceability (it got longer because C1 moved to where it belongs).
- **U6 ↔ C21 (fuel gauge, 8.3 mm) not moved** — lowest-risk item on the list
  and the U6 corner is dense; left for a later pass.
- All new copper is 0.09 mm track (the board's baseline width) and 0.20/0.10
  vias, the same as the rest of the board.

## Method (per stage)

1. `find_spot` for collision-free positions on the target layer (flipped for
   the test — see tooling fixes below), sorted by distance to the IC pins the
   part's nets land on.
2. Route each pad with `multilayer_astar_mixed` under the **net's own
   `.kicad_dru` per-pair clearance exceptions** (parsed from the rule file;
   never looser than the rules), 0.215 mm otherwise; the pad end is forced onto
   the part's layer; anchors are IC pads (on their own layer), through-vias,
   outer-layer track ends, or a **new via stitched onto the net's inner-layer
   run** outside the BGA escape field. GND pads get a 0.20/0.10 via into the
   planes.
3. Lay each route as found; on any failure reload the stage start board and
   try the next spot.
4. `kicad-cli pcb drc`; `tools/clean_dangling.sh` removes only *new*
   `track_dangling` items (the old feeds to the part's former position) inside
   a window; re-check every new via against the final board.
5. `tools/drc_diff.py prev after` must report zero new identities → commit.

## Tooling defects found and fixed along the way (each caught by the DRC gate)

- `find_spot` tested candidates un-flipped; `move()` flips the part when the
  layer changes, mirroring the pads — a cleared spot could put a pad 0.193 mm
  from a via. Now flips for the test.
- A track *end* on an inner layer was accepted as a routing anchor: the route
  looked complete and connected nothing. Anchors now carry their layer; inner
  runs are only usable via a stitched via.
- IC pads were anchors without a layer: F.Cu copper was laid from a B.Cu ball.
- The GND route constrained the via end instead of the pad end.
- Hole-to-hole was checked assuming every via drills 0.10 mm; the board also
  has 0.15 mm drills (0.1806 mm DRC miss). Checks now read each via's drill.
- A path's own vias were not checked against each other (two hops 0.28 mm
  apart). Rejected now, and the via penalty raised so decoupling routes stay
  single-layer where they can.
- `R28`'s placement search ignored the crystal's own pads (a GND/XTALO
  short). Exclusion lists removed.
- The XTALO escape via looked "blocked" at 0.20 mm because it legitimately
  hugs a TDO track at 0.11 mm under a rule exception; routing must use the
  same exceptions the rules grant.

## Files

- `baseline.json`, `after_a.json` … `after_i.json` — kicad-cli DRC reports per stage.
- `group_a_x1.py`, `group_b_crystal.py` — the two crystal-group scripts (run from `kicad/` with KiCad's python).
- `../../tools/move_two_terminal.py`, `../../tools/stage.sh`, `../../tools/measure_placement.py` — generic tools.

Regenerate fab outputs before ordering, per `FABRICATION_GUIDE.md`:
```
kicad-cli pcb export gerbers --output fab_output/gerbers/ kicad/haven_dev_board.kicad_pcb
kicad-cli pcb export drill   --output fab_output/gerbers/ kicad/haven_dev_board.kicad_pcb
kicad-cli pcb export pos --format csv --units mm --side both --output fab_output/haven_dev_board-pos.csv kicad/haven_dev_board.kicad_pcb
```
(`fab_output/` is not tracked in git.)

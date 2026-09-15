# Crystal escape: the 24.576 MHz codec crystal from 6 mm to 1 mm, and the flash's cap

Follow-up to `../placement-fix/` (PR #5), which moved every crystal and
decoupling cap back next to its chip except one: the codec crystal stopped
at 6.0 mm pad-to-ball because its escape from the 0.35 mm BGA could not be
changed without re-routing. This stage re-does that escape, and fixes the
one decoupling item PR #5 mis-diagnosed (the flash *does* have a cap — C27 —
it was just 9.8 mm away).

Tooling: KiCad **9.0.8** (`kicad-cli pcb drc --format json --severity-all
--all-track-errors`, pcbnew Python from the same install), the project's
`tools/*.py`, plus `group_c_crystal_escape.py` in this directory. Acceptance
rule unchanged: zero new violation identities by type+description and
unconnected not worse (`tools/drc_diff.py`), before every commit.

## Result

`.kicad_pcb` header unchanged (`version 20241229`, `generator_version "9.0"`).

### DRC, before and after (kicad-cli 9.0.8)

| | violations | by type | unconnected |
|---|---|---|---|
| PR #5 tip `77b8ee2` (`baseline.json`) | 219 | clearance 99, lib_footprint_mismatch 78, solder_mask_bridge 33, track_dangling 9 | 2 |
| after crystal escape (`after_c.json`) | **219** | **identical multiset** | **2** |
| after C27 move (`after_d.json`) | **219** | **identical multiset** | **2** |

`drc_diff.py baseline.json after_d.json` → 0 new violation identities, 0 new
unconnected. The two remaining unconnected items are the same cosmetic
same-net U15 pairs as before.

### Distances — pad to pin

| connection | PR #5 | this PR |
|---|---|---|
| CRYSTAL1.1 (XTALI) → U15 ball B7 | 6.01 mm | **0.98 mm** |
| R28.2 (XTALO) → U15 ball B6 | 4.47 mm | **3.26 mm** |
| R28.1 → CRYSTAL1.3 | 0.86 mm | 1.16 mm |
| C46 (33 pF) → CRYSTAL1.1 | 1.10 mm | 1.03 mm |
| C45 (33 pF) → CRYSTAL1.3 | 0.98 mm | 1.08 mm |
| C27 (100 nF, V_LS) → U14 ball D2 | 9.78 mm | **0.21 mm** |
| C27 GND pad → U14 ball E3 | — | 0.49 mm |

### Net copper

| net | PR #5 | this PR |
|---|---|---|
| XTALI (ball → crystal) | 9.02 mm track, 3 vias | **2.84 mm, 2 vias** |
| XTALO (ball → R28) | 5.09 mm, 3 vias | **4.48 mm, 2 vias** |
| `$1N16368` (R28 → crystal) | 1.89 mm | 2.24 mm |

## How the escape works now

The only exits from balls B6/B7 are their existing via-in-pads (kept). From
there:

- **On B.Cu** TDO's escape track runs 0.17 mm east of the XTALI via and walls
  the pocket off; **on In4** SCL1's escape diagonal does the same. That is
  why PR #5 stopped at 6 mm.
- **On In2** (the second GND plane) there is nothing in this corner except
  the through-via field, and XTALI/XTALO already carry the board's per-pair
  `.kicad_dru` exceptions for exactly those vias (XTALI vs TDO 0.015 mm;
  XTALO vs TMS/TDO/XTALI 0.03–0.05 mm, plus matching `hole_clearance`
  rules). So each net now goes: ball → via-in-pad → ~1–3 mm on In2 → new
  0.20/0.10 exit via → B.Cu stub → pad. XTALI's In2 run is a single 0.9 mm
  segment; XTALO's leaves its via south-west (the one gap in the TMS/TDO/
  XTALI ring), runs under row A and exits south of the crystal next to R28.
- **The crystal is on B.Cu at (61.30, 112.35), rotated 225°.** The free
  pocket east of the BGA is a diagonal band 3.5 mm across between SDA1's and
  PDMDIN's slope-1 escapes; the 1.9 × 2.3 mm crystal only fits with its long
  axis along the band, i.e. at a 45° multiple. 45° placement is routine for
  PCBA. C46 sits 1.0 mm from the XTALI pad with its own GND via; C45 and R28
  sit off the far pad; the crystal's two case/GND pads each have a via into
  the planes.
- Every new via and segment was checked before placement against copper
  clearance (the net's own exceptions, never looser), hole clearance
  (0.15 mm default, pair rules where they exist) and hole-to-hole
  (0.20 mm edge, real drill sizes) — then DRC was the judge.

**Trade-off, stated plainly:** XTALI — the high-impedance oscillator input,
the node that matters most — is now 0.98 mm from its ball with 2.8 mm of
copper. XTALO (the driven, low-impedance side) is 3.26 mm to R28 and ~4.5 mm
of copper because R28 has to sit off the crystal's far pad in this
orientation; rotating the crystal to balance the two legs (135°/315°) put
XTALI at ~2.1 mm, which is the worse trade. Two In2 tracks now cut ~1.5 mm
slots in the GND pour under the BGA corner (through the existing via field,
where the pour is already perforated); refill and DRC show no GND
connectivity change.

## The flash's decoupling cap — C27, not a new part

PR #5's README concluded "U14 has no dedicated decoupling cap on this BOM".
That was wrong: **C27** (100 nF, `V_LS`/`GND`, 0201, `TCC0201X5R104M6R3ZT`)
is drawn immediately beside U14 on the schematic and is its cap by design;
the 5× rescale had left it at (97.86, 117.83), 9.8 mm away. Stage D moves it
to B.Cu directly under the flash: V_LS pad 0.21 mm from ball D2, GND pad
0.49 mm from ball E3 (`tools/move_two_terminal.py --ref C27 --ic U14`, old
feeds removed with `clean_dangling.sh`). **No BOM change.** If Paul wants
bulk capacitance for the QSPI flash as well (a 1 µF alongside the 100 nF is
common practice, not a requirement), that would be a BOM addition for him to
decide — not done here.

## Tooling lessons (both caught by the DRC gate)

- **Refill zones on the board in the project directory, never on a copy in
  /tmp.** A board loaded without its `.kicad_pro`/`.kicad_dru` alongside
  fills its pours with different settings: refilling the *untouched* PR #5
  board from /tmp produced 5 phantom `track_dangling`/`via_dangling`
  warnings and 4 phantom unconnected items (U15 GND/V_LS balls, a GND via
  pair 20 mm away); the same board refilled from `kicad/` reproduced the
  baseline exactly. `group_c_crystal_escape.py` copies its best snapshot
  into the project before the final refill. (`CODEX_NOTES.md` already
  warned about /tmp copies and design rules; this is the zone-fill face of
  the same problem.)
- pcbnew 9 hands back an unusable board object after `Remove()` + `Save()`
  + `LoadBoard()` in one process, so the script strips the old copper in
  one process (`--phase strip`) and places/routes in another (`--phase place`).
- `placement_lib.layer_id` only knew F.Cu/B.Cu; it now knows the inner
  layers.

## Files

- `baseline.json` — DRC at PR #5's tip; `after_c.json` (crystal escape);
  `after_d.json` (C27 move).
- `group_c_crystal_escape.py` — the crystal-group script (run from `kicad/`
  with KiCad's python: `--phase strip`, then `--phase place`).
- `../../tools/placement_lib.py` — inner-layer names added.

`fab_output/` is not tracked; regenerate before ordering, per
`FABRICATION_GUIDE.md`:
```
kicad-cli pcb export gerbers --output fab_output/gerbers/ kicad/haven_dev_board.kicad_pcb
kicad-cli pcb export drill   --output fab_output/gerbers/ kicad/haven_dev_board.kicad_pcb
kicad-cli pcb export pos --format csv --units mm --side both --output fab_output/haven_dev_board-pos.csv kicad/haven_dev_board.kicad_pcb
```

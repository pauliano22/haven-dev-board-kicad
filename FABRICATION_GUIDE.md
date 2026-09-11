# Ordering the Haven dev board

Board: `haven_dev_board.kicad_pcb`, commit `fd2960b` on `experiment/codex-astra-routing`.
73.1mm × 161.1mm, 6 copper layers, 1.6mm finished thickness.

## Why this needs an assembly service, not just a bare board

This board carries a BGA-56 (0.35mm ball pitch), a DSBGA-25 (0.4mm pitch), a
WLCSP-22, and a couple dozen 0201 passives. None of that is hand-solderable —
0.35mm pitch is below what a soldering iron and steady hands can reliably do,
and a BGA has no exposed leads at all; it needs solder paste + a stencil +
reflow, ideally with pick-and-place for placement accuracy. **Order fab and
assembly together (PCBA / "turnkey"), not a bare board.**

## Files (already generated in `fab_output/`)

| File | Purpose |
|---|---|
| `haven_dev_board-gerbers.zip` | Bare-board fab: copper layers, mask, silkscreen, drill, board outline |
| `haven_dev_board-pos.csv` | Pick-and-place (component position + rotation), mm/CSV |
| `../HAVEN_BOM.csv` | Bill of materials — every part has a manufacturer + MPN |

Re-run after any future board edit:
```
kicad-cli pcb export gerbers --output fab_output/gerbers/ kicad/haven_dev_board.kicad_pcb
kicad-cli pcb export drill --output fab_output/gerbers/ kicad/haven_dev_board.kicad_pcb
kicad-cli pcb export pos --format csv --units mm --side both --output fab_output/haven_dev_board-pos.csv kicad/haven_dev_board.kicad_pcb
```

## Picking a fab/assembly house

JLCPCB and PCBWay both do turnkey PCBA and both handle 6-layer boards and
BGA/WLCSP placement routinely — this isn't unusual work for them. A few things
specific to this board to flag when you get a quote:

- **6 layers.** More expensive than the 2-layer boards these services are
  cheapest at, but well within normal turnkey capability.
- **0.35mm BGA pitch.** Some services quote "advanced" or "high-density"
  assembly for anything under 0.4-0.5mm pitch — expect a small surcharge and
  possibly a slightly longer lead time (extra AOI/X-ray inspection on BGA
  joints), not a capability problem.
- **Part sourcing.** The BOM's manufacturer/MPN columns came from the original
  EasyEDA source data — worth spot-checking that JLC/PCBWay's own parts
  library actually stocks each one (their upload tools cross-reference
  automatically and will flag anything missing so you can substitute or
  provide it yourself).
- **Order at least 3-5 assembled boards**, not 1. At this pitch, a DOA or a
  bad joint on first assembly run is a real possibility, and you don't want
  your only board to be the one with a problem.

## What to actually upload

Most turnkey flows want, as separate uploads:
1. `haven_dev_board-gerbers.zip` (includes the drill file)
2. `HAVEN_BOM.csv`
3. `haven_dev_board-pos.csv`

Their web tool will parse all three, show you a 3D preview to visually
sanity-check part placement/orientation before you pay, and flag any BOM line
it can't source. **Look at that 3D preview carefully** — it's the cheapest
possible point to catch a rotated or flipped part before money is spent.

## After it arrives

The firmware side (`haven_zephyr_app`) has the ADAU1860 driver currently
stubbed pending real hardware — first bring-up priority once boards land is
almost certainly: power-on, confirm the MDBT531 boots and enumerates over
SWD/USB, then bring up I2C to the ADAU1860 codec (SCL1/SDA1, closed tonight)
before anything audio-shaped is attempted.

# Antenna placement check — MDBT53 (nRF5340 module)

Written 2026-09-22, checked against `kicad/haven_dev_board.kicad_pcb` on the
`fab-package-crystal-fix` board (the one ready to order). Read with KiCad's
own Python API (`pcbnew`), not by eye, so the coordinates below are real.

## What I checked

Raytac's own MDBT53 layout guidance (from its datasheet's RF Layout
Suggestion / Keep-Out Area section, per search snippets — I did not open the
full PDF this pass) says: place the module toward the edge of the board,
since center placement performs worse than edge placement, and give any
second wireless antenna at least 10 mm of separation.

## What the board actually has

- **Module position**: MDBT531 sits at (78.26, 69.98) mm on a board that
  spans roughly x 42.0–114.9 mm, y −19.1–141.8 mm (72.9 × 160.9 mm).
  That's almost exactly the horizontal center of the board (36.3 mm from the
  left edge, 36.6 mm from the right) and far from the top and bottom edges
  (89.1 mm and 71.8 mm away).
- **A keepout zone already exists right next to the module**: bounding box
  (71.11, 65.23)–(75.01, 74.73) mm, sitting flush against the module's left
  edge (74.7–85.1 mm). Whoever placed the module already added a
  no-copper zone for the antenna side. That's the right instinct, and it's
  already done — I didn't add it.
- Two other keepouts exist elsewhere on the board (near 55.5–62.0, 108–115
  and 65.0–68.0, 31.5–34.5 mm); I didn't trace what those protect.

## What this means

Center placement is not what Raytac recommends for maximum range, and this
board doesn't follow that guideline. But two things make it low priority to
fix on this order:

1. **Haven is worn on the body**, talking to a phone that's usually within a
   meter or two (in a pocket, on a desk). That's a small fraction of BLE's
   normal range even with real-world attenuation, so losing some peak range
   to a non-ideal antenna position is unlikely to be the thing that breaks
   the product. This is a reasoned judgment, not a measurement — if the
   enclosure ends up heavily shielding one side, revisit it.
2. **The board is already routed and DRC-checked.** Moving the module now
   means re-routing everything connected to it — the same kind of change
   that caused real DRC shorts earlier in this project when done by script.
   Not worth the risk for a "probably fine" RF concern on the first order.

## Recommendation

- **Don't touch this for the current order.** Ship it as designed.
- **For a v2 board**, place the module at a board edge (Raytac's own
  suggestion) with its existing keepout zone carried along, and get the
  layout reviewed by Raytac directly — they offer a free layout review
  (service@raytac.com) that beats guessing from a datasheet snippet.
- If range problems show up during bring-up (weak connection through the
  enclosure, dropouts at normal wearing distance), this is the first place
  to look.

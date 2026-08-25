# Haven Dev Board — KiCad Port

A from-scratch KiCad recreation of the stock OpenEarable hardware (the base
Haven is built from), generated programmatically from the real EasyEDA Pro
project data rather than hand-traced from screenshots. This is **not** a
copy-paste of the user's live EasyEDA edits — it's a fresh port of the
*stock* OpenEarable design (`OpenEarable-PCB-main-2.0.epro`), per the
explicit scope agreed before this work started.

Open `kicad/haven_dev_board.kicad_pro` in KiCad. **No KiCad install or
`kicad-cli` was available in the sandbox this was built in — none of this
has been opened in real KiCad, run through ERC, or run through DRC.**
Treat the schematic as a strong first draft and the PCB as a best-effort
faithful port; both need a real review pass before anything is fabricated.

## What's actually in here

| Section | Confidence | Why |
|---|---|---|
| BOM (89 parts, real values/part numbers) | High | Parsed directly from the `.epro`'s structured JSON, not guessed |
| Digital/power netlist (MCU, power management, flash, SD, USB, IO) | High | Two independent extraction methods agree exactly (see below) |
| Footprints (real pad shapes/sizes/positions) | High | Parsed directly from the real `.efoo` footprint data |
| PCB placement (component X/Y/rotation) | High | This is the **real board's actual placement**, not a guess |
| PCB routing (traces/vias/copper pours) | High for continuity, **unverified for DRC** | Real copper geometry ported directly; never run through a design-rule checker |
| Audio-analog section (ADAU1860 pins, mic, DAC) | Medium | Connectivity is real (same ground-truth source), but pin *electrical roles* (which precise decoupling network, differential pairing, etc.) haven't been cross-checked against the ADAU1860 datasheet |
| RF/antenna, USB signal integrity, any trace-width/impedance intent | **Needs real EE review** | Geometry ported as-is; nothing here was checked against RF/USB layout rules |
| Symbol/footprint graphics (visual appearance) | Cosmetic only | Pins are placed at electrically-correct coordinates but pin-stub direction and body-rectangle sizing are auto-generated, not hand-drawn — expect a plain, boxy look, not the polished look of a hand-drawn library part |

## Data source and methodology

The source is `OpenEarable-PCB-main-2.0.epro`, an EasyEDA Pro export. Unlike
the live `.eprj2` project file (an encrypted SQLite database), a `.epro` is
a zip of plaintext, line-delimited JSON records — genuinely parseable, not
reverse-engineered from pixels.

Two independent data sources were extracted and cross-checked against each
other:

1. **Schematic layer** (`.esch`, `.esym`): component placement, symbol pin
   layouts, and net-label text. EasyEDA's schematic format has no explicit
   netlist — connectivity has to be reconstructed from which pins sit near
   which net-label text. This reconstruction (`extracted/parse_netlist2.py`)
   hit two real bugs before it produced a trustworthy result, both fixed
   and documented in code comments:
   - A naive `name.split(".")[0]` truncated decimal component values
     (e.g. `"2.2uH.1"` → `"2"` instead of `"2.2uH"`), breaking symbol
     lookup for 15 parts. Fixed with a regex that strips only the trailing
     `.N` variant suffix, plus an HTML-entity unescape (BOM value strings
     use a literal `>`, symbol titles use `&gt;`).
   - The nRF5340 module's dedicated DC-DC/decoupling pins (`DECR`, `DCC`,
     `DECD`, `DCCD`, `DCCH` — per the module's own symbol pin names) were
     being swept into unrelated neighboring nets by the proximity-matching
     heuristic, since these pins sit only ~10 units from adjacent signal
     pins on a tight-pitch module. These pins are excluded from proximity
     matching entirely; per the nRF5340 datasheet they only ever connect
     to a local decoupling capacitor, never a routed signal net.

2. **PCB layer** (`.epcb`) — discovered partway through this work, and a
   materially better source: every real pad on the actual manufactured
   board has a `PAD_NET` record giving its **already-resolved** net name
   directly, plus a `COMPONENT` record giving its **real placed position
   and rotation** on the actual board. This is ground truth, not a
   reconstruction. **This is the netlist actually used in the generated
   schematic and PCB** (`extracted/pcb_netlist.json`,
   `extracted/pcb_placement.json`) — it covers ~85% of all pins vs. ~64%
   for the schematic-proximity heuristic, and every net checked against
   both sources agreed exactly (DIN, DOUT, BCLK, LRCLK, FLASH_RESET,
   SD_ENABLE, SCL1/SDA1, and the full GND net all matched).

   The PCB layer also contains real routed copper — 1003 trace segments,
   260 vias, and 6 ground/power copper pours — on a genuine 6-layer
   stackup (confirmed via `LAYER_PHYS` dielectric/copper-thickness
   records): `TOP / prepreg / GND-plane / core / Inner1 / prepreg /
   Inner2 / core / POWER-plane / prepreg / BOTTOM`. All of this routing
   was ported directly rather than re-routed from scratch.

Coordinate systems were independently reverse-engineered and validated for
each domain (schematic-space units are 10 mil per raw grid unit;
PCB-space units are 1 mil per raw unit — confirmed against overall board
span, ~13.5mm × 26.7mm, plausible for a small in-ear wearable). PCB-space
rotation was independently validated against real trace/via endpoints on
two components with 90°/270° rotations (not just 180°, which can't
distinguish rotation direction) — computed pad positions landed within
0.01 raw units (~0.0003mm) of real trace endpoints, confirming standard
CCW rotation with **no mirroring needed**, even for back-side (layer 2)
parts.

The board outline's arc segments (`POLY` records on the OUTLINE layer) use
a `(start, end, sweep-angle)` encoding with no explicit center point. The
center/midpoint formula was derived from scratch and verified in closed
form against two real corner-fillet arcs before being trusted for the
whole outline.

### Coordinate-generation strategy (why the connectivity should be trusted even without ERC)

Every generated symbol instance (schematic) and footprint instance (PCB)
is placed at **rotation zero**, with the component's real rotation baked
directly into each pin/pad's own local coordinate instead. This sidesteps
any uncertainty about whether KiCad's internal rotation transform sign
convention matches EasyEDA's: since only pure translation is asked of
KiCad, and the label/pad-net coordinates are computed with the exact same
Python expression used to place the pin/pad itself, they are numerically
identical by construction — not just "close." The actual rotation-direction
question was still independently resolved and validated (see above); this
strategy just removes it as a second, compounding source of risk.

## Known limitations / simplifications

- **No ERC or DRC has been run.** No KiCad install was available. Do not
  trust net-class assignments, clearance, or single-pin/unconnected-pin
  warnings until this is opened in real KiCad.
- **POLY-shaped pads** (rare — a few connector pads on J1/CN1 use a custom
  polygon rather than a rectangle/ellipse) are approximated by their
  bounding rectangle, not their exact polygon outline.
- **Via layer spans**: the source data's per-via layer-span field was
  empty for every via found, which is consistent with (but doesn't
  strictly prove) all-through vias. Every via is generated as a full
  F.Cu–B.Cu through via. If any are actually blind/buried, this needs
  correcting.
- **Board stackup thicknesses** are not precisely declared in the
  generated file (KiCad's default 1.6mm/2-layer-style general thickness
  is used) — the *layer names and count* (6 copper layers) are real and
  correct, but exact dielectric thicknesses from the source data were not
  carried through.
- **Silkscreen art, logos, and precise designator label placement** from
  the original board were not ported — only functional copper, pads, and
  the board edge. Reference designators use KiCad's default auto-placed
  text.
- **Pin electrical types** (input/output/power/etc.) are uniformly set to
  "passive" in the generated symbols. This was a deliberate choice: I
  don't have verified per-pin electrical-role data from any datasheet, and
  marking pins with specific types I can't back up would be fabricating
  detail I don't actually have grounds for. This means ERC in KiCad won't
  be meaningful for pin-direction conflicts until someone fills in real
  electrical types from actual datasheets.
- **~15% of pins have no assigned net** (72 of 460 PCB pads; a very
  similar fraction on the schematic side). Spot-checked and these are
  overwhelmingly genuine — reserved MCU pins (the DC-DC pins above),
  unused GPIOs, and connector pins with more physical positions than the
  design actually uses (e.g. CN1 pins 13–24, CARD1 pin 1). They are not
  silently dropped; they're just left unconnected in the generated files
  rather than fabricating a connection.

## A genuine anomaly in the *original* stock design (not introduced here)

One net in the real board data is literally named `#ERROR` by EasyEDA
itself — it ties together MDBT531 pin 3 (`P1.08`, a GPIO), Q2 pin 1 (a
small MOSFET, `CSD13380F3T`), and U8 pin 1 (a 1MΩ 0201 resistor, despite
the "U" designator). The three pins are genuinely electrically connected
in the source data; EasyEDA just never resolved a human-readable name for
this net, most likely because whatever label it depended on was deleted or
renamed at some point in the original design's history. Worth a look if
this circuit (looks like some kind of gated pull-up/sense line, possibly
battery- or fault-related) turns out to matter — it's ported through
faithfully under that literal name (`#ERROR`) in both the schematic and
PCB so it isn't lost.

## File layout

```
kicad/
  haven_dev_board.kicad_pro     project file
  haven_dev_board.kicad_sch     schematic (89 components, net labels for connectivity)
  haven_dev_board.kicad_sym     project symbol library (one symbol per component, no sharing)
  haven_dev_board.kicad_pcb     PCB (real placement, real footprints, real routing, real outline)
  footprints.pretty/            33 generated footprints
  sym-lib-table, fp-lib-table   project-local library tables

extracted/                      all extraction/generation scripts + intermediate JSON,
                                 kept for provenance and so the pipeline can be re-run
                                 (e.g. after a schematic re-export) rather than redone by hand
```

## Suggested next steps for a human pass

1. Open in KiCad, run ERC and DRC, see what falls out.
2. Cross-check the ADAU1860 audio-analog section (U15's ~29 unmatched
   pins, mostly clustered here) against the real datasheet.
3. Review U2 (BQ25120A charger) and U6 (BQ27220 fuel gauge) — both have a
   meaningful number of unmatched pins too.
4. Decide whether the `#ERROR` net circuit needs a real name/investigation.
5. If this is meant to diverge from stock OpenEarable (per the earlier
   Gemini-assisted cleanup pass on the user's live EasyEDA project), diff
   this port against that pass and carry over the same changes here.

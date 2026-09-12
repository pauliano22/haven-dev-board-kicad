# Why this board is expensive, and a real path to fix it

Written after a round of research into whether a cheaper hardware path exists
for Haven, prompted by the ~$500 PCBWay quote for 5 turnkey-assembled boards
of the current design. Short version: **the cost isn't the board size, the
layer count, or the quantity — it's three specific chip packages, and there's
a concrete way to avoid all three without changing what the product does.**

## The actual cost driver

Three parts on the current board use fine-pitch BGA/DSBGA packages:

| Part | Function | Package | Pitch |
|---|---|---|---|
| ADAU1860 (U15) | Audio DSP/codec | BGA-56 region | 0.35mm |
| BQ25120A (U2) | Battery charger | DSBGA-25 | 0.40mm |
| BQ27220 (U6) | Fuel gauge | DSBGA-9 | 0.50mm |

These three parts are why the board needs 6 layers (BGA-56 escape routing
needs internal layers regardless of board size), why it needs laser-drilled
microvias (0.1mm drill, found by direct measurement), and why the fab quote
lands in the "Advanced"/precision tier instead of a standard one. **None of
this is caused by board size or quantity** — a bigger board (which is what
the 5x rescale did) doesn't reduce the pitch requirement under these three
chips, and going to fewer layers would make routing them harder, not easier.
Verified: reducing quantity from 5 to 2 wouldn't meaningfully help either,
since JLC/PCBWay's assembly setup cost is flat across low quantities (their
own price matrix showed identical $29 assembly cost at qty 5 and qty 20).

## Existing alternatives checked, and why they don't solve this

- **OpenEarable 2.0** (the upstream project this board is ported from):
  same ADAU1860 + same nRF5340 module + same charger/fuel-gauge combo.
  Same cost driver. Only sold assembled at ~$2,566 (OpenWearables developer
  bundle) — not a cheaper path.
- **OpenEarable 1.3** (earlier generation, ~$40/unit at batch-of-10,
  built around a u-blox NINA-B306 module instead of raw nRF5340+ADAU1860):
  genuinely cheap and easy to assemble, but **architecturally wrong for
  Haven** — checked its firmware README directly: "Audio is played from
  and recorded to the internal SD card." It's a record-then-playback
  research logging platform (IMU, pressure sensor, an *in-ear ultrasound*
  mic for research use), not a live ambient-audio pass-through device. It
  has no outward-facing mic and no real-time audio path. Cannot do what
  Haven needs (filter ambient sound as you hear it) without a fundamentally
  different audio pipeline than what its hardware/firmware provides.
- **OpenHA** (openaudiology/openha): a project literally named "open
  source hearing aid," Cortex-M4 based. Looks thin/stalled (targeted for a
  2018 release, still listed as "in development" years later) — not
  something to build on without a lot more digging than a name match
  justifies.

## The real fix: we don't need the ADAU1860 at all

Checked Haven's own validated Teensy prototype
(`legacy_prototypes/teensy_hearing_shield/src/main.cpp`) to see how the
*proven-working* version actually did real-time filtering. It uses the
Teensy Audio Library running biquad notch/peaking filters (up to 5 bands,
44.1kHz, plain double-precision math) **on the Teensy's own general-purpose
CPU** — not a dedicated DSP chip. The only external audio hardware is an
`AudioControlSGTL5000` — a basic, cheap, QFN-32 (5x5mm) ADC/DAC codec chip
with no onboard DSP cores at all. The codec's only job is getting analog
audio in and out; all the actual filtering happens in firmware.

**This is the same architecture the current board already needs — it just
picked the wrong chip for the codec role.** The ADAU1860 was carried over
from OpenEarable 2.0's design, not chosen because Haven's own firmware
needs its onboard DSP cores. Haven's nRF5340 (dual-core Cortex-M33, far
more capable than a Teensy's M4) can run the same biquad filtering in
firmware with room to spare, exactly like the Teensy already proves works.

**Concrete swap:** replace the ADAU1860 (BGA, $$$) with a simple codec chip
in an easy QFN package. Real candidates found:
- TI TLV320AIC3104 — 5x5mm QFN-32, low-power stereo codec
- TI TLV320AIC3253 — 4x4mm QFN (or WCSP), has **digital/PDM mic input** —
  worth a close look since the board already uses a PDM mic (SPH0641LU4H-1)
- NXP/Freescale SGTL5000 — the exact chip the Teensy prototype used, QFN

**Charger/fuel-gauge:** BQ25120A/BQ27220 (DSBGA) could similarly be swapped
for QFN alternatives — TI BQ24032A (3.5x4.5mm QFN, single-cell, dynamic
power path) is a real candidate, though it trades away I2C fuel-gauge
telemetry the current combo provides. Worth deciding whether that telemetry
is actually used by the app/firmware today before treating it as a hard
requirement.

## What this would mean

If all three fine-pitch parts are swapped for QFN equivalents: the board
plausibly drops to 2-4 layers, standard (not laser) via drilling, and a
standard (not "Advanced") fab tier — landing in a cost range much closer to
a Teensy/Nordic-DK-style prototype board than the current ~$500 quote. The
MDBT53-1M radio module would likely remain the one moderately fine-pitch
part (LGA/BGA-like, ~0.35mm pitch per its own datasheet) since a small
integrated BLE module is hard to avoid at this size — but one fine-pitch
part instead of three is a meaningfully different (and meaningfully
cheaper) manufacturing story.

## Not yet done / needs a real decision

This is a real architecture change, not a tweak — it means re-deriving the
audio front-end schematic (new codec chip, new charger IC, likely new
decoupling/crystal layout done correctly from scratch rather than ported)
rather than patching the current board. That's a decision for the project
owner, not something to execute unprompted. If this direction is chosen,
the crystal-placement and decoupling-placement issues found separately
(see git history / conversation log, not yet fixed as of this writing)
would need to be designed correctly from the start rather than retrofitted.

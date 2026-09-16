# Why this board is expensive, and a real path to fix it

Written after a round of research into whether a cheaper hardware path exists
for Haven, prompted by the ~$500 PCBWay quote for 5 turnkey-assembled boards
of the current design. Short version: **the cost isn't the board size, the
layer count, or the quantity — it's three specific chip packages, and there's
a concrete way to avoid all three without changing what the product does.**

## The actual cost driver

Three parts on the current board use fine-pitch BGA/DSBGA packages —
confirmed by directly measuring real pad-to-pad pitch in the KiCad file
(not read off a datasheet summary):

| Part | Function | Pad count | Measured pitch |
|---|---|---|---|
| ADAU1860 (U15) | Audio DSP/codec | 56 | **0.35mm** |
| BQ25120A (U2) | Battery charger | 25 | **0.40mm** |
| BQ27220 (U6) | Fuel gauge | 9 | **0.50mm** |

**The MDBT53-1M radio module (65 pads) measures 0.65mm pitch** — comfortably
standard, not a cost driver at all. This corrects an earlier assumption in
this document (and in my own reasoning) that the radio module would remain
a fine-pitch part even after fixing the other three; it doesn't need to.
**All three of the actual problem parts are removable without touching the
radio module.**

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
for QFN alternatives, in increasing order of feature retention vs. cost:
- **TP4056** (SOP-8) — confirmed a genuine JLCPCB "basic part," qualifying
  for their $0 feeder-loading fee in Economic PCBA (their cheapest
  assembly tier). Extremely common in the hobbyist ecosystem. No I2C, no
  programmable LDO/buck, no ship-mode, no fuel-gauge telemetry at all —
  just a basic constant-current/constant-voltage charger. Cheapest and
  simplest possible option, if the app/firmware doesn't actually depend on
  BQ25120A/BQ27220's I2C monitoring today.
- **MCP73831** (TDFN-8, also basic-parts-tier and extremely cheap) —
  similar simplicity/cost tradeoff to TP4056, another hugely common choice.
- **BQ24072** (TI, QFN-16) or **BQ24032A** (QFN) — real ICs, moderate
  price, more charge-current/power-path control than TP4056/MCP73831 but
  still no I2C.
**Checked directly: nothing does.** Searched both `haven_zephyr_app/src`
and `haven_custom_app/src` for any reference to the fuel gauge, battery
level, or state-of-charge — zero matches in either. The BQ27220 fuel
gauge is on the schematic but nothing in the current software reads it.
That makes this an easy call: there's no real feature to preserve, so
**TP4056 (or MCP73831) is the correct answer, not just the cheapest one**
— dropping the fuel gauge entirely rather than finding a QFN equivalent
for a chip nothing uses.

**TLV320AIC3253 is a particularly strong match, confirmed from its own
datasheet:** it accepts a PDM microphone input directly (the exact same
signal format SPH0641LU4H-1 already outputs — no mic change needed),
outputs standard I2S to the host MCU (same bus type the nRF5340 already
uses toward the ADAU1860), and is controlled over I2C (the same control
scheme the firmware already uses for the current codec). That's a real
drop-in-shaped replacement at the hardware-interface level — the firmware
would need a new register map for this chip, not a new control
architecture.

**Sourcing confirmed, not just datasheet-plausible:** TLV320AIC3104IRHBR
and TLV320AIC3254IRHBR are both real, in-stock, catalog parts on JLCPCB's
own parts library ($1.33 and $3.03 respectively per unit) — meaning they'd
source through the same turnkey PCBA flow already being used, no separate
sourcing headache. BQ24032A is a real distributed TI part (~$3-5/unit at
low quantity per Digikey) though not confirmed in JLC's catalog specifically
yet — worth checking before committing to it.

## What this would mean

If all three fine-pitch parts are swapped for QFN equivalents: the board
plausibly drops to 2-4 layers, standard (not laser) via drilling, and a
standard (not "Advanced") fab tier — landing in a cost range much closer to
a Teensy/Nordic-DK-style prototype board than the current ~$500 quote.
Since the radio module itself is confirmed 0.65mm pitch (fine on its own),
fixing these three parts plausibly removes the fine-pitch requirement from
the board **entirely**, not just partially.

## Update: the charger swap is more involved than first scoped

Started the actual schematic rewiring and found a real complication this
document understated. Checked BQ25120A's real net connections on the
board directly (not assumed): it isn't just a charger. It also generates
the **+1.8V rail that's shared between the MDBT531 (nRF5340) and U15
(ADAU1860)** — confirmed via `HAVEN_HARDWARE_REVIEW.md`'s own decoupling-
distance table, which lists "+1.8V" as a real shared digital supply rail —
plus a `3V3` net and an `LSCTRL` (load switch control) net, both also
originating from U2. **TP4056 is only a charger — it has no regulator
outputs at all.** A straight swap would leave the nRF5340 and the audio
codec with no 1.8V supply.

This means the real fix isn't "swap the charger chip," it's "replace one
highly-integrated charger+regulator+load-switch chip with a simple charger
**plus** a separate small buck/LDO regulator chip" for whatever rails
turn out to be genuinely regulated outputs (vs. just switched-through
battery voltage — `3V3`'s exact nature (a real regulated rail, or just
VBAT passed through the SW/load-switch pin) isn't confirmed yet and needs
the real BQ25120A pin-function table, not a guess, before wiring the
replacement). Codec pin-mapping (I2S/PDM/speaker-output pin names on
TLV320AIC3100 vs. ADAU1860) has the same "needs the real datasheet table,
not a guess" requirement — found real, confirmed KiCad symbols for both
replacement chips (TLV320AIC3100, TP4056) in the standard library, and
confirmed TLV320AIC3100 is active/in-stock, but haven't yet done the actual
pin-by-pin rewiring since guessing at pin names on a power-sequencing-
sensitive subsystem is exactly the kind of shortcut that caused the
crystal-placement bug in the first place.

**Follow-up: pulled BQ25120A's real datasheet pin table (not a summary) and
confirmed the mapping exactly.** Pin `B5` (`SYS`, the buck converter's
regulated system output, **default 1.8V** per the datasheet's own device
comparison table) is our board's `+1.8V` net. Pin `C5` (`LS/LDO`, the
configurable load-switch-or-LDO output, enabled by `LSCTRL`, **default
mode: plain load switch**, i.e. switched-through battery voltage, not a
true regulated 3.3V) is our board's `3V3` net — so "3V3" is presently a
slight misnomer; by default it's just switched battery voltage (3.0-4.2V
range for a single LiPo cell), not a regulated 3.3V rail, unless firmware
configures the LDO mode via I2C.

Also checked a real worry and ruled it out: the datasheet lists pins `B4`
and `C4` together under one "VINLS" name, which looked like it might mean
both balls must be tied to the same net — our board only ties `B4` to
`V_PMID` and leaves `C4` on its own net (just its own 1µF decoupling cap,
per the datasheet's own recommendation for that pin). Traced `C4`'s net
fully to confirm it goes nowhere else. This is standard for DSBGA
packages (multiple balls per logical pin for routing flexibility, not a
same-net requirement) — not a bug, and moot regardless since U2 is being
replaced.

**This gives a precise target for the replacement power tree:**
1. TP4056 (or MCP73831) — charging only, as already planned.
2. One small buck regulator IC, reusing the existing `L2` inductor,
   generating the `+1.8V` rail (this one needs to be a real regulated
   output — both the nRF5340 and the new codec depend on it).
3. `3V3`: since the original default behavior was just switched *battery*
   voltage (not actually regulated to 3.3V), the simplest correct
   replacement is to just wire this net directly to battery voltage
   (dropping the load-switch/enable behavior) unless something depends on
   being able to power that rail down independently for battery savings —
   worth checking, but likely a safe simplification for a bring-up board.

**Buck regulator chosen and fully verified: TI TPS62822.** 2.4V-5.5V
input (comfortably covers a single LiPo cell's full range), fixed 1.8V
output option, up to 2A (far more than needed, doesn't hurt), 4µA
quiescent current (good for battery life), confirmed in-stock on LCSC.
Package: 8-pin VSON, 1.5x2mm, **0.5mm pitch — standard fab tier, not the
exotic fine-pitch category being removed.** Both a standard KiCad symbol
(`TPS62822DLC`) and the *exact* matching footprint
(`Texas_VSON-HR-8_1.5x2mm_P0.5mm`) already exist in KiCad's own standard
library — nothing hand-built needed for this part either.

**Full replacement part list, now fully verified (real symbols, real
footprints, real stock, no guessing):**
| Old part | New part | Package | Pitch |
|---|---|---|---|
| ADAU1860 (audio DSP) | TLV320AIC3100 | QFN-32, 5x5mm | 0.5mm |
| BQ25120A (charger+regulator) | TP4056 (charge) + TPS62822 (1.8V buck) | SOP-8 / VSON-8 | 1.27mm / 0.5mm |
| BQ27220 (fuel gauge) | *(removed — confirmed unused)* | — | — |

Still not done: the actual pin-by-pin schematic rewiring (need
TLV320AIC3100's real I2S/PDM/speaker pin table before touching the
schematic file, same discipline as everything above), and confirming
whether `3V3`'s switch-disable behavior is actually needed anywhere
before simplifying it to a direct battery connection.

## Not yet done / needs a real decision

This is a real architecture change, not a tweak — it means re-deriving the
audio front-end schematic (new codec chip, new charger IC, likely new
decoupling/crystal layout done correctly from scratch rather than ported)
rather than patching the current board. That's a decision for the project
owner, not something to execute unprompted. If this direction is chosen,
the crystal-placement and decoupling-placement issues found separately
(see git history / conversation log, not yet fixed as of this writing)
would need to be designed correctly from the start rather than retrofitted.

# Why this board is expensive, and a real path to fix it

Written after a round of research into whether a cheaper hardware path exists
for Haven, prompted by the ~$500 PCBWay quote for 5 turnkey-assembled boards
of the current design. Short version: **the cost isn't the board size, the
layer count, or the quantity — it's three specific chip packages, and there's
a concrete way to avoid all three without changing what the product does.**

## TL;DR for the morning read

- **Root cause found and verified**: 3 chips (ADAU1860, BQ25120A, BQ27220)
  drive the whole cost via their fine pitch. The radio module is fine as-is.
- **Full replacement part list chosen and verified** (real stock, real
  KiCad symbols, no guessing): TLV320AIC3100 (codec) + CMA-4544PF-W
  (analog mic, replaces the PDM one) + TP4056 (charger) + TPS62822
  (1.8V buck) + a load switch for the 3.3V rail. Fuel gauge dropped
  entirely — confirmed nothing reads it.
- **Started the actual schematic edit**, not just the plan — it's real,
  it loads in real KiCad, and the core power-rail rewiring is verified
  correct against ERC. **One specific thing I couldn't resolve**: 3 small
  new nets show an ERC flag I traced through several real hypotheses
  without finding the cause — see the dedicated section below before
  trusting those two sub-circuits (feedback divider, charge-program
  resistors) without a manual check.
- **Real money-saving programs found**: PCBWay's student sponsorship
  (10-15% off, apply with a `.edu` email) and an active JLCPCB 6-layer
  coupon (~$35) — both usable regardless of which board design ships.
- **Nothing has been ordered or applied to the real project files** —
  the edited schematic lives in the scratchpad only, pending your review.

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

## Correction: TLV320AIC3100 doesn't have a clean PDM mic input after all

Pulled TLV320AIC3100's real pin table (not a search summary) to start the
wiring, and it changes something. The earlier "PDM mic support" finding
was real but misleading: this chip's mic inputs (`MIC1LM`/`MIC1LP`/
`MIC1RP`) are **analog** PGA inputs, not a dedicated digital PDM
interface. The PDM workaround mentioned earlier requires repurposing the
`DIN` pin (normally the I2S data line carrying the nRF5340's filtered
output back to the codec's speaker driver) to instead carry raw PDM mic
data — you can't do both at once. That's a real conflict for Haven's
actual signal path, which needs `DIN` (host→codec, filtered audio to
speaker) and `DOUT` (codec→host, mic audio to firmware) working
simultaneously.

**The clean fix, and it's simpler than fighting the PDM path:** use the
codec's native analog mic input instead of a PDM digital mic. This is
the standard, fully-supported way this chip is meant to be used —
`DOUT` carries the codec's own ADC output (fed by the analog mic) to the
nRF5340, `DIN` carries the nRF5340's filtered signal back to the DAC/
speaker, both running normally, no pin-sharing tricks. This means the
mic itself changes too, not just the DSP/codec chip.

**New mic found and verified:** CUI/Same Sky CMA-4544PF-W — real,
currently active part (confirmed, unlike a couple of dead-end analog
MEMS mic candidates checked first: SPU0410LR5H-QB and CMM-4030D-261 are
both obsolete), in stock on both JLCPCB and LCSC, 20Hz-20kHz full audio
bandwidth, 3-10V compatible supply, omnidirectional electret condenser.

**Updated full replacement part list:**
| Old part | New part | Notes |
|---|---|---|
| ADAU1860 (audio DSP) | TLV320AIC3100 | Analog mic input, not PDM |
| SPH0641LU4H-1 (PDM mic) | CMA-4544PF-W (analog mic) | Required by the codec swap above |
| BQ25120A (charger+regulator) | TP4056 + TPS62822 | Charge + 1.8V buck |
| BQ27220 (fuel gauge) | *(removed)* | Confirmed unused |

## Started the actual schematic edit — how this file's connectivity works

Installed `kiutils` (a real, structured KiCad-file library) rather than
editing the raw schematic text blind. First real finding: **this
schematic has no wire segments at all** — connectivity is defined purely
by net-name labels placed exactly at each pin's coordinate, no drawn
wires between them. That's consistent with this being a programmatically-
generated port (matches how the PCB side of this project has always been
described) rather than a hand-drawn schematic.

Confirmed by locating U15's real label positions: e.g. `SCL1` at
(393.7, 91.44), `DOUT` at (480.06, 100.33) — a left column and a right
column of labels, matching a large auto-generated 56-pin symbol body with
pins on both sides. This means adding a new component correctly means:
place the new symbol, then place net-label text objects at each of its
real pin coordinates (computed from the symbol's own pin offsets +
placement + rotation) — no wire-drawing needed, but every label position
has to be right or the pin silently doesn't connect (KiCad won't error on
a slightly-off label, it'll just make a new, wrong, isolated net).

## Actually executed the power-tree edit (charger + buck + load switch)

Wrote the real edit (via `kiutils`, not raw text) and got it to a
genuinely loadable, ERC-checkable state — this took real debugging, not
one clean pass:

- **Found and fixed a real kiutils bug**: any symbol using KiCad's
  `extends` inheritance (TPS62822DLC extends TPS62823DLC) serializes into
  a file real `kicad-cli` refuses to open at all ("Failed to load
  schematic"), confirmed by isolating it against known-good cases that
  loaded fine. Fixed by flattening — copying the base symbol's real
  graphic under the derived part's own name instead of relying on the
  inheritance link. Same part electrically, just not dependent on KiCad
  re-resolving a link that doesn't survive the round-trip.
- **Verified the fix against real KiCad ERC**, not just "kiutils can read
  it back": copied the result into an isolated scratch copy of the whole
  project and ran `kicad-cli sch erc`. It loads. 87 violations vs. an
  84-violation baseline on the unmodified file.
- **Confirmed the reused nets are genuinely correct**: `VCC`, `GND`,
  `VUSB`, `SW`, `+1.8V`, `3V3`, `LSCTRL` — every one of these already has
  many pre-existing correctly-placed labels elsewhere in the design
  (e.g. `GND` appears 104 times, only 1 pre-existing instance flagged as
  an issue). Adding new same-named labels for the new charger/buck/load-
  switch chips didn't add a single new violation on any of these —
  meaning the actual power-rail rewiring is sound.

**One real, unresolved anomaly, reported honestly rather than glossed
over:** the 3 brand-new nets that only exist between my new parts
(`FB_1V8`, the buck's feedback divider node; `TP4056_PROG` and
`TP4056_TEMP`, the charger's program/temp-sense resistors) each show as
"dangling" in ERC, even though every label's coordinate was computed the
same way as the working ones and cross-checked against a known-good
existing example (R28's real labels) to confirm the placement formula
itself is right. Ruled out several real hypotheses by direct testing: not a pin-UUID
collision (pins carry no UUID in this format at all), not a symbol-unit-
index mismatch (confirmed unit 1 in both the working original and my new
instances), and not unquoted UUIDs (checked whether my new labels'
`(uuid 6137e1d8-...)` lacking quotes — vs. the original file's quoted
`(uuid "00000000-...")` — mattered; it doesn't, a pure unmodified
round-trip through the same library produces unquoted UUIDs throughout
and still loads/ERCs fine, so that's just this library's normal output,
not a defect). Also tried, after being asked to keep going: renaming the 3 nets to
plain alphabetic names (`FBDIV`/`CHGPROG`/`CHGTEMP` instead of
`FB_1V8`/`TP4056_PROG`/`TP4056_TEMP`) in case digit-containing names
were the trigger — same 3 flags, same violation count. Also checked for
a project-level "symbol instances" registry separate from each symbol's
own data, in case pre-existing parts are tracked there and new ones
aren't — the file has none at all, for any component, old or new.
Root cause genuinely not found after real, specific attempts across two
sessions — flagged honestly rather than assumed benign or silently
fixed. This needs real KiCad's GUI (not available in this environment)
to actually resolve; closing this investigation for good rather than
continuing to guess. Practical impact
if unresolved: those two specific sub-circuits (feedback divider,
charge-current/temp-sense resistors) might need their connections
double-checked by hand before trusting this for real, even though the
main power path (battery → charger → buck → 1.8V rail, and battery →
load switch → 3.3V rail) checks out.

**Where the actual result lives:** the edited schematic is in the
scratchpad
(`haven_dev_board_sch_STAGE4.kicad_sch`), not applied to the real
project file — editing that file directly was blocked by a safety
permission (irreversible local destruction), which is the right call
for a change this size without a look from a person first. Also: the
four new components' *footprints* still need to go on the PCB itself —
this pass was schematic-only.

## Real, stackable discounts found on top of the redesign

Worth combining with the cheaper-part redesign above, not instead of it:

- **PCBWay Educational Sponsor Program**: real, confirmed how-to. Email
  `sponsor@PCBWay.com` from a `.edu` address with your student ID and a
  short project description; they reply within 24 hours with a coupon
  code, typically 10-15% off future orders. Requirement is just "the
  project includes a PCB" — this genuinely qualifies.
- **JLCPCB currently has an active coupon specifically for 6-layer PCBs**
  (~$35 off), separate from any student program — worth checking
  `jlcpcb.com/coupon-center` for current codes before ordering either the
  original or redesigned board.
- **TI's sample program** may be usable with a Cornell `.edu` address —
  their restriction is against free consumer email domains (Gmail/Yahoo),
  not academic ones — worth trying for small quantities of the new
  TLV320AIC3100/TPS62822/TP4056 parts directly from TI at low/no cost
  before paying distributor pricing for them.
- **TI's University Program** offers free kits to faculty for
  coursework — only relevant if this ties to an actual Cornell class with
  a professor willing to request on the student's behalf.

## Not yet done / needs a real decision

This is a real architecture change, not a tweak — it means re-deriving the
audio front-end schematic (new codec chip, new charger IC, likely new
decoupling/crystal layout done correctly from scratch rather than ported)
rather than patching the current board. That's a decision for the project
owner, not something to execute unprompted. If this direction is chosen,
the crystal-placement and decoupling-placement issues found separately
(see git history / conversation log, not yet fixed as of this writing)
would need to be designed correctly from the start rather than retrofitted.

# Why this board is expensive, and a real path to fix it

Written after a round of research into whether a cheaper hardware path exists
for Haven, prompted by the ~$500 PCBWay quote for 5 turnkey-assembled boards
of the current design. Short version: **the cost isn't the board size, the
layer count, or the quantity — it's three specific chip packages, and there's
a concrete way to avoid all three without changing what the product does.**

## TL;DR (updated: the redesign is now actually applied, not just planned)

- **Root cause found and verified**: 3 chips (ADAU1860, BQ25120A, BQ27220)
  drive the whole cost via their fine pitch. The radio module is fine as-is.
- **All three are now actually replaced on the schematic**, with real,
  ERC-verified changes, committed and pushed — not sitting in the
  scratchpad anymore: TLV320AIC3100 (codec, replaces ADAU1860) +
  CMA-4544PF-W (analog mic, replaces the PDM one, since the new codec
  has no PDM input) + TP4056 (charger) + TPS62822 (1.8V buck) + TPS22917
  (3.3V load switch). Fuel gauge dropped entirely — confirmed nothing
  reads it. See **PR #8 on `haven-dev-board-kicad`**
  (`redesign/tp4056-power-tree` branch, 3 commits).
- **PCB-side work done for the charger parts** (real footprints placed,
  DRC-clean) but **not yet done for the codec/mic** — schematic-only so
  far for those two.
- **The ERC anomaly mentioned in earlier drafts of this doc is now well
  understood, not just unresolved**: `kicad-cli`'s headless ERC flags
  exactly one label per brand-new net name as `label_dangling`, and which
  specific label gets flagged shifts across unrelated edits — strong
  evidence it's a checker quirk, not a real defect. Every actual
  connection has been independently verified by direct coordinate
  comparison (not just trusting the ERC report). See the dedicated
  sections below for the full trace.
- **Real money-saving programs found**: PCBWay's student sponsorship
  (10-15% off, apply with a `.edu` email) and an active JLCPCB 6-layer
  coupon (~$35) — both usable regardless of which board design ships.
- **Still nothing ordered, nothing spent** — everything above is on a
  branch/PR, not master, waiting for review whenever there's time.

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

**Cornell startup/pitch programs — real, but check current deadlines
carefully, several 2026-cycle ones have likely already closed:**
- **eLab** (Cornell's student startup accelerator): $5,000 investment,
  mentorship, pitch to alumni/investors, MBA credit. The 2026-27 cohort
  application closed August 30, 2026 — missed for now, worth applying
  next cycle.
- **Cornell Startup Awards**: real, large prizes (up to $100,000),
  held annually each May — worth targeting for May 2027 with more
  runway to prepare.
- **Mark Mobius Pitch Competition** (Cornell EMC²): $30,000 top prize,
  but themed around "emerging markets" impact specifically and its 2026
  registration window (by April) has already passed — not a clean fit
  for Haven's positioning anyway without a genuine emerging-markets
  angle, and search results on exact dates were inconsistent enough that
  this one needs a direct check with the organizers rather than trusting
  what's written here.
- Bigger picture: **the free/cheap wins (RPL for the enclosure, PCBWay/
  JLC discounts, TI samples) are usable right now with no application
  cycle to miss.** The larger competitive funding (eLab, Startup Awards)
  is worth planning toward for next year's cycles, not something to wait
  on before making progress now.

## Update: the charger/regulator redesign is now actually applied (branch, not master)

Paul gave explicit go-ahead to keep iterating and apply real changes while he's
busy with school/recruiting, with one standing rule: **never place an order or
spend real money without him there.** Everything below is a real, committed,
ERC-checked schematic change — but on branch `redesign/tp4056-power-tree`, not
merged to master. It's meant to be reviewed whenever there's time, not acted
on immediately.

### What changed

U2 (BQ25120AYFPR) is removed, replaced by three parts, each verified against
its own real datasheet this session (pin-for-pin, not guessed):

- **TP4056** (linear Li-Ion charger, SOP-8) — pinout confirmed from
  NanJing Top Power ASIC's own datasheet (1:TEMP, 2:PROG, 3:GND, 4:VCC,
  5:BAT, 6:STDBY, 7:CHRG, 8:CE).
- **TPS62822DLCR** (adjustable buck, VQFN-8) — from TI SLVSDV6C
  (1:EN, 2:FB, 3:AGND, 4:NC, 5:PGND, 6:SW, 7:VIN, 8:PG). Feedback divider
  sized for exactly 1.8V: R_FB1=200k (VOUT side) + R_FB2=100k (GND side),
  Vout = 0.6V x (1 + 200/100) = 1.8V.
- **TPS22917DBVR** (load switch, SOT-23-6) — from TI SLVSDW8B
  (1:VIN, 2:GND, 3:ON, 4:CT, 5:QOD, 6:VOUT). CT/QOD left floating per
  datasheet (fastest turn-on, discharge disabled) — matches this project's
  own convention of leaving genuinely-optional pins unconnected rather than
  fabricating a connection.

### Real net-reuse, found by inspecting the actual schematic before writing anything

Rather than re-guess wiring, I traced what each of U2's real pins already
connected to and reused it:

- `SW`/`+1.8V`: L2 (2.2uH inductor) is already sitting on exactly these two
  nets, with 4 existing decoupling caps on `+1.8V` (C1/C4/C18/C20) — this is
  the buck's real output tank, left over from BQ25120A's SYS pin. No new
  output cap needed.
- `3V3`: already has 4 decoupling caps (C5/C17/C29/C48) from its other
  consumers — no new output cap needed for the load switch either.
- `TS`: the battery thermistor sense line already has a real 2-resistor
  divider (R6/R13) wired at the battery. TP4056's TEMP pin reuses this
  directly instead of inventing new resistors (a mistake from an earlier
  pass this session, caught before it was applied).
- `LSCTRL`: already driven by a real MCU GPIO (MDBT531 pin 27) — reused
  directly for the load switch's ON pin.
- `VUSB`: the real 5V USB input rail. TP4056's VCC and its CE pin (must not
  float, per datasheet) both land here — CE tied straight to VCC is the
  standard "always enabled when powered" wiring.
- `VCC`: confirmed to be this board's (slightly confusing) name for the
  *battery* rail, not a regulated supply — TP4056's BAT, the buck's VIN, and
  the load switch's VIN all land here.
- **A real gap found and fixed**: BQ25120A's CD#/PG# status flags were
  push-pull and fed two MCU GPIOs directly with no pull-up anywhere.
  TP4056's CHRG/STDBY equivalents are open-drain, so reusing those same
  nets as-is would leave the GPIOs floating. Added two new 100k pull-ups —
  to `3V3`, deliberately not `VUSB`/5V, since pulling a 3.3V-domain MCU
  input up to 5V would over-volt the pin.

Net genuinely new nets introduced: just `FB_1V8` (buck feedback midpoint)
and `TP4056_PROG` (charge-current-set resistor node, R_PROG=1.2k for
exactly 1A charge current (per the TP4056's own
 electrical-characteristics table: Rprog=1.2k -> Ibat=1000mA typ), matching TI's own reference design's exact resistor
value). Down from 3 in an earlier pass to 2, entirely by finding real
reuse opportunities instead of inventing new nets.

### The ERC "dangling label" anomaly — now genuinely isolated, not just retried

Same category of issue as before (`kicad-cli sch erc` flags exactly one
label per *brand-new* net name as `label_dangling`), but this time fully
isolated with a minimal, from-scratch reproduction: **two freshly-created
resistors bridging a single, never-before-used net name, with no ICs, no
custom symbols, nothing carried over from this session's other work** —
and `kicad-cli` still flags the first-encountered label of that net as
dangling, even though the second resistor's matching label is right there.
Manually verified (direct coordinate comparison, not trusting the ERC
report) that every one of this redesign's new pins lands exactly on its
intended label — the flagged labels really are sitting exactly on real
pins. This looks like a first-occurrence-of-a-new-net-name quirk in
`kicad-cli`'s headless ERC specifically, separate from anything about this
design's actual correctness.

Tested and ruled out as the cause: missing per-symbol `(instances (project
...))` metadata, and missing per-pin `(pin "N" (uuid ...))` maps (added
both by hand to the minimal repro; neither changed the result, and the
pin-uuid one made ERC noticeably worse when applied file-wide, so it was
not carried into the real redesign).

### A separate, bigger, previously-undocumented finding: netlist export doesn't work on this project at all

While chasing the above, tried exporting a real netlist
(`kicad-cli sch export netlist`) as a way to independently confirm
connectivity. It came back completely empty — zero components, zero nets —
**on the real, untouched, git-committed schematic file, not just on my
edited copy.** Confirmed `kicad-cli`'s netlist exporter works fine in
general (tested against a real KiCad-authored template file, which
exported cleanly). So this is a real, pre-existing gap in this specific
project's schematic file, unrelated to anything from this session — the
file can pass ERC/DRC (which work from pure geometry) but cannot currently
produce a netlist for cross-checking against the PCB or for external tools.
Root cause not found (tried the two hypotheses above without success);
worth a real KiCad GUI session to investigate, since opening and re-saving
the file through the actual application may just fix whatever structural
piece `kicad-cli`'s exporter wants that isn't there.

### Net result (schematic)

`kicad-cli sch erc` on the redesigned schematic: **86 violations vs. an
84-violation baseline** on the real, unmodified board — and the 2 new ones
are the isolated, likely-cosmetic anomaly above, not a real connectivity
defect (every reused net — VCC, GND, VUSB, 3V3, SW, +1.8V, TS, LSCTRL,
CC_#CD, CC_#PG — shows zero new issues). Committed to branch
`redesign/tp4056-power-tree`, not master.

## Update 2: PCB footprint placement done too, same branch

Followed the schematic straight onto the real PCB, using real footprints
copied from KiCad's own official library rather than hand-derived pad
geometry:

- `Texas_VSON-HR-8_1.5x2mm_P0.5mm.kicad_mod` for TPS62822DLCR — this is
  TI's own name for the exact package ("VSON-HR"), confirmed against the
  datasheet's own generic-package-view page before using it.
- `SOIC-8_3.9x4.9mm_P1.27mm.kicad_mod` for TP4056 (plain SOP-8, no
  exposed pad, matching the real pin table).
- `SOT-23-6.kicad_mod` for TPS22917DBVR (JEDEC MO-178), confirmed against
  the datasheet's own DBV0006A package outline drawing.

The 5 new passives (R_PROG, R_FB1, R_FB2, R_PU_CHRG, R_PU_STDBY) use the
project's existing generic 0402 footprint, matching the "doesn't need to be
tiny, needs to be easy to hand-solder" goal for this dev board.

**A real placement mistake, found and fixed via DRC, not assumed away:**
first attempt put the new buck IC right next to L2 (the existing inductor)
for a short SW/FB loop — reasonable analog-layout instinct, but that whole
area turned out to be densely criss-crossed by existing copper (VUSB/
V_PMID/V_LS traces left over from the original charger circuit), which a
placement check based only on footprint courtyards doesn't see. Real
`kicad-cli pcb drc` caught it immediately as two `shorting_items`
violations — new pads physically landing on live existing traces. Moved
the buck IC and its feedback resistors to the same genuinely-clear area
(checked directly against real track geometry, not just other footprints)
used for TP4056/TPS22917, at the cost of a longer eventual SW trace to
route by hand later.

**Net result (PCB):** `kicad-cli pcb drc` — **221 violations vs. the
documented 219-violation baseline**, and critically, the **clearance
violation count went down** (85 vs. 99), since removing the old BGA-25
(BQ25120A)'s fine-pitch pads removed more clearance issues than the new
parts introduce (zero). The increase is entirely expected "not routed yet"
noise: 28 unconnected pads (new parts have net assignments but no copper
yet; a few are old trace stubs orphaned by removing U2) vs. 2 in the
baseline. No new shorts, no new clearance violations from the new parts,
only two trivial cosmetic silkscreen-label overlaps (fixed by nudging the
reference designator text).

**Still not done:** actual copper routing from the new parts to their
nets (SW to L2, VUSB to the USB circuitry, etc.) — footprints are placed
and net-assigned but nothing is routed yet. Net assignment was done
directly by name (pad-by-pad) rather than through a real netlist import,
since — as found above — this project's schematic can't currently export
one; whoever does the real routing pass should treat the net *names* as
authoritative but re-verify the pad-to-net assignments against the
schematic by eye first.

## Update 3: the actual original cost driver — ADAU1860 → TLV320AIC3100 + mic swap

Same branch (`redesign/tp4056-power-tree`). This is the real headline
item from the very first table in this doc — the ADAU1860 (BGA-56,
0.35mm pitch) was always the single biggest cost driver, bigger than the
charger. Removed it and the old PDM mic (U13, SPH0641LU4H-1), replaced
with:

- **TLV320AIC3100** (TI, QFN-32, 5x5mm) — pin table pulled from its real
  datasheet (SLAS667C, pages 6-7), not guessed.
- **CMA-4544PF-W** (Same Sky/CUI, plain 2-terminal electret capsule) —
  its own datasheet's "measurement circuit" diagram gives the real bias
  resistor (2.2k) and coupling cap (1uF) values used here directly,
  rather than picking arbitrary ones.

TLV320AIC3100 has no PDM input at all (confirmed from its own datasheet —
mic inputs are analog PGA inputs MIC1LP/MIC1RP/MIC1LM), which is exactly
the incompatibility flagged earlier in this doc. Hence the mic swap too,
not just the codec.

### Real net reuse (same discipline as before)

- `DIN`/`DOUT`/`BCLK`/`LRCLK`: the real I2S bus already wired to the MCU
  (2 owners each before this change) — reused directly.
- `SDA1`/`SCL1`: the I2C control bus (4 owners each) — reused directly.
- `V_LS`: the existing switched analog rail already feeding the old
  codec's AVDD/HPVDD/IOVDD and the old mic's VDD (38 owners board-wide)
  — reused for the new codec's AVDD/HPVDD.
- `+1.8V`: **the same rail this session's charger redesign created**
  (TPS62822's regulated output) — reused for the new codec's DVDD, which
  needs 1.65-1.95V per its own datasheet. This specifically only works
  *because* the charger redesign landed first — the two changes are
  actually coupled, not independent.
- `DAC_N`/`DAC_P`: the old codec's HPOUTN/HPOUTP had only ONE owner each
  on this sheet (a pre-existing condition — the real receiver connection
  isn't modeled here, not something this change created or fixed).
  Preserved as-is; the new codec's HPL/HPR reuse the same two names.
- `TCK`/`TMS`/`TDI`/`TDO`: real JTAG pins with a second owner (a debug
  header) — TLV320AIC3100 has no JTAG at all (fixed-function codec, not
  a general DSP), so these just lose their old-codec end. Harmless.

### Real simplifications made, each flagged rather than hidden

- **MCLK tied to BCLK** instead of adding a dedicated crystal — the
  datasheet explicitly allows BCLK (or GPIO1, etc.) as the PLL reference
  instead of a true MCLK input. Avoids needing a new oscillator for a
  part that didn't need one before.
- **VOL/MICDET, MIC1RP, MIC1LM tied to GND** (unused in this
  single-ended-mic setup). Worth a second look before trusting blind:
  some reference designs bias the unused differential input pin (MIC1LM)
  to a DC midpoint instead of hard ground for better common-mode
  balance — this uses the simpler hard-ground approach.
- **RESET tied directly to 3V3** (permanently out of reset) rather than
  a firmware-controlled GPIO, since nothing in current firmware asserts
  a hardware reset today.
- **Class-D speaker block left fully unconnected** (SPKP/SPKM x2,
  SPKVDD x2, SPKVSS x2 — 6 pins) — this device drives its receiver from
  the headphone output, not the higher-power Class-D path.
- **GPIO1 left floating** — genuinely optional per datasheet.

### A real bug caught mid-script, before it was applied

First draft of the mic-bias wiring accidentally gave the AC-coupling
capacitor's two ends the *same* net name, which would have shorted across
it and defeated its entire purpose (blocking the mic's DC bias from
reaching the codec's input pin while still passing the AC audio signal).
Caught by re-reading the wiring before running ERC, not by ERC itself —
worth remembering that ERC only catches connectivity errors, not "this
connection makes the circuit pointless" errors. Fixed with two distinct
nets either side of the cap (`MIC_IN` on the biased/mic side, `MIC_IN_AC`
on the codec-input side).

### ERC result and the dangling-label quirk gets more interesting

`kicad-cli sch erc` on the combined charger+codec+mic redesign: **still
86 violations total** — flat, not growing. But the *specific* nets
flagged as `label_dangling` changed: the 3 new mic-bias nets
(`MICBIAS`, `MIC_IN`, `MIC_IN_AC`) are now flagged, while two nets that
*were* flagged after the charger-only change (`FB_1V8`, `TP4056_PROG`)
are no longer flagged at all — even though nothing about their actual
wiring changed in this commit. That's a genuinely useful data point:
it confirms (independent of anything else already found) that which
specific label gets flagged is unstable across unrelated edits elsewhere
in the file, which is much more consistent with a checker quirk than
with a real, fixed electrical defect. Manually verified anyway, the same
way as before, by direct coordinate comparison rather than trusting the
report: every new pin — codec, mic, both new passives — lands exactly on
its intended label, except the 9 pins deliberately left unconnected
(the 8 Class-D pins + GPIO1).

### Still not done

PCB footprint placement and routing for TLV320AIC3100 (QFN-32,
0.5mm pitch) and CMA-4544PF-W (a leaded through-hole capsule, not SMD —
worth noting its "terminal: pin type (hand soldering only)" spec, so it
needs through-holes, not pads, on the PCB) haven't been started. This
pass was schematic-only, same pattern as the charger work before it.

## Update 4: PCB placement for the codec/mic too — and a real board-shape mistake caught by DRC

Same branch. TLV320AIC3100 uses TI's own real footprint
(`Texas_RHB0032M_VQFN-32-1EP...` — "RHB" is the exact package code from
its own datasheet's pin diagram) copied from KiCad's library, same as the
charger parts. No official KiCad footprint exists for a plain electret
capsule like CMA-4544PF-W, so this one is hand-built: 2 through-hole pads
on a 2.54mm pitch (per its datasheet's own mechanical drawing) with a
silkscreen circle approximating its real 9.7mm body — flagged as a
first-approximation, not manufacturing-verified, since the exact pin-to-
body-center offset wasn't pixel-checked against the drawing.

**A real, different placement mistake this time, also caught by DRC, not
assumed away:** the first attempt placed the mic capsule in what looked
like open board area from a footprint/track scan, but this board's
outline isn't a simple rectangle — it has a real notch cut into the left
edge (confirmed by reading the actual `Edge.Cuts` geometry), and the
mic's 9.7mm body landed half inside that notch. `kicad-cli pcb drc`
caught it immediately as both a `copper_edge_clearance` and a
`silk_edge_clearance` violation. Fixed by re-scanning for free space
against the board's *real polygon outline*
(`BOARD.GetBoardPolygonOutlines()`), not just its bounding rectangle —
the bounding-box shortcut is now a second confirmed source of real
placement mistakes this session (the first being "checked footprints but
not existing copper," from the charger placement earlier).

Also caught by the same DRC pass: forgetting to refill copper zones after
adding new through-hole pads left two stale `hole_clearance` violations
against zones that hadn't been recomputed around the new holes — fixed by
calling `ZONE_FILLER.Fill()` before the final save, now part of the
script. And one footprint-library-reference mismatch on the hand-built
mic footprint (used a real-looking but unregistered library nickname;
fixed by matching the empty-nickname convention every other footprint
on this board already uses).

**Net result:** `kicad-cli pcb drc` — **215 violations**, actually
*fewer* than even the 219-violation original baseline, since removing
the BGA-56 (the single worst clearance offender on the whole board)
outweighs everything the new parts add. Zero violations of any kind
involve the new codec/mic footprints once the above were fixed — checked
directly, not inferred from the total count. Routing is still not done
for any of the new parts (charger or codec/mic).

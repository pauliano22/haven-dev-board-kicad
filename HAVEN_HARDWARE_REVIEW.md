# Haven Dev Board — Hardware Design Review

Reviewer notes on the KiCad port in this repo (`kicad/`), written against the
files as generated, plus one real external datasheet lookup (cited below).
**No KiCad install is available in this environment — nothing here was
run through ERC/DRC.** Every finding below states its own confidence level:
tool-verified (parsed from the actual generated files or measured from real
coordinate data), general-best-practice inference, or genuinely unresolved.

Audit scripts used: `extracted/sexp_parser.py` (independent S-expression
parser, written fresh for this review rather than reusing the generator's
code path), `extracted/audit_schematic.py`, `extracted/audit_pcb.py`.

---

## 0. Cross-check against upstream OpenEarable firmware (2026-09-10)

Several of the questions this review left open turn out to be answered by a
source that was in the workspace all along: the upstream
[`OpenEarable/open-earable-2`](https://github.com/OpenEarable/open-earable-2)
firmware, which drives this exact codec on this exact board (Haven's KiCad
port is of the stock OpenEarable main PCB, so upstream's devicetree and
driver *are* ground truth for how these nets are actually used). Everything
below is **sourced from upstream code**, not from the ADAU1860 datasheet —
the datasheet PDF was not fetchable in the environment this cross-check was
done in, so nothing here is "datasheet-verified"; it's "matches firmware
that ships on this hardware". File references are into a clone of upstream
at its 2026-09 `main`.

### 0.1 The codec's register map is public and already transcribed

The premise in `haven-zephyr-app` that "there is no public ADAU1860
register map" is wrong. Upstream's `src/drivers/ADAU1860.h` carries the
full map (~350 named registers, `VENDOR_ID = 0x4000C000` through
`DAC_NOISE_CTRL1 = 0x4000CC12`), and `src/drivers/ADAU1860.cpp` is a
working bring-up sequence for it. Two consequences for this board's
firmware, both firmware-side rather than layout-side, but recorded here
because the review's §1 was reasoning about them:

- **Control-port addressing is 32-bit**, not the 16-bit big-endian
  framing used by older SigmaDSP parts (`ADAU1860.cpp:512-517` builds a
  4-byte address for every read, `:544-549` for every write). A 16-bit
  framing simply addresses nothing on this chip.
- **The DSP program is a raw memory image**, not a SigmaStudio `ADISIGM`
  blob: `Lark-fdsp.c` ("Lark" is ADI's codename for the ADAU1860) is
  plain `uint32_t` arrays written straight to `FDSP_PROG_MEM = 0x40008000`
  and the three parameter banks (`ADAU1860.cpp:335-341`). The design tool
  for this chip is ADI's **Lark Studio**, not SigmaStudio+ — per the
  EVAL-ADAU1860 user guide (UG-2017), its "Download to Target" writes
  exactly these parameter + command words into FastDSP memory, and the
  FastDSP input source is chosen in its drag-and-drop schematic.

### 0.2 §1 resolved: DIN/DOUT direction, and I2S master/slave

**DIN/DOUT — the flagged discrepancy was real, and the overlay comment was
the backwards one.** Upstream's pinctrl
(`boards/teco/openearable_v2/openearable_v2_nrf5340_cpuapp_common-pinctrl.dtsi:14-17`)
puts `I2S_SDOUT` on P0.28 and `I2S_SDIN` on P0.31. This review's §1 table
has net `DIN` on MDBT531 pin 60 = P0.28 and `DOUT` on pin 56 = P0.31. So:

| Net | nRF pin | nRF role (upstream pinctrl) | ADAU1860 pin (this port) | Direction |
|---|---|---|---|---|
| `DIN`  | P0.28 | `I2S_SDOUT` | C1 `SDATAI_0` | **nRF → codec** |
| `DOUT` | P0.31 | `I2S_SDIN`  | B1 `SDATAO_0` | **codec → nRF** |

The net names are from the *codec's* point of view, and the ADAU1860's own
pin names (`SDATAI` = input, `SDATAO` = output) were telling the truth
after all. The `haven-zephyr-app` overlay's "DIN (ADAU1860->nRF)" comment
is inverted; see the ADAU1860 driver PR on `haven-zephyr-app` for the fix.

**Master/slave — the overlay's 2026-08-25 inference ("codec has its own
24.576 MHz crystal, therefore codec is I2S master, nRF is slave") reaches
the wrong conclusion.** Upstream runs the **nRF5340 as I2S master**:
`I2S_SCK_M` on P1.10 and `I2S_LRCK_M` on P0.30 (pinctrl `:14-15`, the `_M`
suffix is Nordic's master-mode pin function), with an `I2S_MCK` output on
P1.14 (`:10`) and `hfclkaudio-frequency = <12288000>` in the board DTS
(`openearable_v2_nrf5340_cpuapp_common.dts:51`). The codec is the slave.
The crystal doesn't contradict this: the ADAU1860 has asynchronous
sample-rate converters precisely so its internal clock domain can run off
its own crystal while its serial port follows an external bit clock —
upstream enables them (`ASRC_PWR`, `ASRCI_*`/`ASRCO_*` routing,
`ADAU1860.cpp:164-209`). §1's "the schematic genuinely cannot settle
master/slave" stands as a statement about the schematic; upstream's
firmware settles it.

### 0.3 §3.5 checklist items, revisited

- **Item 2 (DIN/DOUT):** resolved above.
- **Item 3 (AGND/DGND split):** still a real layout question, but its
  urgency is lower than §3.1 implies — the unified `GND` pour is exactly
  what the stock OpenEarable board ships with, and that board produces
  usable audio in the field. Treat as "improve on rev 2", not "blocks rev 1".
- **Item 6 (unused second serial port / `DMIC23`):** upstream leaves
  `SPT1_*` unused as well and only drives `DMIC01` (`ADAU1860.cpp:168-169`
  powers DMIC channels 0 & 1 only), so the dangling `_1` port and `DMIC23`
  pins match the working reference. Whether they need a defined pull is
  still a datasheet question, but the stock board evidently gets away
  without one.
- **Power sequencing the codec actually needs** (not on the original
  checklist, added because the port's netlist confirms the wiring):
  `DAC_ENABLE` — MDBT531 pin 37 → U15 E4 — is the codec's enable/PD pin,
  driven as `enable-gpios = <&gpio0 4>` in upstream's DTS (`:130`) and
  asserted at `ADAU1860.cpp:58`; `V_LS` is a load-switched rail
  (`load_switch`, `enable-gpios = <&gpio1 11>`, DTS `:26-28`); upstream
  then waits 35 ms for common-mode rise (`:71`), bypasses/configures the
  PLL (`CLK_CTRL13`, `:88-117`) and polls `STATUS2` bit 7 for power-up
  (`:95-105`). I2C address `0x64` is confirmed by upstream's DTS (`:127`).
- **The mic path never touches the nRF.** `U13` (`SPH0641LU4H-1`) is a
  **PDM** mic; the netlist has it on `PDMCLK`/`PDMDIN` → U15 C4/C5 (the
  codec's DMIC pins), also brought out on the flex connector `CN1` pins
  5/7. So mic audio goes mic → codec → (FastDSP) → DAC → `DAC_P`/`DAC_N`
  → speaker, entirely inside the codec, and the nRF only ever writes
  coefficients over `SDA1`/`SCL1`. Note for `haven-hardware`: the
  `SPH0645LM4H-B` in `haven_dev_board/component_libraries/` is an **I2S**
  mic — the wrong interface class for this topology; the stripped-down
  board wants a PDM part like the `SPH0641LU4H-1` that's actually here.

### 0.4 §3.4 HPVDD / HPVDD_L — still unresolved

Nothing in upstream's DTS or driver mentions an `HPVDD` net either; the
codec's headphone supply is configured in registers (`HP_LVMODE_CTRL*`,
`HPLDO_CTRL`, `ADAU1860.cpp:255-266`), which suggests the callout may have
referred to a supply/trace *inside* the codec's own power arrangement or to
a note on the live EasyEDA schematic. Still needs whoever read it off the
live schematic to point at the net.

### 0.5 §8 (U1: BMX160 vs BMI160) — a second data point, not a reversal

Upstream's devicetree declares the IMU as `bmx160: bmx160@68`
(`openearable_v2_nrf5340_cpuapp_common.dts:175`) and ships a BMX160 driver
(`src/SensorManager/BMX160/DFRobot_BMX160.{h,cpp}`) — i.e. the reference
firmware believes a 9-axis BMX160 is on the board. That is in tension with
§8's wiring-based argument for BMI160. Both are real evidence; neither is a
part number read off a chip. Recording this rather than flipping the BOM
back: **check the physical part marking on an assembled board (or ask the
OpenEarable team) before any production order.** Irrelevant to audio
either way — nothing in Haven's firmware touches the IMU.

### 0.6 Two practical consequences

- **Hardware before this board is fabricated (neither option is cheap):**
  (a) an nRF5340 DK plus ADI's EVAL-ADAU1860EBZ (~$485 at Newark, ~$535
  total) — the eval board brings the codec's DMIC input out on header P44
  and serial port 0 on header P2, so it wires to the DK with this board's
  exact topology, and it carries the USB interface Lark Studio uses; or
  (b) a stock OpenEarable 2.0 unit (Developer Starter Bundle: €2,348 at
  shop.openwearables.com), which *is* this board and takes Haven firmware
  via J-Link + OpenEarable's debug breakout per upstream's README. Either
  takes the PCB fab off the critical path; fab this port only after §3.2
  and a real ERC/DRC pass.
- **The DSP-side work that remains** is not a SigmaStudio blob or a
  parameter-RAM map: upstream's FastDSP program already has five biquad
  slots with hardware safeload (`FDSP_SL_ADDR`/`FDSP_SL_P*`/
  `FDSP_SL_UPDATE`, `ADAU1860.h:181-202`, used at `ADAU1860.cpp:407-425`),
  coefficients in Q5.27 (`src/audio/Equalizer.cpp:10-11`; cross-checked
  against RBJ math — the 150 Hz peaking row matches to five decimals).
  What's missing is a program variant whose *input* is the DMIC rather
  than the I2S port (upstream's takes I2S from the phone) — in Lark
  Studio that's an input-source choice in the FastDSP schematic (UG-2017
  pp. 6-7 route `AIN1`/`ASRCI0` in their example). One caveat that matters
  for this board: upstream frame-clocks FastDSP from the **192 kHz** DMIC
  stream (`ADAU1860.cpp:343`, `FDSP_CTRL4 = 2`), and UG-2017 says the
  filter fs must equal the FastDSP source rate (`FDSP_RATE_SOURCE`), so
  coefficient math must use whichever rate the program actually runs at.
  UG-2017 also confirms `EQ_ROUTE` selects the hardware EQ engine's input
  ("set fs to be same as the equalizer source, EQ_ROUTE").

---

## 1. Firmware cross-check: does the port's netlist match the current overlay?

Read `haven_workspace/firmware/haven_zephyr_app/boards/nrf5340dk_nrf5340_cpuapp.overlay`
(read-only) for the authoritative current values, then parsed the actual
`haven_dev_board.kicad_sch` (not the intermediate JSON) to check every claim.

**Net names and pin numbers: exact match, verified.**

| Signal | Overlay claim | Port's schematic (MDBT531 pin) | Match |
|---|---|---|---|
| I2C1 SDA1 | P1.15 | pin 47 → net `SDA1` | ✓ |
| I2C1 SCL1 | P1.00 | pin 45 → net `SCL1` | ✓ |
| I2S DIN | P0.28 | pin 60 → net `DIN` | ✓ |
| I2S BCLK | P1.10 | pin 59 → net `BCLK` | ✓ |
| I2S LRCLK | P0.30 | pin 57 → net `LRCLK` | ✓ |
| I2S DOUT | P0.31 | pin 56 → net `DOUT` | ✓ |

All six checked exactly. The ADAU1860 (U15) side also confirms the I2C bus
separation the overlay's comment claims: U15's `SDA/MISO/UART_CTRL_TX` pin
sits on `SDA1` and its `SCL/SCLK` pin sits on `SCL1` — the codec's control
port really is on the dedicated bus, not the charger/fuel-gauge's shared
SDA/SCL.

**Signal direction (DIN/DOUT) and master/slave: NOT verified — and there's a
real discrepancy worth flagging, not a clean match.**

The port's schematic only carries net *names* as text; every generated pin
is typed `passive` in the symbol library (documented in the original
README as a deliberate choice, since I have no sourced per-pin electrical-
role data). Net names and generic pin numbers say nothing about which chip
actually drives a wire. So: I have **not** verified the overlay's directional
comments — and checking against the ADAU1860's own pin *names* (which the
port does carry, straight from the original schematic's symbol data)
surfaces something worth a real look:

| nRF net | ADAU1860 pin on that net | Pin's own name suggests |
|---|---|---|
| `DIN` (overlay: ADAU1860→nRF) | U15 pin C1 | `SDATAI_0/MP6` — codec's serial-data-**input** |
| `DOUT` (overlay: nRF→ADAU1860) | U15 pin B1 | `SDATAO_0/MP5` — codec's serial-data-**output** |

Taken at face value, this is backwards from the overlay's stated direction:
a net where the codec's own pin is named "input" would mean the *nRF*
drives it, not the codec. **I'm not confident this is a real error though** —
all four ADAU1860 serial-port pins involved (`BCLK_0/MP3`, `FSYNC_0/MP4`,
`SDATAI_0/MP6`, `SDATAO_0/MP5`) carry an `MPx` (multi-purpose pin) suffix,
meaning they're documented by ADI as configurable/multiplexed pins whose
actual role depends on the ADAU1860's internal register configuration, not
a fixed hardware function. So the pin's *default* name may simply not match
how this design's firmware configures it. This needs an actual ADAU1860
register-map/datasheet check, not something resolvable from schematic data
alone — flagging it rather than either confirming the overlay or claiming a
contradiction.

One more data point on master/slave specifically: since all four relevant
ADAU1860 pins are multi-purpose/configurable, the schematic genuinely
**cannot** settle master/slave — confirming that the overlay's own
reasoning (inferring slave mode from the presence of a dedicated 24.576MHz
crystal on the ADAU1860, rather than from pin names) was the right approach
already, not a shortcut. I have nothing here that contradicts it.

Also notable: U15 has an entire *second* serial port's worth of pins
unconnected in this design — `BCLK_1/MP7`, `FSYNC_1/MP8`, `SDATAI_1/MP10`,
`SDATAO_1/MP9`, `DMIC23/MP2` all show up as dangling (see §2). The ADAU1860
appears to expose two serial audio ports; only one (`_0`) is wired here.
Worth confirming that's intentional.

---

## 2. Automated schematic cleanup

Parsed the real `.kicad_sch` (not regenerated from scratch) looking for
parsing artifacts, dangling nets, and metadata cruft.

**Fixed (safe, mechanical, zero connectivity change):**
- Two exact-duplicate net labels sitting on top of each other at the same
  coordinate (`SD_STATE_3V3` at one point, `$1N2586` at another) — both
  arose because two *different* components' pins genuinely land at the
  same schematic coordinate by coincidence, so each got its own generated
  label. Verified both underlying pin pairs really do share that net before
  removing the redundant copy; connectivity is unchanged (still 385→383
  labels covering the same 452 pins at 85.2%).

**Found and logged, not touched (need a human judgment call, not a mechanical fix):**
- **67 dangling (unlabeled) pins across 8 components.** Spot-checked all of
  them — none look like parsing bugs:
  - U15 (ADAU1860): 20 pins — the entire unused second serial port (above),
    plus other MPx pins not wired.
  - U14 (flash): 14 pins, all literally named `NC` by the part's own pinout
    — genuine no-connects.
  - MDBT531: 13 pins — all unused GPIOs, consistent with earlier hardware
    bring-up work on this project.
  - CN1 (battery connector): 12 pins (positions 13–24) — connector footprint
    has more physical positions than this design uses.
  - U1 (BMX160 IMU): 4 pins — `INT1`, `INT2`, `OSDO`, `OCSB` all unused,
    consistent with running the IMU in plain I2C mode with interrupts unused.
  - U12 (USB-C connector): 2 pins — `SBU1`/`SBU2` (sideband-use, alt-mode
    signaling) unused, expected for a non-alt-mode USB-C port.
  - U5 (KTD2026 RGB driver): pin `ST` unused — worth a datasheet check on
    what this pin does before assuming it's safe to leave floating.
  - CARD1 (microSD): pin `RSV` (reserved) unused — expected.
- **Placeholder UUIDs.** Every generated `uuid` field is a sequential
  fake (`00000000-...-000000000042` style) rather than a real random v4
  UUID. Harmless — they're only used as unique identifiers, never
  cross-referenced by value except the root sheet UUID, which I left
  alone — but cosmetically nonstandard. Logging rather than mass-editing
  hundreds of lines for a purely cosmetic, zero-risk-either-way item.

No connectivity was restructured. The 85.2%/84.3% (schematic/PCB) net
coverage figures from the original port stand unchanged.

---

## 3. Design & routing review

### 3.1 Analog/digital ground plane separation (ADAU1860)

**Tool-verified: there is no separate analog ground plane. GND is one
unified net and one unified copper pour on every layer that has a pour.**

The generated PCB's zone list has exactly one `GND` zone per inner layer
(layers 15 and 16 — see the 6-layer stackup in the main README) and no
second ground net (no `AGND`, `DGND`, or similar) anywhere in the 85-net
list. The ADAU1860's ground pins (per the schematic) tie into this same
single `GND` net alongside the nRF5340, USB, charger, and every digital
IC on the board.

This matches what a from-scratch faithful port of the *stock* board would
produce if the stock board itself never split analog/digital ground — I
have no data suggesting a split ground was intended and lost in translation;
this is what the source data actually shows. **What would need to change**:
a proper analog ground for a codec like the ADAU1860 typically wants (a) a
star-point or single-stitch-via connection between analog and digital
ground domains right at the codec, not a fully merged plane, and (b) the
ADAU1860's analog supply/ground pins routed to a locally poured analog
ground island rather than the general board pour. Implementing this would
mean editing the zone definitions and possibly re-routing a few of the
codec's ground pin connections — not something to do mechanically without
the codec's actual pinout diagram in hand (which pins ADI's own reference
layout marks as "AGND" vs "DGND").

### 3.2 BLE antenna keepout (MDBT53 module)

**Sourced from a real datasheet lookup** (WebSearch/WebFetch — full PDF
render wasn't possible in this sandbox, no `pdftoppm`/poppler available, so
the exact keepout dimension in mm from Raytac's diagram could not be
extracted, only the text guidance surrounding it):

> "Make sure to keep the 'No Ground Pad' as wider as you can regardless of
> the size of your PCB... included in the corresponding position of the
> antenna in EACH LAYER... place the module towards the edge of PCB."
> — Raytac RF layout guidance for the MDBT53 family
> ([SparkFun-hosted datasheet PDF](https://cdn.sparkfun.com/assets/9/7/0/8/6/_nRF5340__MDBT53-1M___MDBT53-P1M_Spec__Ver.D_.pdf))

This is almost certainly the actual source of the "no ground pad, as wide
as possible" callout mentioned for this project — it's Raytac's own literal
phrasing. (I initially went looking for this near a component's exposed
thermal pad — U5/KTD2026 has a `DFN...-EP` footprint — but its exposed pad
turns out to already be normally tied to `GND`, not a special case. The
antenna-keepout reading fits far better.)

**Tool-verified against the actual generated PCB**: this guidance is **not
implemented**. MDBT531's placement center sits ~7.3mm from the nearest
board edge (board is ~14.6mm × 32.2mm; the module is a 14.3mm × 9.3mm
part, so it is reasonably close to an edge — partial credit on the
"place near the edge" guidance). But a real point-in-polygon test against
the actual `GND` copper pour on both inner layers (15 and 16) shows the
module's center point sits **inside solid ground copper fill**, with the
nearest pour boundary only ~2.5mm away — nowhere near "as wide as possible."
I did not check whether this holds specifically under the antenna trace
itself (that needs the module's mechanical drawing to know exactly which
edge of the package the antenna occupies, which I couldn't extract from the
un-renderable PDF) — but given the pour comes this close to the module's
center generally, a real keepout is very unlikely to exist anywhere nearby.
**This is the single highest-priority hardware finding in this review** —
worth Raytac's own free layout-review service (`sales@raytac.com`,
mentioned on their site) before this ever gets fabricated.

### 3.3 Decoupling capacitor placement

**Tool-verified** — computed real center-to-center distances from the
ported placement data:

| IC | Net | Nearest cap | Distance |
|---|---|---|---|
| U2 (BQ25120A charger) | VUSB | C22 | 2.15mm |
| U2 | V_BAT | C21 | 2.83mm |
| U2 | V_PMID | C16 | 2.67mm |
| U2 | +1.8V | C18 | 2.54mm |
| U6 (BQ27220 fuel gauge) | V_BAT | C21 | 1.65mm |
| U6 | VCC | C19 | 2.25mm |
| U15 (ADAU1860) | V_LS | C33 (10µF) | 2.01mm |
| MDBT531 + U15 (shared) | +1.8V | C1 (1µF) | 5.17–5.91mm |

Charger and fuel-gauge decoupling is tight and looks good across the
board — consistently ~1.6–2.9mm, no red flags. The shared digital `+1.8V`
rail feeding both the nRF5340 module and the ADAU1860 is comparatively far
from its nearest cap (~5.2–5.9mm) — not egregious, and the MDBT53 module
likely has some decoupling built in on its own carrier PCB already (typical
for this class of pre-certified module), but worth a closer look given this
rail also feeds a sensitive audio codec's digital supply. `DAC_P`/`DAC_N`
(the codec's differential audio output pair) have no nearby caps at all —
this is **not** automatically a problem the way rail decoupling is; these
are signal lines, not supply rails, so "no decoupling cap" doesn't mean
the same thing here. Whether they need an AC-coupling or filter cap is a
signal-path design decision for whoever owns the analog output stage, not
a decoupling-proximity issue.

### 3.4 The two original trace-width callouts

- **"No ground pad, as wide as possible"** — see §3.2. High confidence
  this refers to the MDBT53 antenna keepout (Raytac's own phrasing), not a
  separate item. Not implemented in the current port.
- **HPVDD/HPVDD_L wide headphone-supply traces** — **could not locate
  this net anywhere in the parsed data.** There is no net literally named
  `HPVDD` or `HPVDD_L` in the 85-net list extracted from the real board.
  I checked the PCB layer's own free-text annotations (`STRING` records —
  there are only 9 in the whole file) in case this was a schematic
  comment rather than a formal net; all 9 turned out to be silkscreen
  labels for the battery/speaker connector (`B+`, `B-`, `S+`, `S-`, `IN`,
  `OUT`, `LR`, `B`) and a board revision mark (`v2.0`), not this callout.
  The closest functionally-related net is `DAC_P`/`DAC_N` (the codec's
  differential audio output), which does use somewhat-wider-than-minimum
  traces in places (0.127–0.2mm vs. the board's 0.09mm baseline signal
  width — for comparison, the widest power/ground traces on the board run
  0.25–0.257mm) but not a single consistent "as wide as possible" width
  throughout the net. **I can't confirm or deny whether the port respects
  this specific callout — I genuinely don't have parseable evidence of
  what net it refers to.** This needs whoever originally read it off the
  live EasyEDA schematic (visually, not from the `.epro` export) to point
  at the actual net name or trace run in question.

### 3.5 Manual review checklist for the I2S bus and ADAU1860 analog lines

Given everything above, here's what a human should walk through by hand,
roughly in priority order:

1. **Antenna keepout first** — before anything else gets fixed, either
   send the layout to Raytac's free review service or get the exact
   keepout dimension from the datasheet's diagram (needs real PDF
   rendering, unavailable here) and clear the `GND` pour on layers 15/16
   under and around the module accordingly. This is the one finding here
   that materially affects RF certification/range, not just signal
   integrity.
2. **Resolve the DIN/DOUT direction question (§1)** against the ADAU1860's
   actual register-configuration for its serial port 0, not just its
   default pin names, before trusting either the overlay's comment or my
   flagged discrepancy.
3. **Confirm the ADAU1860's real AGND/DGND pin split** from ADI's own
   datasheet or reference layout, then decide whether this board actually
   needs a split ground plane or whether the single-plane approach the
   stock design uses is acceptable for this application's audio quality
   bar.
4. **Check the `+1.8V` decoupling distance** (~5.2–5.9mm to nearest cap)
   against the ADAU1860's datasheet recommended decoupling proximity —
   if ADI specifies something tighter, this rail may need an additional
   local cap near the codec rather than relying on the shared one.
5. **Re-examine `DAC_P`/`DAC_N`** against the real analog output stage
   design intent (headphone amp? line-out? passive filter?) — confirm
   whether these need explicit filter/AC-coupling caps that aren't present
   in this port, and separately track down the real "HPVDD/HPVDD_L"
   callout from wherever it was originally read.
6. **Double check the unused ADAU1860 second serial port and `DMIC23`
   pin** (§1, §2) — confirm leaving them floating (vs. a defined pull) is
   the ADAU1860's recommended handling for unused MPx pins.
7. Only after 1–6: general DRC/ERC pass in real KiCad once available,
   which will catch anything mechanical this text-only review can't see
   (clearance violations, footprint courtyard overlaps, etc.).

---

## Summary of confidence levels

| Finding | Confidence |
|---|---|
| I2C1/I2S net names & pin numbers match overlay | Tool-verified |
| DIN/DOUT direction discrepancy vs. overlay | **Resolved (§0.2)** — `DIN` is nRF→codec, overlay comment was backwards; matches upstream OpenEarable pinctrl |
| nRF5340 is I2S master, codec is slave | **Resolved (§0.2)** — from upstream pinctrl/DTS; overlay's slave-mode inference was wrong |
| Codec power sequencing (`DAC_ENABLE`, `V_LS` load switch) | Netlist + upstream driver (§0.3) |
| Mic is PDM into the codec; nRF not on the audio path | Tool-verified from netlist (§0.3) |
| No analog/digital ground split | Tool-verified; same as the shipping stock board, so lower urgency (§0.3) |
| Antenna keepout guidance (Raytac quote) | Sourced from real datasheet search — exact mm dimension NOT obtained (PDF unrenderable here) |
| Antenna keepout not implemented in this port | Tool-verified (point-in-polygon against real pour data) |
| Decoupling cap distances | Tool-verified (measured from real placement data) |
| HPVDD/HPVDD_L identity | Unresolved — not in parsed data, not in upstream firmware either (§0.4) |
| "No ground pad" = antenna keepout, not an exposed-pad note | High-confidence inference, not certain |
| U1 (IMU) is actually BMI160, not BMX160 | Wiring inspection says BMI160 (§8); upstream firmware says BMX160 (§0.5) — **check the physical part before ordering** |

---

## 8. U1 resolved: BMX160 label vs. BMI160 sourced part

Previously flagged (BOM `U1` row) as a genuine discrepancy: the schematic's
own component value said `BMX160` (Bosch 9-axis IMU, has an on-die
magnetometer) while the sourced Manufacturer Part was `BMI160` (6-axis,
accel+gyro only, no magnetometer) — a real difference, not a typo, since
both are legitimate distinct Bosch part numbers. Both share the same
LGA-14 (3.0×2.5mm, 0.5mm pitch) package and pinout, so footprint alone
can't disambiguate them.

**Resolved by checking the actual net connections at U1's pins 2/3
(`ASDX`/`ASCX`)** — BMI160's auxiliary sensor interface, meant for wiring
an *external* magnetometer (e.g. a companion BMM150) when one is wanted.
In this schematic those two pins are tied to `GND`. Grounding an unused
aux interface is BMI160's own documented reference-design pattern for "no
external magnetometer connected." BMX160 has no analogous *external*
aux-magnetometer pins to ground in the first place — its magnetometer is
on-die, using that same physical interface internally — so grounding them
is specifically a BMI160-without-magnetometer configuration, not a valid
way to wire a BMX160.

**Fix applied**: schematic `Value` property for U1 corrected from `BMX160`
to `BMI160` (both the library symbol definition and the placed instance)
to match the part that's actually wired and actually sourced. `HAVEN_BOM.csv`
updated to match, with its discrepancy note replaced by this resolution.
Net effect: no magnetometer is present on this board as wired — nothing
in Haven's firmware currently expects one, so this doesn't change any
functional behavior, only fixes the part-number inconsistency before a
production order could lock in the wrong label.

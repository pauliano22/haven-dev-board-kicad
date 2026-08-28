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
| DIN/DOUT direction discrepancy vs. overlay | Tool-verified data, inference-level conclusion (genuinely needs datasheet/register check) |
| No analog/digital ground split | Tool-verified |
| Antenna keepout guidance (Raytac quote) | Sourced from real datasheet search — exact mm dimension NOT obtained (PDF unrenderable here) |
| Antenna keepout not implemented in this port | Tool-verified (point-in-polygon against real pour data) |
| Decoupling cap distances | Tool-verified (measured from real placement data) |
| HPVDD/HPVDD_L identity | Unresolved — genuinely could not locate in parsed data |
| "No ground pad" = antenna keepout, not an exposed-pad note | High-confidence inference, not certain |
| U1 (IMU) is actually BMI160, not BMX160 | Resolved by wiring inspection — see §8 below |

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

---

## 9. Board rescale + autoroute: why ~93 nets remain unrouted

After rescaling the board 5x (see `feature/board-rescale-and-route`) and
routing with Freerouting (a real autorouter, not hand-placed traces), 93
of 304 nets remain unrouted. This section documents *why*, since it's a
real, reproducible finding, not an unexplained gap.

**Tool-verified, via three independent attempts**: a fresh autorouter run
with default settings (prioritized selection, greedy optimization)
converges to exactly 93 unrouted / 2 violations. A second fresh run with
different settings (random selection, global optimization) converges to
the *identical* 93 unrouted / 2 violations / identical score. Re-feeding
an already-routed board back into the router — with or without locking
the existing traces as fixed — made results *worse* (142-143 unrouted),
not better, in every attempt. Two structurally different search
strategies landing on the exact same outcome, while every attempt to
build on partial progress regresses, is strong evidence this is a real
structural ceiling, not an under-explored search space.

**Root cause, tool-verified**: the unrouted connections concentrate
overwhelmingly on the board's finest-pitch packages:

| Component | Package | Pitch | Share of unrouted connections |
|---|---|---|---|
| U15 (ADAU1860) | BGA-56 | 0.35mm | 37% |
| U2 (charger) | DSBGA-25 | 0.40mm | 20% |
| MDBT531 (nRF5340 module) | 65-pin castellated | 0.50mm | 24% |
| U10 | UQFN-16 | 0.40mm | 13% |
| CN1 | FPC connector | 0.35mm | 11% |

(Percentages overlap since some connections involve two of these parts.)

Escaping a 56-ball BGA at 0.35mm pitch — getting a trace out from a ball
buried in the middle of the grid, surrounded on all sides by other balls
— is a well-known hard problem in PCB layout. The standard solution is
via-in-pad (a microvia drilled directly through the pad itself, dropping
straight to an inner layer) or careful hand-placed dogbone escapes,
neither of which a generic autorouter's default via rules reliably
produces. This board's current via spec (drill 0.15mm / pad ~0.25-0.3mm,
see the earlier via-geometry fix) is in the right size range for
via-in-pad on a 0.35mm pitch part, but placing them correctly under
specific balls is a targeted, chip-by-chip task, not something bulk
autorouting handles well by default.

**What this means practically**: the remaining ~93 connections need
either (a) a human doing manual escape routing for these five specific
fine-pitch parts in KiCad's interactive router — a normal, bounded PCB
layout task, likely 30-60 minutes of focused work given the board now
has generous surrounding space — or (b) confirming the fab can support
via-in-pad at this pitch and re-running the router with that explicitly
modeled. It is *not* something further autorouter attempts are likely to
resolve; that's been directly tested, not assumed.

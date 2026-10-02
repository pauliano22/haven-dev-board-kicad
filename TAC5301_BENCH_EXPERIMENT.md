# TAC5301-Q1 bench latency experiment — the thing the evaluation doc said to do before trusting the PCB

`TAC5301_EVALUATION.md` (branch `docs/tac5301-q1-evaluation`) picked TAC5301-Q1 over the
AIC3254 based on datasheet-table arithmetic, not a measurement, and said explicitly: *"Before
any schematic work: confirm real hear-through latency and that the 3+2 (or 3+3) band split
sounds and measures correctly before committing PCB time to it."* That didn't happen before the
`redesign/tac5301-codec-swap` branch's schematic/PCB work went ahead. This is that experiment,
designed for real — a minimal breadboard loopback, not a eval-board purchase (TI doesn't sell a
dedicated EVM for this part), using a real register sequence pulled directly from the datasheet
(SLASFD9A, fetched and read in full this pass — not inferred from the summary tables the
evaluation doc cited).

**Cost: ~$10-15 in parts, all already on hand or trivial to source. Time: an afternoon, not a
week — most of the "cheap experiment" cost in the original architecture memo was the AIC3254
EVM purchase, which this avoids entirely.**

## What this proves or disproves

1. **Real hear-through latency**, measured, not computed from filter-delay tables. The
   evaluation doc's ~120-190µs is worst-case-pairing arithmetic from Tables 6-32–6-36 (ADC) and
   6-56–6-60 (DAC) — add the two group-delay-in-samples figures, divide by fS. A measurement
   also catches anything the arithmetic can't: analog path delay, ADC/DAC conversion overhead
   not captured in the "filter" group delay alone, and PCB-level surprises.
2. **Whether the loopback mixer path actually works as the register map describes** (Figure
   6-61: ADC output → loopback mixer → DAC's own processing chain, entirely inside the chip, no
   ASI/I2S round-trip needed for the audio itself — only BCLK/FSYNC need to toggle to keep the
   PLL locked).

This experiment does NOT test the 3+3 biquad coefficient split (notch-filter correctness) —
that's a second, separate bench step once the base loopback path is confirmed working, using
Haven's actual 5-band coefficients instead of the unity/passthrough default. See "Phase 2" below.

## Real parts list (verified against the actual datasheet this pass)

| Part | Role | Notes |
|---|---|---|
| TAC5301QRGERQ1 | DUT | Confirmed 2,834 in stock at Mouser, $1.07-1.61/unit (see `docs/tac5301-q1-evaluation` branch) |
| nRF5340 DK | I2C master + I2S/BCLK clock source | Already on hand per the architecture memo's own Step 1 — no new purchase |
| CMA-4544PF-W | Analog electret mic | Same part already in the real schematic (U-whatever on `redesign/tac5301-codec-swap`) — pull one off that BOM, don't buy a second design |
| A small speaker or headphone driver | Audio output | Anything 8-32Ω, doesn't need to be the final earpiece driver |
| VQFN-24 0.5mm breakout/adapter board | Hand-solder or reflow the TAC5301 onto something breadboard-pitch | **This is the one real risk item** — 0.5mm QFN is not hand-solderable with an iron reliably; either get a QFN-24 breakout PCB (common, ~$2-5, many sellers) and reflow/hot-air it on, or find someone with a hot-air/reflow setup. Don't attempt it with just an iron and solder wick. |
| HVDD supply, 7.5V (MICBIAS default) to ~9V | Bench power supply or the boost converter already designed this session | A bench supply set to 9V is simplest for this test — don't need the real TPS61040 boost circuit for a bring-up bench test |
| IOVDD/AVDD/DVDD (1.8V/3.3V as the datasheet's power table specifies) | Digital/analog supply rails | Bench supply or an existing 3.3V/1.8V LDO breakout |
| Decoupling caps per pin | Per datasheet layout guidance | Standard 0.1µF/pin practice — same as every other codec bring-up in this project's history |

## Real wiring (from the actual datasheet, this pass)

- **Mic input**: CMA-4544PF-W's output pin → AC-coupling cap → TAC5301's IN1P (single-ended
  mode), IN1M grounded after its own AC-coupling cap (datasheet §6.3.3, Figure 6-18,
  "AC-Coupled Microphone... Single-ended Input Connection" — exactly the CMA-4544PF-W bias
  circuit already designed on the real board this session, just without the extra hop through
  R29/C50/C51/C52's specific component values — a simpler bench version is fine for this test).
- **DAC output**: OUT1P/OUT1M → speaker/headphone driver, differential or single-ended per
  datasheet §6.3.4 (mirrors the input side).
- **MICBIAS**: pin sourced from HVDD per the datasheet's mic-bias circuit (§6.3.6) — this is the
  same architecture as the real board's TPS61040 boost converter, just substitutable with a bench
  supply at this stage.
- **I2C**: SDA/SCL to the nRF5340 DK's TWI pins. **7-bit I2C address is 0x50** (datasheet §6.4.1,
  "the 7-bit I2C target address is fixed to 7'b1010000" — confirmed directly, not assumed).
- **BCLK/FSYNC**: from the DK's I2S peripheral, running continuously at BCLK = 256×fS (datasheet
  §6.3.2: the device's PLL auto-configures every internal clock from the BCLK/FSYNC ratio, no
  external crystal or MCLK pin needed — confirmed directly from the datasheet text, this is a
  real simplification the evaluation doc didn't know to mention). For fS = 48kHz: BCLK =
  12.288MHz, FSYNC = 48kHz. **No real I2S audio DATA needs to be transmitted** — see below.

## The actual I2C init sequence (every address verified against the real register map, SLASFD9A §7)

The datasheet's register space is paged (§7.1: "Page 0" = §7.1.1 register group, "Page 1" =
§7.1.2 register group, confirmed by matching each section's own heading, e.g. "7.1.1 TAC5301-Q1
_B0_P0 Registers" = Page 0). Register 0x00 on every page is the page-select register,
write-before-use.

**One real, useful finding from reading the actual reset values (not just the field
descriptions): several of the registers this test needs are already correct at power-on reset**,
which makes the real minimal sequence shorter than the evaluation doc could have anticipated:

| Step | Page | Reg (hex) | Name | Value | Why |
|---|---|---|---|---|---|
| already default | 0 | — | `CH_EN` (0x76) | reset = `0xCC` | IN_CH1_EN, IN_CH2_EN, OUT_CH1_EN, OUT_CH2_EN all already enabled (datasheet §7.1.1.86) — **no write needed** |
| already default | 0 | — | `ADC_BQ1..3`, `DAC_BQ1..3` coefficients | reset N0 = `0x7FFFFFFF`, N1/N2/D1/D2 = `0` | This is a unity-gain passthrough biquad (H(z) = 1) at reset, per the register map's own listed reset values (§7.2.1-7.2.4 tables) — **the chip ships configured for clean passthrough on all 6 biquad slots**, so Phase 1 of this test (raw loopback latency) needs zero coefficient writes |
| 1 | 0 | `0x50` | `ADC_CH1_CFG0` | `0x40` | bits[7:6]=01 (single-ended analog input, matching the CMA-4544PF-W wiring), bits[3:2]=00 (AC-coupled, default) |
| 2 | 0 | `0x72` | `DSP_CFG0` | `0x9C` | **Corrected from an earlier draft of this doc**, which only set bits[7:6] and missed bits[3:2]. Full register (§7.1.1.84, Table 7-86): bits[7:6]=`10`b ultra-low-latency ADC decimation filter; bits[5:4]=`01`b (reset default, 1Hz HPF — left alone); **bits[3:2]=`11`b, 3 biquads per ADC channel** (reset default is `10`b = only 2/channel — doesn't affect Phase 1 since the extra slot is still unity at reset, but Phase 2 needs this bit set to reach all 3 bands) |
| 3 | 0 | `0x73` | `DSP_CFG1` | `0x9C` | Same correction, DAC side (§7.1.1.85, Table 7-87): bits[7:6]=`10`b ultra-low-latency DAC interpolation filter; bits[5:4]=`01`b (reset default HPF, left alone); **bits[3:2]=`11`b, 3 biquads per DAC channel** |
| 4 | 0 | `0x2C` | `MIXER_CFG0` | `0x10` | bit4 `EN_LOOPBACK_MIXER`=1, everything else 0 — **this also keeps `EN_DAC_ASI_MIXER` (bit7) at its reset-default 0**, meaning the DAC hears *only* the loopback path, nothing from the (unused) I2S data stream, which is why no real ASI audio data needs to flow for this test |
| 5 | 0 | `0x78` | `PWR_CFG` | `0xE0` | bit7 `ADC_PDZ`=1, bit6 `DAC_PDZ`=1, bit5 `MICBIAS_PDZ`=1 — power up ADC, DAC, and the mic bias together |
| optional | 1 | `0x73` | `MICBIAS_CFG` | `0xA0` (reset default) | MICBIAS_VAL=1010b=7.5V is already the reset value — only write this if a different mic-bias voltage is wanted |

That's **5 register writes** for a working ADC→loopback→DAC passthrough path (plus the implicit
page-0 default, since page 0 is also the reset state — no page-select write needed unless you've
touched page 1 first for the optional MICBIAS_CFG write, in which case write `0x00`=`0x00` to
return to page 0 before the above).

## Procedure

1. Wire the breadboard per above. Power up IOVDD/AVDD/DVDD per the datasheet's supply sequencing
   notes (§6.4), then HVDD last (mic bias only needs to be live once MICBIAS_PDZ is set, step 5).
2. Start BCLK/FSYNC toggling from the nRF5340 DK *before* sending the I2C sequence — the PLL
   needs a running clock to lock onto (§6.3.2).
3. Send the 5-write sequence above over I2C.
4. **Reuse `haven-zephyr-app/tools/calibration/measure.py` directly, standalone** — it has no BLE
   dependency (confirmed by reading it this pass: `click()` and `delay_seconds()` are pure
   numpy/scipy, `SoundDeviceIO.play_and_record()` is a thin `sounddevice` wrapper). Skip the
   `Rig`/`HavenSession` orchestration layer entirely (that's BLE-coupled to the real Haven
   firmware, which doesn't exist for this part yet) and call the measurement functions directly:
   ```python
   import sys; sys.path.insert(0, "path/to/haven-zephyr-app/tools/calibration")
   from measure import click, delay_seconds
   from audio_io import SoundDeviceIO
   # same open-ear-reference / in-ear-hear-through structure as latency.py's run(),
   # just without the BLE bypass toggle -- the TAC5301 IS the hear-through path,
   # continuously, once the 5 writes above are sent.
   ```
5. Compare the measured device latency against the evaluation doc's ~120-190µs estimate and the
   300µs comb-filter threshold from `HARDWARE_ARCHITECTURE_DECISION.md`.
6. **While the breadboard is already wired and powered, measure real current draw** (multimeter
   in series on the AVDD/HVDD/IOVDD supplies, or a USB power meter if those rails are bench-
   supplied from one source) during the hear-through test. This is nearly free to add to the same
   session and settles a real, previously-undocumented finding: the datasheet's own tables put
   TAC5301-Q1's hear-through current meaningfully higher than the ADAU1860's (see
   `POWER_BUDGET.md`'s 2026-10-01 update) — a real measurement replaces that bracketed estimate.

## Phase 2 (only if Phase 1 passes): the actual notch-filter coefficients

Once raw loopback latency is confirmed acceptable, repeat with Haven's real 5-band biquad
coefficients split across the two biquad banks (the evaluation doc's open question —
"whether the 3+3 loopback split can actually implement 5 independent notch/peaking bands,"
reasoned through on paper but not bench-verified) instead of the reset-default unity
coefficients.

**A real correction to the evaluation doc's assumption, found reading the full register map this
pass**: the 3 biquads allocated to a channel in "3 biquads per channel" mode are **not** a
contiguous block (filters 1, 2, 3) — they're interleaved across the device's 4-channel-capable
biquad bank (§6.3.7.1.5 Table 6-17 / §6.3.7.2.4 Table 6-41): channel 1 (the only channel this mono
part uses) gets **filters 1, 5, and 9**, with filters 2/3/4, 6/7/8, 10/11/12 reserved for channels
2-4 (unused here). Concretely, for Haven's mono hear-through path:

| Biquad | Page/registers (ADC) | Page/registers (DAC) |
|---|---|---|
| Channel-1 biquad A (filter 1) | Page 8, R8-R27 | Page 16, R8-R27 |
| Channel-1 biquad B (filter 5) | Page 8, R88-R107 | Page 16, R88-R107 |
| Channel-1 biquad C (filter 9) | Page 9, R48-R67 | Page 17, R48-R67 |

(Table 6-18 / 6-42 give the full filter→register mapping if a different split is ever wanted.)
Writing to filters 2/3/4/etc. would silently do nothing for this mono part — a real bug this
correction heads off before anyone wires up the wrong registers.

This needs the actual Q-format coefficient math from the existing `haven-zephyr-app`
ADAU1860 driver's band-to-biquad conversion, re-targeted at this chip's coefficient byte layout
(§7.2.1-7.2.4 register tables — 4-byte big-endian fields per N0/N1/N2/D1/D2 coefficient per
20-register block). The reset value `0x7FFFFFFF` for N0 (unity) matches two's-complement Q1.31
(2³¹-1 = 0x7FFFFFFF ≈ +1.0, the closest Q1.31 can represent to exact unity) — a reasonable,
evidence-based inference, not confirmed by an explicit "Q1.31" statement anywhere in this
datasheet, so verify against §6.3.7.1.5/6.3.7.2.4 or a real coefficient readback before trusting
it for a safety-relevant filter.

## What this doesn't settle

- Real supply sequencing edge cases (brown-out behavior, `BRWNOUT` register at 0x2E) — not
  needed for a bench bring-up, worth reading before a real product power-up sequence.
- PCB-level crosstalk/noise that a breadboard won't reproduce — the real board's layout (already
  routed, this session) is denser than a breadboard, so a clean bench measurement is necessary
  but not sufficient proof the real PCB performs identically.
- Everything in Phase 2 above.

---

*Sources: TAC5301-Q1 datasheet SLASFD9A (Rev. A, April 2025 / revised April 2026), fetched and
read in full this pass — §6.3.2 (PLL/clock auto-config), §6.3.3/6.3.4 (input/output channel
config), §6.3.6 (mic bias), §6.3.7.1.7/6.3.7.2.5 (filter mode selection, Tables 6-19/6-43),
§6.4.1 (I2C address), §6.4.2 (software reset), §7.1.1 (Page 0 registers: CH_EN 0x76, ADC_CH1_CFG0
0x50, MIXER_CFG0 0x2C, PWR_CFG 0x78, P0_R114/P0_R115 filter-select at 0x72/0x73), §7.1.2 (Page 1:
MICBIAS_CFG 0x73), §7.2 (biquad coefficient register reset values). `TAC5301_EVALUATION.md`
(`docs/tac5301-q1-evaluation` branch) for the open items this experiment addresses.
`haven-zephyr-app/tools/calibration/measure.py`, `audio_io.py` for the reusable measurement math.

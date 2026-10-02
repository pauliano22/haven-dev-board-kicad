# Power budget — how long Haven runs on a charge

Written 2026-09-22. This is a design estimate, not a measurement — nothing has
run on real hardware yet. Numbers below are cited to a source or flagged as
unverified; nothing here is a guess dressed up as a fact.

## Per-component current draw

| Part | Mode | Current | Source |
|---|---|---|---|
| nRF5340 | BLE active, 0 dBm TX | 3.4 mA | [datasheet excerpt](https://robu.in/wp-content/uploads/2024/09/ISC_nRF5340_7002_A_Datasheet-.pdf) |
| nRF5340 | BLE active, RX | 2.7 mA | same |
| nRF5340 | idle / advertising gaps | low µA range | Nordic datasheet — exact figure not pulled this pass |
| ADAU1860 | active: 1 DAC + 1 ASRC + 32 FastDSP instr. at 192 kHz, no analog ADC (Table 6 rows 1–3 bracket Haven's config) | **3–8 mW quiescent** (≈ 1–2.5 mA battery-referred); **≈ 17 mW at 1 mW into 32 Ω** (≈ 5 mA) | ADAU1860 data sheet Rev. 0, Tables 6–7, pp. 9–10 — read 2026-09-29, see `ADAU1860_DATASHEET_NOTES.md` |
| PDM mic (SPH0641LU4H-1) | low-power mode | 235 µA | [Knowles datasheet](https://www.mouser.com/datasheet/2/218/-746191.pdf) |
| PDM mic | standard performance mode | 1 mA | same |
| BQ25120A charger | quiescent, buck enabled, no load | 700 nA | [TI datasheet](https://www.ti.com/lit/ds/symlink/bq25120a.pdf) |
| BQ27220 fuel gauge | NORMAL mode | 50 µA | [TI datasheet](https://www.ti.com/lit/ds/symlink/bq27220.pdf) |
| BQ27220 fuel gauge | SLEEP mode | 9 µA | same |

**Update 2026-09-29 — the ADAU1860 number is now from the datasheet**, and it
is small: 3–8 mW quiescent for Haven's configuration (Tables 6–7), rising to
≈ 17 mW only while driving 1 mW into a 32 Ω load. Battery-referred that is
≈ 1–2.5 mA idle and ≈ 5 mA at full output, not the 15–20 mA the paragraph
below feared. The codec no longer dominates; the mic's performance mode and
the output level matter as much. The scenarios below are updated with it.

## Two scenarios, with the ADAU1860 gap called out

**Continuous hear-through, BLE idle (the normal wearing state):**
mic (1 mA, or 0.235 mA in low-power mode) + ADAU1860 (1–2.5 mA
battery-referred, datasheet) + BQ27220 (0.05 mA) + BQ25120A (~0) ≈
**2–3.5 mA quiet hear-through**, ≈ **6–7 mA while the earpiece is actually
producing 1 mW** (loud). Regulator efficiency assumed ~85 %; nothing yet
measured.

**Active BLE connection (app open, adjusting settings):** add the nRF5340's
~3 mA on top of the above.

## Runtime by battery size (datasheet-based: ~3 mA quiet, ~7 mA loud)

| Cell capacity | Runtime at ~3 mA (quiet hear-through) | Runtime at ~7 mA (continuous loud output) |
|---|---|---|
| 40 mAh (small in-ear pouch cell) | ~13 h | ~6 h |
| 60 mAh | ~20 h | ~9 h |
| 100 mAh | ~33 h | ~14 h |

No specific battery cell is chosen yet in the BOM — only the charge/fuel-gauge
ICs and a connector. These sizes are typical for in-ear wearables, not a
recommendation until real current is measured.

## Charging

BQ25120A's fast-charge current is set by an external resistor/register, not
fixed — the schematic's ISET value decides it, and I didn't re-derive it from
the board files this pass. A 40–60 mAh cell at a typical ~0.5C small-cell
charge rate would take roughly 1–2 hours; confirm the actual ISET-programmed
current before quoting a number to anyone outside this project.

## Update 2026-10-01 — TAC5301-Q1 real power numbers (this redesign branch only)

The `redesign/tac5301-codec-swap` branch replaces the ADAU1860 with TAC5301-Q1. Read the real
datasheet (SLASFD9A) directly for its current-consumption table (§5.6) rather than estimating.
**This is a real, previously-undocumented tradeoff that matters as much as the latency
difference already written up elsewhere** (`TAC5301_EVALUATION.md`,
`TAC5301_BENCH_EXPERIMENT.md`): TAC5301-Q1 draws meaningfully more current than the ADAU1860 in
every comparable state.

| Configuration | IAVDD | IHVDD | IIOVDD | Rail voltages (test condition) |
|---|---|---|---|---|
| Sleep (software shutdown, all clocks stopped) | 9 µA | 0.01 µA | 1 µA | — |
| MICBIAS on (10V, 30mA-capable), ADC off | 1.6 mA | 1.1 mA | 0.02 mA | AVDD=IOVDD=3.3V, HVDD=11V |
| ADC 1-ch + MICBIAS on, PLL off, 48kHz | 5.7 mA | 1.1 mA | 0.3 mA | same |
| ADC 1-ch + DAC-to-HP 1-ch, MICBIAS **off**, PLL off, 48kHz | 24.5 mA | 1.1 mA | 0.3 mA | same |

No row in the datasheet covers Haven's actual operating point (ADC + DAC + MICBIAS all
simultaneously active, which is what continuous hear-through needs) — TI defers that to a
separate "Power Consumption Matrix Across Various Usage Scenarios" application report, not
fetched this pass. **Bracketing like the ADAU1860 entry above does** (add the isolated
MICBIAS current, ~1.6 mA, onto the ADC+DAC row, since the two conditions don't appear to double-
count the same current path): **≈26 mA IAVDD** for full hear-through at 48kHz, PLL off.

Power-referred at the datasheet's own test rails (AVDD/IOVDD=3.3V, HVDD=11V — note Haven's real
board targets HVDD≈9V via the TPS61040 boost converter designed this session, not 11V, so this
overstates the HVDD contribution slightly):

- Idle (MICBIAS on, ADC/DAC off): ≈(1.6×3.3 + 1.1×11 + 0.02×3.3) ≈ **17.5 mW**
- Full hear-through (ADC+DAC+MICBIAS, PLL off): ≈(26.1×3.3 + 1.1×11 + 0.3×3.3) ≈ **99 mW**

Battery-referred (3.7V cell, ~85% regulation efficiency, same assumption as the ADAU1860 figures
above): **≈5.5 mA idle, ≈31.5 mA full hear-through** — compare to the ADAU1860's real, datasheet-
verified **≈1–2.5 mA idle, ≈5 mA loaded** (`ADAU1860_DATASHEET_NOTES.md`). That's roughly
**2-6x more current** at every comparable point, not a rounding difference.

**Caveats, stated plainly**: these two chips' tables use different test conditions (the ADAU1860
table's "loaded" row is 1mW into 32Ω at PLL presumably on and 192kHz FastDSP running; the
TAC5301 rows above are PLL *off* at 48kHz, which is the lower-power option — PLL *on* would be
higher still, and Haven's design may need PLL on depending on whether the nRF5340's I2S BCLK
output lands on an exact multiple the TAC5301 can use without it). This is a real, substantial,
previously-missing data point for comparing the two codec choices — not just a latency tradeoff,
a battery-life one — and should be measured for real as part of `TAC5301_BENCH_EXPERIMENT.md`
(a current-draw reading during the loopback test is nearly free to add to that same bench setup).

## What to do next

1. ~~Open the ADAU1860 datasheet and read its active-mode current table.~~
   Done 2026-09-29 (`ADAU1860_DATASHEET_NOTES.md`). Still open: the DMIC
   decimator's own draw is not tabulated; measure it.
2. Once real hardware exists, measure actual current with a multimeter or a
   power profiler (Nordic's Power Profiler Kit works well with the nRF5340) —
   this whole document is a placeholder for that measurement, not a
   substitute for it.
3. Pick a battery cell size once the real current number is in, sized against
   a target runtime (e.g., "one full day of wear" or "8-hour workday").

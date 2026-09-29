# ADAU1860 datasheet — the numbers this project had been guessing at

Read 2026-09-29 from the ADAU1860/ADAU1860-1 data sheet, **Rev. 0, 30 pages**
(Analog Devices, `analog.com/media/en/technical-documentation/data-sheets/adau1860.pdf`).
Every earlier document in this repo and in `haven-zephyr-app` said "not
datasheet-verified" because the PDF could not be fetched; this file records
what the datasheet actually says, with page numbers, so those caveats can be
retired one by one. Only the datasheet is used here — no register map, no
forum posts. The register-level facts (route numbers, safeload, STATUS2 bits)
live in the separate hardware reference manual, which was **not** read, so
they stay "matches upstream firmware", not "datasheet-verified".

## 1. Power (Table 5, 6, 7 — pages 9–10)

Test conditions for Tables 6/7: MCLK 24.576 MHz external, PLL bypassed,
DVDD 0.9 V, AVDD = HPVDD = IOVDD = 1.8 V, FastDSP at 192 kHz (27-bit biquads),
DAC at 192 kHz, one serial port as slave, 32 Ω headphone load, no signal.

| Configuration (Table 6 row) | AVDD+HPVDD | DVDD | IOVDD | Power |
|---|---|---|---|---|
| 0 ADC, 1 DAC, 1 ASRCI, 0 FastDSP instr., 13 EQ filters | 0.99 mA | 1.09 mA | 0.15 mA | 3.0 mW |
| 2 ADC, 1 DAC, 1 ASRCI, 32 FastDSP instr., 13 EQ | 2.18 mA | 2.54 mA | 0.15 mA | 6.5 mW |
| 3 ADC, 1 DAC, 1/3 ASRC, 32 FastDSP instr. | 2.58 mA | 3.04 mA | 0.315 mA | 8.0 mW |
| Table 7 "ANC phone call", normal perf., no load | 2.58 mA | 3.06 mA | 0.316 mA | 7.97 mW |
| Table 7 same, **1 mW into 32 Ω headphones** | 7.41 mA | 3.06 mA | 0.316 mA | 16.66 mW |
| Power-down, PD pin low (Table 5) | 6.6 µA | 56.9 µA | 2.6 µA | ≈ 0.07 mW |

Power column = Σ(I × V) at the stated rails (computed here; Table 7's own
"Total Power" column gives 7.97 / 16.66 mW for the last two rows, which
matches).

**Haven's operating point** — PDM mic (no analog ADC/PGA), one DAC, one
ASRC input (nRF I2S, only needed during tones), ~32 FastDSP instructions at
192 kHz, DMIC decimator — is not a listed row. It is bracketed by rows 1 and
3: **≈ 3–8 mW quiescent, ≈ 17 mW while actually driving 1 mW into the
earpiece.** Referred to a 3.7 V cell through ~85 %-efficient regulation that
is **≈ 1–2.5 mA idle hear-through, ≈ 5 mA at 1 mW output.** The codec is
therefore *not* the battery-life problem `POWER_BUDGET.md` feared
(15–20 mA); the PDM mic in standard-performance mode (1 mA) and the
headphone output level matter as much.

## 2. Latency (Table 8, page 11; features, page 1)

- Analog in → analog out group delay: **12.9 µs at fS = 192 kHz**, 7.5 µs at
  384 kHz, 5 µs at 768 kHz (Table 8). Haven's path is DMIC → FastDSP → DAC,
  which adds the DMIC decimator; the datasheet does not tabulate that path,
  so treat "tens of microseconds" as the expectation, to be measured with
  the `tools/calibration` latency procedure. This is three orders of
  magnitude under the ~1 ms comb-filter threshold — the whole reason the
  codec stays in the loop.
- ASRC start-up time to lock: **25 ms max** (Table 8). The firmware's
  power-up wait and STATUS2 `ASRCI_LOCK` poll should allow at least this.

## 3. Things the board already does right, now with a citation

- **Bypass capacitors (page 29, "Power Supply Bypass Capacitors")**: one
  0.1 µF per supply pin to the nearest ground pin, connections as short as
  possible, *single layer, no vias*, plus one 10–47 µF bulk per supply.
  This is exactly what issue #4 / PRs #5 and #7 restored after the 5×
  rescale had moved the caps 8–50 mm away.
- **HPVDD_L (pin D1, page 26; Layout, page 29)**: decouple with **10 µF** to
  HPGND; the trace to HPVDD/HPVDD_L "must be wider than the traces to the
  other pins". C33 (10 µF, 1.9 mm from the pins after #5) satisfies the
  first; the 0.09–0.2 mm V_LS traces noted in `ORDER_README.md` do not
  satisfy the second. Low risk at in-ear power (the 7.4 mA of Table 7 is a
  32 Ω load at 1 mW), acceptable for the bench board, fix on the wearable.
- **Grounding (page 29)**: "Use a single ground plane" — the unified GND the
  review flagged as risk A8 is what the datasheet asks for.
- **PD pin (page 26)**: floating PD holds the chip in power-down — the
  `DAC_ENABLE` (nRF P0.04 → E4) drive in the firmware is required, not
  optional.

## 4. One thing to check: crystal load capacitance (Table 2, page 8)

The crystal amplifier is specified for **1–36 MHz** and a **maximum load
capacitance of 20 pF**. The board uses two 33 pF caps (C45/C46), which
present 33/2 = 16.5 pF plus stray/pin capacitance (typically 2–5 pF) ≈
19–22 pF — right at the limit. The stock OpenEarable 2.0 uses the same
values and oscillates, so this is a **check**, not a defect: if the codec
crystal fails to start at bring-up (`POWER_UP_COMPLETE` timeout with the
I2C ID read working), drop C45/C46 to 22 pF before suspecting anything
else. The crystal's own CL rating (HUAXIN CN4024M57620001) was not found.

## 5. Firmware constants confirmed

- DAC digital gain: **0.375 dB steps, −71.25 to +24 dB** (Table 1, page 5) —
  matches `CONFIG_HAVEN_OUTPUT_CEILING_DB` / `DAC_VOL0` math in
  `haven-zephyr-app` PR #14 (dB = 24 − 0.375 × code).
- DAC volume ramp rate 4.5 dB/ms — a mute/unmute or ceiling change settles
  in ≈ 20 ms; the tone path's fade timing can rely on this.
- FastDSP biquads are 27-bit-precision (pages 10, 15) — consistent with the
  Q5.27 coefficient format proven from the upstream banks in PR #8.
- DMIC clock rates characterised at 3.072 and 6.144 MHz (Figures 41–44,
  page 22); the 6.144 MHz option is the one to use for a 192 kHz decimated
  path.
- Package: 56-ball, 0.35 mm pitch WLCSP, 2.980 × 2.679 mm (page 1) — the
  part that sets the fab tier, as `HARDWARE_COST_ALTERNATIVES.md` concluded.

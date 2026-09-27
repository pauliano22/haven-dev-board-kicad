# Hardware architecture decision: keep the codec in the loop, lose the BGA

*Response to `HARDWARE_COST_ALTERNATIVES.md` (2026-09-12). Written 2026-09-14.*

## The answer in one paragraph

The cost analysis is right and the conclusion is half right. The three fine-pitch packages (ADAU1860 0.35 mm BGA-56, BQ25120A 0.40 mm DSBGA-25, BQ27220 0.50 mm DSBGA-9) are what push the board into 6 layers, laser microvias and the "advanced" PCBA tier, and swapping them for QFN parts is the correct way to get a cheap board. But the ADAU1860 was not "the wrong chip for the codec role" — it was chosen (inherited, but correctly) because it is the mechanism for Haven's one hard physical requirement: hear-through latency well under a millisecond. Moving the biquads onto the nRF5340 (option C below) reintroduces I2S block buffering of **≥0.7–1 ms at the smallest practical block, and ~6–9 ms if done the way the Teensy prototype did it**, which puts comb-filter notches inside the speech band (derivation §3) and keeps the nRF CPU + I2S running continuously (**≈5.6 mA**, §4) instead of asleep. The Teensy prototype proved the *filter math*; its latency was never measured. There is a third option that satisfies both the physics and the cost: a QFN codec **with its own programmable DSP** — the TI **TLV320AIC3254** Paul already found in JLCPCB's catalog at $3.03 (VQFN-32, 5×5 mm, **0.5 mm pitch**, PDM mic input, two miniDSP cores each running up to **1,152 instructions per sample at 48 kHz**, plus fixed processing blocks with **5 programmable biquads** and a DRC). Recommendation: **option B (AIC3254 in the loop), with the charger swapped to a QFN/SOP power-path part and battery voltage read by the nRF's ADC instead of a fuel gauge** — and one cheap experiment first (§7) to pin the latency numbers this memo can only estimate.

## 1. The three options

| | **A — current** | **B — QFN codec with on-chip DSP** | **C — dumb codec, filter on nRF5340** (Paul's proposal) |
|---|---|---|---|
| Codec | ADAU1860 (BGA-56, 0.35 mm) — FastDSP owns mic→5 biquads→limiter→DAC at 192 kHz; nRF only writes coefficients | **TLV320AIC3254** (VQFN-32 5×5 mm, 0.5 mm) — miniDSP or fixed biquad blocks own the loop; nRF only writes coefficients | SGTL5000 / TLV320AIC3104 / AIC3254-as-dumb-codec (QFN) — ADC→I2S→nRF→I2S→DAC; nRF runs the biquads |
| Where the audio loop runs | inside the codec | inside the codec | through the MCU |
| Hear-through latency (§3) | converter delays only: est. **50–150 µs** (192 kHz path); FastDSP frame 5 µs | converter delays at 48 kHz: est. **0.5–1 ms** (TI publishes block group delays in SLAA408 — not fetched; 96/192 kHz modes would cut it); DSP adds ~0 | converter delays **+ I2S block buffering**: ≥ **0.7–1.0 ms** extra at 16-sample blocks, **2.7–4 ms** at 64, **5.8–8.7 ms** Teensy-style (128 @ 44.1 k) |
| Comb notches in 200–8000 Hz (§3) | 0 (first notch ≥ 3.3 kHz only if Δt ≥ 150 µs; none below 100 µs) | 0–1 if Δt ≤ 0.5 ms; up to 8 at 1 ms | 8 at 1 ms; ~47 at 6 ms |
| MCU power for audio (§4) | ~0 (nRF sleeps between BLE events) | ~0 | **CPU 3.3 mA @64 MHz + I2S 2.3 mA ≈ 5.6 mA continuous** (Nordic PS) |
| Codec power | unknown (datasheet not obtained); ADI markets the part for hearables | **4.1 mW playback + 6.1 mW record ≈ 10 mW** (datasheet p.1; both paths run in hear-through) | same class as B (converters still run) **plus** the MCU 5.6 mA |
| Unit BOM (codec) | consignment part, ~$5–10 (est.) | **$3.03** (JLC catalog, Paul) | $1.33 AIC3104 / SGTL5000 |
| Layers / vias / PCBA tier | 6 layers, laser microvias, advanced (~$500 / 5 boards, Paul's quote) | **plausibly 4 layers, standard vias, standard tier** (MDBT53 is 0.65 mm pitch) | same as B |
| Firmware chip-specific code to (re)write | exists: `adau1860_*`, `lark_*` ≈ 1,420 lines, compiles for both boards | new: AIC3254 register driver ≈ 400–600 lines (I2C register pages; no 32-bit addressing, no memory images unless miniDSP is used) | new: codec init ≈ 200 lines **+** an nRF DSP path (I2S RX/TX ring, biquad kernel, timing) ≈ 300–500 lines that must be real-time-safe |
| Firmware that survives unchanged | — | BLE, protocol, clamps, tone safety, NVS, GATT, acks, `tone_gen.c` (I2S master), calibration rig, app: ≈ 1,800 of 3,240 firmware lines + all tools + the whole app | same |
| DSP tooling | Lark Studio (Windows) for anything beyond coefficient writes | **none needed** for the fixed blocks (5 biquads + DRC are register-programmable, datasheet Tables 2/3); PurePath Studio (TI, access-controlled) only if the miniDSP is used | none (C code) |
| Hardware limiter (3rd safety layer) | FastDSP limiter slot (PR #14) | **DRC on ADC path, AGC / digital volume on DAC path** (datasheet p.1, p.31) — register-programmable | firmware only (a bug is a loud bug) |
| Sourcing risk | ADAU1860 + MDBT53 likely consignment at JLC/PCBWay | catalog part; MDBT53 still consignment | catalog part; MDBT53 still consignment |
| Time to first sound | firmware done; hardware = eval board $485 / OpenEarable €2,348 / this BGA board | **TLV320AIC3254EVM** exists (TI, ~$100–200) → DK + EVM bench; new schematic; ~1 week of driver work | as B plus the nRF DSP path and its latency debugging |

Confidence: package/pitch, instruction budget, PDM input, power figures and DRC/AGC for the AIC3254 are **verified** from the datasheet (SLAS549D: p.1, p.30–31, p.34, p.50). nRF5340 currents **verified** (product specification, "Current consumption"). Latency figures are **derived** (§3) from block sizes and the published block-processing model; converter group delays are **estimated** and must be measured. Costs are Paul's or JLC catalog figures.

## 2. Why the loop has to stay in the codec — the physics, restated

Hear-through only works if the processed sound and the sound that leaks past the eartip arrive together. If the processed path is late by Δt, the two add with a phase that rotates through frequency, producing comb-filter notches at

    f_k = (2k + 1) / (2·Δt),  k = 0, 1, 2 …

(notebook `01-acoustics-and-psychoacoustics.md`). For the 200–8000 Hz band Haven cares about:

| Δt | notches in band | first notch |
|---|---|---|
| 50 µs | 0 | 10 kHz |
| 150 µs | 2 | 3.3 kHz |
| 300 µs | 4–5 | 1.7 kHz |
| 1 ms | 8 | 500 Hz |
| 4 ms | ~32 | 125 Hz |
| 6 ms | ~47 | 83 Hz |

Anything above ~0.3 ms audibly colours speech; above ~1 ms it sounds like "two of everything". This is the requirement (R1 in `00-problem-breakdown.md`) that dictated a codec-resident DSP in the first place. It is also why the Teensy prototype, valuable as it was, does not settle the architecture: it validated the filters and the user experience of *notching*, but nobody measured its latency (there is no measurement in `haven-legacy-teensy`, `haven-legacy-dsp-sandbox` or the workspace docs — checked), and its block size makes the number predictable (§3).

## 3. Latency derivations

**Common to all options — converter group delay.** Sigma-delta ADCs and DACs use linear-phase decimation/interpolation filters whose delay is a fixed number of samples: at 48 kHz, tens of samples each way ⇒ roughly 0.3–0.6 ms per direction for ordinary codecs. The ADAU1860 runs its DMIC decimation and FastDSP at **192 kHz** (upstream `DMIC_CTRL2 = 0x04`, `FDSP_CTRL4 = 2`), so the same filter structures cost 4× less time — that is the specific reason option A's latency is estimated at 50–150 µs. The AIC3254 lists three interpolation filter types "depending on required frequency response, group delay and sampling rate" (p.31) and processing blocks "tuned for … low group delay" (p.30–31); the numbers are in TI's app note SLAA408, which was not fetched — **measure, don't assume**. At 96 or 192 kHz DAC/ADC rates (both supported, p.31) the AIC3254 figure would shrink accordingly.

**Option C adds block buffering.** Zephyr's nRF I2S driver (`drivers/i2s/i2s_nrfx.c`, NCS 3.4) is double-buffered EasyDMA: an RX block is delivered to the application only when it is full; the application processes it and queues a TX block, which starts playing at the *next* block boundary. Minimum end-to-end through the MCU is therefore about two block durations plus processing, three in practice with the TX queue depth the driver needs to avoid underrun ("Next buffers not supplied on time" is a hard error that stops the stream). Block size must be a multiple of 4 bytes; very small blocks mean interrupt rates the BLE stack has to coexist with.

| Block (samples @ 48 kHz) | block time | MCU path (2–3 blocks) | IRQ rate | + converters (~0.7 ms est.) |
|---|---|---|---|---|
| 16 | 0.33 ms | 0.67–1.0 ms | 3,000/s | **1.4–1.7 ms** |
| 32 | 0.67 ms | 1.3–2.0 ms | 1,500/s | 2.0–2.7 ms |
| 64 | 1.33 ms | 2.7–4.0 ms | 750/s | 3.4–4.7 ms |
| 128 @ 44.1 kHz (Teensy `AUDIO_BLOCK_SAMPLES`, `cores/teensy4/AudioStream.h:54`) | 2.9 ms | 5.8–8.7 ms | 344/s | **6.5–9.4 ms** |

So the Teensy prototype almost certainly ran at 6–9 ms — dozens of comb notches across the speech band. If it sounded acceptable, that is evidence the *user experience* was tested with music/voice sources in a quiet room rather than as transparent hear-through against leakage, or that the earpiece sealed well enough to suppress the leaked path. Either way it is not evidence that MCU-side filtering meets R1. The 16-sample case is the best C can do, and it is still ≥ 3× worse than B's converter-only estimate, at 3,000 interrupts per second forever.

**The CPU load itself is not the problem.** Five biquads on one channel at 48 kHz is ~2.5 MIPS in fixed point — trivial for a Cortex-M33 at 64 MHz. The problem is buffering latency and the fact that the CPU can never sleep.

## 4. Power

Nordic nRF5340 product specification, "Current consumption" (typ., 3 V, DC/DC on): CPU running from flash at 64 MHz **3.3 mA**; at 128 MHz **7.8 mA**; I2S transferring 2×16-bit at 48 kHz **2.31 mA**; System ON idle **1.3 µA**. Option C therefore holds the application core at ≈ **5.6 mA** (64 MHz) continuously, on top of the BLE stack. Options A and B leave the nRF in System ON idle between BLE events (advertising/connection events average tens of µA).

Codec side: AIC3254 **4.1 mW** stereo playback + **6.1 mW** stereo record at 48 kHz (datasheet p.1) — hear-through needs both, so ≈ 10 mW; mono and lower PowerTune classes (PTM_R1…) reduce it. ADAU1860: no figure obtainable here (datasheet unfetched); ADI positions it for hearables and OpenEarable runs it from an earbud battery, so assume the same class as the AIC3254 or better — **unknown**.

Battery: the OpenEarable 2.0 battery capacity is not stated anywhere in the upstream repo (the fuel-gauge default `capacity_mAh = 3000` in `BQ27220.h` is a placeholder); a typical earbud cell is 40–80 mAh. Taking **60 mAh** as a stated assumption and ≈ 6 mA for a codec in hear-through plus BLE:

- A/B: 60 mAh / ~6.5 mA ≈ **9 h**
- C: 60 mAh / ~12 mA ≈ **5 h**

Roughly, option C halves the wearable's battery life to buy nothing the user can hear except comb filtering. (Assumptions explicit; the codec numbers dominate and must be measured on the bench — the calibration rig PR #11 includes a battery-current line item for exactly this.)

## 5. Cost and manufacturability

Paul's measurements stand: ADAU1860 0.35 mm, BQ25120A 0.40 mm, BQ27220 0.50 mm pitch; MDBT53-1M 0.65 mm. Removing the three fine-pitch parts removes the need for laser microvias and (plausibly) two layers, and moves the job out of the advanced tier. Option B keeps that entire saving: the AIC3254 is a 0.5 mm-pitch VQFN-32 (datasheet p.50), catalog-stocked at JLC ($3.03), and the MDBT53 is fine as is.

Two things `HARDWARE_COST_ALTERNATIVES.md` does not yet account for:

1. **The BQ25120A is also the board's power supply.** Its integrated buck (L2, 2.2 µH) and LDO generate the **+1.8 V** and **3V3** rails (notebook `10-hardware-bom.md`, power tree). Replacing it with a TP4056 or MCP73831 — which are chargers only — means adding a regulator (e.g. a small buck or LDO for 1.8 V, plus the 3V3 rail if anything still needs it) and a load switch strategy for ship/storage. Not hard, but it is a new part and a new design task, not a drop-in.
2. **Battery telemetry.** True, nothing in the software reads the BQ27220 today. But a wearable without a battery percentage cannot warn the user, cannot protect the cell from deep discharge in firmware, and cannot implement ship mode (the BQ25120A's ~nA storage state). The cheap answer is not a QFN fuel gauge: it is a resistor divider (or the charger's battery pin) into the **nRF5340's SAADC** for voltage-based state of charge — good enough for "low battery", zero BOM cost — and a charger with a **power path** so the device runs from USB while charging. In increasing capability: TP4056 (SOP-8, linear 1 A, thermal regulation, no power path, no ship mode), MCP73831 (TDFN-8, 500 mA, no power path), **BQ24072/BQ24074** (QFN-16, power path/DPPM, no I2C) — the last is the one that behaves like a product.

## 6. The claims in `HARDWARE_COST_ALTERNATIVES.md`, one by one

- **"The cost isn't the board size … it's three specific chip packages."** Agreed, and well shown (measured pitch, flat assembly setup cost, laser-via finding).
- **"OpenEarable 1.3 is architecturally wrong (record-then-playback)."** Agreed.
- **"6 layers are caused by the BGA escape."** Agreed.
- **"The fuel gauge is unused by software."** True today; see §5 for why telemetry still matters and how to get it for free.
- **"Same architecture, wrong chip — the Teensy proves the nRF can do the filtering."** Disagree on the architecture, agree on the chip's *package*. The Teensy proved the math and the interaction, not the latency (§3); a codec-resident DSP is what makes sub-millisecond hear-through possible, and dropping it is the one change that alters what the product *does*, contrary to the memo's framing. The right move is a QFN codec that keeps the DSP in the loop.
- **"TLV320AIC3253/3254 is a drop-in-shaped replacement."** Agreed — and stronger than stated: the AIC3254's fixed ADC processing blocks **PRB_R2/PRB_R5 carry five programmable biquads** (datasheet Table 2, p.30) and the DAC blocks carry more plus a DRC (Table 3, p.31), all register-programmable over I2C without any DSP tool. Its two miniDSP cores (1,152 instructions per sample at 48 kHz, "can exchange data", p.34) are the upgrade path if anything more than notches is ever wanted. (Note: the datasheet is for the AIC3254; the "3253" in the memo appears to be a typo — the JLC catalog line Paul quoted is AIC3254IRHBR.)

## 7. Recommendation and the cheapest experiment that settles it

**Recommend option B**: TLV320AIC3254 (RHB), PDM mic into its digital-mic input, hear-through implemented inside the codec, a QFN power-path charger (BQ24072-class) plus an SAADC battery-voltage read, MDBT53-1M unchanged. This keeps R1 (codec-owned loop), keeps every codec-agnostic piece of firmware and the whole app, removes all three fine-pitch packages, and uses catalog parts.

Two unknowns decide whether B delivers A's latency or merely beats C:

1. **Is there a fully internal ADC→DAC digital path on the AIC3254 that runs through the biquad blocks?** The datasheet's fixed processing blocks sit on the ADC and DAC paths with the serial interface in between; the miniDSP cores "can exchange data" (p.34), which is an internal path but needs PurePath Studio. If a register-level ADC→DAC route exists (to verify in SLAA408 / the register map), B needs no DSP tool at all; if not, B uses the miniDSP.
2. **What are the AIC3254's ADC + DAC group delays at 48 / 96 / 192 kHz?** SLAA408 has them; the bench will confirm.

**Cheapest experiment (≈ $200, one week, no custom PCB):**

- **Step 1 — nRF5340 DK alone, $0:** loop I2S SDOUT→SDIN with a jumper and measure the Zephyr I2S round-trip for 16/32/64-sample blocks (GPIO toggle at RX-block-ready and TX-start, logic analyzer or `k_cycle_get_32`). This nails option C's buffering term with no codec at all.
- **Step 2 — TLV320AIC3254EVM-U (TI) + DK:** configure PRB_R2 with Haven's five biquads via I2C, drive the PDM mic input, measure hear-through latency by impulse cross-correlation (PR #11's `latency.py`) at 48 and 96 kHz, and measure supply current. If Δt ≤ 300 µs, B is confirmed as the product path.
- **Step 3 (optional, $485) — EVAL-ADAU1860EBZ + DK:** same measurements on option A, using the driver in PR #9, to know exactly what the BGA buys.

**What changes in the open PRs if B is chosen:** PRs #8 (format analysis), #9, #10's codec half, #13, #14 become reference material for the bench, not the product; `tone_gen.c`, the BLE/protocol/safety/ack layers (#10's nRF half, #12), the calibration rig (#11), the app PRs (#6–#8), and the documentation PRs carry over unchanged. The board PRs (#3, #5) still document the current design correctly but the placement work would be redone on a new, smaller schematic — designed right from the start, as `HARDWARE_COST_ALTERNATIVES.md` already says.

**What I would not do:** ship option C to save $3 of codec. It trades the product's defining property for a cheaper part while the cheaper part with the right property sits in the same catalog.

---

*Sources.* TLV320AIC3254 datasheet SLAS549D (rev. Nov 2014): p.1 features/power, p.30 Table 2 ADC processing blocks, p.31 DAC section/Table 3, p.34 miniDSP ("up to 1152 instructions on every audio sample at a 48kHz sample rate"; "very-low group delay"), p.27 Table 1 (DMDIN/DMCLK multifunction pins), p.50 RHB mechanical (5×5 mm, 0.5 mm pitch). nRF5340 Product Specification, "Current consumption" (IAPPCPU5 3.3 mA @ 64 MHz; IAPPCPU4 7.8 mA @ 128 MHz; II2S2 2.31 mA; ION_IDLE2 1.3 µA). Zephyr `drivers/i2s/i2s_nrfx.c` (NCS `ncs-v3.4-branch`). PaulStoffregen/cores `teensy4/AudioStream.h:54,58` (`AUDIO_BLOCK_SAMPLES 128`, 44.1 kHz). Upstream OpenEarable `ADAU1860.cpp` (192 kHz DMIC/FastDSP). `HARDWARE_COST_ALTERNATIVES.md`, `FABRICATION_GUIDE.md` (this repo). Notebook notes 00, 01, 10, 12 (`victorzhu443/haven-engineering-notes`). ADAU1860 datasheet and SLAA408 were **not** obtainable in this environment; every figure that depends on them is marked estimated.

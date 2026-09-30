# TAC5301-Q1 evaluation: a second QFN codec candidate, verified from the real datasheet

*Follow-up to `HARDWARE_ARCHITECTURE_DECISION.md` (2026-09-14), which recommended the TLV320AIC3254
pending an unresolved ~$200/1-week bench experiment. Written 2026-10-01 after the $500 board cost
became the actual blocker on shipping anything, prompting a fresh look at whether that bench
experiment can be narrowed or skipped by reading harder before spending money.*

## TL;DR

- **A second real candidate exists: TI's TAC5301-Q1** (VQFN-24, 4x4mm, mono, SLASFD9A — Apr 2025,
  revised Apr 2026, newer silicon than the AIC3254's 2014-revision datasheet).
- **My first read of it (conversation, not this doc) was wrong and is corrected here.** The
  feature list's "programmable EQ and biquad filters" plus a "12 biquad" figure in the biquad
  section reads like plenty of headroom. It isn't, read carelessly: **that 12 is a shared pool
  across the whole TAC5x1x family and is capped at 3 biquads per channel on this specific mono
  part** (datasheet §6.3.7.1.5, §6.3.7.2.4, both state "limited to 3/channel" explicitly). Caught
  this before it went into a recommendation — flagging the correction here rather than quietly
  fixing it, per this repo's own standing practice of disclosing reversed conclusions
  (`CODEX_NOTES.md`'s LRCLK/XTALI entries).
- **But the real number is still good enough, once the actual signal path is verified, not
  assumed.** The ADC-side chain and the DAC-side chain each have their own independent 3-biquad
  bank, and the DAC signal chain's mixer explicitly accepts **"ADC loopback"** as a selectable
  input, feeding straight into the DAC-side HPF/biquad stage (Figure 6-61, `EN_LOOPBACK_MIXER`
  register, Page 10 "ADC to DAC loopback mixer" coefficients). That means a hear-through signal
  can pick up **3 biquads on the way out of the ADC and another 3 on the way into the DAC, all
  inside the chip, no host round-trip** — up to 6 total, comfortably covering Haven's ≤5-band
  spec, split however's convenient (e.g. 3 ADC-side + 2 DAC-side).
- **Latency, from the real filter-characteristics tables, not an estimate:** ultra-low-latency
  mode gives ADC group delay of **2.7–2.8 samples** (Tables 6-32–6-36) and DAC group delay of
  **1.7–3.2 samples** depending on output rate (Tables 6-56–6-60), both in units of `1/fS`. At
  48kHz that's roughly **120–190µs combined** (worst-case pairing); it gets smaller at 96/192kHz.
  For comparison, the architecture memo's own threshold for audible comb-filtering starts around
  300µs — this is comfortably under it, in the same range as the ADAU1860's own *estimated*
  50–150µs, except this number comes from a published filter-characteristics table instead of an
  estimate.
- **Real stock, confirmed at Mouser (2026-09-30): 2,834 units, ships immediately.** Pricing at
  prototype quantities: $1.61 (qty 1), $1.18 (qty 10), $1.07 (qty 25), $1.00 (qty 100). TI's own
  site listing of $0.66 was stale/wrong — the real distributor price is 1.6–2.4x that, but still
  well under the AIC3254's $3.03. The 20-week figure on the listing is Mouser's *factory
  lead-time for restocking after current inventory runs out*, not a blocker — there's nowhere
  near enough demand from a handful of prototype boards to touch that. **This was the one open
  item and it's now closed: real, in-stock, cheap.**

## What this changes vs. the AIC3254 recommendation

The AIC3254 path had one specific, unresolved compromise: its lowest-latency ADC filter tier
(Filter C) supports 5 biquads, but its lowest-latency **DAC** filter tier only goes to 4 — the 5th
band would need the higher-group-delay Filter A. TAC5301-Q1 doesn't have that asymmetry in the
same way (3+3 split across two independent chains instead of one chain maxing out), though it
trades "5 on one side" for "has to split across both sides to reach 5," which needs confirming in
practice: I have not confirmed whether all 6 available biquad slots can independently take
arbitrary notch/peaking coefficients (vs. some being reserved for HPF-like fixed roles) or whether
splitting a single logical dampening band's coefficients across two different digital stages
(ADC-side vs. DAC-side, at potentially different internal sample domains) introduces any
combination artifact. This is a real open question, not assumed clean.

Two things this candidate does *not* need that the AIC3254 path was uncertain about: no miniDSP,
no PurePath Studio, no "is there a register-only path or do we need the DSP tool" question at all
— every biquad on both sides is plain register coefficients (`ADC_BQ1..12_*`, `DAC_BQ1..N_*`),
confirmed directly from the register map (§7.2.3 onward), not inferred.

## What's still unverified (do this before writing any schematic)

1. ~~Real distributor stock and price~~ **Resolved 2026-09-30**: 2,834 in stock at Mouser,
   $1.07–1.61/unit at prototype quantities, ships immediately. See TL;DR.
2. **Whether the 3+3 loopback split can actually implement 5 independent notch/peaking bands** —
   reasoned through on paper this tick, not bench-verified. The ADC loopback path to the DAC chain
   does **not** appear to pass through the DAC chain's sample-rate converter (Figure 6-61 shows the
   SRC block specifically in the *Aux ASI* input path, a separate branch from the "Tone Generator or
   ADC loopback" input into the adder) — so both biquad banks should be operating on the same
   signal at the same sample rate, with no resampling between them. Under that condition, cascading
   any 5 (of the available 6) independently-programmed biquad sections is a standard LTI cascade:
   the combined transfer function is just the product of each section's response, regardless of
   which physical bank each one lives in. **One real firmware requirement this implies**: each
   side's HPF (`ADC_DSP_HPF_SEL`/`DAC_DSP_HPF_SEL`, Tables 6-15/6-39) and digital volume control
   need to be left at their lowest-cutoff/unity settings, or they'd act as extra, unaccounted-for
   filter stages in the cascade — a straightforward init-sequence detail, not a redesign. This
   reasoning is solid enough to plan around but should still get a real bench check (a swept sine
   through both banks configured) before it's treated as settled, same as item 3 below.
3. The datasheet's own group delay numbers are worst-case-pairing arithmetic done by me in this
   doc, not a measured round-trip on real hardware. Same caveat the architecture memo already
   raised for the AIC3254: **read the real thing, but bench it before it's a safety claim.**

## Recommendation

**TAC5301-Q1 over TLV320AIC3254, pending the bench check both parts still need.** Reasoning:

| | TAC5301-Q1 | TLV320AIC3254 |
|---|---|---|
| Price (prototype qty) | $1.07–1.61 (confirmed, Mouser) | $3.03 (JLC catalog) |
| Stock | 2,834 @ Mouser, ships now | not independently re-confirmed this pass |
| Biquads for 5 bands | 3+3 across two banks, needs the paper-verified split (§ above) | 5 on ADC (Filter C), only 4 on DAC at the same latency tier — needs Filter A for the 5th, at a latency cost |
| Group delay (ultra-low-latency, 48kHz) | ~120–190µs combined, from real filter tables | not fully pinned down from public docs this pass |
| DSP tool dependency | none — pure register writes, confirmed from register map | none for fixed blocks; miniDSP only if going beyond them |
| Datasheet currency | Apr 2025, rev. Apr 2026 | Sept 2008, rev. Nov 2014 |
| Package | VQFN-24, 4×4mm | VQFN-32, 5×5mm |

TAC5301-Q1 wins on price, confirmed stock, and datasheet-sourced (not estimated) latency numbers.
Its one real asterisk — needing the 5 bands split 3+2 (or similar) across two independently-clocked
biquad banks instead of 5 in one bank — is reasoned through above as sound, not hand-waved, but
it's paper reasoning, not a bench measurement.

**Before any schematic work**: run the cheap experiment the architecture memo already proposed
(§7 there), but aimed at this part instead of the AIC3254 — a TAC5301-Q1 costs about $1.50 in
parts; TI doesn't appear to sell a dedicated EVM for it the way it does for the AIC3254 family, so
the practical version of that experiment is likely a small breakout/dead-bug prototype on a
breadboard-friendly adapter rather than an off-the-shelf eval board. Confirm real hear-through
latency and that the 3+2 (or 3+3) band split sounds and measures correctly before committing PCB
time to it.

---

*Sources: TAC5301-Q1 datasheet SLASFD9A (Apr 2025, rev. Apr 2026) — §6.3.7.1 ADC Signal-Chain
(Figure 6-23), §6.3.7.1.5 ADC biquads ("limited to 3/channel"), §6.3.7.1.7.2/6.3.7.1.7.3 ADC
low-/ultra-low-latency filter tables (6-27 through 6-36), §6.3.7.2 DAC Signal-Chain (Figure 6-61,
"Tone Generator or ADC loopback" mixer input), §6.3.7.2.4 DAC biquads, §6.3.7.2.5.2/6.3.7.2.5.3 DAC
low-/ultra-low-latency filter tables (6-51 through 6-60), §7.2.3 Page 10 register map ("ADC to DAC
loopback mixer"). `HARDWARE_ARCHITECTURE_DECISION.md` (2026-09-14, this repo) for the latency
threshold derivation and the AIC3254 comparison baseline.

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
- **Price: TI lists it at $0.66**, cheaper than the AIC3254's $3.03 — but TI's own site shows it
  out of stock at that price, and I have not yet confirmed real stock/price at LCSC, Digikey, or
  Mouser. **This is the one open item before committing any schematic time to this part** — an
  automotive-qualified (AEC-Q100) part sometimes has thinner small-quantity consumer-channel
  stock than its price suggests, and that needs a real distributor check, not a search-snippet
  guess.

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

1. **Real distributor stock and price** at LCSC/JLC/Digikey/Mouser, in the quantities Haven would
   actually order. TI's own $0.66/out-of-stock listing is not enough to commit to.
2. **Whether the 3+3 loopback split can actually implement 5 independent notch/peaking bands**
   with the coefficients Haven's existing `apply_bands`-style tuning already computes, or whether
   the split requires re-deriving which bands go on which side and re-checking the combined
   transfer function is still correct — this is a real DSP question, not just a register-count
   question.
3. The datasheet's own group delay numbers are worst-case-pairing arithmetic done by me in this
   doc, not a measured round-trip on real hardware. Same caveat the architecture memo already
   raised for the AIC3254: **read the real thing, but bench it before it's a safety claim.**

## Recommendation

Don't commit schematic time to either QFN candidate yet. Next step is cheap and non-committal:
confirm real TAC5301-Q1 stock/pricing at an actual distributor. If that comes back reasonable,
it's now a genuine two-way comparison (TAC5301-Q1 vs TLV320AIC3254) instead of a single unresolved
recommendation, and the $200 bench-test question from the architecture memo should specify *which*
part(s) to buy eval hardware for, rather than assuming AIC3254 by default.

---

*Sources: TAC5301-Q1 datasheet SLASFD9A (Apr 2025, rev. Apr 2026) — §6.3.7.1 ADC Signal-Chain
(Figure 6-23), §6.3.7.1.5 ADC biquads ("limited to 3/channel"), §6.3.7.1.7.2/6.3.7.1.7.3 ADC
low-/ultra-low-latency filter tables (6-27 through 6-36), §6.3.7.2 DAC Signal-Chain (Figure 6-61,
"Tone Generator or ADC loopback" mixer input), §6.3.7.2.4 DAC biquads, §6.3.7.2.5.2/6.3.7.2.5.3 DAC
low-/ultra-low-latency filter tables (6-51 through 6-60), §7.2.3 Page 10 register map ("ADC to DAC
loopback mixer"). `HARDWARE_ARCHITECTURE_DECISION.md` (2026-09-14, this repo) for the latency
threshold derivation and the AIC3254 comparison baseline.

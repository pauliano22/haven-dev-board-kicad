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
| ADAU1860 | active, FastDSP running | **not verified** | ADI's own PDF timed out twice on fetch (a recurring issue with this host). Datasheet-page-count context suggests it has a real power table; someone needs to open the PDF directly (link below) and read the DVDD/AVDD active current numbers before this line is trustworthy. |
| PDM mic (SPH0641LU4H-1) | low-power mode | 235 µA | [Knowles datasheet](https://www.mouser.com/datasheet/2/218/-746191.pdf) |
| PDM mic | standard performance mode | 1 mA | same |
| BQ25120A charger | quiescent, buck enabled, no load | 700 nA | [TI datasheet](https://www.ti.com/lit/ds/symlink/bq25120a.pdf) |
| BQ27220 fuel gauge | NORMAL mode | 50 µA | [TI datasheet](https://www.ti.com/lit/ds/symlink/bq27220.pdf) |
| BQ27220 fuel gauge | SLEEP mode | 9 µA | same |

**The ADAU1860 number is the one that actually decides battery life** — it's
the DSP doing the real-time hear-through work continuously, not something
that gets to idle the way the radio does. Don't trust a runtime estimate that
skips it. Get that number before believing anything below at more than
order-of-magnitude confidence.

## Two scenarios, with the ADAU1860 gap called out

**Continuous hear-through, BLE idle (the normal wearing state):**
mic (1 mA) + ADAU1860 (unknown) + BQ27220 (0.05 mA) + BQ25120A (~0) ≈
**1.05 mA + ADAU1860's draw**. If the codec turns out to be single-digit mA
(plausible for a small audio DSP at this process node, but not confirmed),
total lands somewhere in the 3–8 mA range. If it's higher — some
full-featured audio DSPs run 15–20 mA active — that dominates everything else
on this list.

**Active BLE connection (app open, adjusting settings):** add the nRF5340's
~3 mA on top of the above.

## Runtime by battery size (using the low end of the unverified range: ~5 mA total)

| Cell capacity | Runtime at ~5 mA | Runtime at ~10 mA (if ADAU1860 is heavier) |
|---|---|---|
| 40 mAh (small in-ear pouch cell) | ~8 h | ~4 h |
| 60 mAh | ~12 h | ~6 h |
| 100 mAh | ~20 h | ~10 h |

No specific battery cell is chosen yet in the BOM — only the charge/fuel-gauge
ICs and a connector. These sizes are typical for in-ear wearables, not a
recommendation until real current is measured.

## Charging

BQ25120A's fast-charge current is set by an external resistor/register, not
fixed — the schematic's ISET value decides it, and I didn't re-derive it from
the board files this pass. A 40–60 mAh cell at a typical ~0.5C small-cell
charge rate would take roughly 1–2 hours; confirm the actual ISET-programmed
current before quoting a number to anyone outside this project.

## What to do next

1. Open the ADAU1860 datasheet directly (fetches from this session keep timing
   out — try it in a browser) and read its active-mode current table.
2. Once real hardware exists, measure actual current with a multimeter or a
   power profiler (Nordic's Power Profiler Kit works well with the nRF5340) —
   this whole document is a placeholder for that measurement, not a
   substitute for it.
3. Pick a battery cell size once the real current number is in, sized against
   a target runtime (e.g., "one full day of wear" or "8-hour workday").

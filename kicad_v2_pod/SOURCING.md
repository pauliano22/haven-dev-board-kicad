# Haven v2 BTE: off-board and loose parts sourcing

First run: 1 pair (left + right) + 1 charging case. Researched 2026-11-04. Stock and prices are
snapshots from distributor pages and search caches; re-check live before ordering. Nothing bought.
Board parts (radio, codec, PMIC, passives) are in `haven_v2_pod_bom.csv` / `../kicad_v2_inear/`.

| # | Item | Pick | Key specs | Price (est.) | Stock / lead | Where | Notes |
|---|---|---|---|---|---|---|---|
| 1 | Speaker (8 mm) | Ole Wolff **OWR-0860T-16** | 8.0 mm, 16 Ω, 5 mW, 20 Hz–20 kHz, 63.6 dBA @ 1 mW/10 mm, **4.5 mm seated height** | ~$1–2 | not confirmed (DigiKey listing exists) | DigiKey | Taller than the 3.6 mm envelope used in CAD: the in-ear unit must allow 4.5 mm or use the fallback. 16 Ω is within the ADAU1860's specified loads. A generic earphone driver, not a known IEM part; measure it before committing. |
| 1b | Speaker fallback (6 mm) | Ole Wolff **OWR-0640T-16H** | 6 mm, 16 Ω, 50 Hz–20 kHz, 61.8 dBA @ 1 mW/10 mm | $0.68–1.27 | DigiKey temporarily out, ~7-week lead | DigiKey | Smaller and slightly quieter. No 8 mm 32 Ω part with a datasheet was found at DigiKey/Mouser/PUI/Same Sky. |
| 2 | Cable (6-conductor) | **No catalog part found.** Prototype: build a harness of 6 × 38–40 AWG enameled Litz or magnet wire (speaker pair twisted; PDM clock / GND / data side by side), with an aramid (Kevlar) thread strength member, in 1.5 mm silicone or PTFE tubing | ~100 mm per side | ~$15–25 (wire spool + tubing) | stock items | DigiKey/Amazon (magnet wire), any tubing | Catalog 6-core cables are 26–28 AWG (Mogami W2814, Tensility 30-02667), too stiff and thick. For production, ask a micro-cable maker (New England Wire sells 6-core 30 AWG 7/38 by the foot). Fallback if the hand-built harness is unreliable: mic on the pod, which drops the cable to 2 conductors. |
| 3 | Cable ESD | TI **TPD1E05U06DYAR**, LCSC **C3702980** | 0.5 pF, 5.5 V, ±12 kV (IEC), SOT-5X3/SOD-523-class 2-pin | $0.14 (5+) | ~7.7–8.5k at LCSC | LCSC / JLCPCB | LCSC number now in the pod BOM CSV and the generator; the .kicad_sch LCSC field updates on the next generator run. |
| 4 | Pod battery | VARTA **CP1454 A4X** | Ø14.1 × 5.4 mm, 3.7 V, ~108–111 mAh Li-ion | ~$10–15 (est.) | Texim Europe "in stock, price on request"; no DigiKey/Mouser US listing | Texim (quote), VARTA distributors | Request a quote early (2+ cells plus spares). CoinPower cells have no built-in protection PCB; the nPM1100 handles charge termination, but there is no separate over-discharge cutoff on the board. Generic LIR1454 cells are cheaper but unvetted (capacity and safety vary); avoid for skin-worn prototypes. |
| 5a | Case pogo pins | Mill-Max **0925-0-15-20-75-14-11-0** (LCSC C21761899), or a Xinyangze SMD spring pin from LCSC's pogo category (e.g., C5157315) | single SMD spring contact | ~$1–2 each | stock not confirmed | LCSC / DigiKey | Need 4 (2 per pod). Check head diameter vs the pod's Ø1.6 pads, travel, and force (50–200 gf range for charge contacts) on the datasheet before committing. |
| 5b | Magnets | K&J Magnetics **D21B-N52** | 1/8 × 1/16 in (3.18 × 1.59 mm), N52, 10-pack | $1.68 / 10 | in stock | K&J Magnetics | Close to the 3 × 2 mm in CAD (adjust the pocket). Need 2 in the pods + 2 in the case. Exact 3 × 2 mm N52 exists from eBay sellers (unverified). |
| 6a | Case charger + boost | Injoinic **IP5306**, LCSC **C181692** | 5 V/2.1 A boost + 1-cell charger, ESOP-8 | $0.28 (5+) | ~54.7k at LCSC | LCSC / JLCPCB | Common, cheap. Its boost has a light-load auto-shutoff, which can drop out with two small earbud loads; the case board design must check this (load switch / keep-alive), or use TI BQ25619. |
| 6b | Case load switch (per pod) | TI **TPS22910A**, LCSC **C2150034** (YZVT) | load switch, DSBGA-4 | ~$0.8 | 97 at LCSC (YZVR C205966 out of stock) | LCSC / JLCPCB | Need 2. Low stock but enough for a pair. |
| 6c | Case USB-C | G-Switch **GT-USB-9047A** (as on v1) | USB-C receptacle | ~$0.3 | ~2.2k at LCSC (11/3) | LCSC / JLCPCB | Known part from v1. |
| 6d | Case battery | Adafruit **1578** (3.7 V 500 mAh LiPo with protection PCB, ~29 × 36 × 4.75 mm) | 500 mAh | $7.95 | DigiKey ~570, Mouser ~537 | DigiKey / Mouser / Adafruit | Protected, JST connector. 502030 (250 mAh) cells are only from small overseas sellers. 500 mAh gives roughly 3+ full recharges of two 108 mAh pods. |
| 7 | Ear tips | **Tipsy Comfort Eartip Set** (3 silicone, 4.5 mm bore + 3 memory foam, 4.9 mm bore, S/M/L) | fits a ~5.4 mm nozzle (confirm) | ~$15–20 | retail | hifihub / Amazon | Alternatives: Final Audio Type-E (silicone, 4.5–5.5 mm nozzles), Comply SmartCore variety pack (foam, 4.8–6.3 mm nozzles). |

## Cost subtotal (these parts only, 1 pair + case, rough)
Speakers 2 × ~$1.5 ≈ $3 · cable materials ≈ $20 · ESD 6 × $0.14 ≈ $1 · CP1454 2 × ~$12 ≈ $24 ·
pogo pins 4 × ~$1.5 ≈ $6 · magnets $2 · IP5306 + 2 × TPS22910A + USB-C ≈ $2.5 · case LiPo $8 ·
ear tips $18. **≈ $85 before shipping** (add ~$20–40 across DigiKey / K&J / Texim / tips).
Not included: the two PCB assemblies (pod + in-ear, case board), radio modules, nPM1100s, shells.

## Open items
- Speaker height (4.5 mm) vs the in-ear unit envelope: update the CAD or switch to the 6 mm driver.
- CP1454 quote from Texim / a VARTA distributor.
- Cable: build one test harness and flex-test it before the real assembly.
- Pogo pin datasheet check against the pod pad size.

# Haven v2 earbud: schematic

Draft schematic for the compact v2 earbud (charging-case bud, no USB-C). Plan, part choices and
size study: `HAVEN_V2.md` in the workspace root. v1 (`kicad/`, trimmed OpenEarable board) is
untouched.

**Generated.** `tools/gen_v2_schematic.py` writes everything in this folder: the schematic, the
symbol library, the new footprints, and copies of the v1 footprints it reuses. Edit the script
and rerun it; don't hand-edit `haven_v2.kicad_sch`. Connections are net labels placed exactly on
pin ends, so the sheet looks like a parts list rather than a drawn circuit. A tidy drawn version
can come later; the netlist is what layout needs.

## Status (2026-10-29)
- 67 parts, 46 nets. `kicad-cli sch erc`: **0 violations**.
- Checked beyond ERC: KiCad's exported netlist matches the script's intended netlist net for net
  (0 mismatches); every symbol pin has a pad on its footprint; the new footprints load (MDBT53V-1M
  39 pads, nPM1100 25 balls).
- BOM export works: `haven_v2_bom.csv`.
- No PCB yet.
- All symbol pins are typed "passive", so ERC checks wiring and unconnected pins but not driver
  conflicts.

## Where the kept circuits come from
v1's schematic can't be trusted for connectivity: its symbols load, but its pin-to-net wiring is
scrambled (the mic's DATA pin lands on GND, the radio module is entirely unconnected). The
**Rev A board** (branch `rev-a/native-trim`) is the reliable source, since its copper was checked
pad by pad against OpenEarable's routing. The ADAU1860, mic, codec crystal, load switch, status
LED and 32 kHz crystal circuits here copy that board's pad-to-net map, with the same part values
and LCSC numbers. The ADAU1860 ball names come from v1's symbol and agree with the copper at every
signal ball checked (SDA/SCL on C6/C7, HPOUTP/N on F2/G1, PD# on E4, XTALI on B7).

## New parts, checked against datasheets
| Part | Source | What was verified |
|---|---|---|
| Raytac MDBT53V-1M | Raytac "MDBT53V-1M & MDBT53V-P1M Spec" Ver.D, 2024-10-25 (raytac.com download id 62) | Pin table §2.5 pp. 15–17 (all 39 pins); pad positions and 0.55 × 0.4 mm size §2.2 p. 10; pin layout p. 7; antenna keep-out 3.8 mm and top-layer no-copper patch p. 9; reference circuits §8.1 pp. 41–42 |
| Nordic nPM1100-CAAB-R | "nPM1100 Product Specification" v1.2 (4445_367), §8.1 pp. 42–43 | All 25 balls (Table 21); VOUTBSET table (Table 16, p. 29): both low = 1.8 V; charge resistor (Table 11); ship mode §3.5 p. 10; config 3 reference circuit p. 47 |

The nPM1100 PS v1.4 (2024) changes pin 3 to VOUTBSET0 and pins 4/25 to AVSS. Those are **QFN**
pin numbers. This design uses the WLCSP. I couldn't download v1.4 itself (403), so I worked from
v1.2.

## Power tree
```
Case pogo pin (5 V) ─ P1 ─┬─ D1 ESD clamp
                          ├─ R114/R115 divider ─ VBUS_DET (P0.25/AIN4): "in case"
                          └─ nPM1100 VBUS (fixed 100 mA input limit)
                               ├─ charger ─ VBAT ─ CP1254 (60 mAh), 20 mA charge, 4.20 V
                               └─ VSYS (battery, or VBUS while charging)
                                    ├─ R112/R113 divider ─ VSYS_SENSE (P0.05/AIN1): battery level
                                    ├─ red status LED (U4, R4, Q2)
                                    └─ buck, 2.2 uH ─ +1V8 (150 mA max)
                                         ├─ MDBT53V-1M VDD + VDDH (normal-voltage mode)
                                         └─ U3 load switch (SENSORS_ENABLE, P1.11) ─ V_LS
                                              ├─ ADAU1860 IOVDD, AVDD, HPVDD, REG_EN (internal LDO → DVDD)
                                              └─ SPH0641 mic VDD
```
Everything runs at 1.8 V, like v1, whose BQ25120 buck also made 1.8 V for the nRF and codec. The
nPM1100 replaces the BQ25120, the BQ27220 fuel gauge (battery level comes from VSYS_SENSE now),
the USB-C connector and its ESD array.

The nRF's internal DC/DC inductors L101/L102 (10 uH, Raytac's DC/DC circuit) are placed in the
schematic. Leaving them unpopulated runs the module in LDO mode with no other change.

## nRF5340 pin map vs v1 (firmware impact)
The MDBT53V-1M brings out only 25 GPIOs, and several of v1's pins aren't among them.

| Signal | v1 (MDBT53-1M) | v2 (MDBT53V-1M) | Change |
|---|---|---|---|
| Codec I2C SCL / SDA | P1.00 / P1.15 | **P1.03 / P1.02** | moved (not on module) |
| Codec enable (PD#) | P0.04 | P0.04 | same |
| Codec + mic rail (SENSORS_ENABLE) | P1.11 | P1.11 | same |
| I2S BCLK | P1.10 | **P0.13** | moved |
| I2S LRCLK | P0.30 | **P0.14** | moved |
| I2S nRF → codec (DIN) | P0.28 | **P0.15** | moved |
| I2S codec → nRF (DOUT) | P0.31 | P0.31 | same |
| Status LED | P1.08 | **P1.12** | moved |
| Charger status / error | BQ25120 I2C on P0.24/P0.21, INT P0.19, CD P0.17, PG P0.18, LSCTRL P0.14 | **CHG P0.10, ERR P0.11** (open drain, use pull-ups) | nPM1100 has no I2C |
| Ship mode | – | **SHPACT P0.12** | new |
| Battery level | BQ27220 fuel gauge | **VSYS_SENSE P0.05/AIN1** | new, ADC |
| In-case detect | nRF VBUS pin | **VBUS_DET P0.25/AIN4** | new; MDBT53V has no VBUS pin |
| Button | P1.05 (ON+BTN) | none | removed (see below) |
| USB D+/D-, SD, flash, IMU, RGB pins | various | none | removed |
| Spare | – | P1.13 on TP6 | for touch or one-wire later |
| 32 kHz crystal | XL1/XL2 | XL1/XL2 | same part and 9 pF caps |

Firmware needs a new board target (`haven_v2`) with these pins; the codec driver itself doesn't
change. Charger handling moves from I2C to three GPIOs plus one ADC channel.

## Choices made
- **No button.** Earbuds are usually tap or touch controlled, and the IMU that could detect taps
  was removed. The bud wakes when it goes into the case (VBUS ends ship mode). Pairing and power go
  through the case and the app. Firmware can put the bud in ship mode with SHIP_EN when it's out
  of the case. P1.13 is on a test pad for a touch sensor later. TP7 (SHPHLD) can take a button if
  one is ever wanted.
- **Charge current 20 mA** (R111 30 kΩ), about 0.3C for a 60 mAh CP1254: roughly a 3 h charge.
- **4.20 V termination.** Safe for 4.2 V and 4.35 V CoinPower variants. A 4.35 V cell would leave
  some capacity unused.
- **No battery thermistor:** the CP1254 doesn't have one, so NTC sees a fixed 10 kΩ (Nordic
  config 1).

## Sourcing (snapshot 2026-10-29)
| Part | Where | Note |
|---|---|---|
| MDBT53V-1M | DigiKey 25 in stock, $7.00, Active | Not at LCSC: consign to JLCPCB or use Global Sourcing. Low stock. |
| nPM1100-CAAB-R | Future 6,000; RS | Not at LCSC: consign. |
| ADAU1860BCBZRL | LCSC C17592940, 116 in stock, $12.38 | |
| Passives, mic, crystals, LED, FET, load switch | LCSC numbers from the Rev A BOM | Quoted on Rev A 2026-10-29 |
| R111, R113–R115, C110, L101/L102, D1 | not chosen | open item 2 |

## Open questions
1. **ESD clamp D1** on the exposed VBUS pad: part not chosen (SOD-523 footprint placeholder).
2. LCSC parts for R111 (30k 1%), R113 (560k), R114 (100k), R115 (47k), C110 (2.2 uF ≥10 V 0402),
   L101/L102 (10 uH 0402, check current rating against Nordic's DC/DC guidance).
3. **nPM1100 land pattern:** I read Nordic's ball map as a top view with A1 top-left, using
   0.2 mm NSMD pads. Confirm both against Nordic's reference layout files before layout.
4. **32 kHz load caps:** kept v1's external 9 pF. Raytac's default uses the nRF's internal caps
   instead. Set the firmware LFXO capacitance to match, or depopulate C2/C14 after measuring.
5. **VSYS_SENSE while charging:** VSYS can sit near VBUS; at 5.5 V the divider gives 1.97 V,
   above the 1.8 V rail but under VDD + 0.3 V, through 1 MΩ. Use 1M/470k if that margin is too thin.
6. **Speaker:** the 8 mm, 16–32 Ω driver isn't chosen yet. The ADAU1860 output is specified at
   16/24/32 Ω.
7. **One-wire data over the charge pin** (case ↔ bud) isn't in v2. VBUS_DET sits on an ADC pin so
   a later scheme can sense levels.
8. The codec crystal might need 22 pF caps instead of 33 pF if it won't start (noted for v1 too).

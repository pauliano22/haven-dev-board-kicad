# Routing handoff — Codex/Astra, 2026-09-09

Branch: `experiment/codex-astra-routing`. Baseline: `b535d54`.

Verified result: **116 → 96 missing links**, **50 → 47 open nets**, **415 → 415 violations**, with **no new violation identities**. Fully closed: `$1N2586`, `+1.8V`, `SW`. The historical “87” autorouter metric was not rerun and must not be subtracted from the DRC counts.

Added 35 track segments and 17 through vias. The structural audit confirms all 89 footprints, all 1,015 original segments, all 166 original vias, board setup, layer definitions, and antenna keepout are exactly unchanged as parsed S-expressions. Every addition is outside the antenna keepout. Only existing zone fills were recalculated.

## Scope and remaining limitations

Actual routing attempts and rejected refinements are recorded in CODEX_NOTES.md with unedited CLI output and full JSON reports. All five component six-layer images were inspected through the image-input tool; endpoint close-ups of C32/C36/L2 were also inspected. This was a successful partial routing pass, not completion of every remaining signal. Nets labeled “inspected; not routed” below received visual inspection only, not an exhaustive routing search or a DRC-verified escape attempt.

U15 inner balls remain particularly difficult: the 0.35 mm pitch and 0.25 mm pads leave 0.10 mm between pads. A centered 0.25 mm via fails the unchanged 0.20 mm clearance. Passing even a 0.09 mm trace between two other-net pads would need 0.49 mm of space. This rules out those simple strategies; it is not proof that every possible local reroute is impossible. Same-net neighboring balls can sometimes be joined edge-to-edge (B4→A4 was retained).

CN1 V_LS pin 8: outward candidates conflict with existing GND/IO4 escapes; inward candidate conflicts with a mechanical pad. No CN1 V_LS addition retained. U10 pin 5 is escaped but V_LS remains open elsewhere. Long SW connectivity was verified, but switch-node electrical/EMI performance was not analyzed; review that path before fabrication.

## Every target net from the original remaining-connections list

The image links show the component crops inspected during this pass. A shared component image is reused for its different nets. Counts below are current DRC link counts, not pad counts.

| Net | Target pads / inspected images | Current missing links | Outcome |
|---|---|---:|---|
| `$1N151` | [U15](routing-evidence/images/U15.png): A3, B3 | 2 | inspected; not routed |
| `$1N2586` | [U15](routing-evidence/images/U15.png): G4 | 0 | fully closed |
| `$1N65` | [U2](routing-evidence/images/U2.png): C4 | 1 | inspected; not routed |
| `+1.8V` | [U2](routing-evidence/images/U2.png): B5 | 0 | fully closed |
| `3V3` | [CN1](routing-evidence/images/CN1.png): 3; [U2](routing-evidence/images/U2.png): C5 | 2 | inspected; not routed |
| `BCLK` | [MDBT531](routing-evidence/images/MDBT531.png): 59; [U15](routing-evidence/images/U15.png): B2 | 1 | inspected; not routed |
| `CC_#CD` | [MDBT531](routing-evidence/images/MDBT531.png): 26; [U2](routing-evidence/images/U2.png): E2 | 1 | inspected; not routed |
| `CC_#PG` | [MDBT531](routing-evidence/images/MDBT531.png): 16; [U2](routing-evidence/images/U2.png): D4 | 1 | inspected; not routed |
| `DAC_ENABLE` | [MDBT531](routing-evidence/images/MDBT531.png): 37; [U15](routing-evidence/images/U15.png): E4 | 1 | inspected; not routed |
| `DIN` | [MDBT531](routing-evidence/images/MDBT531.png): 60; [U15](routing-evidence/images/U15.png): C1 | 1 | inspected; not routed |
| `DOUT` | [MDBT531](routing-evidence/images/MDBT531.png): 56; [U15](routing-evidence/images/U15.png): B1 | 1 | inspected; not routed |
| `FLASH_RESET` | [MDBT531](routing-evidence/images/MDBT531.png): 51 | 1 | inspected; not routed |
| `GND` | [CN1](routing-evidence/images/CN1.png): 10; [MDBT531](routing-evidence/images/MDBT531.png): 1, 61; [U10](routing-evidence/images/U10.png): 6, 8; [U15](routing-evidence/images/U15.png): A1, A4, B4, D6, D7, E6, F1, G3, G7; [U2](routing-evidence/images/U2.png): A1, A5 | 22 | partial escapes retained; still open |
| `INT` | [MDBT531](routing-evidence/images/MDBT531.png): 14; [U2](routing-evidence/images/U2.png): D2 | 1 | inspected; not routed |
| `IO5` | [CN1](routing-evidence/images/CN1.png): 4; [MDBT531](routing-evidence/images/MDBT531.png): 21 | 1 | inspected; not routed |
| `LRCLK` | [MDBT531](routing-evidence/images/MDBT531.png): 57; [U15](routing-evidence/images/U15.png): C2 | 1 | inspected; not routed |
| `LSCTRL` | [MDBT531](routing-evidence/images/MDBT531.png): 27; [U2](routing-evidence/images/U2.png): E3 | 1 | inspected; not routed |
| `MR#` | [U2](routing-evidence/images/U2.png): E1 | 2 | inspected; not routed |
| `PDMCLK` | [U15](routing-evidence/images/U15.png): C4 | 1 | inspected; not routed |
| `PDMDIN` | [CN1](routing-evidence/images/CN1.png): 7; [U15](routing-evidence/images/U15.png): C5 | 2 | inspected; not routed |
| `RESETN` | [U2](routing-evidence/images/U2.png): D3 | 1 | inspected; not routed |
| `SCL1` | [CN1](routing-evidence/images/CN1.png): 12; [U15](routing-evidence/images/U15.png): C7 | 2 | inspected; not routed |
| `SCL2` | [CN1](routing-evidence/images/CN1.png): 9 | 2 | inspected; not routed |
| `SDA` | [U2](routing-evidence/images/U2.png): E4 | 2 | inspected; not routed |
| `SDA1` | [U15](routing-evidence/images/U15.png): C6 | 1 | inspected; not routed |
| `SD_STATE` | [MDBT531](routing-evidence/images/MDBT531.png): 23 | 1 | inspected; not routed |
| `SPI_CLK` | [MDBT531](routing-evidence/images/MDBT531.png): 29; [U10](routing-evidence/images/U10.png): 3 | 2 | inspected; not routed |
| `SPI_CS` | [MDBT531](routing-evidence/images/MDBT531.png): 17; [U10](routing-evidence/images/U10.png): 1, 7 | 2 | inspected; not routed |
| `SPI_CS_FLASH` | [MDBT531](routing-evidence/images/MDBT531.png): 43 | 1 | inspected; not routed |
| `SPI_MISO` | [MDBT531](routing-evidence/images/MDBT531.png): 18; [U10](routing-evidence/images/U10.png): 4 | 2 | inspected; not routed |
| `SPI_MOSI` | [MDBT531](routing-evidence/images/MDBT531.png): 19; [U10](routing-evidence/images/U10.png): 2 | 2 | inspected; not routed |
| `SPI_MOSI_SD` | [U10](routing-evidence/images/U10.png): 11 | 1 | inspected; not routed |
| `SW` | [U2](routing-evidence/images/U2.png): A4 | 0 | fully closed |
| `TCK` | [U15](routing-evidence/images/U15.png): A5 | 1 | inspected; not routed |
| `TDI` | [U15](routing-evidence/images/U15.png): A8 | 1 | inspected; not routed |
| `TDO` | [U15](routing-evidence/images/U15.png): A7 | 1 | inspected; not routed |
| `TMS` | [U15](routing-evidence/images/U15.png): A6 | 1 | inspected; not routed |
| `TS` | [U2](routing-evidence/images/U2.png): C3 | 2 | inspected; not routed |
| `VUSB` | [U2](routing-evidence/images/U2.png): A2 | 3 | inspected; not routed |
| `V_LS` | [CN1](routing-evidence/images/CN1.png): 8; [U10](routing-evidence/images/U10.png): 5; [U15](routing-evidence/images/U15.png): A2, B5, D1, E1, F3, F7, G2 | 11 | partial escapes retained; still open |
| `XTALI` | [U15](routing-evidence/images/U15.png): B7 | 2 | inspected; not routed |
| `XTALO` | [U15](routing-evidence/images/U15.png): B6 | 1 | inspected; not routed |

## Current DRC missing-link details

Generated directly from `routing-evidence/final.json`; original REMAINING_CONNECTIONS.md preserved for historical comparison.

### #ERROR — 1 missing links

- Track [#ERROR] on In4.Cu, length 22.0138 mm at 75.1752,45.8508 mm ↔ Pad 1 [#ERROR] of Q2 on F.Cu at 69.7999,43.3077 mm

### $1N151 — 2 missing links

- Pad A3 [$1N151] of U15 on F.Cu at 58.0904,112.4979 mm ↔ Pad B3 [$1N151] of U15 on F.Cu at 58.0904,112.1479 mm
- Pad A3 [$1N151] of U15 on F.Cu at 58.0904,112.4979 mm ↔ Track [$1N151] on F.Cu, length 3.8495 mm at 56.171,120.4777 mm

### $1N65 — 1 missing links

- Pad C4 [$1N65] of U2 on B.Cu at 66.5098,32.4772 mm ↔ Pad 1 [$1N65] of C10 on B.Cu at 69.286,24.9778 mm

### $1N70 — 1 missing links

- Pad 2 [$1N70] of C23 on B.Cu at 45.3589,32.3739 mm ↔ Track [$1N70] on B.Cu, length 3.0088 mm at 45.6329,32.6482 mm

### 3V3 — 2 missing links

- Track [3V3] on F.Cu, length 0.6728 mm at 65.1173,133.8556 mm ↔ Pad 3 [3V3] of CN1 on F.Cu at 77.8819,134.7852 mm
- Pad C5 [3V3] of U2 on B.Cu at 66.5098,32.0771 mm ↔ Track [3V3] on F.Cu, length 1.2737 mm at 64.6212,43.2827 mm

### BCLK — 1 missing links

- Pad B2 [BCLK] of U15 on F.Cu at 57.7404,112.1479 mm ↔ Pad 59 [BCLK] of MDBT531 on F.Cu at 77.8102,73.0778 mm

### CC_#CD — 1 missing links

- Pad E2 [CC_#CD] of U2 on B.Cu at 65.7097,33.2773 mm ↔ Pad 26 [CC_#CD] of MDBT531 on F.Cu at 84.8102,67.3526 mm

### CC_#PG — 1 missing links

- Pad D4 [CC_#PG] of U2 on B.Cu at 66.1097,32.4772 mm ↔ Pad 16 [CC_#PG] of MDBT531 on F.Cu at 81.2354,65.9277 mm

### DAC_ENABLE — 1 missing links

- Pad E4 [DAC_ENABLE] of U15 on F.Cu at 58.4404,111.0979 mm ↔ Pad 37 [DAC_ENABLE] of MDBT531 on F.Cu at 83.8602,71.4778 mm

### DIN — 1 missing links

- Pad C1 [DIN] of U15 on F.Cu at 57.3904,111.7979 mm ↔ Pad 60 [DIN] of MDBT531 on F.Cu at 77.4853,74.0277 mm

### DOUT — 1 missing links

- Pad B1 [DOUT] of U15 on F.Cu at 57.3904,112.1479 mm ↔ Pad 56 [DOUT] of MDBT531 on F.Cu at 78.9852,74.0277 mm

### FLASH_RESET — 1 missing links

- Pad 51 [FLASH_RESET] of MDBT531 on F.Cu at 80.8102,73.0778 mm ↔ Pad F2 [FLASH_RESET] of U14 on F.Cu at 104.7598,110.2278 mm

### GND — 22 missing links

- Pad 1 [GND] of C23 on B.Cu at 45.3589,32.9225 mm ↔ Track [GND] on B.Cu, length 0.7020 mm at 45.0845,31.9462 mm
- Pad 1 [GND] of R6 on B.Cu at 45.4599,4.9362 mm ↔ Track [GND] on B.Cu, length 0.4283 mm at 45.4597,5.4193 mm
- Pad 2 [GND] of C44 on B.Cu at 47.1012,100.3707 mm ↔ Track [GND] on F.Cu, length 5.1474 mm at 47.0765,106.0201 mm
- Track [GND] on F.Cu, length 0.5717 mm at 48.2104,107.4322 mm ↔ Pad 2 [GND] of C34 on B.Cu at 48.2103,107.4826 mm
- Pad 2 [GND] of C31 on F.Cu at 56.7194,124.3272 mm ↔ Track [GND] on B.Cu, length 0.0500 mm at 58.5766,125.8027 mm
- Pad 1 [GND] of R8 on B.Cu at 58.1597,28.4692 mm ↔ Pad B2 [GND] of U6 on B.Cu at 51.7603,26.9778 mm
- Pad E6 [GND] of U15 on F.Cu at 59.1404,111.0979 mm ↔ Pad G7 [GND] of U15 on F.Cu at 59.4904,110.3978 mm
- Pad D6 [GND] of U15 on F.Cu at 59.1404,111.4479 mm ↔ Pad E6 [GND] of U15 on F.Cu at 59.1404,111.0979 mm
- Pad D6 [GND] of U15 on F.Cu at 59.1404,111.4479 mm ↔ Pad D7 [GND] of U15 on F.Cu at 59.4904,111.4479 mm
- Pad 2 [GND] of C19 on B.Cu at 62.5355,24.9776 mm ↔ Track [GND] on B.Cu, length 0.4637 mm at 63.0839,24.9777 mm
- Pad 1 [GND] of C46 on B.Cu at 64.7476,117.0602 mm ↔ Track [GND] on B.Cu, length 0.4637 mm at 64.199,117.0602 mm
- Track [GND] on B.Cu, length 0.0021 mm at 66.5083,33.6773 mm ↔ Track [GND] on B.Cu, length 0.6708 mm at 67.3099,33.6773 mm
- Pad 2 [GND] of Q2 on F.Cu at 69.3998,43.3077 mm ↔ Track [GND] on In1.Cu, length 13.1640 mm at 62.6603,44.2929 mm
- Pad 2 [GND] of C13 on B.Cu at 69.4037,120.0685 mm ↔ Track [GND] on B.Cu, length 0.4859 mm at 69.6779,119.7942 mm
- Pad 1 [GND] of C38 on B.Cu at 69.4102,131.8534 mm ↔ Track [GND] on B.Cu, length 0.4637 mm at 69.136,132.1277 mm
- Pad 2 [GND] of C22 on B.Cu at 74.8099,25.8004 mm ↔ Track [GND] on B.Cu, length 0.4859 mm at 75.0839,26.0747 mm
- Pad 2 [GND] of C9 on B.Cu at 78.7604,25.8134 mm ↔ Track [GND] on B.Cu, length 0.4637 mm at 79.0344,26.0877 mm
- Track [GND] on F.Cu, length 3.4975 mm at 94.3623,118.1015 mm ↔ Pad E3 [GND] of U14 on F.Cu at 105.1099,110.4277 mm
- Track [GND] on B.Cu, length 0.6967 mm at 104.4599,3.1326 mm ↔ Pad 1 [GND] of C8 on B.Cu at 104.4598,4.2227 mm
- Track [GND] on B.Cu, length 0.4637 mm at 109.2839,1.2777 mm ↔ Pad 2 [GND] of C6 on B.Cu at 109.0097,1.552 mm
- Track [GND] on B.Cu, length 0.4637 mm at 109.9855,84.4277 mm ↔ Pad 1 [GND] of C2 on B.Cu at 110.5341,84.4276 mm
- Pad 1 [GND] of C14 on B.Cu at 110.5341,62.9776 mm ↔ Track [GND] on B.Cu, length 0.4825 mm at 109.9855,63.4602 mm

### INT — 1 missing links

- Pad D2 [INT] of U2 on B.Cu at 66.1097,33.2773 mm ↔ Pad 14 [INT] of MDBT531 on F.Cu at 80.4853,65.9277 mm

### IO5 — 1 missing links

- Pad 4 [IO5] of CN1 on F.Cu at 77.8819,132.8693 mm ↔ Pad 21 [IO5] of MDBT531 on F.Cu at 83.0604,66.8776 mm

### LRCLK — 1 missing links

- Pad C2 [LRCLK] of U15 on F.Cu at 57.7404,111.7979 mm ↔ Pad 57 [LRCLK] of MDBT531 on F.Cu at 78.5602,73.0778 mm

### LSCTRL — 1 missing links

- Pad E3 [LSCTRL] of U2 on B.Cu at 65.7097,32.8772 mm ↔ Pad 27 [LSCTRL] of MDBT531 on F.Cu at 83.8602,67.7278 mm

### MR# — 2 missing links

- Track [MR#] on F.Cu, length 0.6517 mm at 79.8358,108.0094 mm ↔ Pad 1 [MR#] of Q1 on F.Cu at 105.7147,42.7027 mm
- Pad 1 [MR#] of Q1 on F.Cu at 105.7147,42.7027 mm ↔ Pad E1 [MR#] of U2 on B.Cu at 65.7097,33.6773 mm

### PDMCLK — 1 missing links

- Pad C4 [PDMCLK] of U15 on F.Cu at 58.4404,111.7979 mm ↔ Track [PDMCLK] on In1.Cu, length 5.7973 mm at 75.487,126.7333 mm

### PDMDIN — 2 missing links

- Pad 7 [PDMDIN] of CN1 on F.Cu at 78.5819,134.7852 mm ↔ Pad 1 [PDMDIN] of U13 on B.Cu at 79.2898,126.1681 mm
- Pad 1 [PDMDIN] of U13 on B.Cu at 79.2898,126.1681 mm ↔ Pad C5 [PDMDIN] of U15 on F.Cu at 58.7904,111.7979 mm

### RESETN — 1 missing links

- Pad D3 [RESETN] of U2 on B.Cu at 66.1097,32.8772 mm ↔ Track [RESETN] on In2.Cu, length 1.6973 mm at 78.8037,40.4254 mm

### SCL — 1 missing links

- Pad 6 [SCL] of U5 on F.Cu at 88.7848,117.5776 mm ↔ Track [SCL] on F.Cu, length 0.7291 mm at 78.2354,65.9277 mm

### SCL1 — 2 missing links

- Pad C7 [SCL1] of U15 on F.Cu at 59.4904,111.7979 mm ↔ Pad 12 [SCL1] of CN1 on F.Cu at 79.2819,132.8698 mm
- Track [SCL1] on In1.Cu, length 15.1359 mm at 92.0021,95.8545 mm ↔ Pad C7 [SCL1] of U15 on F.Cu at 59.4904,111.7979 mm

### SCL2 — 2 missing links

- Pad 9 [SCL2] of CN1 on F.Cu at 78.9319,134.7852 mm ↔ Track [SCL2] on In2.Cu, length 45.8906 mm at 90.2647,125.1341 mm
- Track [SCL2] on In2.Cu, length 45.8906 mm at 90.2647,125.1341 mm ↔ Pad 13 [SCL2] of U1 on B.Cu at 78.4104,110.0146 mm

### SDA — 2 missing links

- Track [SDA] on In3.Cu, length 14.6647 mm at 51.5789,31.5549 mm ↔ Pad E4 [SDA] of U2 on B.Cu at 65.7097,32.4772 mm
- Pad 7 [SDA] of U5 on F.Cu at 88.7848,117.9777 mm ↔ Track [SDA] on F.Cu, length 0.7042 mm at 79.7353,65.9277 mm

### SDA1 — 1 missing links

- Pad 11 [SDA1] of CN1 on F.Cu at 79.2819,134.7852 mm ↔ Pad C6 [SDA1] of U15 on F.Cu at 59.1404,111.7979 mm

### SD_STATE — 1 missing links

- Pad 23 [SD_STATE] of MDBT531 on F.Cu at 83.8102,66.8776 mm ↔ Pad 3 [SD_STATE] of Q3 on F.Cu at 110.3102,44.1278 mm

### SPI_CLK — 2 missing links

- Pad 29 [SPI_CLK] of MDBT531 on F.Cu at 83.8602,68.4776 mm ↔ Pad H2 [SPI_CLK] of U14 on F.Cu at 104.7598,109.8277 mm
- Pad 3 [SPI_CLK] of U10 on B.Cu at 93.4594,34.0952 mm ↔ Pad 29 [SPI_CLK] of MDBT531 on F.Cu at 83.8602,68.4776 mm

### SPI_CS — 2 missing links

- Pad 17 [SPI_CS] of MDBT531 on F.Cu at 81.5602,66.8776 mm ↔ Pad 7 [SPI_CS] of U10 on B.Cu at 94.4919,35.1277 mm
- Pad 7 [SPI_CS] of U10 on B.Cu at 94.4919,35.1277 mm ↔ Pad 1 [SPI_CS] of U10 on B.Cu at 92.6596,34.1453 mm

### SPI_CS_FLASH — 1 missing links

- Pad 43 [SPI_CS_FLASH] of MDBT531 on F.Cu at 83.8102,73.0778 mm ↔ Pad D4 [SPI_CS_FLASH] of U14 on F.Cu at 105.4599,110.6276 mm

### SPI_MISO — 2 missing links

- Pad 18 [SPI_MISO] of MDBT531 on F.Cu at 81.9852,65.9277 mm ↔ Pad F4 [SPI_MISO] of U14 on F.Cu at 105.4599,110.2278 mm
- Pad 4 [SPI_MISO] of U10 on B.Cu at 93.8595,34.0952 mm ↔ Pad 18 [SPI_MISO] of MDBT531 on F.Cu at 81.9852,65.9277 mm

### SPI_MOSI — 2 missing links

- Pad 19 [SPI_MOSI] of MDBT531 on F.Cu at 82.3103,66.8776 mm ↔ Pad G3 [SPI_MOSI] of U14 on F.Cu at 105.1099,110.0276 mm
- Pad 2 [SPI_MOSI] of U10 on B.Cu at 93.0596,34.0952 mm ↔ Pad 19 [SPI_MOSI] of MDBT531 on F.Cu at 82.3103,66.8776 mm

### SPI_MOSI_SD — 1 missing links

- Pad 3 [SPI_MOSI_SD] of CARD1 on F.Cu at 76.9048,17.8428 mm ↔ Pad 11 [SPI_MOSI_SD] of U10 on B.Cu at 93.0596,35.7602 mm

### TCK — 1 missing links

- Pad A5 [TCK] of U15 on F.Cu at 58.7904,112.4979 mm ↔ Pad 8 [TCK] of J1 on B.Cu at 78.4102,53.0977 mm

### TDI — 1 missing links

- Pad A8 [TDI] of U15 on F.Cu at 59.8404,112.4979 mm ↔ Pad 2 [TDI] of J1 on B.Cu at 76.0102,53.0977 mm

### TDO — 1 missing links

- Pad A7 [TDO] of U15 on F.Cu at 59.4904,112.4979 mm ↔ Pad 4 [TDO] of J1 on B.Cu at 76.8103,53.0977 mm

### TMS — 1 missing links

- Pad A6 [TMS] of U15 on F.Cu at 59.1404,112.4979 mm ↔ Pad 6 [TMS] of J1 on B.Cu at 77.6101,53.0977 mm

### TS — 2 missing links

- Pad 2 [TS] of R6 on B.Cu at 45.4599,5.4193 mm ↔ Track [TS] on In2.Cu, length 6.9756 mm at 45.5669,12.0935 mm
- Pad C3 [TS] of U2 on B.Cu at 66.5098,32.8772 mm ↔ Pad 1 [TS] of R13 on B.Cu at 45.9999,12.4448 mm

### VCC — 2 missing links

- Track [VCC] on B.Cu, length 0.3628 mm at 62.5355,24.9777 mm ↔ Pad 1 [VCC] of C19 on B.Cu at 63.0841,24.9776 mm
- Track [VCC] on B.Cu, length 0.4000 mm at 66.9098,33.6773 mm ↔ Track [VCC] on In1.Cu, length 1.7904 mm at 62.2106,25.6614 mm

### VUSB — 3 missing links

- Pad 2 [VUSB] of R13 on B.Cu at 45.9999,13.3104 mm ↔ Track [VUSB] on B.Cu, length 0.5717 mm at 46.4325,12.8776 mm
- Pad A2 [VUSB] of U2 on B.Cu at 67.3099,33.2773 mm ↔ Track [VUSB] on In3.Cu, length 0.7377 mm at 73.2902,25.4868 mm
- Track [VUSB] on In1.Cu, length 7.9644 mm at 82.9277,26.4222 mm ↔ Pad 1 [VUSB] of C22 on B.Cu at 74.8099,26.349 mm

### V_LS — 11 missing links

- Track [V_LS] on F.Cu, length 0.6146 mm at 48.0595,99.7249 mm ↔ Pad 1 [V_LS] of C44 on B.Cu at 47.6496,100.3707 mm
- Track [V_LS] on F.Cu, length 0.5717 mm at 48.2104,108.5223 mm ↔ Pad 1 [V_LS] of C34 on B.Cu at 48.2103,108.5727 mm
- Pad A2 [V_LS] of U15 on F.Cu at 57.7404,112.4979 mm ↔ Pad B5 [V_LS] of U15 on F.Cu at 58.7904,112.1479 mm
- Pad F3 [V_LS] of U15 on F.Cu at 58.0904,110.7479 mm ↔ Pad G2 [V_LS] of U15 on F.Cu at 57.7404,110.3978 mm
- Pad F3 [V_LS] of U15 on F.Cu at 58.0904,110.7479 mm ↔ Pad F7 [V_LS] of U15 on F.Cu at 59.4904,110.7479 mm
- Pad 1 [V_LS] of C13 on B.Cu at 69.4037,119.5199 mm ↔ Track [V_LS] on B.Cu, length 0.4637 mm at 69.1295,119.7942 mm
- Pad 2 [V_LS] of C38 on B.Cu at 69.4102,132.402 mm ↔ Track [V_LS] on B.Cu, length 0.4637 mm at 69.6844,132.1277 mm
- Pad 8 [V_LS] of CN1 on F.Cu at 78.5819,132.8693 mm ↔ Track [V_LS] on In3.Cu, length 3.6570 mm at 69.8848,129.5335 mm
- Track [V_LS] on B.Cu, length 1.5083 mm at 94.4917,34.3279 mm ↔ Track [V_LS] on B.Cu, length 0.3998 mm at 92.0276,34.3279 mm
- Pad D2 [V_LS] of U14 on F.Cu at 104.7598,110.6276 mm ↔ Pad H4 [V_LS] of U14 on F.Cu at 105.4599,109.8277 mm
- Pad D2 [V_LS] of U14 on F.Cu at 104.7598,110.6276 mm ↔ Via [V_LS] on F.Cu - B.Cu at 97.8598,116.8499 mm

### V_PMID — 2 missing links

- Track [V_PMID] on B.Cu, length 0.2009 mm at 67.3099,32.8772 mm ↔ Track [V_PMID] on In3.Cu, length 16.6520 mm at 71.1914,32.472 mm
- Pad 1 [V_PMID] of C9 on B.Cu at 78.7604,26.362 mm ↔ Track [V_PMID] on B.Cu, length 0.4637 mm at 78.486,26.0877 mm

### V_SD — 2 missing links

- Track [V_SD] on B.Cu, length 0.6718 mm at 104.4599,4.2227 mm ↔ Pad 2 [V_SD] of C8 on B.Cu at 104.4598,3.1326 mm
- Pad 1 [V_SD] of C6 on B.Cu at 109.0097,1.0034 mm ↔ Track [V_SD] on B.Cu, length 0.4637 mm at 108.7355,1.2777 mm

### XL1 — 1 missing links

- Track [XL1] on B.Cu, length 2.9179 mm at 110.5339,65.8956 mm ↔ Pad 2 [XL1] of C14 on B.Cu at 109.9855,62.9776 mm

### XL2 — 1 missing links

- Pad 2 [XL2] of C2 on B.Cu at 109.9855,84.4276 mm ↔ Track [XL2] on B.Cu, length 6.6294 mm at 110.5339,77.7983 mm

### XTALI — 2 missing links

- Pad B7 [XTALI] of U15 on F.Cu at 59.4904,112.1479 mm ↔ Pad 2 [XTALI] of C46 on B.Cu at 64.199,117.0602 mm
- Pad 2 [XTALI] of C46 on B.Cu at 64.199,117.0602 mm ↔ Track [XTALI] on B.Cu, length 0.6968 mm at 64.7476,117.0602 mm

### XTALO — 1 missing links

- Pad B6 [XTALO] of U15 on F.Cu at 59.1404,112.1479 mm ↔ Pad 2 [XTALO] of R28 on F.Cu at 60.0974,133.2397 mm

## Recheck

```sh
kicad-cli pcb drc --format json -o routing-evidence/final.json kicad/haven_dev_board.kicad_pcb
/usr/bin/python3 routing-evidence/audit_final.py
```

Replay scripts are historical attempts, not an idempotent batch pipeline. Do not run rejected scripts on the final board. Review each script and its logged starting state before replaying.

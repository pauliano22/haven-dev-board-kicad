# Haven v2 behind-the-ear (BTE): schematics

v2's form factor is behind-the-ear (decision 2026-11-03, `HAVEN_V2.md` in the workspace). A pod
behind the ear holds the battery and main board. A fixed thin cable runs over the top of the ear
to a small in-ear unit with the mic, the speaker, the nozzle and the tip.

**Two boards, two KiCad projects:**

| Folder | Board | What's on it |
|---|---|---|
| `kicad_v2_pod/` | Pod board (6-layer, fine pitch) | MDBT53V-1M, nPM1100, ADAU1860 + 24.576 MHz crystal, load switch, status LED, charge pads, SWD pads, cable ESD, cable pads |
| `kicad_v2_inear/` | In-ear board (tiny, 2-layer) | SPH0641 mic, 100 nF, 33 Ω series resistor, cable pads, speaker pads |

The boards are fabricated, assembled and laid out separately, and they share nothing but the
cable. Two projects keep each board's DRC rules, stackup and BOM independent: the pod needs the
6-layer fine-pitch rules for the 0.35 mm BGA, while the in-ear board can be a cheap 2-layer
0.6 mm board. A hierarchical single project would force one stackup on both.

**Generated.** `tools/gen_v2_bte_schematic.py` writes both folders. It reuses the parts, symbols
and writer in `tools/gen_v2_schematic.py`, which still generates the single-board pebble design
in `kicad_v2/`. Edit the scripts, not the `.kicad_sch` files.

## Status (2026-11-03)
- Pod: 76 parts, 47 nets. In-ear: 11 parts, 7 nets.
- `kicad-cli sch erc`: **0 violations on both**.
- Exported netlists match the scripts' intended netlists on every net (0 mismatches).
- BOM export works: `kicad_v2_pod/haven_v2_pod_bom.csv`, `kicad_v2_inear/haven_v2_inear_bom.csv`.
- No PCB layout yet. All symbol pins are "passive", so ERC checks wiring, not driver conflicts.

## Cable harness (6 conductors, ~80–100 mm, fixed)
| Pad | Pod net | In-ear net | Signal | Notes |
|---|---|---|---|---|
| W1 | V_LS | V_MIC | Mic supply, 1.8 V | Switched by U3 with the codec |
| W2 | GND | GND | Ground | Lay it between PDM_CLK and PDM_DATA |
| W3 | CBL_PDMCLK | PDM_CLK | PDM clock, codec → mic | 33 Ω series R120 at the pod (the source) |
| W4 | PDMDIN | PDM_DATA | PDM data, mic → codec | 33 Ω series R1 at the mic (the source) |
| W5 | SPK+ | SPK+ | Speaker + | Twist with SPK− |
| W6 | SPK− | SPK− | Speaker − | |

**Cable:** 6 conductors of 38–40 AWG stranded copper (Litz or PTFE-insulated), the speaker pair
twisted, CLK–GND–DATA adjacent, a TPE or PU jacket of about 1.4–1.6 mm, and an aramid strength
member tied off at both ends. Hearing-aid receiver (RIC) wire usually has only 2–4 conductors, so
it isn't enough on its own. A first build can be hand-made from six PTFE wires under heat-shrink.
**Strain relief** is mechanical and belongs to layout and the shell: put the pads in one row at
the board edge where the cable exits, add an anchor slot for the aramid knot, and pot the joint.

## Decisions

**Mic in the in-ear unit, not the pod.** A mic at the ear-canal entrance hears the room through
the wearer's own outer ear, which keeps natural direction and pinna cues in hear-through. A mic
on the pod behind the ear would sound less natural.
- The PDM clock is **3.072 MHz** (`DMIC_CTRL1 = 0x33` in `haven-zephyr-app/src/adau1860_control.c`),
  so the bit period is 325 ns. Signal delay along 100 mm of cable is about 0.5 ns, negligible
  for timing.
- Edges a few ns long on 100 mm can ring, so each PDM line has a 33 Ω series resistor at its
  source: R120 for the clock at the codec, R1 for the data at the mic. Each runs next to the
  ground conductor.
- Crosstalk is low risk. The speaker lines carry audio-band signals from a low-impedance driver,
  and their coupling into the PDM lines is millivolts. The PDM edges coupling back into the speaker
  is far above audio.
- **Fallback if bring-up shows trouble:** move the mic to the pod (place U13 back on the pod
  board as in `kicad_v2/`), which drops the cable to 2 conductors (SPK±). This is a layout change
  only; the netlist is the same as the single-board design.

**ESD on every cable line leaving the pod** (D2–D6, TI TPD1E05U06DYAR, SOD-523: 5.5 V stand-off,
0.42 pF, ±IEC 61000-4-2 level 4). The cable is touched and the in-ear unit has an open mic port.
D1, the same part, now protects the exposed VBUS charge pad. Pinout from TI SLVSBO7O (rev. O,
2024) Table 4-1: pin 1 I/O, pin 2 GND. The footprint follows TI's DYA0002A land pattern example:
0.4 × 0.67 mm pads, 1.48 mm overall. Check it against TI's drawing once more during layout.

**Battery CP1454 instead of CP1254** (the pod has room). The charge resistor R111 is now 15 kΩ,
for about 40 mA. Nordic's tables give 30 kΩ = 20 mA and 12 kΩ = 50 mA, consistent with
I ≈ 600 V / R at low currents. That's 0.37C for the 108 mAh CP1454 and 0.47C for the 85 mAh
version, so under 0.5C either way: about a 2.5–3 h charge. Termination stays 4.20 V.

**nRF DC/DC inductors not fitted on the first build** (L101/L102 are marked DNP). The module then
runs on its internal LDO, which costs some current but takes a part that's hard to source out of
the first order. Fit a 10 µH 0402 later; nothing else changes.

## Power tree (pod)
```
Case pogo pin (5 V) ─ P1 ─┬─ D1 TPD1E05U06 ESD
                          ├─ R114/R115 divider ─ VBUS_DET (P0.25/AIN4): "in case"
                          └─ nPM1100 VBUS (100 mA input limit)
                               ├─ charger ─ VBAT ─ CP1454 (85–108 mAh), ~40 mA, 4.20 V
                               └─ VSYS
                                    ├─ R112/R113 divider ─ VSYS_SENSE (P0.05/AIN1)
                                    ├─ status LED (U4, R4, Q2)
                                    └─ buck 2.2 µH ─ +1V8
                                         ├─ MDBT53V-1M VDD + VDDH (LDO mode on the first build)
                                         └─ U3 (SENSORS_ENABLE, P1.11) ─ V_LS
                                              ├─ ADAU1860
                                              └─ cable W1 ─ in-ear V_MIC ─ SPH0641
```

## nRF5340 pins and firmware impact
**None.** Every nRF pin is the same as the single-board v2 schematic (`kicad_v2/README.md` pin
table), so the `haven_v2` board target in `haven-zephyr-app` (PR #25) applies unchanged. The codec
still drives the same PDM pins. Only the mic's physical location changes. Firmware may want to
retune for the cable only if bring-up shows PDM errors (for example by lowering the DMIC clock).

## In-ear board
Outline target about **6 × 6 mm**, 2-layer, 0.6 mm thick. It holds the mic (3.5 × 2.7 mm,
**bottom port: drill a 0.5–0.8 mm hole through the board under the port**), C1 and R1 in 0201,
six 0.8 mm cable pads and two 1.2 mm speaker pads. The mic is LGA, so have it assembled, not
hand-soldered.

## Sourcing gaps filled since the single-board v2
| Part | Choice | LCSC |
|---|---|---|
| R111 | 15 kΩ 1% 0201, 0201WMF1502TEE | C473452 |
| R113 | 560 kΩ 1% 0201, RC0201FR-07560KL | C295807 (stock not confirmed) |
| R114 | 100 kΩ 1% 0201, RC0201FR-07100KL | C106224 (stock not confirmed) |
| R115 | 47 kΩ 1% 0201, RC0201FR-0747KL | C138139 |
| C110 | 2.2 µF 25 V X5R 0402, CL05A225KA5NUNC | C307418 |
| R120, in-ear R1 | 33 Ω 1% 0201, ERJ1GNF33R0C | C717007 |
| D1–D6 | TI TPD1E05U06DYAR | **LCSC number not confirmed**; check at upload |
| L101/L102 | not fitted on the first build | – |

Stock was looked up through the JLCSearch catalogue (2026-11-03), which doesn't report stock for
every row. Confirm everything at JLCPCB's BOM upload.

## Open questions
1. TPD1E05U06DYAR LCSC availability; fallback is any 5–5.5 V, < 1 pF SOD-523 TVS with pin 1 = I/O.
2. The nPM1100 land pattern and other open items from `kicad_v2/README.md` still apply.
3. Speaker part (8 mm, 16–32 Ω) still not chosen.
4. Real cable part: choose and measure capacitance per conductor before layout freezes.

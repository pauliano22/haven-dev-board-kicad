# Remaining connections needing manual completion
Generated from KiCad DRC's `unconnected_items` report on the current board
(after autorouting + copper pour fill, antenna keepout added). This is the
**authoritative** list — it reflects actual remaining gaps after the
GND/+1.8V/V_LS zone pours are already accounted for, not the autorouter's
own raw pre-zone count.

**Why these are still open**: see `HAVEN_HARDWARE_REVIEW.md` section 9 —
most of this concentrates on fine-pitch BGA/QFN parts (U15 ADAU1860 at
0.35mm pitch, U2 at 0.40mm, MDBT531, U10, CN1) that need manual
escape-routing a generic autorouter can't reliably close. A few entries are
"dangling track stub" — a short trace segment that reaches partway toward a
plane but doesn't quite land on it; these are usually the easiest to fix
(just extend or add one via).

**How to use this list**: for each net below, every listed pin needs to end
up on the same electrical net. If a net already has most of its pins routed
correctly (check in KiCad — the ratsnest/airwire view will show what's
already connected), these are just the specific stragglers. For a net with
only one listed item, that single pin is isolated and needs a trace or via
run to reach the rest of its own net.

**If fabricating before finishing these**: every pin listed here will need
a manual bodge wire after assembly, soldered directly between the pin (or
an exposed via/test point on that net) and the nearest reachable point on
the same net. `GND` and `V_LS` are the largest groups and also have a
full-board copper pour — for those, the fix is usually just "add a via near
this pad down to the plane," which is a fast fix once you can see the board
under a scope, not a long trace run.

---

### #ERROR (2 item(s))
- Q2 pin 1
- (dangling track stub near 75.1752mm,45.8508mm)

### $1N151 (3 item(s))
- U15 pin A3
- U15 pin B3
- (dangling track stub near 56.1710mm,120.4777mm)

### $1N2586 (2 item(s))
- C32 pin 1
- U15 pin G4

### $1N65 (2 item(s))
- C10 pin 1
- U2 pin C4

### $1N70 (2 item(s))
- C23 pin 2
- (dangling track stub near 45.6329mm,32.6482mm)

### +1.8V (2 item(s))
- U2 pin B5
- (dangling track stub near 79.1404mm,30.9936mm)

### 3V3 (4 item(s))
- CN1 pin 3
- U2 pin C5
- (dangling track stub near 64.6212mm,43.2827mm)
- (dangling track stub near 65.1173mm,133.8556mm)

### BCLK (2 item(s))
- MDBT531 pin 59
- U15 pin B2

### CC_#CD (2 item(s))
- MDBT531 pin 26
- U2 pin E2

### CC_#PG (2 item(s))
- MDBT531 pin 16
- U2 pin D4

### DAC_ENABLE (2 item(s))
- MDBT531 pin 37
- U15 pin E4

### DIN (2 item(s))
- MDBT531 pin 60
- U15 pin C1

### DOUT (2 item(s))
- MDBT531 pin 56
- U15 pin B1

### FLASH_RESET (2 item(s))
- MDBT531 pin 51
- U14 pin F2

### GND (58 item(s))
- C13 pin 2
- C14 pin 1
- C19 pin 2
- C2 pin 1
- C22 pin 2
- C23 pin 1
- C31 pin 2
- C34 pin 2
- C38 pin 1
- C44 pin 2
- C46 pin 1
- C6 pin 2
- C8 pin 1
- C9 pin 2
- CN1 pin 10
- CRYSTAL1 pin 2
- MDBT531 pin 1
- MDBT531 pin 61
- Q2 pin 2
- R6 pin 1
- R8 pin 1
- U10 pin 6
- U10 pin 8
- U14 pin E3
- U15 pin A1
- U15 pin A4
- U15 pin B4
- U15 pin D6
- U15 pin D7
- U15 pin E6
- U15 pin F1
- U15 pin G3
- U15 pin G7
- U2 pin A1
- U2 pin A5
- U6 pin B2
- (dangling track stub near 104.4599mm,3.1326mm)
- (dangling track stub near 108.5833mm,29.1035mm)
- (dangling track stub near 109.2839mm,1.2777mm)
- (dangling track stub near 109.9855mm,63.4602mm)
- (dangling track stub near 109.9855mm,84.4277mm)
- (dangling track stub near 45.0845mm,31.9462mm)
- (dangling track stub near 45.4597mm,5.4193mm)
- (dangling track stub near 47.0765mm,106.0201mm)
- (dangling track stub near 48.2104mm,107.4322mm)
- (dangling track stub near 62.6603mm,44.2929mm)
- (dangling track stub near 63.0839mm,24.9777mm)
- (dangling track stub near 64.1990mm,117.0602mm)
- (dangling track stub near 66.1097mm,31.8362mm)
- (dangling track stub near 66.5098mm,33.6758mm)
- (dangling track stub near 69.1360mm,132.1277mm)
- (dangling track stub near 69.6779mm,119.7942mm)
- (dangling track stub near 75.0839mm,26.0747mm)
- (dangling track stub near 78.4095mm,58.2678mm)
- (dangling track stub near 79.0344mm,26.0877mm)
- (dangling track stub near 94.3623mm,118.1015mm)
- (dangling via stub near 64.2879mm,116.3819mm)
- (dangling via stub near 79.0980mm,129.5594mm)

### INT (2 item(s))
- MDBT531 pin 14
- U2 pin D2

### IO5 (2 item(s))
- CN1 pin 4
- MDBT531 pin 21

### LRCLK (2 item(s))
- MDBT531 pin 57
- U15 pin C2

### LSCTRL (2 item(s))
- MDBT531 pin 27
- U2 pin E3

### MR# (3 item(s))
- Q1 pin 1
- U2 pin E1
- (dangling track stub near 79.8358mm,108.0094mm)

### PDMCLK (2 item(s))
- U15 pin C4
- (dangling track stub near 75.4870mm,126.7333mm)

### PDMDIN (3 item(s))
- CN1 pin 7
- U13 pin 1
- U15 pin C5

### RESETN (2 item(s))
- U2 pin D3
- (dangling track stub near 78.8037mm,40.4254mm)

### SCL (2 item(s))
- U5 pin 6
- (dangling track stub near 78.2354mm,65.9277mm)

### SCL1 (3 item(s))
- CN1 pin 12
- U15 pin C7
- (dangling track stub near 92.0021mm,95.8545mm)

### SCL2 (3 item(s))
- CN1 pin 9
- U1 pin 13
- (dangling track stub near 90.2647mm,125.1341mm)

### SDA (4 item(s))
- U2 pin E4
- U5 pin 7
- (dangling track stub near 61.9484mm,41.9244mm)
- (dangling track stub near 79.7353mm,65.9277mm)

### SDA1 (2 item(s))
- U15 pin C6
- (dangling track stub near 79.2819mm,135.4461mm)

### SD_STATE (2 item(s))
- MDBT531 pin 23
- Q3 pin 3

### SPI_CLK (3 item(s))
- MDBT531 pin 29
- U10 pin 3
- U14 pin H2

### SPI_CS (3 item(s))
- MDBT531 pin 17
- U10 pin 1
- U10 pin 7

### SPI_CS_FLASH (2 item(s))
- MDBT531 pin 43
- U14 pin D4

### SPI_MISO (3 item(s))
- MDBT531 pin 18
- U10 pin 4
- U14 pin F4

### SPI_MOSI (3 item(s))
- MDBT531 pin 19
- U10 pin 2
- U14 pin G3

### SPI_MOSI_SD (2 item(s))
- CARD1 pin 3
- U10 pin 11

### SW (2 item(s))
- L2 pin 1
- U2 pin A4

### TCK (2 item(s))
- J1 pin 8
- U15 pin A5

### TDI (2 item(s))
- J1 pin 2
- U15 pin A8

### TDO (2 item(s))
- J1 pin 4
- U15 pin A7

### TMS (2 item(s))
- J1 pin 6
- U15 pin A6

### TS (4 item(s))
- R13 pin 1
- R6 pin 2
- U2 pin C3
- (dangling track stub near 45.5669mm,12.0935mm)

### VCC (4 item(s))
- C19 pin 1
- (dangling track stub near 62.2106mm,25.6614mm)
- (dangling track stub near 62.5355mm,24.9777mm)
- (dangling track stub near 66.9098mm,33.6773mm)

### VUSB (6 item(s))
- C22 pin 1
- R13 pin 2
- U2 pin A2
- (dangling track stub near 46.4325mm,12.8776mm)
- (dangling track stub near 69.2443mm,21.4409mm)
- (dangling track stub near 74.9633mm,26.4222mm)

### V_LS (23 item(s))
- C13 pin 1
- C34 pin 1
- C38 pin 2
- C44 pin 1
- CN1 pin 8
- U10 pin 5
- U14 pin D2
- U14 pin H4
- U15 pin A2
- U15 pin B5
- U15 pin D1
- U15 pin E1
- U15 pin F3
- U15 pin F7
- U15 pin G2
- (dangling track stub near 48.0595mm,99.7249mm)
- (dangling track stub near 48.2104mm,108.5223mm)
- (dangling track stub near 50.9004mm,110.5491mm)
- (dangling track stub near 69.1295mm,119.7942mm)
- (dangling track stub near 69.6844mm,132.1277mm)
- (dangling track stub near 73.5418mm,129.5335mm)
- (dangling track stub near 92.0276mm,34.3279mm)
- (dangling via stub near 97.8598mm,116.8499mm)

### V_PMID (4 item(s))
- C9 pin 1
- (dangling track stub near 67.3099mm,32.8772mm)
- (dangling track stub near 78.2616mm,25.4018mm)
- (dangling track stub near 78.4860mm,26.0877mm)

### V_SD (4 item(s))
- C6 pin 1
- C8 pin 2
- (dangling track stub near 104.4599mm,4.2227mm)
- (dangling track stub near 108.7355mm,1.2777mm)

### XL1 (2 item(s))
- C14 pin 2
- (dangling track stub near 110.5339mm,65.8956mm)

### XL2 (2 item(s))
- C2 pin 2
- (dangling track stub near 110.5339mm,77.7983mm)

### XTALI (3 item(s))
- C46 pin 2
- U15 pin B7
- (dangling track stub near 64.7476mm,117.0602mm)

### XTALO (2 item(s))
- R28 pin 2
- U15 pin B6


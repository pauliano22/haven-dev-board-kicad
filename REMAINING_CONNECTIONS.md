# Remaining connections needing manual completion

Generated from KiCad DRC's `unconnected_items` report on the current board
(after autorouting + copper pour fill). This is the **authoritative** list —
it reflects actual remaining gaps after the GND/+1.8V/V_LS zone pours are
already accounted for, not the autorouter's own raw pre-zone count.

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

### #ERROR (1 item(s))
- (dangling track stub near 75.1752mm,45.8508mm)

### $1N151 (1 item(s))
- U15 pin A3

### $1N2586 (1 item(s))
- U15 pin G4

### $1N65 (1 item(s))
- U2 pin C4

### $1N70 (1 item(s))
- C23 pin 2

### +1.8V (1 item(s))
- (dangling track stub near 79.1404mm,30.9936mm)

### 3V3 (2 item(s))
- C48 pin 1
- U2 pin C5

### BCLK (1 item(s))
- U15 pin B2

### CC_#CD (1 item(s))
- U2 pin E2

### CC_#PG (1 item(s))
- U2 pin D4

### DAC_ENABLE (1 item(s))
- U15 pin E4

### DIN (1 item(s))
- U15 pin C1

### DOUT (1 item(s))
- U15 pin B1

### FLASH_RESET (1 item(s))
- MDBT531 pin 51

### GND (31 item(s))
- C13 pin 2
- C14 pin 1
- C2 pin 1
- C6 pin 2
- CN1 pin 10
- CRYSTAL1 pin 2
- Q2 pin 2
- U10 pin 6
- U10 pin 8
- U15 pin F1
- U15 pin G3
- U15 pin B4
- U15 pin A4
- U15 pin D6
- U15 pin G7
- U15 pin D7
- U2 pin A5
- U2 pin A1
- U6 pin B2
- (dangling track stub near 66.5098mm,33.6758mm)
- (dangling track stub near 45.4597mm,5.4193mm)
- (dangling track stub near 63.0839mm,24.9777mm)
- (dangling track stub near 64.1990mm,117.0602mm)
- (dangling track stub near 69.1360mm,132.1277mm)
- (dangling track stub near 79.0344mm,26.0877mm)
- (dangling track stub near 75.0839mm,26.0747mm)
- (dangling track stub near 104.4599mm,3.1326mm)
- (dangling track stub near 45.0845mm,31.9462mm)
- (dangling track stub near 48.2104mm,107.4322mm)
- (dangling track stub near 94.3623mm,118.1015mm)
- (dangling track stub near 47.0765mm,106.0201mm)

### INT (1 item(s))
- U2 pin D2

### IO5 (1 item(s))
- CN1 pin 4

### LRCLK (1 item(s))
- U15 pin C2

### LSCTRL (1 item(s))
- U2 pin E3

### MR# (2 item(s))
- Q1 pin 1
- (dangling track stub near 79.8358mm,108.0094mm)

### PDMCLK (1 item(s))
- U15 pin C4

### PDMDIN (2 item(s))
- CN1 pin 7
- U13 pin 1

### RESETN (1 item(s))
- U2 pin D3

### SCL (1 item(s))
- U5 pin 6

### SCL1 (2 item(s))
- U15 pin C7
- (dangling track stub near 81.2994mm,85.1518mm)

### SCL2 (2 item(s))
- CN1 pin 9
- (dangling track stub near 92.1019mm,126.9713mm)

### SDA (2 item(s))
- U5 pin 7
- (dangling track stub near 61.9484mm,41.9244mm)

### SDA1 (1 item(s))
- (dangling track stub near 79.2819mm,135.4461mm)

### SD_STATE (1 item(s))
- MDBT531 pin 23

### SPI_CLK (2 item(s))
- MDBT531 pin 29
- U10 pin 3

### SPI_CS (2 item(s))
- MDBT531 pin 17
- U10 pin 7

### SPI_CS_FLASH (1 item(s))
- MDBT531 pin 43

### SPI_MISO (2 item(s))
- MDBT531 pin 18
- U10 pin 4

### SPI_MOSI (2 item(s))
- MDBT531 pin 19
- U10 pin 2

### SPI_MOSI_SD (1 item(s))
- CARD1 pin 3

### SW (1 item(s))
- U2 pin A4

### TCK (1 item(s))
- U15 pin A5

### TDI (1 item(s))
- U15 pin A8

### TDO (1 item(s))
- U15 pin A7

### TMS (1 item(s))
- U15 pin A6

### TS (2 item(s))
- R6 pin 2
- U2 pin C3

### VCC (2 item(s))
- (dangling track stub near 62.5355mm,24.9777mm)
- (dangling track stub near 66.9098mm,33.6773mm)

### VUSB (3 item(s))
- R13 pin 2
- U2 pin A2
- (dangling track stub near 82.9277mm,26.4222mm)

### V_LS (13 item(s))
- CN1 pin 8
- U10 pin 5
- U14 pin D2
- U14 pin H4
- U15 pin E1
- U15 pin D1
- U15 pin F3
- U15 pin B5
- U15 pin F7
- (dangling track stub near 69.1295mm,119.7942mm)
- (dangling track stub near 69.6844mm,132.1277mm)
- (dangling track stub near 48.2104mm,108.5223mm)
- (dangling track stub near 48.0595mm,99.7249mm)

### V_PMID (2 item(s))
- C9 pin 1
- (dangling track stub near 67.3099mm,32.8772mm)

### V_SD (2 item(s))
- C6 pin 1
- (dangling track stub near 104.4599mm,4.2227mm)

### XL1 (1 item(s))
- (dangling track stub near 110.5339mm,65.8956mm)

### XL2 (1 item(s))
- C2 pin 2

### XTALI (2 item(s))
- C46 pin 2
- U15 pin B7

### XTALO (1 item(s))
- U15 pin B6


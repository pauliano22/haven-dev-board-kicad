# Haven dev board — order package (crystal-placement-fixed)

Generated from PR #7's board (includes the #5 placement fix + the codec crystal
escape: XTALI now ~1 mm from the codec instead of 6 mm; flash decoupling cap
moved next to its chip). Stock design otherwise: ADAU1860 kept, stock charger.

Verified before packaging: DRC 219 violations / 2 unconnected (identical to the
long-standing baseline, zero new); BOM and placement file both list the same
89 parts (nothing missing either way).

## Upload to PCBWay or JLCPCB (turnkey PCBA, 6-layer, qty 5)
1. haven_dev_board-gerbers.zip   (copper, mask, paste, silk, outline, drill)
2. HAVEN_BOM.csv
3. haven_dev_board-pos.csv
Board: 73.1 x 161.1 mm, 6 layers, 1.6 mm. Order 5, not 1.

## Things to expect / check in their web tool
- **ADAU1860 (U15) will almost certainly not be in their stock** (BGA-56,
  0.35 mm). Expect to be asked to supply it yourself (consignment) or pick a
  sourcing option. Same possible flag for the WLCSP flash and DSBGA parts.
- Look at their 3D preview for rotated/flipped parts before paying.
- Expect an "advanced / high-density" tier (0.35 mm BGA, microvias). That is
  why it's ~$500 - it doesn't go away with any charger swap.
- U1 is BMI160 in the BOM (matches how the board is wired). Upstream firmware
  calls it BMX160 - irrelevant until firmware uses the IMU; if a quote flags
  it as unavailable, it's safe to leave U1 unpopulated for a first bring-up.
- Silkscreen is nearly empty (known, cosmetic).

Nothing has been ordered. Ordering/paying needs you.

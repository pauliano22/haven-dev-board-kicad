# Haven dev board: first-hour bring-up checklist

Do these IN ORDER. Stop at the first failure - each step depends on the last.
Facts below come from the reviewed upstream-derived notes (haven-zephyr-app
PR #9, haven-dev-board-kicad PR #3); anything marked (verify) is unconfirmed.

## Before boards arrive
- [ ] A **debugger/programmer** for the nRF5340 (SWD). The cheapest way is an
      nRF5340 DK, whose "debug out" header programs other boards. (verify the
      board's SWD header/pads and pinout in the schematic first)
- [ ] A **multimeter**, a LiPo battery or bench supply, USB-C cable.
- [ ] Firmware built: haven-zephyr-app driver stack (PRs #8-#14). Build the
      **smoke-test variant first** (DMIC-direct, no DSP - CONFIG_HAVEN_DAC_SOURCE).
- [ ] Optional insurance: build with the internal-RC clock fallback
      (-DFILE_SUFFIX=lfrc, PR #12) in case the 32.768 kHz crystal misbehaves.
- [ ] The **ADAU1860 chip**: confirm it is in the order/consignment, and that
      the PCBA house will actually place it.

## Step 0 - look before powering
- [ ] Inspect under magnification: BGA/WLCSP look aligned, no tombstoned 0201s.
- [ ] Resistance between each main rail and GND (VBAT, +1.8V, 3V3, V_LS):
      none should be a dead short (~0 ohm).

## Step 1 - power
- [ ] Power from USB or battery through a current-limited supply if you can.
- [ ] Measure +1.8V, 3V3, and (after firmware enables it) V_LS ~1.8V.
      V_LS is a load switch - it stays OFF until the MCU turns it on (P1.11).
- [ ] Idle current sane (a few mA, not hundreds). Hot part = power off.

## Step 2 - MCU alive
- [ ] Debugger connects and sees the nRF5340 (both cores).
- [ ] Flash any blinky/log build. Serial/RTT log appears.
      If not: suspect 32.768 kHz crystal or programming connection.

## Step 3 - Bluetooth
- [ ] Phone (nRF Connect app) sees a device advertising as "Haven".
- [ ] Connect and write a JSON line to the NUS RX characteristic.

## Step 4 - codec on the I2C bus
- [ ] Firmware drives DAC_ENABLE (P0.04) high and V_LS (P1.11) on, waits 35 ms.
- [ ] Codec answers on I2C: bus SCL=P1.00, SDA=P1.15, address 0x64 (verify).
      The boot log prints vendor/device/rev ID. If "No response":
      check DAC_ENABLE, the V_LS rail, and the I2C pull-ups.
- [ ] Power-up sequence completes (log shows STATUS2 polls succeed, no timeout).

## Step 5 - first sound
- [ ] Smoke-test build: mic (PDM) -> DAC direct. Speak; hear yourself in the
      earpiece/headphone output. (No DSP in this path, so no limiter - keep
      the output ceiling low and start with speaker OUT of your ear.)
- [ ] Switch to the FastDSP build: hear-through with 5 flat bands.
- [ ] If silent in FastDSP but smoke test works: rebuild with "Route B"
      (EQ engine, PR #13) to localize the fault.
- [ ] Send a MULTI_FILTER from the app; confirm a notch audibly changes.

## Step 6 - safety, before anyone wears it
- [ ] Set the hardware output ceiling (PR #14) conservatively.
- [ ] Do NOT run hearing tests on a build with no limiter in the path
      (dac_source = dmic_direct).
- [ ] Acoustic calibration (PR #11 rig) before trusting any dB numbers.

## If something fails, what to write down
Log output, which step, a photo of the board, and the rail voltages. That is
enough for us to diagnose remotely.

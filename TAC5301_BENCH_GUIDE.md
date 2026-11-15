# TAC5301 bench test: step-by-step guide for Paul

Written 2026-11-14 for the Thanksgiving session. Phone-friendly version with a checklist and pin diagram: https://claude.ai/artifact/SXkNK5PMh6Cjwn3c1Tj5pk (source `visuals/tac5301_bench/`). **Nothing in here has been run on hardware.** The firmware builds and
its host tests pass; the wiring comes from TI's datasheet (SLASFD9A, copy in `~/.cache/haven_datasheets/tac5301/`).
Background and register details: `TAC5301_BENCH_EXPERIMENT.md`.

**What this test is.** One TAC5301 chip on an adapter board, a microphone, a speaker and the nRF5340 dev kit (DK) on a
breadboard. If it works, sound into the microphone comes out of the speaker through the chip, and then the delay can be
measured. It answers one question: is this cheaper, easier-to-solder chip fast enough to replace the ADAU1860.
**It is not needed for the v3 pod**, which uses the ADAU1860. Skip it and nothing in the v3 plan changes.

**What you have:** 2 chips, 2 adapter boards, 2 microphones, 1 speaker, the DK. So you get two attempts at the soldering.

## 1. Three things found while preparing this (2026-11-14)

1. **The adapter fits.** Schmartboard 204-0015-01 has a 24-pin, 0.5 mm, 4 x 4 mm position. That is this chip's package.
2. **The chip's main ground is the metal square under its belly, and the adapter has no pad for it, only a hole.**
   The four corner contacts are also grounds and the adapter has no pads for them either. If the belly pad is not
   soldered (through the hole, from the back), the chip has no digital ground and will not answer. Step 3.4 covers it.
3. **The bench firmware had two faults that would have given silence.** It never woke the chip from its sleep state,
   and it stopped the audio clock whenever no test tone was playing. Both are fixed, with tests. The firmware now also
   asks the chip for its status and prints a plain PASS or what is missing.

## 2. What you need besides the kit

Check this list **before** the trip. Anything missing is a few dollars but takes days to arrive.

| Item | How many | Notes |
|---|---|---|
| Breadboard, full or half size | 1 | |
| Jumper wires, pin-to-pin (male-male) | about 20 | The DK's headers are sockets |
| 9 V battery and a snap-on clip with wires | 1 | Powers the microphone bias only |
| Capacitor 0.1 uF ceramic, with legs | 3 | |
| Capacitor 1 uF ceramic, with legs, **rated 25 V or more** | 5 | Two of them see 9 V |
| Capacitor 10 uF, with legs (ceramic or electrolytic, 10 V or more) | 3 | Electrolytic: the striped leg is minus, to ground |
| Resistor 4.7 kohm | 2 | |
| Resistor 2.2 kohm | 1 | |
| Resistor 100 ohm | 1 | Keeps the speaker quiet for the first power-up |
| Soldering iron with a fine tip, **0.5 mm or smaller** | 1 | Schmartboard's own rule: tip no wider than the pin spacing |
| Flux pen or flux paste | 1 | Not optional for this |
| Thin solder (0.5 mm or thinner) | | Only for the belly pad and the header pins |
| Solder wick (braid) | | To remove a bridge |
| Masking tape, tweezers, a magnifier or phone macro lens | | |
| Multimeter with a continuity beeper | 1 | Used in four steps below |
| Micro-USB cable for the DK, and the laptop with this workspace | | |

Not needed for the first session: an oscilloscope or audio interface. Those are for the delay measurement (section 7).

## 3. Solder the chip to the adapter (the hard part; about an hour, unhurried)

The adapter has two positions. Use the **24-pin** one (marked "QFN 24PINS", "4x4 mm"). The chip sits turned 45 degrees,
on the X of silver fingers. The silver fingers already carry solder; you add none to them.

1. **Find pin 1 on both.** On the chip, pin 1 is at the corner with the dot. On the adapter, header hole 1 is printed
   "1". With the multimeter on beep, touch header hole 1 and find which silver finger beeps. That finger takes chip pin 1.
   Pins count **counter-clockwise** looking down at the top of the chip.
2. **Before soldering, learn the grounds.** Turn a chip upside down. Beep between the big centre square and each of the
   four corner contacts. They should all beep together (they are one piece of metal inside). Write down what you see.
   If they do not beep, tell me before going on: the plan for grounding changes.
3. **Place and tape.** Flux the fingers. Set the chip on the X, dot toward the pin-1 finger, belly square over the hole.
   Check with the magnifier that every contact sits on its own finger on all four sides. Tape across one side to hold it.
4. **Solder the belly pad first, from the back.** Turn the board over, holding the chip in place. Put flux in the hole,
   touch the iron inside the hole against the chip's metal, feed thin solder until the hole is filled, about 3 seconds.
   This fixes the chip in place and is the ground connection. Then solder a short wire into that solder blob, or onto the
   ring around the hole: this wire goes to ground on the breadboard.
5. **Solder the four sides.** For each finger: put the iron tip in the groove at the outer end and slide it toward the
   chip until it touches. Do not press down. Flux each side before you do it. Remove the tape for the last side.
6. **Inspect.** Under the magnifier, no solder should join two neighbouring fingers. A bridge: add flux, drag the wick
   and iron across it.
7. **Meter check, no power yet.** Neighbouring header holes must NOT beep with each other, with one expected
   exception: holes 10 and 12 are both ground and may beep with each other and with the belly-pad wire (11 sits
   between them and must NOT beep with either). Holes 11 and 23 are the same supply and may beep with each other.
   Anything else beeping with its neighbour is a bridge.
8. Solder the two rows of header pins into the adapter and push it into the breadboard across the centre gap.

## 4. Wire it up (power off, battery unplugged)

Header hole numbers are the chip's pin numbers. "DK" is the dev kit. Ground everywhere means the breadboard's ground rail,
which is joined to a **GND** pin on the DK and to the battery's black wire.

| Adapter pin | Chip name | Connect to |
|---|---|---|
| belly-pad wire | VSS (ground) | Ground. **Required.** |
| 1 | DREG | 10 uF capacitor to ground. Nothing else |
| 2 | BCLK | DK pin **P1.06** |
| 3 | FSYNC | DK pin **P1.07** |
| 4 | DOUT | leave empty |
| 5 | DIN | DK pin **P1.08** |
| 6 | IOVDD | DK **VDD** pin, and a 0.1 uF capacitor to ground |
| 7 | SCL | DK pin **P1.03**, and a 4.7 kohm resistor to the DK VDD rail |
| 8 | SDA | DK pin **P1.02**, and a 4.7 kohm resistor to the DK VDD rail |
| 9 | GPIO1 | leave empty |
| 10 | VSSA | Ground |
| 11 | AVDD | DK **VDD** rail, with a 0.1 uF and a 10 uF capacitor to ground |
| 12 | VSSA | Ground |
| 13 | HVDD | Battery red wire (9 V), and a 1 uF capacitor to ground. **Connect the battery last** |
| 14 | MICBIAS | 1 uF capacitor to ground, and the 2.2 kohm resistor to the microphone's + pin |
| 15 | IN1P | 1 uF capacitor, other leg to the microphone's + pin |
| 16 | IN1M | 1 uF capacitor, other leg to ground |
| 17, 18 | IN2P, IN2M | leave empty |
| 19 | OUT1M | Speaker, one wire |
| 20 | OUT1P | 100 ohm resistor, then the speaker's other wire |
| 21, 22 | OUT2P, OUT2M | leave empty |
| 23 | AVDD | DK **VDD** rail, with a 0.1 uF capacitor to ground |
| 24 | VREF | 1 uF capacitor to ground. Nothing else |

- **Microphone:** two pins. The one whose solder pad is joined to the metal can is ground (beep it against the can).
  The other is +.
- **DK VDD is 3.0 V. The chip's analog supply is specified for 3.0 to 3.6 V**, so this is right at the bottom edge.
  It is the simplest hookup and should work. If the chip answers but behaves oddly, power pins 11 and 23 from a real
  3.3 V source instead (the Teensy's 3.3 V pin is fine, grounds joined) and leave pin 6 on the DK.
- Keep the capacitors on pins 1, 11, 23 and 24 as close to the adapter as the breadboard allows.
- Keep the microphone and the speaker about 30 cm apart, speaker facing away. Close together, they howl.

## 5. Power-up, in this order

1. Meter on beep: 9 V rail to ground must not beep. DK VDD rail to ground must not beep.
2. Plug the DK into the laptop and switch it on. Measure pin 6 and pin 11 to ground: about 3.0 V.
   Pin 1 to ground should read about 1.5 V; it may only appear after the firmware has started the chip (section 6).
3. Feel the chip. It must not get warm. Warm: unplug and re-check pins 10 to 13 and the belly pad.
4. Clip in the 9 V battery. Pin 13 to ground: about 9 V.

## 6. Run the test

On the laptop, in the WSL terminal. The DK has to be handed to WSL first, from Windows PowerShell:
`usbipd.exe list`, then `usbipd.exe attach --wsl --busid <the J-Link line's id>`.

```
~/projects/active/haven_workspace/firmware/haven_zephyr_app/tools/tac5301_bench.sh --build
```

It builds the bench firmware, loads it, restarts the DK and prints what the chip reports. Do not connect the Haven
app during this test (a tone command would stop the audio clock). After moving a wire, re-check without re-loading:

```
~/projects/active/haven_workspace/firmware/haven_zephyr_app/tools/tac5301_bench.sh --check-only
```

| The script ends with | Meaning | Look at |
|---|---|---|
| `RESULT: RUNNING` | The chip is awake, locked to the clock, microphone bias on | Tap the microphone. You should hear it. Then remove the 100 ohm resistor if it is too quiet |
| `THE CHIP DID NOT ANSWER` | No reply on the two control wires | Belly-pad ground, pins 6 / 10 / 11 / 12 / 23, SDA and SCL swapped, the two 4.7 kohm resistors, a solder bridge |
| `clock MISSING` | Chip answers, sees no audio clock | Pins 2 and 3 to P1.06 and P1.07 |
| `mic bias OFF` or `MIC BIAS FAULT` | 9 V missing or the bias is shorted | Battery, pin 13, the capacitor and resistor on pin 14, microphone the right way round |
| `mode ... ASLEEP` | The wake-up did not take | Tell me; send the printed lines |

If the first chip will not answer after an hour of checking, stop and build the second adapter rather than reworking
the first: a QFN that has been heated many times is a poor test subject.

## 7. After it passes: what to measure, and what I need from you

- **Does it pass sound cleanly?** Speak, tap, listen. Hiss and hum on a breadboard are expected and do not count.
- **Current draw**, if your multimeter has a mA range: in series with the wire to pins 11 and 23. The datasheet says
  about 24.5 mA at 3.3 V with everything on. Write the number down.
- **Delay**, the real point of the test. It needs one of these; tell me which you have and I will write that method:
  an oscilloscope with two probes (microphone signal on one, speaker signal on the other, tap the microphone), or
  a USB audio interface or sound card with a stereo line input (same two signals, recorded, I measure the shift
  from the file). The expected figure from the datasheet tables is 0.12 to 0.19 ms; the limit that matters for Haven is
  0.3 ms. A phone recording cannot resolve this.
- Send me: the lines the script printed, a photo of the soldered adapter (both sides) and of the breadboard, and
  what you saw in step 3.2.

## What this guide does not cover

- The filter (notch) settings on this chip. That is a second session, only if the delay is good.
- Loudness limits. The speaker is on a bench, not in an ear. Nothing here goes in or near an ear.

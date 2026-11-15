# Haven v3 charging cradle (2026-11-14)

A desk cradle that charges both v3 pods from any USB-C charger. No battery, no charging chip: each pod has its own
(nPM1100). The cradle only brings 5 V to the pods' two spring pins.

**Why a cradle and not a charging case:** a case carries its own battery and charger board and is a project of its
own. The first pair only needs to charge; this does that with four cheap parts. A case can come later.

## Parts

| Part | Made by | Source |
|---|---|---|
| Dock board, 41 x 51.5 mm, 2 layers, 1.6 mm, ENIG (the pads must be gold) | JLCPCB, fully assembled, nothing to solder | `tools/gen_cradle_v3_pcb.py` -> `haven_v3_cradle.kicad_pcb`, fab files in `fab/v3_cradle/` |
| Base, frame, lid (printed, about 9 g each) | any resin or FDM print service | `hardware/mechanical_cad/v3_slim/cradle_v3.py` -> `cradle_v3_{base,frame,lid}.stl` |
| 8 disc magnets 5 x 2 mm N52, 4 screws M2 x 8 self-tapping | bought | glued into the frame top and lid underside; screws go through frame and board into the base |

Board parts (LCSC numbers from memory, **check them at the JLCPCB quote**): J1 USB-C TYPE-C-31-M-12 (C165948),
R1 / R2 5.1 kohm 0603 (C23186, tell the charger to give 5 V), C1 10 uF 0603 (C19702). Four bare pads CP1-CP4.

## How a pod sits

- Head-side face down in a pocket shaped like the pod. Its two spring pins (pod board P1 = VBUS, P2 = GND) land on two
  1.8 mm gold pads on a tongue of the board; "+" and "-" are printed beside them.
- The pod shell now has a **flat contact land** around the pins (z = -4.4, 5.4 x 4.0 mm, wall thickened inside to
  0.8 mm; `LAND_*` in `pod_v3_styled.py`). Before this the face sloped about 25 degrees there and a flat pad would
  have hit the shell first. With the 4.5 mm pin the tip stands 0.5 mm proud of the land and the pad pushes it in 0.5 mm
  (half its 1.0 mm working travel).
- The rest of the pod's curved head side goes through a hole in the board into a printed cup with 0.3 mm clearance, so
  the pod rests on the land, not the cup.
- The lid rests on the pods (0.3 mm above the frame) and four magnet pairs pull it down, so the magnets' pull presses
  the pods onto the pads. Spring-pin force: 130 gf +-20 % each at the 1.0 mm working point (datasheet); at 0.5 mm it
  is less, not given.
- The speaker cable leaves through an open slot at each pocket's cable end; the lid has a groove over it.
- Both pods are the same part (the v3 pod is mirror-symmetric across its width, so the same pod rotated serves the
  other ear), so both pockets are the same.

## Checks run

- Board: KiCad DRC 0 errors, 0 unconnected, 2 silkscreen warnings. Board outline, holes, tongues, pads and screws are
  read from `cradle_v3_layout.json`, written by the cradle script, so the two cannot drift apart.
- Cradle script asserts: the pod never dips into the board outside the holes; every pad is on board; base, frame and
  lid do not overlap; the lid reaches the pods. Section picture: `cradle_v3_section.png`.

Review (2026-11-14, after the first build):
- Polarity traced from the pod board file to the dock board file: on both pods P1 (VBUS) lands on a VBUS pad and P2
  (GND) on a GND pad. A pod put in turned around lands its pins on the printed cup: no contact, so it cannot be
  reverse-powered. Upside down, the pins face up: no contact.
- The real shell meshes placed in the cradle: no overlap with the base or frame (closest 0.05 mm to the cups, 0.15 mm
  to the pocket walls); the lid presses 0.06 mm into the pod lids, which is the intended contact.
- Added after review: a thumb notch in the frame at the cable end, so the magnet lid can be lifted.
- Screws: M2 x 8 goes through 4.2 mm of frame and the 1.6 mm board and 2.2 mm into the 3 mm base; it does not come
  out the bottom.

## Not checked / open

- Nothing printed or built. Magnet strength in practice; real contact force at 0.5 mm; print tolerances.
- No fuse and no ESD part: a coin across a + and - pad shorts the charger's 5 V (USB chargers current-limit; cheap ones
  may not). The pads are under the pods, recessed in the pockets.
- No parking spot for the in-ear pieces; they hang out on their cables.
- Only the A4/B9 VBUS pins of the socket are wired (all four VBUS contacts are one wire inside a USB-C plug).

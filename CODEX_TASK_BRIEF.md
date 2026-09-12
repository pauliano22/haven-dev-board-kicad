# Task brief: finish routing the Haven dev board (for GPT-6 Astra / Codex)

## Do not just run autoroute again
Reported behavior: when Astra drives KiCad's GUI and presses Auto-Route,
KiCad's own router does the actual work — Astra has no routing engine of
its own for that path. We have already run that exact class of
autorouter (Freerouting) across **5 independent configurations** and
converged on 87 unrouted nets as a real ceiling every time (full
evidence: `HAVEN_HARDWARE_REVIEW.md` section 9). Re-running autoroute
will almost certainly reproduce the same 87 and tell us nothing new.

**What would actually be new and useful**: manual, per-pad escape
routing — placing individual vias/dogbone traces to get each fine-pitch
ball or pad out to open space, the way a human PCB designer does it one
part at a time. If you're working via `pcbnew`'s Python API or
`kicad-cli` (recommended for a local/Codex setup — no GUI needed), that
means scripting individual via placements per net, not calling a bulk
router. If nothing better than "run the autorouter again" is on offer,
say so plainly rather than reporting a rerun as progress.

## Context
Haven is a hearing-protection wearable. This is its bench dev board (a
DSP board built on the OpenEarable open-hardware platform), deliberately
sized 5x larger than the final wearable so it's actually routable on a
bench. The repo is public:

`https://github.com/pauliano22/haven-dev-board-kicad`

Branch: `feature/board-rescale-and-route`
File to open: `kicad/haven_dev_board.kicad_pcb` (KiCad 9)

## What's already done (don't redo it)
- Board resized 5x, re-placed, and routed with Freerouting (a real
  autorouter). Result: 934 -> 415 total DRC violations.
- Tuned across 5 independent autorouter configurations. Best result —
  **87 of 304 nets remain unrouted** — is a real ceiling for a
  conventional autorouter, not an under-explored setting. Full evidence
  trail: `HAVEN_HARDWARE_REVIEW.md` section 9.
- BLE antenna keepout implemented as a KiCad rule area (blocks
  copper/vias/tracks) across all 6 copper layers under the MDBT53
  module. **Do not add copper, vias, or tracks inside this keepout
  zone** — it's there for RF performance, verified against the real
  Raytac datasheet. See section 3.2.
- 78 footprints (mostly 0201/0402 passives) have pad rotations baked in
  at the geometry level instead of via the footprint's rotation field —
  cosmetic vs. the library, not a routing problem. **Do not run "Update
  Footprint from Library"** on this board — it would silently move
  these pads back to un-rotated positions and orphan existing traces.
  See section 10.

## The actual task
Route the 87 remaining nets. The authoritative, net-by-net list with
exact pin names is `REMAINING_CONNECTIONS.md` in the repo root — read it
first. Almost all of it concentrates on fine-pitch escape routing under
five parts:

| Component | Package | Pitch |
|---|---|---|
| U15 (ADAU1860 DSP) | BGA-56 | 0.35mm |
| U2 (charger) | DSBGA-25 | 0.40mm |
| MDBT531 (nRF5340 BLE module) | 65-pin castellated | 0.50mm |
| U10 | UQFN-16 | 0.40mm |
| CN1 | FPC connector | 0.35mm |

This is the part a bulk autorouter structurally can't do well: escaping
a ball/pad buried in the middle of a fine-pitch grid needs either
via-in-pad or a careful hand-placed dogbone escape. The board's current
via spec (0.15mm drill / ~0.25-0.3mm pad) is sized for via-in-pad at
this pitch — use it.

## Constraints (don't relax these)
- Don't touch the antenna keepout zone (see above).
- Respect existing clearances — don't just close nets by running traces
  through/over other copper. 226 clearance + 38 "shorting" DRC
  violations already exist from the autorouter's leftover partial
  attempts; most of the shorting ones are dangling stubs from these
  same 87 nets (verified: 24/38 land on already-known dangling-stub
  coordinates in `REMAINING_CONNECTIONS.md`) — clean those up as you
  route through the area, don't add new ones.
- Don't modify footprints, part placement, or anything outside the
  routing layers unless a net genuinely can't be closed without a small
  local placement nudge — if so, say so explicitly in your summary,
  don't do it silently.
- 6-layer board — inner layers are available for escape routing, not
  just top/bottom.

## What to hand back
1. The modified `.kicad_pcb` file (or a diff/branch, if you're working
   in a git checkout — please commit to a **new branch**, don't push to
   `feature/board-rescale-and-route` directly).
2. A plain count: how many of the 87 nets you actually closed.
3. Output of `kicad-cli pcb drc` (or KiCad's built-in DRC) run *after*
   your changes, so the result is checkable, not just claimed.
4. Anything you deliberately left unrouted and why (e.g. "couldn't
   escape this ball without a placement change").

## Honesty check for whoever's driving this
GPT-6 Astra's own benchmark number (EEBench, 69.3%) comes from
atopile's code-based PCB flow, not from visually operating KiCad's GUI
the way this task requires — the GUI-clicking approach is closer to
OpenAI's launch demo than to the rigorously-scored benchmark, so treat
the real accuracy here as unverified, not "69.3%-good." Don't take the
DRC-clean claim on faith — re-run DRC yourself against the returned
file before deciding anything closed.

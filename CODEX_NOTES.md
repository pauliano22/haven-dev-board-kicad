# Shared notes: ChatGPT Agent Mode (GUI) routing experiment

This branch is the **GUI-driven** counterpart to
`experiment/codex-astra-routing` (Codex CLI, script/file-only, no
screen). This one runs in ChatGPT's Agent Mode sandbox, which has an
actual desktop and can open KiCad's PCB editor and drive it with
mouse/keyboard, the way a human would. Kept on a separate branch
deliberately, so each technique's results are independently checkable
against the same starting point rather than getting tangled together.

This is a coordination log between whoever's driving Agent Mode and
Claude (working in a separate session). It's asynchronous, not live —
whoever reads this next picks up from the last entry. Append, don't
rewrite history; newest entry at the bottom.

**Branch**: `experiment/astra-agentmode-routing`, forked from the same
commit as `experiment/codex-astra-routing` — the point where the
93->87 unrouted fix and the footprint-mismatch/shorting investigation
landed on `feature/board-rescale-and-route` (see
`HAVEN_HARDWARE_REVIEW.md` sections 9-10).

**The actual point of this branch**: don't let Agent Mode just press
Auto-Route. It has GUI control, which Codex doesn't — the thing worth
testing here specifically is whether it can do genuine per-pad manual
escape routing (placing vias, dragging traces by hand in KiCad's
interactive router) the way a skilled human would. If it just clicks
the autorouter button, that's not testing anything new — we've already
proven that path hits 87 across 5 configurations of the same class of
autorouter.

**Ground rules** (same as the Codex branch):
- Push commits to *this* branch only. Never push to
  `feature/board-rescale-and-route` or `master` directly.
- Read `CODEX_TASK_BRIEF.md` and `REMAINING_CONNECTIONS.md` before
  starting.
- Log every attempt here, including ones that don't work.
- Always include real `kicad-cli pcb drc` output (run from a terminal
  in the same sandbox — Agent Mode has shell access too, this isn't
  GUI-only) with any claimed progress.

---

### [Codex Agent Mode] — 2026-09-09
**Goal this session**: Set up the Windows GUI routing experiment and begin manual escape routing.
**What I tried**: Confirmed the host is Windows. Cloned this branch into `C:\Work\haven-board` after Controlled Folder Access blocked Documents. Read `CODEX_TASK_BRIEF.md`, `CODEX_NOTES.md`, `REMAINING_CONNECTIONS.md`, and the relevant hardware review section. No KiCad GUI routing was completed; no traces or vias were placed, and no board file was modified. KiCad 9.0.8 installation was started with `winget install --id KiCad.KiCad -e --version 9.0.8 --accept-source-agreements --accept-package-agreements --silent`; the download was still in progress when this handoff was made. No autorouter was run.
**Result**: No post-change DRC was run. Starting DRC/unrouted counts were not captured before the urgent handoff. The board remains at the branch's original state with the documented remaining connections unchanged.
**Unrouted count before -> after**: Not measured -> unchanged; no routing edits were made.
**Blockers / questions for the other side**: Next session must verify KiCad 9.0.8 installation completed, launch the actual PCB Editor GUI, open `kicad/haven_dev_board.kicad_pcb`, and perform manual per-pad escape routing for U15, U2, MDBT531, U10, and CN1. Then save, run DRC, append real before/after DRC output, commit, and push. Do not run Update Footprint from Library, do not add copper/vias/tracks in the MDBT531 antenna keepout, and do not rerun autoroute.

## Entry template (copy this for each session)

### [who/tool] — [date]
**Goal this session**:
**What I tried** (manual GUI routing on which nets, or something else):
**Result** (paste real DRC output, not a summary):
**Unrouted count before -> after**:
**Blockers / questions for the other side**:

---

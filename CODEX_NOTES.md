# Shared notes: Codex/Astra routing experiment

This is a coordination log between Codex (working locally, driven by
the project owner) and Claude (working in a separate session on the
main `feature/board-rescale-and-route` branch). It's asynchronous, not
live — whoever reads this next picks up from the last entry. Append,
don't rewrite history; newest entry at the bottom.

**Branch**: `experiment/codex-astra-routing`, forked from
`feature/board-rescale-and-route` at the commit that fixed the 93->87
unrouted count and investigated the footprint-mismatch/shorting
findings (see `HAVEN_HARDWARE_REVIEW.md` sections 9-10).

**Ground rules**:
- Push commits to *this* branch only. Never push to
  `feature/board-rescale-and-route` or `master` directly.
- Read `HAVEN_HARDWARE_REVIEW.md` (sections 9-10) and
  `REMAINING_CONNECTIONS.md` before starting — don't rediscover what's
  already documented.
- Log every attempt here, including ones that don't work — a
  "tried X, made it worse" entry is as useful as a success, and stops
  the same dead end getting re-tried.
- Always include real `kicad-cli pcb drc` output (unrouted count,
  violation count) with any claimed progress. A claim without a DRC run
  attached doesn't count as verified here.

---

## Entry template (copy this for each session)

### [who] — [date]
**Goal this session**:
**What I tried**:
**Result** (paste real DRC output, not a summary):
**Unrouted count before -> after**:
**Blockers / questions for the other side**:

---

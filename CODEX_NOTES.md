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

### Codex/Astra — 2026-09-09 — attempt 1 (rejected)
**Goal this session**: Test individual power/ground via-in-pad escapes on U15 and U2.
**What I tried**: Added 0.25 mm / 0.15 mm through vias at U15 GND/V_LS balls and U2 A1/A5/B5, then refilled zones. No autorouter. Rejected and restored original board because new clearance violations appear. Script and full DRC JSON in routing-evidence. Initial /tmp runs lacked matching project/library context; authoritative run below used the original project directory. Existing 0.20 mm clearance prevents these centered vias at 0.35 mm pitch (actual 0.10 mm gap). No rules relaxed.
**Result** (paste real DRC output, not a summary):
Baseline:
```
Found 415 violations
Found 116 unconnected items
Saved DRC Report to /tmp/haven-baseline.json
```
Candidate (rejected):
```
Found 456 violations
Found 112 unconnected items
Saved DRC Report to routing-evidence/attempt1.json
```
**Unrouted count before -> after**: 116 -> 112 DRC links in rejected candidate; retained board remains 116. Zero nets claimed closed. The historical 87 autorouter metric is not the same as DRC's 50 distinct open nets.
**Blockers / questions for the other side**: Centered via-in-pad is incompatible with current clearance settings. Several vias also remain dangling after zone fill; next attempt will move vias outboard with explicit per-pad traces.

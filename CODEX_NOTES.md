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

### Codex/Astra — 2026-09-09 — attempt 2 (rejected)
**Goal this session**: Outboard dogbones on U2 A1/A5/B5 and U10 5/6/8.
**What I tried**: Explicit 0.15 mm traces and 0.30/0.15 mm through vias; refilled zones. Rejected entire trial, restored baseline. U10 vias collide with inner USB/VUSB tracks. Script used PAD.GetLayer(), which does not correctly select U2's bottom copper pad layer; this trial must not be reused unchanged.
**Result** (paste real DRC output, not a summary):
```
Found 431 violations
Found 118 unconnected items
Saved DRC Report to routing-evidence/attempt2.json
```
**Unrouted count before -> after**: 116 -> 118 in rejected trial; retained 116. Zero nets closed.
**Blockers / questions for the other side**: Need explicit pad copper-layer selection and inner-layer obstacle checks. Next trial restricts scope to U2 B5 and A1.

### Codex/Astra — 2026-09-09 — attempt 3 (rejected)
**Goal this session**: Correct U2 dogbone layer selection; test A1 GND and B5 +1.8V.
**What I tried**: Explicit B.Cu traces with 0.30/0.15 mm vias. A1 introduces no new reported violation; B5 via shorts SCL on In1.Cu. Rejected combined trial and restored baseline. User requested visual inspection before further candidates; switching to exported SVG close-ups.
**Result** (paste real DRC output, not a summary):
```
Found 416 violations
Found 114 unconnected items
Saved DRC Report to routing-evidence/attempt3.json
```
**Unrouted count before -> after**: 116 -> 114 in rejected candidate, retained 116. Zero nets claimed closed.
**Blockers / questions for the other side**: Inspect all copper layers before relocating B5; isolate A1 in a separate net attempt.

### Codex/Astra — 2026-09-09 — attempt 4 (+1.8V, retained)
**Goal this session**: Close U2 B5 +1.8V after visual inspection.
**What I tried**: Exported six copper SVG layers with kicad-cli; rendered and personally inspected cropped U2/U15/U10/CN1/MDBT531 contact sheets using the image tool. U2 In1 image shows the SCL corridor above the pad row. Placed B.Cu 0.15 mm escape from B5 to (66.9098,30.9000), with 0.30/0.15 mm through via beyond that corridor. Refilled existing zones. Script attempt4.py; reusable crop renderer and inspected images included. Compared violations by type and involved item UUIDs: zero newly introduced violations. +1.8V disappears entirely from unconnected_items (49 open nets versus baseline 50).
**Result** (paste real DRC output, not a summary):
Before:
```
Found 415 violations
Found 116 unconnected items
Saved DRC Report to /tmp/haven-baseline.json
```
After:
```
Found 415 violations
Found 115 unconnected items
Saved DRC Report to routing-evidence/attempt4.json
```
**Unrouted count before -> after**: DRC missing links 116 -> 115; distinct open nets 50 -> 49. One net fully closed: +1.8V. Historical autorouter 87 metric not rerun.
**Blockers / questions for the other side**: None for this escape; existing board violations remain. No footprint, clearance, placement or antenna keepout changes.

### Codex/Astra — 2026-09-09 — attempt 5 (GND, retained refinement)
**Goal this session**: Escape exposed GND pads after inspecting all six layers in component close-ups.
**What I tried**: U2 A1/A5 outward B.Cu dogbones; CN1 pin 10 outward F.Cu dogbone; U15 A1/A4/F1/G3/G7 outward F.Cu dogbones. U15 0.09 mm traces begin 0.124 mm outward from pad center, still overlapping the 0.25 mm ball pad, to respect neighboring-pad clearance. Vias 0.30/0.15 mm. Initial CN1 0.15 mm trace failed 0.20 mm clearance by 0.015 mm; refined to 0.10 mm and reran from pre-attempt board. Refined script retained. Compared DRC violation identities: zero new violations. No existing traces removed.
**Result** (paste real DRC output, not a summary):
Before:
```
Found 415 violations
Found 115 unconnected items
Saved DRC Report to routing-evidence/attempt4.json
```
Initial candidate:
```
Found 416 violations
Found 107 unconnected items
Saved DRC Report to routing-evidence/attempt5.json
```
Refined candidate:
```
Found 415 violations
Found 107 unconnected items
Saved DRC Report to routing-evidence/attempt5-refined.json
```
**Unrouted count before -> after**: 115 -> 107 missing links; GND remains open elsewhere, so no additional whole net closed. Cumulative one whole net closed (+1.8V), nine links removed versus baseline.
**Blockers / questions for the other side**: Inner U15 GND balls still cannot use centered through vias at current clearance. These successful outer escapes do not establish a solution for inner balls.

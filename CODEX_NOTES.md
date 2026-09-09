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

### Codex/Astra — 2026-09-09 — attempt 6 (V_LS, retained final)
**Goal this session**: Escape V_LS on exposed U15 balls and U10/CN1.
**What I tried**: Used inspected six-layer images plus KiCad GetEffectiveShape/Collide checks at 0.20 mm against existing copper on all shared layers. Explicit routes only. Straight candidates at U15 A2/E1/G2 and CN1 8 were blocked before insertion; tried staggered alternatives. Final retained U15 A2/D1/E1/G2 and U10 5. E1 shares D1's via to avoid same-net hole spacing failure. A2/G2 require short In3.Cu tracks to reach the V_LS fill beyond neighboring GND antipads. CN1 8 remains blocked by existing IO4/GND escapes outward and a mechanical pad inward; no route added there. Initial/refined/final full DRC files retained. Final violation identity comparison against attempt5-refined: no new violations.
**Result** (paste real DRC output, not a summary):
Before:
```
Found 415 violations
Found 107 unconnected items
Saved DRC Report to routing-evidence/attempt5-refined.json
```
Initial:
```
Found 415 violations
Found 106 unconnected items
Saved DRC Report to routing-evidence/attempt6.json
```
Refinement (rejected):
```
Found 417 violations
Found 105 unconnected items
Saved DRC Report to routing-evidence/attempt6-refined.json
```
Final:
```
Found 415 violations
Found 103 unconnected items
Saved DRC Report to routing-evidence/attempt6-final.json
```
**Unrouted count before -> after**: 107 -> 103 DRC links. V_LS remains open elsewhere; cumulative one whole net closed and 13 missing links removed from baseline.
**Blockers / questions for the other side**: Copper collision checks alone do not prove connectivity or same-net drill spacing; DRC caught both and final routes address them. Inner BGA V_LS balls still need further work.

### Codex/Astra — 2026-09-09 — attempt 7 (GND, retained final)
**Goal this session**: Escape U15 B4, U10 6/8, MDBT531 1/61.
**What I tried**: Joined U15 B4 to adjacent same-net A4 with a 0.09 mm edge-to-edge trace. Outward B.Cu U10 dogbones; F.Cu MDBT531 dogbones entirely on board side of antenna boundary. First geometry checks rejected U10 6 near V_LS via, module 1 near SWCLK/#ERROR, module 61 near In4 3V3. Tried explicit alternatives: U10 6 bends past V_LS; module 1 via (75.65,66.8), module 61 via (76.2,74.5277). Full-width copper bounding boxes are outside antenna rectangle. No additions to keepout. All five final escapes pass copper-shape checks; DRC adds zero violation identities.
**Result** (paste real DRC output, not a summary):
Before:
```
Found 415 violations
Found 103 unconnected items
Saved DRC Report to routing-evidence/attempt6-final.json
```
Initial (two accepted routes):
```
Found 415 violations
Found 101 unconnected items
Saved DRC Report to routing-evidence/attempt7.json
```
Final:
```
Found 415 violations
Found 98 unconnected items
Saved DRC Report to routing-evidence/attempt7-final.json
```
**Unrouted count before -> after**: 103 -> 98 links; GND still open elsewhere. Cumulative 18 links removed, one whole net closed.
**Blockers / questions for the other side**: No constraint changes; inner U15 GND group still isolated.

### Codex/Astra — 2026-09-09 — attempt 8 ($1N2586, retained)
**Goal this session**: Fully close U15 G4 to C32 pin 1.
**What I tried**: Refreshed SVGs and inspected U15 and C32 close-ups. Explicit F.Cu 0.09 mm escape starts at G4's outer edge, bends right of G3's ground via, then runs through open space to C32. Entire polyline checked against KiCad copper shapes. No via needed. DRC violation identity comparison: zero new violations; $1N2586 absent from unconnected_items.
**Result** (paste real DRC output, not a summary):
Before:
```
Found 415 violations
Found 98 unconnected items
Saved DRC Report to routing-evidence/attempt7-final.json
```
After:
```
Found 415 violations
Found 97 unconnected items
Saved DRC Report to routing-evidence/attempt8.json
```
**Unrouted count before -> after**: 98 -> 97 links; 49 -> 48 distinct open nets. Cumulative two whole nets closed (+1.8V, $1N2586), 19 missing links removed.
**Blockers / questions for the other side**: None for this net; existing board DRC errors remain.

### Codex/Astra — 2026-09-09 — attempt 9 (SW, retained)
**Goal this session**: Connect U2 A4 to L2 pin 1.
**What I tried**: Inspected U2 and L2 six-layer crops. B.Cu 0.15 mm outward A4 escape to x=68.1, widening to 0.30 mm for the remaining explicit diagonal/horizontal path to L2. Checked every segment against other copper; no autorouter. DRC adds zero violations. This closes connectivity; it is not validation of switching-regulator EMI or power performance on the rescaled board.
**Result** (paste real DRC output, not a summary):
Before:
```
Found 415 violations
Found 97 unconnected items
Saved DRC Report to routing-evidence/attempt8.json
```
After:
```
Found 415 violations
Found 96 unconnected items
Saved DRC Report to routing-evidence/attempt9.json
```
**Unrouted count before -> after**: 97 -> 96 links; SW fully closed. Cumulative three whole nets closed and 20 links removed.
**Blockers / questions for the other side**: Review switch-node length in a later power-layout pass; component positions were preserved as requested.

### Codex/Astra — 2026-09-09 — final verification / handoff
**Goal this session**: Verify retained board and clearly identify unfinished routing for Claude.
**What I tried**: Fresh DRC on final board; parsed-S-expression audit against b535d54. All 89 footprints, 1,015 original tracks, 166 original vias unchanged; setup/layers/general and antenna rule area unchanged. Added 35 segments and 17 vias, all fully outside antenna keepout. No new DRC violation identities. CODEX_ROUTING_HANDOFF.md indexes every target net to inspected component images and lists all current missing links. Explicitly distinguishes actual route attempts from visual-only assessment; not every remaining signal was attempted or solved.
**Result** (paste real DRC output, not a summary):
Baseline:
```
Found 415 violations
Found 116 unconnected items
Saved DRC Report to /tmp/haven-baseline.json
```
Final:
```
Found 415 violations
Found 96 unconnected items
Saved DRC Report to routing-evidence/final.json
```
**Unrouted count before -> after**: 116 -> 96 DRC missing links; 50 -> 47 distinct open nets. Exactly three whole nets closed: +1.8V, $1N2586, SW. 20 links removed. The historical 87 autorouter count was not reproduced or reinterpreted.
**Blockers / questions for the other side**: Board remains unfinished, with all 415 pre-existing violations. Inner BGA escape constraints and CN1 V_LS candidates documented in handoff. No claim that the remaining 47 nets are impossible; several were only visually assessed. No autorouter, placement edits, footprint updates, rule relaxation, or antenna copper additions performed.

### Codex/Astra — 2026-09-09 — attempt10
**Goal this session**: Repair C19 GND/VCC terminal connections before harder escapes.
**What I tried**: Inspected fresh C19 six-layer crop. Removed seven explicitly identified local terminal segments that reach the opposite-net pad; retained their remote vias. Added GND via at the actual pad 2 and a B.Cu VCC dogbone to its existing via. All new copper passed exact KiCad shape checks at 0.20 mm. Retained; footprint unchanged. Removed segments and geometry checks are recorded in attempt10.geometry.txt.
**Result** (paste real DRC output, not a summary):
Before:
```
Found 415 violations
Found 96 unconnected items
Saved DRC Report to routing-evidence/session2/baseline.json
```
After:
```
Found 410 violations
Found 94 unconnected items
Saved DRC Report to routing-evidence/session2/attempt10.json
```
**Unrouted count before -> after**: 96 -> 94 missing links; 47 -> 47 distinct open nets. Newly closed: none. New violation identities: 0.
**Blockers / questions for the other side**: VCC remains open at U2; C19's two missing connections are closed. This fixes local routing drift without updating library footprints.

### Codex/Astra — 2026-09-09 — attempt11
**Goal this session**: Close XL2 at C2 and repair its GND terminal.
**What I tried**: Inspected C2 six-layer SVG crop. Replaced three local wrong-pad terminal segments with explicit B.Cu paths: XL2 approaches actual pad 2 from above/left; GND approaches pad 1 from below. Both full paths passed 0.20 mm copper-shape checks; no vias or footprint changes.
**Result** (paste real DRC output, not a summary):
Before:
```
Found 410 violations
Found 94 unconnected items
Saved DRC Report to routing-evidence/session2/attempt10.json
```
After:
```
Found 406 violations
Found 92 unconnected items
Saved DRC Report to routing-evidence/session2/attempt11.json
```
**Unrouted count before -> after**: 94 -> 92 missing links; 47 -> 46 distinct open nets. Newly closed: XL2. New violation identities: 0.
**Blockers / questions for the other side**: None for XL2; net fully closed. Retained only after zero-new-violation DRC check.

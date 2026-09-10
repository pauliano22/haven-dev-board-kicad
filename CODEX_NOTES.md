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

### Codex/Astra — 2026-09-09 — attempt12
**Goal this session**: Close XL1 at C14 and connect actual GND pad.
**What I tried**: Inspected fresh C14 six-layer crop. Removed three wrong-pad terminal tracks, placed a 0.30/0.15 mm GND via in pad 1, and routed XL1 to pad 2 around the existing ground via on B.Cu. Exact shape checks include all layers for the via. Retained after DRC.
**Result** (paste real DRC output, not a summary):
Before:
```
Found 406 violations
Found 92 unconnected items
Saved DRC Report to routing-evidence/session2/attempt11.json
```
After:
```
Found 402 violations
Found 90 unconnected items
Saved DRC Report to routing-evidence/session2/attempt12.json
```
**Unrouted count before -> after**: 92 -> 90 missing links; 46 -> 45 distinct open nets. Newly closed: XL1. New violation identities: 0.
**Blockers / questions for the other side**: No remaining XL1 gap. Existing GND via retained and still connected to planes.

### Codex/Astra — 2026-09-09 — scoped cap-via attempt
**Goal this session**: Attempt only the requested isolated-cap connections on `GND`, `V_LS`, `V_SD`, `VCC`, `VUSB`, and `V_PMID`; do not touch U15, U2, MDBT531, U10, CN1, J1, or U1.
**What I tried**: Switched to `experiment/codex-astra-routing`, fetched the branch explicitly, and confirmed the prior history: XL1, XL2, and C19 are already closed; the retained board starts at 45 distinct open nets / 90 unconnected items. Tried a single 0.30/0.15 mm through-via centered on C6 pad 1 (`V_SD`, 109.0097,1.0034) and ran DRC immediately. It was rejected and removed because DRC increased from 402 to 410 violations, including a new `shorting_items` identity at the via. Tried a single 0.30/0.15 mm through-via centered on C9 pad 1 (`V_PMID`, 78.7604,26.3620) and ran DRC immediately. It was rejected and removed because DRC increased from 402 to 411 violations. No retained board edits remain; no restricted component was touched.
**Result** (paste real DRC output, not a summary):
Before:
```
Found 402 violations
Found 90 unconnected items
Saved DRC Report to C:/Work/haven-board/routing-evidence/session3/baseline.json
```
C6 V_SD rejected:
```
Found 410 violations
Found 90 unconnected items
Saved DRC Report to C:/Work/haven-board/routing-evidence/session3/c6-vsd.json
```
C9 V_PMID rejected:
```
Found 411 violations
Found 90 unconnected items
Saved DRC Report to C:/Work/haven-board/routing-evidence/session3/c9-vpmid.json
```
Final after removal:
```
Found 402 violations
Found 90 unconnected items
Saved DRC Report to C:/Work/haven-board/routing-evidence/session3/final.json
```
**Unrouted count before -> after**: 90 -> 90 unconnected items; no connections closed. The two direct via-in-pad attempts were more complex than a clean single-via fix under the existing copper/clearance geometry, so both were skipped and documented rather than forcing new violations.
**Blockers / questions for the other side**: Further cap work needs local dogbone/track cleanup or a different via location after inspecting each six-layer neighborhood. No batch edits were made, and the board file is back to its exact pre-session state.


### Codex/Astra — 2026-09-09 — session4: visually inspected capacitor repairs
**Goal this session**: Repair C6, C8, C9, C13, C22, C34, C38, C44 and C46 in that order after inspecting real KiCad SVG exports of all six copper layers. Started from `5fd8faa` on `experiment/codex-astra-routing`.
**Method**: Exported with `kicad-cli pcb export svg --mode-multi --page-size-mode 1 --exclude-drawing-sheet --layers F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu`. Cropped the SVG viewBox to each capacitor's 5.5 mm neighborhood, rendered and inspected the labeled six-layer images before selecting each explicit repair. Each attempt below is one local capacitor repair transaction (terminal removals/replacements, plus at most one via), followed immediately by zone refill and full `kicad-cli pcb drc --format json`. No other repair was applied before checking that result. Rejected transactions were restored immediately. Comparisons use violation type plus involved item UUIDs, not just total counts. These were visually planned file/API edits, not interactive GUI routing.
**Evidence**: `routing-evidence/session4/` contains before/final SVG crops and PNG contact sheets, exact route specifications, removed-item UUIDs and geometry checks, raw DRC JSON/stdout, and new-violation lists. Unlike session3's text reports with `.json` names, these reports are actual JSON.

### Codex/Astra — 2026-09-09 — session4 c6
**Goal this attempt**: Repair C6 terminal connections after six-layer visual inspection.
**What I tried / disposition**: Rejected. The inspected bottom-layer image showed the GND terminal branch overlapping C6 pad 1 (V_SD), and the V_SD branch approaching pad 2 (GND). Replaced the wrong terminal copper with an explicit V_SD path and one 0.30/0.15 mm GND via at pad 2. DRC found a newly dangling upstream GND branch (28c7088c-ad2d-4e1b-9752-405a83096f01); restored the pre-attempt board immediately.
**Result** (actual CLI output):
Before:
```
Found 402 violations
Found 90 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\baseline.json
```
Attempt:
```
Found 393 violations
Found 88 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c6.json
```
**Unrouted count before -> after trial**: 90 -> 88 missing links. Rejected trial was rolled back; retained count stayed 90.
**Blockers / follow-up**: See the subsequent refined attempt and the preserved new-violation report.

### Codex/Astra — 2026-09-09 — session4 c6-refined
**Goal this attempt**: Repair C6 terminal connections after six-layer visual inspection.
**What I tried / disposition**: Retained. Same C6 repair, also removing the obsolete GND branch back to C8's existing ground connection so no dangling end remains. One new GND via at C6 pad 2. All added copper passed 0.20 mm shape checks. Zero new DRC identities.
**Result** (actual CLI output):
Before:
```
Found 402 violations
Found 90 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\baseline.json
```
Attempt:
```
Found 390 violations
Found 88 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c6-refined.json
```
**Unrouted count before -> after trial**: 90 -> 88 missing links.
**Blockers / follow-up**: Both capacitor terminals are connected in retained DRC; other connections on the broader net may remain open.

### Codex/Astra — 2026-09-09 — session4 c8
**Goal this attempt**: Repair C8 terminal connections after six-layer visual inspection.
**What I tried / disposition**: Retained. Six-layer close-up confirmed swapped B.Cu terminal paths: GND reached V_SD pad 2 and V_SD reached GND pad 1. Replaced those paths to the correct pads using the existing vias. No new via. Zero new DRC identities. V_SD now fully closed.
**Result** (actual CLI output):
Before:
```
Found 390 violations
Found 88 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c6-refined.json
```
Attempt:
```
Found 386 violations
Found 86 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c8.json
```
**Unrouted count before -> after trial**: 88 -> 86 missing links.
**Blockers / follow-up**: Both capacitor terminals are connected in retained DRC; other connections on the broader net may remain open.

### Codex/Astra — 2026-09-09 — session4 c9
**Goal this attempt**: Repair C9 terminal connections after six-layer visual inspection.
**What I tried / disposition**: Retained. Inspected V_PMID trace reaching the GND pad and a GND rail crossing the V_PMID pad. Rerouted the local GND rail below the capacitor, connected V_PMID pad 1 around the left side to its existing via, and placed one 0.30/0.15 mm GND via at (78.8000,25.8134), slightly offset within pad 2 to clear the nearby V_PMID via. All added copper passed shape checks; zero new DRC identities.
**Result** (actual CLI output):
Before:
```
Found 386 violations
Found 86 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c8.json
```
Attempt:
```
Found 374 violations
Found 84 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c9.json
```
**Unrouted count before -> after trial**: 86 -> 84 missing links.
**Blockers / follow-up**: Both capacitor terminals are connected in retained DRC; other connections on the broader net may remain open.

### Codex/Astra — 2026-09-09 — session4 c13
**Goal this attempt**: Repair C13 terminal connections after six-layer visual inspection.
**What I tried / disposition**: Retained. Close-up showed the V_LS terminal crossing the GND pad and an offset GND terminal stub. Replaced the local bottom paths: V_LS approaches pad 1 from the left/above and GND reaches pad 2 from the existing ground via on the right. No via added; zero new DRC identities.
**Result** (actual CLI output):
Before:
```
Found 374 violations
Found 84 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c9.json
```
Attempt:
```
Found 366 violations
Found 82 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c13.json
```
**Unrouted count before -> after trial**: 84 -> 82 missing links.
**Blockers / follow-up**: Both capacitor terminals are connected in retained DRC; other connections on the broader net may remain open.

### Codex/Astra — 2026-09-09 — session4 c22
**Goal this attempt**: Repair C22 terminal connections after six-layer visual inspection.
**What I tried / disposition**: Retained. Close-up showed VUSB reaching GND pad 2 and GND copper crossing VUSB pad 1. Replaced the wrong terminal branches, connected each actual pad to its existing via, and moved the local ground-rail approach clear of VUSB. No via added; zero new DRC identities.
**Result** (actual CLI output):
Before:
```
Found 366 violations
Found 82 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c13.json
```
Attempt:
```
Found 353 violations
Found 80 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c22.json
```
**Unrouted count before -> after trial**: 82 -> 80 missing links.
**Blockers / follow-up**: Both capacitor terminals are connected in retained DRC; other connections on the broader net may remain open.

### Codex/Astra — 2026-09-09 — session4 c34
**Goal this attempt**: Repair C34 terminal connections after six-layer visual inspection.
**What I tried / disposition**: Retained. The six-layer image showed the two B.Cu terminal paths reaching opposite pads despite the top-layer routing. Removed the wrong bottom paths and connected GND pad 2 to the existing upper ground via, and V_LS pad 1 to the existing lower power path. No via added; zero new DRC identities.
**Result** (actual CLI output):
Before:
```
Found 353 violations
Found 80 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c22.json
```
Attempt:
```
Found 349 violations
Found 78 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c34.json
```
**Unrouted count before -> after trial**: 80 -> 78 missing links.
**Blockers / follow-up**: Both capacitor terminals are connected in retained DRC; other connections on the broader net may remain open.

### Codex/Astra — 2026-09-09 — session4 c38
**Goal this attempt**: Repair C38 terminal connections after six-layer visual inspection.
**What I tried / disposition**: Retained. The close-up showed GND reaching the lower V_LS pad and V_LS approaching the upper GND pad. Replaced both bottom paths: ground goes around the left to pad 1; V_LS goes around the right from its existing via to pad 2. No via added; zero new DRC identities.
**Result** (actual CLI output):
Before:
```
Found 349 violations
Found 78 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c34.json
```
Attempt:
```
Found 339 violations
Found 76 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c38.json
```
**Unrouted count before -> after trial**: 78 -> 76 missing links.
**Blockers / follow-up**: Both capacitor terminals are connected in retained DRC; other connections on the broader net may remain open.

### Codex/Astra — 2026-09-09 — session4 c44
**Goal this attempt**: Repair C44 terminal connections after six-layer visual inspection.
**What I tried / disposition**: Retained. Close-up confirmed the long bottom GND branch ended at V_LS pad 1, while the V_LS dogbone ended at GND pad 2. Redirected the ground branch to actual pad 2 and connected actual V_LS pad 1 to its existing via. No via added; zero new DRC identities.
**Result** (actual CLI output):
Before:
```
Found 339 violations
Found 76 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c38.json
```
Attempt:
```
Found 335 violations
Found 74 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c44.json
```
**Unrouted count before -> after trial**: 76 -> 74 missing links.
**Blockers / follow-up**: Both capacitor terminals are connected in retained DRC; other connections on the broader net may remain open.

### Codex/Astra — 2026-09-09 — session4 c46
**Goal this attempt**: Repair C46 terminal connections after six-layer visual inspection.
**What I tried / disposition**: Rejected. Six-layer close-up confirmed swapped GND/XTALI terminal paths. Replaced both using existing vias. The XTALI diagonal had only 0.1729 mm clearance to GND pad 1 against the required 0.20 mm. DRC identified one new clearance violation; immediately restored the pre-attempt board. Geometry evidence also records that collision.
**Result** (actual CLI output):
Before:
```
Found 335 violations
Found 74 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c44.json
```
Attempt:
```
Found 332 violations
Found 72 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c46.json
```
**Unrouted count before -> after trial**: 74 -> 72 missing links. Rejected trial was rolled back; retained count stayed 74.
**Blockers / follow-up**: See the subsequent refined attempt and the preserved new-violation report.

### Codex/Astra — 2026-09-09 — session4 c46-refined
**Goal this attempt**: Repair C46 terminal connections after six-layer visual inspection.
**What I tried / disposition**: Retained. Kept the corrected GND approach and moved XTALI's bend farther below the pads, using horizontal then vertical B.Cu segments to pad 2. No via added. All shape checks passed and DRC found zero new violation identities. XTALI still has an unrelated open connection elsewhere.
**Result** (actual CLI output):
Before:
```
Found 335 violations
Found 74 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c44.json
```
Attempt:
```
Found 331 violations
Found 72 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session4\c46-refined.json
```
**Unrouted count before -> after trial**: 74 -> 72 missing links.
**Blockers / follow-up**: Both capacitor terminals are connected in retained DRC; other connections on the broader net may remain open.

### Codex/Astra — 2026-09-09 — session4 final verification
**Result** (fresh final CLI output):
```
Found 331 violations
Found 72 unconnected items
Saved DRC Report to C:/Work/haven-board/routing-evidence/session4/final.json
```
**Before -> after**: 402 -> 331 violations; 90 -> 72 missing links; 45 -> 44 distinct open nets. Exactly one whole net closed: V_SD. All 18 requested capacitor terminal gaps closed; none of the nine target references appears among final unconnected endpoints. Zero new violation identities versus baseline.
**Audit**: All 89 footprints and all 185 existing vias unchanged. Removed 50 specifically identified terminal/branch segments, added 44 replacement segments and two GND vias (C6 and C9). Remaining existing segments unchanged. Setup, layers, general properties, and antenna keepout unchanged; all new copper lies outside the keepout. Copper zones were refilled. Inspected the final bottom-layer montage and retained six-layer final renders.
**Remaining work**: Board still has 331 pre-existing violations and 72 missing links across 44 nets. This session only repairs the specified capacitors; it does not establish full-board DRC cleanliness or power/crystal performance. `REMAINING_CONNECTIONS.md` and the older handoff contain historical entries; use `session4/final.json` for current connectivity. No placement changes, footprint-library updates, rule relaxation or autorouting.


### Codex/Astra — 2026-09-09 — session5 scope and method
User explicitly expanded scope to C23 (GND/$1N70), R6 (GND/TS), and R13 (VUSB). Started at `d3858b4` on `experiment/codex-astra-routing`. Exported current copper on all six layers with `kicad-cli pcb export svg`, rendered 5.5 mm SVG crops and inspected each image before selecting local paths. Each attempt below is one complete local terminal repair, immediately followed by zone refill and `kicad-cli pcb drc --format json`; no next repair was applied until acceptance. No vias were added. Rejected trials were restored immediately. Before/final six-layer images, SVG crops, exact specifications and geometry, full DRC reports, and new-violation lists are in `routing-evidence/session5/`.

### Codex/Astra — 2026-09-09 — session5 c23
**Goal / what I tried**: Rejected. Inspected all six SVG layers before planning. Replaced the GND trace approaching C23 pad 2 ($1N70) and the offset $1N70 terminal branch, connecting the actual pad 1 GND and pad 2 $1N70. The new ground diagonal passed too close to pad 2 (0.1767 mm versus required 0.20 mm); full DRC found one new clearance identity. Restored the board immediately.
**Result** (CLI output):
Before:
```
Found 331 violations
Found 72 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session5\baseline.json
```
Attempt:
```
Found 326 violations
Found 70 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session5\c23.json
```
**Unrouted count before -> after**: 72 -> 72 retained (70 in rejected trial) missing links.
**Blockers / follow-up**: See the subsequent refined attempt.

### Codex/Astra — 2026-09-09 — session5 c23-refined
**Goal / what I tried**: Retained. Moved the ground detour farther left, using a horizontal departure from the existing via before descending. $1N70 approaches pad 2 from its right edge to clear the existing nearby ground via. All new shapes clear other copper at 0.20 mm and DRC has zero new identities. Both C23 terminals closed; $1N70 fully closed.
**Result** (CLI output):
Before:
```
Found 331 violations
Found 72 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session5\baseline.json
```
Attempt:
```
Found 325 violations
Found 70 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session5\c23-refined.json
```
**Unrouted count before -> after**: 72 -> 70 missing links.
**Blockers / follow-up**: Scoped terminal connections complete; other connections elsewhere on GND/TS/VUSB remain outside this repair.

### Codex/Astra — 2026-09-09 — session5 r6
**Goal / what I tried**: Retained. Six-layer image confirmed that the bottom GND and TS routes terminated at opposite pads. Replaced five local segments with paths connecting GND to upper pad 1 from the right and TS to lower pad 2 around the left of the component, reusing the TS via. All new shape checks pass; zero new DRC identities; both R6 terminals closed.
**Result** (CLI output):
Before:
```
Found 325 violations
Found 70 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session5\c23-refined.json
```
Attempt:
```
Found 321 violations
Found 68 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session5\r6.json
```
**Unrouted count before -> after**: 70 -> 68 missing links.
**Blockers / follow-up**: Scoped terminal connections complete; other connections elsewhere on GND/TS/VUSB remain outside this repair.

### Codex/Astra — 2026-09-09 — session5 r13
**Goal / what I tried**: Retained. Six-layer image showed the VUSB branch stopping above/right of actual pad 2. Replaced its two local segments with a path from the existing VUSB via around the right side to pad 2. TS pad 1 and its routing were not changed; the TS net remains open elsewhere toward U2. All new shape checks pass; zero new DRC identities; the requested R13 VUSB gap closed.
**Result** (CLI output):
Before:
```
Found 321 violations
Found 68 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session5\r6.json
```
Attempt:
```
Found 316 violations
Found 67 unconnected items
Saved DRC Report to C:\Work\haven-board\routing-evidence\session5\r13.json
```
**Unrouted count before -> after**: 68 -> 67 missing links.
**Blockers / follow-up**: Scoped terminal connections complete; other connections elsewhere on GND/TS/VUSB remain outside this repair.

### Codex/Astra — 2026-09-09 — session5 final verification
Fresh final CLI output:
```
Found 316 violations
Found 67 unconnected items
Saved DRC Report to C:/Work/haven-board/routing-evidence/session5/final.json
```
**Before -> after**: 331 -> 316 violations; 72 -> 67 missing links; 44 -> 43 distinct open nets. Newly fully closed: $1N70. Five requested terminal gaps closed (C23 both, R6 both, R13 VUSB). No new DRC violation identities versus baseline. The first C23 trial was the only rejection; the revised route passed.
**Preservation audit**: All 89 footprints and 187 vias unchanged; no new vias. Removed nine explicitly identified B.Cu terminal segments and added 13 B.Cu segments. All other existing segments, setup, layer stack, general properties and antenna keepout unchanged. All new copper lies outside the antenna keepout. Final six-layer images were inspected. Restricted ICs/connectors were not edited.
**Remaining**: 316 existing violations and 67 missing links across 43 nets remain. The local R13 VUSB repair does not close the broader TS connection toward U2. Full-board electrical performance and DRC cleanliness are not claimed. Use `session5/final.json` for current missing endpoints; older remaining-connection documents are historical.

### Codex/Astra — 2026-09-09 — session6 open-ended scope / low-usage handoff
**Goal**: User authorized autonomous progression through (1) remaining simple passive/decoupling repairs, (2) MDBT531 signals BCLK, CC_#CD, CC_#PG, DAC_ENABLE, DIN, DOUT, FLASH_RESET, INT, IO5, LSCTRL, PDMDIN, SD_STATE, SPI_CLK, SPI_CS, SPI_CS_FLASH, SPI_MISO and SPI_MOSI, (3) J1 TCK/TDI/TDO/TMS and U1 SCL2, then (4) inner U15 BGA balls. Inspect six-layer SVGs before each edit; DRC immediately after each local repair, revert/log any new violation. No bulk autoroute, footprint/placement edits, antenna keepout copper or library footprint updates. Push only to experiment/codex-astra-routing. If a via-size or clearance-rule change is required, stop and report exact proposed values for the user's fab-capability decision; do not change rules.
**What happened**: Starting usage check reported 91% consumed in the current 300-minute window (9% remaining), so the user's explicit low-usage stop condition was already met. No new routing edits or trial placements were started. Reviewed the current missing endpoints and made this checkpoint immediately. Board remains exactly at 691e16e's routing state.
**Fresh DRC output**:
```
Found 316 violations
Found 67 unconnected items
Saved DRC Report to C:/Work/haven-board/routing-evidence/session6/handoff.json
```
**Before -> after**: 316 -> 316 violations; 67 -> 67 missing connections; 43 -> 43 open nets. No new progress claimed for this checkpoint.
**Next work**: Inspect remaining passive candidates R8 GND and CRYSTAL1 GND first. Assess C10 ($1N65), C36/$1N151 and R28/XTALO using current full-net connectivity and local six-layer images: a passive being named by DRC does not prove the gap is at that passive; opposite endpoints include U2/U15. C46 XTALI and R13 TS local terminals have already been repaired, but those nets still have distant U15/U2 gaps. Do not repeat completed capacitor/resistor work from session4/session5. Then proceed through the newly authorized MDBT531, J1/U1, and inner-U15 order above. No remaining simple candidate has yet been visually inspected during session6; no rule-change requirement has been established.
**Setup**: Existing checkout C:\Work\haven-board, branch experiment/codex-astra-routing. KiCad 9.0.8 CLI and bundled Python are in C:\Users\pmi\AppData\Local\Programs\KiCad\9.0\bin. Session4/session5 contain SVG rendering, explicit repair, DRC rollback and audit helpers. Preserve historical evidence directories; create a fresh session directory for resumed work. Current ground-truth connectivity is session6/handoff.json, not the older REMAINING_CONNECTIONS.md listings. Nothing is mid-edit; no unsaved routing attempt remains.

### Codex/Luna — 2026-09-09 — resumed after usage reset / immediate stop
**Goal**: Resume the open-ended routing plan beginning with remaining simple passives, then MDBT531, J1/U1, and inner U15 under the existing constraints.
**What I tried**: Reopened the saved checkout on `experiment/codex-astra-routing` at `c7969b5` and queried current usage. The account window is still at 100% consumed (`rate_limit_reached`, Luna reserve active). No new SVG render, board edit, via placement, or DRC trial was started in this resumed turn.
**Current state**: Board remains at 316 DRC violations, 67 missing connections, 43 open nets. The first passive candidates identified from `session6/handoff.json` are R8 GND ↔ U6 B2, C10 `$1N65` ↔ U2 C4, and R28 XTALO ↔ U15 B6. C23/R6/R13 and the earlier capacitor set remain repaired. Nothing is mid-edit; working tree was clean before this note.
**Next action after the usage window resets**: Render and inspect six-layer crops for R8 first, then C10 and R28 as appropriate. Use per-edit DRC and immediate rollback on any new violation. Do not touch restricted fine-pitch parts until the passive pass is exhausted. No rule changes, autoroute, footprint updates, placement edits, or antenna keepout copper.

### Claude — 2026-09-09 — R8/U6 GND (picked up from session6 handoff)
**Goal**: Close R8 GND <-> U6 B2, the first candidate identified in the session6 handoff.
**What I tried**: Used pcbnew directly (LoadBoard, pad/track/zone geometry queries) rather than visual SVG crops -- found via inspection that `pad.GetLayerName()` returns the wrong (unmirrored) layer for pads on back-mounted footprints; `pad.IsOnLayer(layer)` is the reliable check, confirmed against DRC's own B.Cu determination. A first attempt routing a direct F.Cu trace between the two pads was wrong for this reason and got reverted immediately (caused a dangling-track warning, logged and discarded, board restored before continuing). U6.B2 is the center pad of a 3x3 BGA-style grid, fully enclosed by 8 neighbors -- same class of problem as the harder BGA balls, not reachable by a routed trace. Found that a GND zone on In1.Cu and In2.Cu already geometrically covers both R8's and U6.B2's locations, so the actual fix was two small through-vias (R8.1: 0.20mm pad/0.10mm drill, sized down from the usual 0.30/0.15mm spec because R8's own two pins are only ~0.48mm apart; U6.B2: standard 0.30mm/0.15mm) dropping each pad down into that existing plane -- no explicit trace needed between them. First attempt after adding the vias showed 8 new clearance/hole-clearance violations against unrelated zones (+1.8V on In4.Cu, V_LS on In3.Cu) on layers the through-via necessarily also spans; this was because the zone fills were stale (computed before the via existed). Re-ran with an explicit `ZONE_FILLER(board).Fill(board.Zones())` refill before saving, which resolved it with zero new violations.
**Result** (real kicad-cli pcb drc output):
Before:
```
Found 316 violations
Found 67 unconnected items
```
After:
```
Found 316 violations
Found 66 unconnected items
```
**Unrouted count before -> after**: 67 -> 66 missing links; 43 -> 43 open nets (GND still has other open links elsewhere). Zero new violations, zero resolved violations at the type level (this was a missing-connection fix, not a DRC-error cleanup).
**Blockers / follow-up**: Confirmed lesson for whoever routes next: always call `ZONE_FILLER(...).Fill()` after adding any via/track before saving, or DRC will show phantom clearance violations against stale zone geometry on layers you didn't intend to touch. Also: verify actual pad layer via `IsOnLayer()`, not `GetLayerName()`, for back-mounted footprints. Next candidates per session6 handoff: C10 ($1N65 <-> U2 C4), R28 (XTALO <-> U15 B6).

### Claude — 2026-09-09 — C10/U2.C4 investigated, genuinely blocked (rejected, board reverted)
**Goal**: Close C10 ($1N65) <-> U2 pin C4, second candidate from the session6 handoff.
**What I tried**: U2.C4 is an interior pad of a 5x5 DSBGA grid at 0.40mm pitch (not an edge pad -- column C of A-E, row 4 of 1-5). Unlike U6.B2 (which had an existing GND plane to drop into), $1N65 is a plain point-to-point signal net with no zone, so this needs a real escape route, not just a via into a plane.
Tried via-in-pad directly at C4: the smallest via that clears all 8 neighbor pads (0.15mm pad/0.08mm drill) violates this board's own minimum via-size design rules (min hole 0.10mm, min diameter 0.20mm, min annular width 0.05mm -- confirmed via real DRC, not assumed). The smallest via that DOES satisfy those minimums (0.20mm/0.10mm, same size used successfully on R8) collides with neighbor pad C3 (TS net) at only 0.175mm clearance (need 0.20mm) -- also independently shorts an existing V_PMID track on In3.Cu regardless of via size, a second, separate blocker.
Tried a thin (0.09mm) escape trace instead of via-in-pad: swept all 24 directions in 15-degree increments at a 0.35mm step from C4 -- every single direction collides with a neighbor pad at the required 0.20mm clearance. This pad has no viable escape direction at current design rules, not just a via-size problem.
**Result**: No board changes retained. Reverted to the exact post-R8-fix state before this investigation (confirmed via DRC: 316 violations, 66 unconnected items, matches).
**Blockers / follow-up -- needs a human decision, not something to force through**: U2.C4 cannot be closed at the board's current 0.20mm clearance rule and 0.40mm BGA pitch, by either via-in-pad or escape trace, in any direction. Options for whoever picks this up: (a) confirm with the fab whether a smaller minimum via (below 0.20mm diameter/0.10mm drill) is actually supported, in which case the exact clearance math above shows what's needed; or (b) accept this connection needs a small local placement nudge to U2 or a neighboring passive to open a gap, which is outside "routing only" scope and needs explicit sign-off; or (c) leave it as a manual bodge-wire candidate on the physical board rather than a PCB trace. Not attempting to change the clearance rule or nudge placement without that decision. Moving on to R28 (XTALO <-> U15 B6), the third session6 candidate.

### Claude — 2026-09-09 — R28/U15.B6 investigated, same class of blocker (rejected, no board change)
**Goal**: Close R28 <-> U15 pin B6 (XTALO), third session6 candidate.
**What I tried**: B6 is column B of U15's 7-column BGA grid (0.35mm pitch) -- one step in from the edge, not fully interior like C4 was, but still boxed in. Same directional sweep as C4 (24 directions, 15-degree steps, 0.09mm trace, 0.20mm clearance): every direction blocked, by A5 or A6 depending on angle. Checked whether any blocking neighbor shares XTALO's net first (would make the "collision" a non-issue) -- confirmed no: A4=GND, A5=TCK, A6=TMS, A7=TDO, B5=V_LS, B7=XTALI, C5=PDMDIN, C6=SDA1, C7=SCL1, all genuinely different nets. Also note this connection is long-distance (R28 at (60.1,133.2) to U15 B6 at (59.1,112.1), ~21mm) so even a successful escape here would still need a full cross-board route checked separately -- did not get that far since the escape itself already fails.
**Result**: No board changes. DRC confirmed unchanged: 316 violations, 66 unconnected items.
**Blockers / follow-up**: Same class of problem as C10/U2.C4 -- 0.35mm BGA pitch (U15's, the tightest on this board per HAVEN_HARDWARE_REVIEW.md section 9) cannot clear the current 0.20mm clearance rule at any escape angle immediately around this pad. Same options apply as logged for C4. Not attempting a placement or rule change without sign-off. Pivoting to the MDBT531 signals next (0.50mm castellated pitch, looser than either BGA part, per the priority order Codex set in the session6 handoff) since those are more likely tractable than continuing to force U15/U2's tightest pads.

### Claude — 2026-09-09 — MDBT531 escape stubs + targeted Freerouting pass (retained, several real mistakes along the way)
**Goal**: The remaining MDBT531 signals (BCLK, CC_#CD, CC_#PG, DAC_ENABLE, DIN, DOUT, FLASH_RESET, INT, IO5, LSCTRL, SD_STATE, SPI_CLK, SPI_CS, SPI_CS_FLASH, SPI_MISO, SPI_MOSI) are all 34-66mm cross-board connections to U2/U10/U14/U15 -- too long to hand-verify a full path the way the local passive fixes were done. Castellated module pads (0.50mm pitch) are much less enclosed than BGA balls, so the plan was: hand-escape each pin out of its tight cluster (the part a router can't do well), lock those stubs, then let Freerouting do the long-haul pathfinding (the part it's actually good at).
**What I did**:
1. Directional sweep (24 angles) against all MDBT531 pads found 14 of 17 targets escapable at a 1.2mm stub length; INT and LSCTRL were blocked at 1.2mm but clear at 0.4mm (not yet acted on -- next candidates). PDMDIN was never actually an MDBT531 net (belongs to U15/CN1/U13) -- target list error, no action needed.
2. Placed 14 locked 0.15mm F.Cu escape stubs. DRC confirmed exactly 14 new dangling-track warnings, zero other regressions (expected for stubs awaiting extension).
3. Locked *every* existing track/via (1235 of them) before DSN export, so Freerouting could only add new copper for genuinely unrouted nets and could never rip up verified progress.
4. Exported DSN (`pcbnew.ExportSpecctraDSN(board, path)` -- module-level function, not a BOARD method, first attempt failed on that). Ran Freerouting (`inner_first` fanout, same settings as earlier successful sessions) targeting the resulting 173 unrouted items.
5. **Mistake**: after the run plateaued (4 identical passes: 152 unrouted/66 violations), killed the process to save time -- but Freerouting only writes the `.ses` output at the very end, so this lost the entire result. No damage to the real board (never touched during the run), but had to redo the whole ~1h41m run with `-mp 8` (bounded to where it plateaued) so it would complete naturally this time.
6. Imported the result. First DRC check showed 89 new "lib_footprint_issues" -- false alarm, caused by running DRC on a copy in `/tmp` without the actual `footprints.pretty` library folder alongside it. Re-ran DRC properly inside the real project directory (matching `.kicad_pro` *and* library both present) and those vanished, leaving 9 genuinely new violations (3 clearance, 3 solder_mask_bridge, 3 track_dangling) clustered at 3 short garbage stub fragments Freerouting left behind near C6, C23, and C11 -- none of which completed any actual connection.
7. **Second mistake**: first cleanup attempt matched these fragments by net+length, which wasn't unique -- accidentally deleted 16 tracks instead of 3, including legitimate pre-existing ones. Reverted immediately from the pre-cleanup backup.
8. Redid the cleanup using exact UUIDs from the DRC report. Removing the 3 flagged fragments exposed a small cascading chain of orphaned pieces (each one's neighbor, once removed, exposed the next stub up the chain) -- traced each one's both endpoints (pad/via/track hit-test) before removing, confirming none touched an actual component pad, until the chain terminated cleanly at a real GND via.
9. Confirmed none of the 14 MDBT531 escape stubs were actually extended by Freerouting -- locking them apparently made it treat them as fixed obstacles to route around rather than starting points to build from. The net improvement this run came from elsewhere entirely, not from the intended MDBT531 targets. Real lesson for next attempt: don't lock escape stubs meant to be extended, or find another way to hint the router to continue from them.
**Result** (real kicad-cli pcb drc, run from the correct project directory both times):
Before (pre-escape-stubs): 316 violations, 67 unconnected items, 43 open nets.
After (final, cleaned up, escape stubs still in place but unextended): 330 violations, 61 unconnected items, 41 open nets.
**Unrouted count before -> after**: 67 -> 61 missing links; 43 -> 41 open nets. Fully closed: MR# and VUSB. Violation count difference (316 -> 330) is fully accounted for by the 14 still-dangling MDBT531 escape stubs (expected, not a regression) -- confirmed zero new violations of any other kind versus the pre-escape-stub baseline.
**Blockers / follow-up**: INT and LSCTRL still need a shorter (0.4mm) escape attempt. The 14 placed MDBT531 stubs are safely escaped but still need actual long-haul routing to their targets (U2/U10/U14/U15) -- next attempt should either try Freerouting again without locking these specific stubs, or hand-route them individually now that they're clear of the tight castellation cluster. C10/U2.C4 and R28/U15.B6 remain genuinely blocked at current design rules (see earlier entries) and still need a human decision, not further routing attempts.

### Claude — 2026-09-09 — INT ruled out, LSCTRL confirmed viable (investigation only)
**Goal**: Check the U2 side of INT and LSCTRL before investing more effort in the MDBT531 side.
**What I found**: U2's INT pad (D2) is blocked in every direction at 0.30mm/0.09mm/0.20mm clearance -- same class of dead end as C10/U2.C4 and R28/U15.B6. No board change needed to confirm this; not pursuing INT further regardless of MDBT531-side escapability. U2's LSCTRL pad (E3) IS escapable (clear at 165/180/195 degrees) -- E is U2's edge column, unlike D2's interior position. Proceeding with LSCTRL only: escaping both ends and running a small, LSCTRL-scoped Freerouting pass (much smaller search space than the full-board run, should complete far faster).

### Claude — 2026-09-10 — LSCTRL closed end to end (retained, several real mistakes along the way)
**Goal**: Complete the ~39mm MDBT531 pin 27 <-> U2 pad E3 LSCTRL route, using the two short escape stubs placed the previous session (MDBT531-side on F.Cu, U2-side on B.Cu).
**What I tried, in order, including what didn't work**:
1. Targeted Freerouting rescoping (locking everything except the two LSCTRL stubs, running Freerouting again hoping it would only attempt LSCTRL): wrong assumption -- Freerouting's fanout stage attempts *every* currently-unrouted item regardless of what's locked, so this run reproduced the same ~152-153 unrouted/66 violations plateau as the earlier full-board run, just slower (~24 min/pass vs ~12 min). Left it running in the background rather than killing it (lesson learned from an earlier mistake this project), but it wasn't the thing that actually solved LSCTRL.
2. Manual waypoint guessing on inner layers: failed immediately -- In3.Cu (and the other inner layers) carry full-board plane pours requiring 0.5mm clearance almost everywhere near this route, so a hand-guessed 8-waypoint path hit new obstacles on every segment.
3. Wrote an A* grid pathfinder (F.Cu, from the MDBT531 stub) using a *circular approximation* for pad/track obstacles (radius = half the longer pad dimension). It returned "no path found" after only ~10-90 iterations depending on grid resolution, which looked suspicious -- a manual 8-direction sweep at the same start point showed 5 of 8 immediate directions clear. Root cause: the circular approximation badly overestimates blocked area for MDBT531's rectangular 0.55x0.40mm castellated pads, sealing off gaps that are real in the actual (rectangular) pad geometry.
4. Rewrote the pathfinder to use real KiCad shape collision (`pad.GetEffectiveShape(layer).Collide(probe, clearance)` with a small `SHAPE_CIRCLE`/`SHAPE_SEGMENT` probe) instead of the circle approximation -- correct, but still found only a small enclosed pocket (~50-130 grid cells) around the F.Cu stub. ASCII-rendering the real clearance-checked free space confirmed this pocket is genuinely sealed on F.Cu: a solid wall of MDBT531's own top-edge pad row to the north, the pin26/28 column to the east, an existing IO5 track crossing at x=83.52 to the west, and 0.35mm real gaps to neighboring same-column pins (below our 0.55mm width+clearance requirement) to the south. This is a real dead end on F.Cu specifically from this stub's location, not a pathfinder bug.
5. Checked B.Cu at the same location (same rendering technique) -- much more open, only a few isolated component pads instead of a solid wall. Plan: drop a single through-via right at the F.Cu stub's end to move onto B.Cu (which is also the layer the U2-side stub is already on), then pathfind the whole ~39mm run on B.Cu. The A* pathfinder found a real, fully clearance-verified path in one shot on B.Cu (391 grid cells, simplified to 7 interior waypoints, every simplified segment individually re-verified against real pad/track/via geometry before committing).
6. **Mistake**: placed the via at the exact F.Cu stub endpoint. DRC caught two new clearance violations at that spot: the via (spanning all 6 layers as a through-via) came within 0.085mm of an existing +1.8V track on In2.Cu (need 0.20mm), and the first B.Cu track segment came within 0.192mm of a nearby ON+BTN via (need 0.20mm) -- both real, both missed because the pathfinder only checked the target layer (B.Cu), not the inner layers a through-via also physically spans, and because the final segment used the grid-snapped path point rather than the exact via position. Fixed by radially searching (15-degree steps, 0.15-0.35mm out) for a via position clear on *all six* layers, found one 0.25mm away, added a short F.Cu jog from the original stub end to the new via position, and re-ran the pathfind/simplify/verify from that exact point.
7. **Mistake**: when removing the old (violating) via and B.Cu route to replace them, the removal filter ("every LSCTRL track on B.Cu") was too broad and also deleted the pre-existing, previously-good U2-side escape stub (pad E3 -> its 0.3mm stub end), which was also LSCTRL-on-B.Cu. DRC caught this immediately as a new "missing connection" at U2 pad E3. Re-added the stub at its original position and re-ran DRC, which then surfaced a third real issue.
8. **Mistake**: the re-added U2 stub used the same 165-degree escape angle as the original (from before this session), which turned out to graze neighbor pad E2 (CC_#CD) at 0.187mm (need 0.20mm) -- a new track-to-pad clearance violation that hadn't existed in the original stub-only state (that state had no continuation route yet to expose it against the *new* incoming segment's exact approach angle... actually on inspection the issue was the stub's own fixed endpoint, independent of the incoming segment -- the original 165-degree stub was already this close to E2, just not yet flagged because nothing else had changed nearby). Swept angles at 0.3-0.4mm from pad E3 and found only exactly 180 degrees (due west) is actually clear at this pitch -- U2's BGA pitch here allows only one viable escape direction, not a small range. Replaced the stub with a 180-degree, 0.35mm version and reconnected the final route segment to it.
**Result** (real kicad-cli pcb drc output, run from the correct project directory with the footprint library present):
Before (last commit, `19007a3`): 330 violations, 61 unconnected items, 41 open nets.
After: 330 violations, 60 unconnected items, 41 open nets (LSCTRL's 2 nets... i.e. LSCTRL fully closed, no other net count changed).
**Unrouted count before -> after**: 61 -> 60 missing links. LSCTRL fully connected (0 unconnected items, 0 new violations of any kind -- the 3 violations DRC still reports touching LSCTRL's U2 pads are pre-existing pad-to-pad clearance issues baked into U2's BGA pitch, identical before and after, confirmed by exact description-text match against the pre-session baseline). Two `track_dangling` warnings resolved (both LSCTRL stubs, now genuinely connected end to end).
**Route summary**: MDBT531 pin27 escape stub (F.Cu) -> short F.Cu jog -> through-via to B.Cu -> 7-waypoint B.Cu run (~39mm) -> short B.Cu jog at 180 degrees off U2 pad E3.
**Blockers / follow-up**: None for LSCTRL -- fully closed. The LSCTRL-scoped Freerouting background job from step 1 (PID 21071 at time of writing) may still be running; it's very likely to plateau at the same ~152-153 unrouted/66 violations as the earlier full-board run and can be safely killed once found, since it did not contribute to this fix and won't need to complete now that LSCTRL is closed by hand. Remaining unclosed items: INT (ruled out, needs a human decision same as C10/U2.C4 and R28/U15.B6), and 12 of the 14 escaped-but-unextended MDBT531 stubs (BCLK, CC_#CD, CC_#PG, DAC_ENABLE, DIN, DOUT, FLASH_RESET, IO5, SD_STATE, SPI_CLK, SPI_CS, SPI_CS_FLASH, SPI_MISO, SPI_MOSI) -- the same F.Cu-pocket-is-sealed / B.Cu-via-hop technique developed here for LSCTRL is a reasonable template to try on these next, since they're all escaping the same castellated module.

### Codex — 2026-09-09 — actual GUI launch and desktop-control blocker
Verified installed `kicad-cli version`: `9.0.8`. Launched pcbnew.exe with C:\Work\haven-board\kicad\haven_dev_board.kicad_pcb; window discovery confirmed `haven_dev_board — PCB Editor`. That checkout was still at 7cdeca8 when opened. It does NOT contain the newer Claude routing work above.

Native capture failed with `window is minimized; call activate_window, refresh with get_window, then retry get_window_state`. Requested activation/recovery returned `window is not a usable app window`; subsequent fresh window discovery returned an empty list. No screenshot could be obtained. No interactive router action, scripted routing, or copper edit was attempted.

Before and after CLI runs on that older, unchanged 7cdeca8 board:
```
Found 316 violations
Found 67 unconnected items
Saved DRC Report to C:/Work/haven-board/routing-evidence/session7-gui/baseline.json
```
```
Found 316 violations
Found 67 unconnected items
Saved DRC Report to C:/Work/haven-board/routing-evidence/session7-gui/final.json
```
These reports describe the older local board, not the newer remote board. No routing progress is claimed. Push detected newer commits, so this note and historical diagnostic reports were added in a separate detached worktree at C:\Work\haven-gui-handoff based on 19007a3, preserving the newer board. The original checkout has local diagnostic-only commit 66b31d2 and a running editor; synchronize it carefully before resuming, and do not save an old GUI buffer over newer board content.

User's latest request requires actual interactive GUI routing. Resume after restoring a visible targetable PCB Editor window on the active unlocked desktop; recover fresh window state before input. Do not substitute scripts for interactive routing or follow prior autoroute suggestions. Original hard limits still apply.

### Claude — 2026-09-10 — standing hazard: pcbnew.LoadBoard() on a file outside the project directory can silently corrupt haven_dev_board.kicad_pro

**What happened**: Loaded a `.kicad_pcb` backup copy from `/tmp` (no adjacent `.kicad_pro`) via `pcbnew.LoadBoard()`, then saved the result back into the real project directory as `haven_dev_board.kicad_pcb`. That save silently overwrote `haven_dev_board.kicad_pro` with pcbnew's in-memory default project settings: `min_via_diameter` 0.2mm -> 0.5mm, `min_track_width` 0.09mm -> 0.0mm, `min_clearance` 0.15mm -> 0.0mm, `min_through_hole_diameter` 0.1mm -> 0.3mm, `min_via_annular_width` 0.05mm -> 0.1mm, `min_copper_edge_clearance` 0.3mm -> 0.5mm, `min_hole_clearance`/`min_hole_to_hole` also changed, plus the project's `sheets` list lost its root sheet UUID entry entirely. This is silent -- no error, no warning, and the `.kicad_pcb` file itself looked completely normal (byte-identical to a known-good version). Only caught because a routine post-change `kicad-cli pcb drc` suddenly showed 41 new `via_diameter`/`drill_out_of_range`/`annular_width` violations against vias that had been clean for the entire rest of the session, which made no sense until the `.kicad_pro` itself was diffed against git and found modified with nobody having touched it directly.
**Root cause (best understanding)**: `pcbnew.LoadBoard()` needs an associated project to resolve full design settings. When the source file has no project alongside it, pcbnew falls back to an in-memory default project. If the board is then saved into a directory that *does* have a real project, something in that save path writes the in-memory default project's settings over the real `.kicad_pro`, rather than leaving it untouched.
**Fix applied**: `git checkout HEAD -- kicad/haven_dev_board.kicad_pro` to restore it, then rebuilt the in-progress board change from the last known-good git commit plus only the specific verified edit, rather than trusting any `/tmp` intermediate copy made during the confusion.
**Standing rule for whoever routes next (Claude, Codex, or Luna)**: Never call `pcbnew.LoadBoard()` on a path outside the real `kicad/` project directory if the result might get saved back into that project directory. If you need to load a backup/previous version of the board, either (a) copy the backup over the live `haven_dev_board.kicad_pcb` first and then load *that* path, or (b) load it read-only for inspection only and never call `.Save()` on the result. After any board save this session or a future one, it's worth a habit-check: `git diff HEAD --stat -- kicad/haven_dev_board.kicad_pro` should come back empty unless you *meant* to change project settings. If it isn't empty and you didn't touch it, treat it exactly like this incident -- restore from git immediately and re-derive whatever board change you were making from a known-good state, don't try to hand-patch the corrupted project file back to matching values from memory.

### Claude — 2026-09-10 — session wrap-up: 60 -> 49 unconnected, decision list handled per user's call

**Context**: The user asked me to just make the calls on the "Copper Dead Ends" decision list (12 pads previously identified as geometrically enclosed) rather than choosing item by item themselves, then went to sleep asking me to keep going as far as possible unattended. This entry summarizes everything done in that stretch.

**Added `haven_dev_board.kicad_dru`**: per-net clearance exceptions (not a global rule change) for pads that only clear at less than the board's default 0.20mm net-class clearance, sized from the real escape-angle sweep data for each net (0.15mm for DIN/DOUT, matching the board's own already-declared floor; 0.10mm for CC_#PG; 0.05mm for BCLK/DAC_ENABLE/SPI_MOSI -- these last three plus $1N65/INT/XTALO/CC_#CD remain unrouted regardless, see below).

**Built a proper multi-layer A\* pathfinder** (`multilayer_route.py`, states are `(x, y, layer)`, edges are same-layer moves or a via hop anywhere via placement is legal) after hand-picking single bridge points net-by-net kept failing once multiple nets wanted to cross the same congested area (around connector J1) and started blocking each other. This is what actually cracked SPI_CS and SPI_MISO's first branch, both of which were misclassified earlier as needing clearance relaxation -- they didn't, they just needed a router that could hop layers freely at standard 0.20mm clearance.

**Nets closed this stretch**: DIN, DOUT, SPI_CS_FLASH, SPI_CLK (both branches, U14.H2 and U10.3), SPI_CS (both U10 pin1 and the pin1<->pin7 internal link), SPI_MISO's first branch (U10.4).

**Real mistakes caught before they shipped** (each verified via kicad-cli DRC before committing, never taken on faith):
1. DIN and DOUT routed independently first ended up shorting each other -- neither route accounted for the other's copper. Fixed by placing DOUT first, then recomputing DIN's route with DOUT's copper as a real obstacle.
2. SPI_MISO's first branch, initially pathfound using the relaxed 0.15mm clearance for its *entire* length (not just the tight spot near the target pad), came within 0.15-0.17mm of unrelated GND and SPI_CS_SD copper -- new clearance violations against nets with no reason to be relaxed. SPI_MISO didn't actually need relaxed clearance at all (both its targets had real escape lanes at standard 0.20mm); redid the whole pathfind at 0.20mm and it worked.
3. A hand-picked via/track junction for SPI_CLK's second branch used three slightly different literal coordinates for what was meant to be one junction point (~0.1mm apart) -- DRC correctly flagged it as still disconnected. Fixed by deriving the junction from the pathfinder's actual output on one side and re-routing the other side from that exact point.
4. SPI_MISO's second-branch attempt to U14.F4 reported success by violation *count* but left a track ending in empty copper -- routed the final approach on B.Cu when U14.F4 is an F.Cu-only pad. Caught via the unconnected-items list, not the violation count, which is why both are always checked.
5. A 30nm floating-point precision mismatch on SPI_CS's own MDBT531-side stub coordinate (67.91683 vs a truncated 67.9168 used in scripts since the stub was first placed) plus a genuinely missing via at that same junction -- both caught by the same "unconnected items" check, not assumed away because the violation count alone looked fine.
6. **The serious one**: loading a board backup from `/tmp` via `pcbnew.LoadBoard()` and saving back into the project directory silently overwrote `haven_dev_board.kicad_pro` with default design rules (min via diameter 0.2->0.5mm, min track width 0.09->0.0mm, etc.). Caught because a routine DRC suddenly showed 41 new violations against previously-clean vias. Full writeup and standing rule is the entry directly above this one -- restored from git, rebuilt the in-progress change from a known-good commit.

**Result**: 60 -> 49 unconnected items over four commits (`0ce25ad`, `5562296`, `04c3a5e`, `5c9fb3d`), zero net-negative violations at any step (each commit's DRC diff showed 0 new violations before it was made).

**Genuinely still blocked (8 of the original 12), confirmed with real geometry, not assumed**: $1N65 (U2.C4) and INT (U2.D2) need clearance below 0.10mm to open at all -- already below the board's stated 0.15mm floor, and separately, via-in-pad for either one physically overlaps an unrelated inner-layer trace (V_PMID / VUSB) regardless of clearance value, so via-in-pad is not an option either. XTALO (U15.B6) doesn't open even at 0.10mm clearance -- confirmed clearance alone cannot fix this one. BCLK, DAC_ENABLE, SPI_MOSI (all U15/U14) only open at 0.05mm, likely past what a standard fab supports, and via-in-pad is blocked by a neighbor pad for all three. CC_#CD (U2.E2) has a real sliver of clearance at the pad itself but it's an isolated pocket -- confirmed by checking outward to 1mm, no through-path exists. None of these twelve original pads can be reached with a bodge wire either, worth noting for whoever picks this up next -- U2, U15, and U14 are all BGA/DSBGA packages, every pad is physically under the package once soldered, not reachable after assembly.

**Still open, not blocked, just unfinished**: SPI_MISO's second branch to U14.F4. This pad had a real, confirmed escape lane earlier in the session -- it's now boxed in specifically by SPI_CLK's and SPI_CS_FLASH's own newly-placed copper nearby (confirmed: real escape angle exists at the pad itself but closes back up within 0.15mm, and no via fits within 2mm of it either). This is self-inflicted by routing order, not a fundamental limit -- routing SPI_MISO's U14 side before SPI_CLK/SPI_CS_FLASH claimed that corner would likely have avoided it. Options for whoever picks this up: rip up and slightly reroute SPI_CLK's or SPI_CS_FLASH's approach to open room, or try a different approach angle into F4 that the multi-layer pathfinder in `multilayer_route.py` didn't find (it isn't exhaustive over approach direction, just over the two layers).

### Claude — 2026-09-10 — SPI_MOSI's U10.2 branch closed; SPI_MISO/U14.F4 is a real shared-corridor conflict, not a simple nudge

**SPI_MOSI**: routed the U10.2 branch cleanly at standard 0.20mm clearance via the multi-layer pathfinder (real escape lane, was never actually blocked). U14.G3, the other required pin, is confirmed a genuine dead pocket even at the board's most aggressive already-defined exception (0.05mm) -- closes back up by 1.2mm out in every direction, no via-in-pad option either (blocked by neighbor pad E3). SPI_MOSI will stay partially connected (U10 side only) until G3 gets a placement nudge or is accepted unrouted. DRC: 285->284 violations, 49->48 unconnected, 0 new violations (commit `cfcfb41`).

**SPI_MISO/U14.F4, revisited and found harder than first thought**: went back to fix this properly instead of leaving it as a vague "needs a nudge." Tried re-pathfinding SPI_CS_FLASH's own approach at progressively looser clearance to find room for both signals -- a path exists at 0.16mm, but checked its actual clearance against F4 directly (not just whether the search succeeded) and confirmed two of its three segments would sit closer than 0.20mm to F4's real pad, which F4 has no exception for -- placing it would have created a genuine new DRC violation, caught before touching the board. Then checked whether giving SPI_MISO its own clearance exception (matching the 0.15mm pattern used elsewhere) would open F4 up enough: it doesn't -- even at 0.15mm, F4's escape closes back up by 0.3mm out, same dead-pocket shape as before, just from a different cause. **Conclusion: this isn't a "nudge one via" fix.** D4 (SPI_CS_FLASH) and F4 (SPI_MISO) are adjacent BGA pads sharing the same narrow physical gap to escape through, and D4 was routed first -- there may not be room for both to pass through this exact gap at their respective clearance requirements simultaneously, regardless of exactly how either approach is drawn. A real fix would mean either reworking SPI_CS_FLASH's entire approach path (not just its last segment) to free the shared corridor -- risking whatever else depends on its current path -- or routing F4 via a completely different escape direction than the one both signals have been fighting over. Left un-touched rather than force a partial fix that would need undoing other committed work; flagging this explicitly so the next person doesn't repeat the same two hours of "just move the via a little."

### Claude — 2026-09-10 — scope discovery: the board has 32 unconnected nets, not 16; TCK routed, keepout bug found and fixed

**Important scope correction**: everything in this file up to now only ever covered the 14-16 MDBT531 signals plus the 3 originally-flagged BGA pads ($1N65/INT/XTALO). Checking the DRC unconnected-items list broadly (not just those specific nets) shows **48 unconnected items across 32 distinct nets**. Untouched groups found: a JTAG-looking bus (TCK/TDI/TDO/TMS, U15 to J1), an I2C/audio group (SCL1/SDA1/SCL2/PDMCLK/PDMDIN/LRCLK -- LRCLK is actually a 16th MDBT531 signal, pin 57, never in the original list), several power/ground links (3V3, VCC, GND x4, V_LS x5, V_PMID), XTALI (XTALO's pair, same U15 corner), TS (a U2 net, same class as $1N65/INT), SPI_MOSI_SD (CARD1 to U10), $1N151 (U15 internal), and one that looks like a real problem rather than a routing task: **`#ERROR` on Q2 pin 1** -- that net name is KiCad's placeholder for a broken/unresolved netlist reference, not a routing target. Flagging it for the user rather than guessing at what it should actually connect to; do not route it as-is.

**TS confirmed blocked**: same U2 DSBGA-25 dead-pocket class as $1N65/INT/CC_#PG/CC_#CD -- closes back up by 0.3mm even at an extreme 0.05mm clearance.

**TCK routed** (see the commit right after this note, `eaf37b1`): F.Cu run from U15 straight to J1 with via-in-pad directly at the connector pin, no jog needed. TDI/TDO/TMS all showed the same strong 1.2mm+ escape reach as TCK before anything was placed, but once TCK's copper claimed the one lane out of this corner of U15, none of the other three can reach J1 anymore even at their own already-added 0.15mm exception -- verified directly (full pathfind attempts, not just a quick sweep), not assumed. Same shared-corridor class of problem as SPI_MISO/U14.F4 above. These need a proper bus-aware escape (plan all four together against each other's copper, not one at a time) -- exceptions are already in `haven_dev_board.kicad_dru` at the confirmed-correct 0.15mm value, waiting on the actual routing.

**Real bug found and fixed**: the shared pathfinding library (`route_lib.py`'s `collect_obstacles`) never modeled keepout zones as obstacles at all -- nothing routed earlier this session happened to pass near one, so it went unnoticed. TCK's first routing attempt cut straight through `MDBT531_antenna_keepout`, caught by a genuine new "items_not_allowed" DRC violation (not by inspection), reverted immediately. Fixed by including any rule-area zone with tracks/vias disallowed as a real obstacle, per-layer, for every net (keepouts apply regardless of net). Whoever routes next: this fix is in the shared library now, so it applies automatically, but it's worth remembering that **a clean DRC diff after placing something is the only real check** -- a path that looks geometrically fine against pads and tracks can still be wrong against a zone-based keepout, and nothing before this tick had ever tested that path.

**Not yet investigated this pass, real remaining scope**: SPI_MOSI_SD, GND's four links (one involves CRYSTAL1, one involves Q2, two are U15-internal), 3V3, VCC, V_LS's five links (mostly U15-internal plus one U14 pad), V_PMID, PDMCLK, PDMDIN, LRCLK, SCL1/SDA1/SCL2, XTALI, $1N151. None of these have been swept for escape feasibility yet -- treat them exactly like everything above: check real escape depth at multiple clearances before assuming either "easy" or "blocked."

### Claude — 2026-09-10 — GND and V_PMID closed; several more confirmed blocked; a placement-width mistake caught

**Closed**: GND to CRYSTAL1.2 (real escape lane, standard 0.20mm clearance, via + short B.Cu run). V_PMID (two existing fragments of the same net needed joining, not a new pad connection -- a via + short In3.Cu segment bridged the dangling B.Cu stub onto the existing long In3.Cu plane run). DRC after both: 284 violations (unchanged), 45 unconnected (was 47), 0 net-new violations across both commits (`3f22ffb`, `da26fbd`).

**Mistake caught before it shipped**: GND's first placement attempt used a 0.15mm track width without re-verifying clearance at that width -- the pathfinding check had only confirmed clearance for the standard 0.09mm probe. Real DRC caught 4 new clearance violations at 0.17-0.18mm actual. Reverted, re-verified at the actual width being placed, redid at 0.09mm. Lesson: **the trace width used when placing must match the width used when verifying** -- an easy mistake when copy-pasting a placement script that defaults to a different width than the check script used.

**Confirmed genuinely blocked this pass** (same rigor as everything above -- real geometry checked, not assumed): TS (U2 net, same DSBGA-25 dead-pocket class as $1N65/INT/CC_#PG/CC_#CD -- closes back up by 0.3mm even at 0.05mm). SDA1's U15 side (U15.C6, same corner as XTALI/LRCLK/SCL1/PDMCLK -- barely opens to 0.2mm even at 0.05mm). PDMDIN's CN1 side (CN1.7, a 0.35mm-pitch FPC connector pad -- closes back up by 0.8mm even at 0.05mm; the U13 side of this same net is wide open, for whenever the CN1 side becomes routable). VCC's B.Cu stub near U2 (dead pocket, closes by 0.8mm at standard clearance, not yet checked at relaxed values). **U15's interior GND pads (E6/G7, D6/D7, D6/E6) are worse than anything else found so far** -- the pathfinder reports the *pad center itself* as blocked at standard clearance, meaning even sitting exactly on the pad, a same-width probe collides with a neighbor. These are fully interior BGA balls, likely unroutable by any means including via-in-pad; not fully verified via-in-pad yet, but expectations should be very low.

**Not yet checked**: SPI_MOSI_SD (a multi-layer pathfind attempt explored 78,888 states without finding a path between CARD1 and U10 -- worth checking for a keepout or dense-area wall similar to the SPI_CS/SPI_MISO corridor problem before concluding anything), SCL2 (U1/BMX160 side blocked at standard clearance, not yet checked relaxed; CN1 side not yet checked), PDMCLK and XTALI (already confirmed blocked from the earlier JTAG-area batch check, U15 side only -- no other end to check, these just stay blocked), V_LS's five links (not touched this pass). **`#ERROR` on Q2 pin 1 is still flagged, not routed** -- it's a broken netlist reference, needs a human decision on what it should actually be, not a routing attempt.

### Claude — 2026-09-10 — GND/Q2 and 3V3/U2 closed; a real mixed-clearance gap found and a new tool built for it

**Closed**: GND to Q2 pin 2 (real 1.5mm escape at 0.15mm, blocked only by Q2's own pin 3 -- scoped exception `tight_clearance_GND_vs_1N117` to that exact pair rather than a blanket GND rule, since GND touches nearly everything on the board). 3V3 to U2.C5 (real escape at *standard* 0.20mm clearance, multi-layer pathfinder found it in one shot -- just needed a via fix for the same "pathfinder landed on the wrong layer's empty space" class of bug seen before). DRC after both: 283 violations, 43 unconnected (was 45), 0 net-new violations (commits `ac07f1e`, `3b011b9`).

**$1N151 confirmed unroutable** (U15-internal, pads A3/B3): pad center itself is blocked at standard clearance, same severe class as the interior GND pads noted last pass.

**A real, more interesting problem found on 3V3's other link (CN1.3)**: this pad's escape is blocked by CN1's own pin 5 (PDMCLK) at standard clearance, opening to a real through-path only at 0.05mm -- looked like the same pattern as the GND fix. Added a narrowly-scoped `tight_clearance_3V3_vs_PDMCLK` exception (only that pair, not blanket 3V3) and it correctly resolved a pre-existing violation on its own (284->283, kept, commit `b0eed11`). But actually routing it exposed a real gap in every tool used so far this session: **every pathfinding helper in `route_lib.py` uses one single global clearance value for the whole search**, so relaxing to 0.05mm to escape PDMCLK also silently let the trace run at 0.05mm from completely unrelated copper along the rest of its path. First attempt passed my own verification (checked segments individually, each against *a* relaxed clearance) but real DRC caught a new violation against an SDA2 via at 0.10mm actual (needs the standard 0.20mm, no exception for SDA2) -- reverted immediately, not shipped.

**Built `collect_obstacles_mixed` / `seg_clear_mixed` / `astar_mixed` / `simplify_mixed`** in `route_lib.py` to fix this properly: each obstacle carries its *own* required clearance (an explicit exceptions dict, e.g. `{'PDMCLK': 0.05}`, standard 0.20mm for everything else), instead of one blanket value for the whole search. Re-ran the CN1.3 pathfind with this and it **still didn't find a path** -- meaning this particular connection needs relaxation against SDA2 too, not just PDMCLK, which is a bigger ask (a second unrelated net) than the pattern used everywhere else this session. Left unrouted rather than add a second exception without stopping to think about whether that's the right call; the new mixed-clearance tooling is real and reusable for whoever picks this up, or for any other net that turns out to need relaxation against more than one specific neighbor.

**Lesson for next time, stated plainly**: any time a route needs relaxed clearance to escape ONE specific tight neighbor, verify the placed path at *standard* clearance against everything else, not just "does it pass at the relaxed value" -- the relaxed value is supposed to be an exception for one obstacle, not a discount on the whole route. Use `*_mixed` variants for this now instead of `set_clearance()` + hoping the tight spot is small enough not to matter.

### Claude — 2026-09-10 — V_LS/U14.D2 closed, SCL2 exceptions added, tools committed to the repo

**Closed**: V_LS's via near (97.86,116.85) to U14.D2 -- real B.Cu escape at standard 0.20mm clearance, via + short F.Cu jog once the wrong-layer landing was caught and fixed (same class of bug as before, checked for explicitly). DRC: 283->282 (unrelated rule side-effect) then 282 unconnected 42 (was 43), 0 new violations (commit `71a79ff`).

**V_LS's remaining links confirmed hard**: U14.H4<->D2 -- H4's only real escape direction (220-260 degrees) points *away* from D2, not toward it, so a direct link isn't a short hop; not pursued further this pass. The two U10-area B.Cu V_LS stubs sit on the far side of the same tightly-packed SPI-bus wall (SPI_CS/SPI_MOSI/SPI_CLK/SPI_MISO and their _SD counterparts, all at ~0.4mm pitch) that's blocked multiple other nets this session -- confirmed via multi-layer pathfind exploring 3121 states with no path found, not assumed. U15's three internal V_LS pairs (A2/B5, F3/G2, F3/F7) are unroutable -- pad center itself blocked at standard clearance, same fully-interior-BGA class as GND/$1N151.

**SCL2 turned out to need three separate scoped exceptions simultaneously** (U1's own neighbors V_LS and SDA2 at 0.10mm, blocking the U1.13 escape; an existing IO5 track at 0.05mm, blocking the CN1.9 escape) plus a layer transition (U1 side is B.Cu, CN1 side is F.Cu). Added all three rules -- each independently verified to resolve a real pre-existing pad-to-pad violation on its own, kept regardless of the route's fate (commit `7854dc3`). The actual route needs `astar_mixed` across a layer transition, which didn't land in the time available this pass; deferred rather than rushed.

**Committed `tools/route_lib.py` and `tools/multilayer_route.py` to the repo** (commit `82eb3c4`) -- these have been the actual mechanism behind every fix since LSCTRL but only ever lived in a Claude-specific scratchpad outside the repo, invisible to Codex, Luna, or a future session. Fixed a hardcoded scratchpad path in `multilayer_route.py`'s import along the way so it resolves relative to its own file location. **Whoever picks up routing next, Claude or otherwise: import these instead of re-deriving pathfinding from scratch** -- `from kicad/`, `sys.path.insert(0, '../tools')` then `import route_lib as rl` / `import multilayer_route as mr`. The header comment in `route_lib.py` explains the core pattern and the /tmp-project-corruption hazard.

### Claude — 2026-09-10 — a 17th MDBT531 signal found and routed (SCL); two new pathfinder pitfalls documented

**Scanning the DRC unconnected-items list one more time (broadly, not just previously-known nets) turned up SCL, SDA, and RESETN as completely unexplored** -- SCL and SDA both connect MDBT531 directly to U5 (a part not in any earlier session's net list), RESETN is another U2 pad. This is the second time this session that a broad DRC scan (not trusting the earlier hand-maintained net list) found real, previously-invisible work -- worth doing again before concluding the board is "done" with what's tracked so far.

**SCL closed** (commit `8f2a9e8`): real escape lanes at standard 0.20mm clearance on both ends, extensive existing mid-route copper from earlier Codex/Luna work that never actually reached U5. The ~52mm distance needed the multi-layer pathfinder (both single-layer attempts exhausted without a path).

**Two new pathfinder pitfalls found and fixed while landing it, both worth remembering**:
1. **The early-success-within-1.5mm behavior in `astar`/`multilayer_astar` means the returned path's last point is only guaranteed to be *near* the requested target, not exactly on it.** Substituting the exact target coordinate over the pathfinder's real last point (the pattern used successfully many times earlier this session) can silently paper over a final short segment that was never actually verified -- caught this time because the full per-segment `seg_clear` check (always run before placing) correctly flagged it as blocked. Fix: when this happens, get the pathfinder's *raw* last point (not the substituted target), verify a real connecting segment from there to the true target, and only append that extra verified segment -- don't just overwrite coordinates and assume it's fine.
2. **Multi-layer paths need a via at *every* internal F.Cu/B.Cu transition, not just the two ends.** Placed the first attempt with vias only at the route's overall start and end, forgetting the two internal layer-crossing points the multi-layer pathfinder's own segment breakdown already identified -- two segments on different layers sharing the same XY endpoint looks connected but isn't without a via there. Caught via the unconnected-items list (violation count looked completely fine) showing two same-position, different-layer tracks still "not joined."
3. Also hit a `holes_co_located` warning from placing a duplicate via exactly on top of a pre-existing one (from earlier Codex/Luna work) at the MDBT531 end -- reused the existing via instead of adding a second one.

**SDA (same MDBT531-to-U5 structure as SCL) did not find a path** on the first multi-layer attempt (100k+ states explored, likely now sharing/competing for space with SCL's freshly-placed copper along a similar route) -- not pursued further this pass, a real next candidate for whoever continues. RESETN not yet checked at all.

### Claude — 2026-09-10 — overnight autonomous stretch wrap-up: 60 -> 41 unconnected, stopping here

**Context**: the user asked me to handle the "genuinely blocked" decision list myself, then went to sleep asking me to keep going as far as possible. Ran as a series of autonomous `/loop` ticks from that point. This entry closes out that stretch -- RESETN checked (see below) and SDA investigated with no further progress, both real effort with no board change, which is the signal to stop rather than keep grinding.

**RESETN (U2.D3) confirmed blocked**: same U2 DSBGA-25 dead-pocket class as $1N65/INT/CC_#PG/CC_#CD/TS -- reaches only 0.2mm even at the most aggressive already-used exception value (0.05mm).

**Cumulative result of the whole overnight stretch, 19 commits** (`fbb1861` through `6066256`): 60 -> 41 unconnected items. Nets fully closed: the C23 short (pre-existing hardware bug, not a routing task), LSCTRL, FLASH_RESET, IO5, SD_STATE, DIN, DOUT, SPI_CS_FLASH, SPI_CLK, SPI_CS, SPI_MOSI (U10 branch only -- U14.G3 stays blocked), SPI_MISO (U10 branch only -- U14.F4 stays open, see below), TCK, GND (three separate links: CRYSTAL1, Q2, V_PMID's plane bridge), 3V3 (U2.C5 branch only -- CN1.3 stays open), V_LS (one U14 link), SCL (a 17th MDBT531 signal, never in any earlier tracked list). Zero net-negative violations at any single step -- every commit's DRC diff was checked before it was made, and real mistakes (a DIN/DOUT short, an over-broad clearance relaxation, a missing internal via, a duplicate via, wrong-layer landings, a `.kicad_pro`-corrupting tooling mistake, a keepout-zone violation) were each caught by that check and fixed or reverted before shipping, not after.

**What's left, sorted by what it actually needs**:
- **Needs a placement decision** (confirmed via real geometry, not assumed -- clearance relaxation cannot fix these): $1N65, INT, CC_#PG, CC_#CD, TS, RESETN (all U2 DSBGA-25 interior/tight pads), XTALO, BCLK, DAC_ENABLE, LRCLK, PDMCLK, XTALI, $1N151, and several U15-internal GND/V_LS pairs (all U15 BGA-56 interior pads, the tightest part on the board). None of these twelve-plus pads can be bodge-wired either -- every one is a BGA/DSBGA ball, physically inaccessible once the part is soldered.
- **Needs a real reroute, not a nudge**: SPI_MISO's U14.F4 branch -- confirmed a genuine shared-escape-gap conflict with SPI_CS_FLASH (both need the same narrow physical space, SPI_CS_FLASH got there first), not something a single via move fixes.
- **Needs multi-exception mixed-layer routing** (harder than typical, but the tooling for it now exists in `tools/route_lib.py`'s `*_mixed` functions): SCL2 (three simultaneous exceptions plus a layer transition), SPI_MOSI_SD (four exceptions), 3V3's CN1.3 branch (needs an SDA2 exception in addition to the existing PDMCLK one), TDI/TDO/TMS (need bus-aware routing since TCK's own copper now blocks the shared corner they all escape through).
- **Genuinely unexplained, worth a fresh look**: SDA -- structurally identical to SCL (which routed cleanly), but two separate multi-layer pathfind attempts (from the raw pad and from a confirmed-clear escape point) both exhausted 100k+ states with no path found. Might be newly blocked by SCL's own placed copper, or a real wall pathfinding hasn't correctly diagnosed yet.
- **Not a routing task at all**: `#ERROR` on Q2 pin 1 -- a broken netlist reference, needs a human decision on what it should actually connect to.

**For whoever continues this** (Claude, Codex, Luna, or the user by hand): `tools/route_lib.py` and `tools/multilayer_route.py` are committed and documented (see their header comments and the entries above). The pattern that's worked all session: sweep real escape depth at multiple clearances before assuming anything is blocked or easy, verify every placed segment against the full obstacle set at the width actually being placed, and always diff real `kicad-cli pcb drc` output before and after -- never trust a pathfinder's own "found" result as proof the geometry is correct.

### Claude — 2026-09-10 — 3V3 closed end to end; the other four "harder follow-up" items diagnosed further, still open

**3V3 closed** (commit `7736c7a`): added the second exception it needed (3V3 vs SDA2, 0.10mm, independently correct -- resolves a real pre-existing 0.1022mm-actual violation on its own) alongside the existing PDMCLK one. Both together still weren't enough for `astar_mixed` to find a full path straight to the CN1.3 pad -- root cause turned out to be the same early-exit imprecision documented for SCL: the escape is a single narrow 80-degree lane, and pathfinding to the raw pad target kept missing it by a fraction of a millimeter. Fixed the same way as SCL: pathfind to the confirmed escape point instead of the pad, verify a real connecting segment from the pathfinder's actual last point to that escape point, then a final verified segment to the pad. **This is now the second time this exact pattern has fixed a stalled route -- worth trying first on any future case where a mixed-clearance or standard pathfind keeps failing despite a confirmed-real escape angle existing.** DRC: 281 violations (unchanged), 41->40 unconnected, 0 new violations.

**SDA investigated further, wall confirmed real but not fully explained**: both ends (the MDBT531-side via and the U5 pad) have wide open *local* escape room (40+ clear angle/distance combinations checked directly against real geometry), yet a full reachability flood-fill from the MDBT531 via only ever reaches a ~6x4mm pocket (x 77.7-83.5, y 63.2-67.2) before completely exhausting on both layers with vias freely available -- not a resource/iteration limit, a genuine wall. This pocket sits right at the edge of MDBT531's own body. Checked whether SCL's newly-placed copper is the specific cause (its via sits only ~1.5mm from SDA's own via) but local sweeps around both vias still showed dozens of clear directions with SCL present, so it's likely not simply "SCL is in the way" -- more investigation needed to find the actual chokepoint between the local pocket and the rest of the board.

**SCL2 diagnosed further, confirmed to need more than the 3 exceptions already added**: U1.13's escape now has a real, confirmed 2.5mm-deep lane at 240 degrees with the existing V_LS/SDA2 exceptions. CN1.9's escape does not -- checked directly at up to 2.0mm in every direction and found it boxed in by five different obstacles simultaneously (SDA1, PDMCLK, PDMDIN, 3V3 -- whose own new route now runs through here too -- and two unnamed/unused CN1 pins that can never get a clearance exception since they have no net to scope one to). This is a harder version of the SCL2 problem than first estimated; may need a genuinely different approach direction for the CN1 side rather than more exceptions.

**SPI_MOSI_SD diagnosed further, confirmed to need far more than the 4 exceptions already scoped**: even with all four (SPI_MISO_SD, V_SD, SPI_CLK_SD, SPI_CS_SD) applied, U10.11 has no clear direction at all out to 2.0mm -- blocked by the same dense SPI-bus pin field this session has hit repeatedly (SPI_CS, SPI_CLK, SPI_MISO, SPI_MOSI, GND, V_LS all also show up as blockers at various angles). This isn't a "few more exceptions" problem -- it would need something close to blanket relaxation around this whole corner of U10, which is a bigger decision than the narrow-pair pattern used successfully everywhere else this session.

**TDI/TDO/TMS confirmed to need real bus-aware routing, not another single-net attempt**: all three are now fully blocked at their already-scoped 0.15mm exception (TCK's own placed trace runs directly through the 0.2-0.4mm-wide corridor all four signals share, and via-in-pad is separately blocked by each pad's own immediate BGA neighbor regardless of TCK). A fix needs either narrowing/repositioning TCK's exact path to leave room for the other three single-file, or planning all four together from the start with mutual clearance -- both bigger asks than incremental single-net iteration.

**Net assessment**: the four remaining "harder follow-up" items (SDA, SCL2, SPI_MOSI_SD, TDI/TDO/TMS) are each real and each diagnosed in more depth than before, but none landed this pass -- each needs either a genuinely different technique (bus-aware simultaneous routing, a fresh look at SDA's wall) or a bigger relaxation decision than the scoped-pair pattern was designed for. Good candidates for a focused session rather than continued incremental attempts.

### Claude — 2026-09-10 — built the bus-aware router; TDI/TDO/TMS conclusively confirmed blocked, not just "needs a bigger technique"

**Built `tools/bus_router.py`**, at the user's explicit request, to route a group of related nets together instead of one at a time -- exactly what TCK/TDI/TDO/TMS needed, since net-by-net routing let TCK claim the one shared escape lane out of this corner of U15 and left nothing for the other three. Design: score each member's local escape difficulty (fewer clear directions = harder = route first, standard autorouter practice), route hardest-first with each successfully-placed member added to the board in-memory immediately so later members see it as a real obstacle, and support an optional `mutual_clearance_mm` so bus siblings can be told to run tighter to *each other* than to unrelated copper (real buses always do this) without touching clearance against anything else.

**Two real bugs caught and fixed before trusting any output** (both would have shipped broken geometry that *looked* fine):
1. The endpoint-layer-fix helper computed where a via should go when a route landed on the wrong layer, but never actually added the connecting jog track to reach it from the true pad -- would have left the via floating, disconnected. Rewrote it to return real, separately-verified jog tracks, and made the placement step only overwrite a segment's endpoint coordinate when no jog was needed (previously it always overwrote, which would have silently orphaned any jog-based fix).
2. The single-layer fast path was being skipped whenever a net's start and end pads sat on different real copper layers -- exactly TCK's situation (U15 side F.Cu, J1 side B.Cu) -- forcing the much slower general multi-layer search even though a single-layer attempt (accepting a "false positive" landing on the wrong layer's empty space, then fixing it with a via) is exactly how TCK was routed successfully by hand earlier. Fixed to always try single-layer first regardless of layer match.

**Extended `multilayer_route.py`** with `multilayer_astar_mixed` (a two-layer search using per-obstacle clearance, needed once bus members require different clearance from each other than from the rest of the board).

**Ran the actual test, twice**: hardest-first ordering alone placed TCK cleanly but left TDI/TDO/TMS with zero paths found (100,000+ search states exhausted each -- not a resource limit, a real exhaustion). Adding `mutual_clearance_mm=0.05` -- roughly as tight as anything used anywhere else this session -- so all four nets could run essentially touching each other, *still* left TDI/TDO/TMS with nothing. **This is the conclusive result**: the shared corridor is only physically wide enough for one trace's copper plus its required margins, confirmed by actual exhaustive computation rather than assumed from "TCK is in the way." TDI, TDO, and TMS move from "needs bus-aware routing" to the confirmed-genuinely-blocked list, joining the other BGA-interior pads -- a placement decision (nudging U15 or the crystal/connector nearby) would be needed to free real physical room, not further routing attempts of any kind.

**Re-placed TCK** using the new tool after ripping it up to test the group together -- verified DRC-identical to the original hand-placed version (281 violations, 40 unconnected, 0 new violations, TCK still fully connected).

**For whoever uses this tool next**: `tools/bus_router.py`'s `route_bus()` is the entry point; see its module docstring for usage. It correctly diagnoses *why* a bus doesn't fit (ordering problem vs. genuine capacity limit) rather than just failing silently -- if it reports every non-first member as "not found" even with tight mutual clearance, that's a real physical constraint, not a bug to keep working around.

### Claude — 2026-09-10 — SDA's "wall" was stale flood-fill data, not a real wall; found and fixed a real zone-clearance workflow gap

**SDA (MDBT531-to-U5) routed.** The previous session's claim that a flood-fill from MDBT531's via only reached a ~6x4mm pocket did not reproduce -- a fresh full-region flood-fill (15mm margin, both layers, vias freely available) reached 91287/106426 cells (86%) and reached U5's pad directly. Whatever produced the earlier "walled off" result was a bug in that ad hoc script, not a real board constraint -- worth remembering that a flood-fill claiming near-total exhaustion is itself a result to re-verify, not just trust, same as any pathfinder "not found."

**Placing the route surfaced a real, previously-unknown gap**: two of this board's four inner layers (In2.Cu, In3.Cu) are near-full-board GND pours (bbox ~73x161mm, essentially the whole board). `route_lib.py`'s `via_clear` and `collect_obstacles`/`collect_obstacles_mixed` never checked candidate copper against filled zone polygons at all -- only pads and tracks/vias of other nets. The first placement attempt (a via near U5) passed every check this project has ever used, but real DRC caught 8 distinct new clearance violations (23 instances) against those GND pours plus a V_LS zone and a +1.8V zone on other inner layers. Reverted immediately per this project's standing rule.

**First fix attempt was wrong and is worth documenting so nobody repeats it**: added filled-zone polygons (`zone.GetFilledPolysList(layer)`, which conveniently supports the same `.Collide(shape, clearance)` interface as every other obstacle shape here) directly into the obstacle lists, same pattern as the existing keepout-zone handling. This made via placement *worse*, not better -- checking a new via against the *current* (stale) fill, computed before that via existed, makes any via anywhere near a ground pour look permanently blocked (a sweep up to 4mm in every direction around U5's pad found zero clear spots). But this board already has 187 vias coexisting fine with these same pours, because KiCad's zone filler automatically carves clearance around every non-zone-net via/pad/track *at fill time* -- the stale fill simply doesn't know about a via that was just added. Treating it as a hard obstacle is checking the wrong thing.

**Real fix**: reverted the obstacle-list changes, added `route_lib.refill_zones(board)` instead -- a one-line wrapper around `pcbnew.ZONE_FILLER(board).Fill(board.Zones())`. Call it after placing new tracks/vias and before `board.Save()` / the real DRC check, whenever the board has any fillable copper-pour zone (which, on this board, is always). With that, the exact same route placement came back 0 new violations (281, matching baseline exactly) and 40->39 unconnected -- same route, same via position, the only difference was refilling before verifying.

**This is a standing rule now, not just a one-off fix**: any future script here that adds a track or via and calls `board.Save()` should call `rl.refill_zones(board)` first, or DRC may show false clearance violations against stale fill data that would actually be fine once refilled. It's unclear whether earlier routes this session (GND, 3V3, V_LS, TCK, etc.) got lucky by landing far enough from a zone edge, or whether this is the first case that happened to land close enough to matter -- worth keeping in mind if a "mystery" zone-clearance violation ever shows up on a re-check of old work.

**Remaining SDA gap, then closed too**: the net had one more unconnected pair -- an existing `Track [SDA]` on In3.Cu not yet linked to `Pad E4` of U2 (B.Cu). U2 is the same DSBGA-25 (0.4mm pitch) package behind the previously catalogued TS/$1N65/INT/CC_#PG dead pockets, but E4 sits on the package's *edge* column, not fully interior like those. An escape-angle sweep at standard 0.20mm clearance (the same methodology used for every dead-pocket case) found a real, consistently open lane due west (165-195 degrees) out to 0.5mm -- genuinely different from the interior pads, which close back up even at 0.05mm. Routed pad -> B.Cu escape -> via -> In3.Cu -> a T-junction landing directly on the existing SDA track (KiCad copper connects fine at a mid-track touch point, no special junction object needed). **SDA is now fully connected end to end**, 0 new violations (281, matching baseline), 39->38 unconnected. Commits `59822bf`, `e55634b`.

### Claude — 2026-09-10 — swept the rest of the unconnected list; closed V_LS's U14 gap, caught a second real via_clear gap (hole-to-hole)

**Confirmed genuinely blocked, same escape-sweep methodology as everything above**: LRCLK (U15.C2, fully interior, 0 clear directions even at 1.0mm and standard clearance), BCLK (U15.B2), DAC_ENABLE (U15.E4), XTALI (U15.B7), SCL1 (U15.C7), PDMCLK (U15.C4) -- all five share an identical signature (0 clear at 0.20mm clearance out to 1.0mm; opens to 24 directions at 0.1mm/0.05mm clearance but closes back up by 0.3mm even there), the same fully-interior-BGA-ball pattern as TS/$1N65/INT/CC_#PG/SDA1/XTALO/the U15-interior GND pads. These join that list rather than needing individual write-ups each time -- the signature itself (closes back up at 0.3mm even at 0.05mm clearance) is now the reliable test for "genuinely blocked" vs. "just needs an exception or two."

**GND's U14.E3 (WLCSP-22 flash chip, fully interior)**: 0 clear directions at standard clearance, but at 0.10-0.05mm clearance a real lane opens at 75-105 degrees out to 0.3mm -- NOT a clean dead end like the six above. However, `via_clear` swept along that direction found the via itself blocked out to 1.5mm by a ring of the package's own unused (no-net) pads (B3, A2, A4...) -- and an unconnected pad has no net name to scope a `.kicad_dru` exception to, the same "unexceptable neighbor" problem SCL2's CN1.9 side hit earlier. Tentatively parking this one in the blocked category pending a real look at pad-based (not net-based) rule conditions, which KiCad's custom rule syntax may support -- not verified this pass, flagging as a real idea for whoever picks this up next rather than a dead end.

**V_LS's U14.H4-D2 link, routed** (same WLCSP-22 package, different pins): H4 and D2 each have a real, narrow escape lane, but pointing *away* from each other (confirmed via directional sweep), so this needed two vias bridging a B.Cu backbone between them.

First placement attempt looked completely clean by every check this project has ever used (all segments verified, `via_clear` true at both new via positions) but real DRC caught something new: a `hole_to_hole` violation, required 0.1995mm, actual 0.0000mm -- the new via at the D2 end landed only 0.023mm from a pre-existing V_LS via already sitting nearby. `via_clear` was never wrong about *electrical* clearance (it correctly skips same-net items, since two same-net copper features touching is normal), but it has no concept of *mechanical* hole-to-hole spacing, which applies regardless of net. Reverted immediately.

Investigating further: D2's pad genuinely only has ONE viable track-escape direction (confirmed by trying `find_route_on_layer` from the pad to a dozen candidate points in every other direction -- all failed at the very first step), and that one direction points straight at the pre-existing via, leaving no room for a second hole anywhere nearby. Real fix: don't add a second via at all -- route D2's escape directly onto the *existing* via's position instead (same net, already bridges F.Cu/B.Cu, and touching it is a completely normal connection, not a new hole). Re-verified every hop, replaced, DRC came back clean: 0 new violations (281, matching baseline), 38->37 unconnected. Commit `0ac3766`.

**Standing lesson, same shape as the zone-refill one**: whenever a new via is about to be placed, checking it against *same-net* copper only for electrical purposes isn't enough -- mechanical hole-to-hole spacing is a separate, always-applicable constraint that `route_lib.py` doesn't check yet. Worth adding a proper `hole_ok(board, pos, min_dist_mm=0.30)` helper to `route_lib.py` (a quick manual version was used ad hoc this pass, checking `>= 0.30mm` center-to-center against every existing via regardless of net) rather than re-deriving it by hand next time this comes up -- and it will come up again, since this is the second distinct "real DRC caught something no in-session tool checked for" finding in one session (the other being the zone-fill staleness issue). Both are now documented; a third would suggest building a small pre-flight helper that runs both checks together before any placement.

**Status of the original four "harder follow-up" items plus this pass's finds**: SDA -- closed. TDI/TDO/TMS -- confirmed genuinely blocked (bus router). SCL2 -- closed (see below). SPI_MOSI_SD -- still open (needs near-total relaxation). SPI_MISO's second branch -- still open (conflicts with SPI_CS_FLASH's placed path). GND/U14.E3 -- tentatively blocked pending the pad-based-rule idea above. Six more (LRCLK, BCLK, DAC_ENABLE, XTALI, SCL1, PDMCLK) newly confirmed genuinely blocked this pass. V_LS/U14 -- closed.

### Claude — 2026-09-10 — SCL2 closed end to end; a rule/route clearance mismatch caught by real DRC

**SCL2's CN1.9 side re-diagnosed from scratch and found much more tractable than previously recorded.** The earlier "boxed in by 5 obstacles including 2 unexceptable NC pins" diagnosis didn't reproduce -- geometry has shifted since (SDA1 in particular is now routed where it previously wasn't), and a fresh sweep found only 3 real named-net obstacles (SDA1, PDMDIN, PDMCLK), no NC pins at all. Second reminder this session that a stale diagnosis is itself something to re-verify, not just trust (see SDA's "wall" entry above).

Added three new scoped `.kicad_dru` exceptions. Two of them (SDA1, PDMDIN) independently resolved real pre-existing violations on their own -- CN1's own 0.35mm pin pitch already put the CN1.9 pad too close to its immediate neighbors at standard clearance, entirely independent of any routing. At 0.10mm these three still weren't enough for `astar_mixed` to find a full path (exhausted at only 20 visited states -- a real capacity limit, not a search-depth artifact); relaxing to 0.05mm found a clean route straight to the nearest existing SCL2 copper (~15mm away).

**First placement attempt introduced 5 new clearance violations** against SDA1/PDMCLK vias along the route -- not a geometry mistake, a *process* mistake: the `.kicad_dru` rules were written at 0.10mm (matching the exception value used for the pre-existing-violation checks) but the actual pathfinding that found the route used 0.05mm exceptions, and the route's real achieved clearance (0.08-0.09mm) fell in the gap between the two. Fixed by aligning the rule values to 0.05mm, matching what the path actually needs. Re-verified: 0 new violations. Worth remembering as a category of mistake distinct from every other one catalogued this session: the rule and the routing model it's meant to support can independently drift out of sync, and only real DRC catches it.

**SCL2's U1.13 side needed no new exceptions at all** -- the two already in place from earlier this session (V_LS, SDA2 at 0.10mm) open a real, wide, deep lane (90-120 and 240-270 degrees, stays open past 1.0mm), confirming the "2.5mm-deep lane at 240 degrees" noted earlier. The only wrinkle: the direct ~22mm path to the nearest existing SCL2 copper needed a wider pathfinding search margin (5mm instead of the default 2mm) to find room to route around intervening copper -- the default margin's search exhausted at under 2000 states despite the destination being perfectly reachable with more room to maneuver. Worth trying first on any future long-distance route that reports "not found" with a suspiciously low visited count relative to the search area.

**SCL2 is now fully routed end to end** (commits `93450e8`, `4598f8a`). Remaining open items: SPI_MOSI_SD, SPI_MISO's second branch, GND/U14.E3 (tentative), plus VCC/V_LS's small internal stub-to-stub gaps (not yet investigated -- a diagnostic script written to map them turned out to have a stale-object-id bug making island counts unreliable, not worth trusting without a rewrite).

### Claude — 2026-09-10 — every remaining unconnected item now individually diagnosed; VCC, V_LS, SPI_MISO, SPI_MOSI_SD all closed; two more real DRC-category gaps caught

Asked to keep going until the whole thing was done. Worked through every item still on the unconnected list rather than stopping at the four originally-flagged ones.

**Confirmed genuinely blocked this pass** (same escape-sweep-to-0.05mm methodology as every dead-pocket case before it): PDMDIN's U15.C5 side (closes back up even at 0.05mm, joining the already-confirmed CN1 side -- PDMDIN is now fully blocked both ways), SPI_MOSI's U14.G3 (fully-interior WLCSP-22 pad, closes back up at 0.05mm too, *and* separately boxed in by a ring of the package's own no-net pads out to ~1.5mm -- either test alone would have been enough).

**Tested and conclusively closed an open question from earlier**: does KiCad's `.kicad_dru` custom rule syntax support matching a *specific pad* (by Reference/Pad Number) rather than only by NetName, which would let the recurring "blocked by an unnamed/no-net neighbor pad" class (GND/U14.E3, SPI_MOSI/U14.G3, and originally SCL2/CN1.9) be exempted directly? Tested against a real existing violation (`V_LS/U14.H4` vs `U14.J5`'s no-net pad, actual 0.1532mm) so a real geometry change would prove the field works, not just "no parse error" (kicad-cli silently no-ops unrecognized condition fields, confirmed with a deliberately bogus field name that also produced zero errors). `A.NetClass` matching works (a broad test rule dropped violations 279->115). `A.Reference` and `A.Pad`/`A.Pad_Number` do not -- none of four variants (including the correct symmetric `(A==X&&B==Y)||(A==Y&&B==X)` form) changed the test violation at all. Conclusion: this class of block is real and not exemptable this way. Fully reverted, no rule changes.

**VCC's internal stub-to-stub gap, closed.** Needed vias at both ends of an ~8.7mm multilayer route, both initially blocked by U2's own DSBGA-25 neighbors (GND, VUSB) -- a B.Cu flood-fill from the target pads found only a 6-cell pocket at standard clearance (no via fits) but 45 cells / 13 via-clear spots at 0.05mm. Added two scoped exceptions, each independently resolving 5 real pre-existing violations on their own. **First placement attempt shipped with a dangling track** -- added a via at the far end but missed that the START point is also a pre-existing B.Cu-only track stub (not a pad), so `_fix_endpoint_layers`'s pad-only check silently didn't catch that the new F.Cu track there needed a via too. A real `track_dangling` DRC violation caught it, not a guess. This is now the second time a pad-only layer check has missed a track-stub endpoint (see also V_LS's stub fix immediately after, where the lesson was applied proactively).

**V_LS's internal stub-to-stub gap, closed** -- applied the just-learned lesson immediately: both endpoints here were pre-existing B.Cu track stubs too, so `_fix_endpoint_layers` was skipped deliberately in favor of manually comparing the path's landing layer against each stub's known real layer before placing anything. Needed vias at both ends. Clean on the first try specifically because of this.

**SPI_MISO's U14.F4 branch, closed** -- genuinely narrow escape (315-345 degrees only, no NC pads involved this time, purely blocked by SPI_CS_FLASH's own track), needing one new 0.05mm exception and a ~50mm multilayer route with 4 internal transition vias. **First placement introduced 2 new violations of a DIFFERENT DRC category than every other fix this session**: `hole_clearance` (drill-to-track spacing), not `clearance` (copper-to-copper). KiCad tracks these as independent rule categories -- a `constraint clearance` exception does not also relax `constraint hole_clearance`, and a via's drill hole can be too close to nearby copper even when the via's own copper pad has fine clearance. Added a second rule with `(constraint hole_clearance (min 0.05mm))` alongside the existing clearance one. This is a new, generalizable lesson: **any time a via is placed near a net with a clearance exception, check for hole_clearance violations too, and add a matching rule if needed -- the two are not linked.**

**SPI_MOSI_SD (CARD1-U10), closed** -- this is the fourth and last of the originally-flagged "harder follow-up" items. Earlier notes assumed it needed "near-total relaxation"; re-diagnosed properly instead of trusting that: U10.11's escape is genuinely narrow but real (not hopeless), and the actual full-distance pathfind only succeeds with relaxation against a specific, identifiable set of neighbors -- found by taking the diagnostic blanket-relaxed path and checking exactly which nets it ran close to at standard clearance, the same technique used for every other multi-exception case this session. Turned out to be a real SPI bus corridor (SPI_CLK, SPI_CLK_SD, SPI_CS_SD, SPI_MISO, SPI_MISO_SD passing close together, same as TCK/TDI/TDO/TMS's corridor) plus one unrelated net (USB_DM) -- six scoped pair rules, not a blanket exception. Both pad ends needed a via placed directly at the pad's own XY (through the part's own footprint). Hit the SAME hole_clearance gap as SPI_MISO (vs SPI_MISO this time) -- fixed the same way. Also hit a related, narrower version of the VCC layer-check lesson: `_fix_endpoint_layers` reported "end-layer fix jog blocked" even though the via was genuinely fine, because that helper's internal checks use plain (non-relaxed) clearance regardless of the `exceptions` dict passed to it -- it takes the parameter but doesn't use it for its own via/segment checks. Worked around by verifying the jog manually under the mixed-exception model before concluding it was actually blocked; it wasn't.

**Where things stand now**: every item on the DRC unconnected list (31 remaining) has been individually diagnosed, not just noted as "hard." All of them fall into one of four buckets: (1) fully-interior BGA/QFN dead pockets confirmed via escape-sweep down to 0.05mm clearance (the large majority -- $1N151, $1N65, CC_#CD, CC_#PG, GND x4 total incl. U14.E3, INT, LRCLK, BCLK, DAC_ENABLE, PDMCLK, PDMDIN x2, RESETN, SCL1 x2, SDA1, SPI_MOSI, TS, V_LS x3, XTALI, XTALO); (2) TDI/TDO/TMS, a genuine physical corridor-capacity limit confirmed by exhaustive bus-router search, not an escape problem; (3) GND/U14.E3 and SPI_MOSI/U14.G3 specifically, blocked by unexceptable no-net neighbor pads, now conclusively confirmed un-fixable via `.kicad_dru` (see the pad-based-rule experiment above); (4) `#ERROR` on Q2 pin 1, a broken netlist reference that should be flagged to the user rather than routed at all, not touched. **None of these can be resolved by more routing attempts** -- the remaining path forward for any of them is a placement change (nudging a part to open real room) or, for `#ERROR`, a schematic/netlist fix, neither of which this session did unilaterally.

All work this pass is committed and pushed to `experiment/codex-astra-routing` (commits `724cebd` through `79b2b10`). DRC: 274 violations (started this session's continuation at 281; net -7 from exceptions that independently fixed real pre-existing pad-spacing issues), 40 -> 31 unconnected across this whole continuation.

### Claude — 2026-09-10 — user asked for a placement nudge on the TDI/TDO/TMS corridor; re-investigation closed TDO instead, and conclusively re-confirmed TDI/TMS with much stronger evidence

**Before touching any part position, re-diagnosed the corridor from scratch** (per the user's own request to first confirm a nudge would actually help) and found the earlier "corridor proven too narrow" conclusion was based on an incomplete picture, not wrong so much as unfinished:

1. `bus_router._fix_endpoint_layers()` checks via/segment clearance using **plain, non-relaxed** values regardless of the `exceptions` dict passed to it -- it accepts the parameter but never uses it in its own internal checks. This made several genuinely-fine vias report as "blocked" in the original bus-router run.
2. An earlier neighbor survey for these four pads used a search that (accidentally) filtered out pads with no net name entirely, so it never surfaced that **TDI specifically** sits next to U15's own unnamed pad B8 at the same 0.35mm distance as its named neighbors. This is the one real, unexceptable blocker in the group.
3. TDO and TMS, once surveyed properly (including no-net pads), have **only named neighbors** -- TDI/TMS/XTALI for TDO; TCK/TDO/XTALO for TMS. No NC pads at either.

**TDO: closed.** Added three scoped 0.05mm exceptions (vs TDI, TMS, XTALI -- each independently resolving a real pre-existing pad-spacing violation), routed it manually (bypassing the buggy `_fix_endpoint_layers`) with a via-in-pad connection at each end. First placement attempt shipped silently broken in two separate, unrelated ways -- both caught by real DRC's "Track has unconnected end", not assumed fixed: (a) a clumsy endpoint-snap collapsed two tiny connector tracks into zero-length degenerate segments with no real geometry; (b) more importantly, the two endpoint vias that the diagnostic had explicitly confirmed were needed were simply never written in the placement code -- verified `start_layer_ok: False` / `end_layer_ok: False`, then only added the connecting *tracks* and forgot the *vias* entirely. Fixed both; final result 271 violations (down from 274 -- the new exceptions fixed 3 real pre-existing violations), 31->30 unconnected. Commit `00029ec`.

**TDI: re-confirmed blocked, now with much stronger evidence, AND now confirmed placement-nudge-proof.** Isolation test: removed every other track on the board in-memory (including TCK's own real, committed route) and re-swept TDI's escape with every named neighbor exceptioned to 0.05mm. Still zero clear directions at any distance up to 0.5mm -- U15's own pad B8 alone, independent of TCK or anything else, closes TDI's entire local escape. Since B8 sits on U15's own footprint at a fixed position relative to TDI regardless of where U15 sits on the board, **nudging U15's placement would not free this pad** -- it is exactly the same class of problem as every other package-interior dead pocket this session, just discovered via a shared-corridor investigation instead of a direct escape-sweep.

**TMS: also confirmed blocked, no NC pad involved this time.** Full neighbor survey found only named nets within 0.6mm (TCK, TDO, XTALO, V_LS, XTALI). A real, if narrow, escape lane exists at ~40 degrees with all of them exceptioned to 0.05mm -- but a fine-grained sweep found it closes back up completely by 0.35mm even at that relaxation. A genuine local dead pocket, not a corridor-sharing problem with TCK/TDI/TDO at all.

**Net effect of this pass**: TCK and TDO of the four JTAG signals are now routed; TDI and TMS are conclusively, individually confirmed blocked by their own local geometry (not a shared-corridor artifact, and not fixable by moving U15). This is worth flagging to the user directly: the placement-nudge idea, while reasonable to try, would not actually help these two -- the fix (if one exists) would be a schematic-level pin reassignment on U15, not a layout change.

### Claude — 2026-09-10 — user said "keep trying"; major breakthrough (`NetName == ''` matches no-net pads) reopens a whole class of previously-"unfixable" blocks

**The user declined further placement nudges for the ~27 package-interior BGA dead pockets** (leave unrouted) but asked to keep trying anything else, including the TDI/TMS corridor. Before touching more geometry, retested the standing "unexceptable no-net neighbor" conclusion (last tested via `A.Reference`/`A.Pad_Number`, both confirmed non-functional) -- and tried `A.NetName == ''` / `B.NetName == ''` specifically, which had never actually been tried. **It works.** Confirmed conclusively against a real existing violation (V_LS vs U14.J5's no-net pad) dropping out cleanly with a test rule, 0 unrelated changes, then fully reverted before proceeding for real. This overturns the "GND/U14.E3 and SPI_MOSI/U14.G3 conclusively un-fixable" line from the previous entry -- that conclusion only tested pad-identity matching, never no-net-name matching.

**TDI: closed.** Its sole blocker (U15's own unnamed pad B8, per the isolation test above) is exactly the case this new rule type targets. Added `tight_clearance_TDI_vs_noname` (0.05mm) plus `tight_clearance_TDI_vs_GND` and a `tight_hole_clearance_TDI_vs_TDO` (hole_clearance is a separate category, same lesson as SPI_MISO/SPI_MOSI_SD earlier). First placement forgot a via at one of TWO internal F.Cu/B.Cu transitions (only added the far one) -- caught by `track_dangling` on both halves, fixed by adding the missing via.

**GND/U14.E3: closed**, resolving the "tentatively parked" item from two entries back. Its via passed every `via_clear` check yet still produced `via_dangling` -- a new failure mode: the via was clear of all *other copper* but didn't actually land inside GND's own zone's *filled polygon*. KiCad's zone filler recedes its fill boundary away from an entire dense pin field to keep clearance from everything nearby, so "clear of other copper" and "inside the real fill" are different, unchecked conditions. Fix: query `zone.GetFilledPolysList(layer).Collide(probe, 0)` directly, not just `via_clear`, before trusting a via will bond to a plane. Found a point satisfying both, re-placed.

**$1N151: closed**, two unrelated sub-fixes. (1) Its "unconnected" pair was actually the package's own adjacent A3/B3 balls, needing only a 0.35mm direct trace, not a route -- worth checking nearest-same-net-copper distance before assuming a long route is needed, a pattern likely to recur. (2) A separate pre-existing C36/C31 island needed a short bridge, closed with a `tight_clearance_1N151_vs_noname`-class exception plus GND/V_LS/BCLK pair rules.

**GND's U15-interior pockets: 2 of 3 closed** (E6-D6, D6-D7) using the same noname exception. The third, **G7-E6, is genuinely blocked** -- confirmed by sweeping clearance down to ~0.005mm; `seg_clear_mixed` still returns False at that floor, meaning the direct line physically overlaps a pad shape, not a tunable margin. Left unrouted.

**V_LS's three U15-interior pockets: 2 of 3 closed.** G2-F3 needed `tight_clearance_V_LS_vs_DAC_P`/`_DAC_N` (0.05mm) plus lowering the pre-existing `tight_clearance_GND_vs_V_LS` rule from 0.10mm to 0.05mm, plus a new `tight_clearance_V_LS_vs_noname`. That last rule had a much bigger blast radius than intended -- it also cleared ~9 other pre-existing "netclass Default" clearance violations between V_LS and no-net neighbor pads elsewhere on U14/U15's dense field, all at 0.10-0.15mm actual (well above the 0.05mm floor used everywhere in this file, not a manufacturability concern like the SPI_MOSI/U14.G3 item below) -- verified each one really did involve a no-net pad before accepting the drop, not just trusting the DRC count. F7-F3 needed a different technique: it's on the same BGA row but 4 columns away, a direct F.Cu line crosses 15 pads and is genuinely blocked there (0.005mm sweep, same signature as G7-E6) -- but B.Cu is completely clear at the standard exception floor, so this used two through-vias (one at each pad) with a short B.Cu backbone between them instead of a single-layer route. **A2-B5 is genuinely blocked** -- same 0.005mm-sweep signature on F.Cu, and B.Cu reports "start blocked" (A2 has no existing via/B.Cu presence, and a new via there collides with the package's own B.Cu-layer copper). Left unrouted.

**Judgment call flagged, NOT shipped: SPI_MOSI/U14.G3.** Re-tested under the new `NetName==''` technique and it IS technically routable, but only by relaxing clearance to 0.02mm across 11 different unrelated net pairs simultaneously -- qualitatively different from every other exception in this file (all single-neighbor or few-neighbor, all at 0.05mm or above). 0.02mm is likely below manufacturable fab tolerance. Deliberately left unrouted pending the user's explicit sign-off rather than shipped unilaterally.

**Net effect of this "keep trying" pass**: TDI, GND/U14.E3, $1N151, 2 of 3 GND U15-interior pairs, and 2 of 3 V_LS U15-interior pairs all closed via the `NetName==''` breakthrough. Confirmed still genuinely blocked (real geometric overlap or verified-unfixable-by-nudge): GND's G7-E6, V_LS's A2-B5, TMS, and the earlier fully-interior BGA list. SPI_MOSI/U14.G3 is flagged, not routed -- needs a call from the user on whether 0.02mm/11-net-relaxation is acceptable. All changes committed and pushed to `experiment/codex-astra-routing` (commits `21892d9` through `585f7ee`).

### Claude — 2026-09-10 — SPI_MOSI/U14.G3 routed at 0.02mm; a real solder-mask-bridge conflict investigated and confirmed unfixable, then shipped with explicit user sign-off

User approved the flagged 0.02mm/11-net exception. First placement attempt was clean by every check used so far, but real DRC caught something new: **14 `solder_mask_bridge` violations**, a DRC category not seen anywhere else this session. Investigated whether this is fixable rather than just disclosing it as a bigger version of the same risk:

- Checked board setup: `pad_to_mask_clearance = 0`, `solder_mask_min_width = 0.1mm` -- a single board-wide value, not (as far as could be determined) exposed as a per-pair `.kicad_dru` constraint the way `clearance`/`hole_clearance` are. Tested this directly: a `physical_clearance` rule scoped to a real pre-existing mask-bridge pair (GND vs V_LS at C11) parsed but changed nothing; a literal `solder_mask_bridge` constraint keyword didn't just no-op -- **it silently invalidated the entire `.kicad_dru` file** (248 violations jumped to 617, confirmed by removing the one bad rule and watching the count return to 248). This is a meaningfully worse failure mode than the earlier-documented "bad condition field no-ops safely" finding, and worth remembering: a bad *constraint keyword* is not safe to experiment with casually the same way a bad *condition* is -- verify the count didn't blow up after any untested keyword, not just check the one violation you're targeting.
- Tried routing mask-safe (every pad, not just the exceptioned nets, held to >=0.1mm) except within U14's own package, on the theory that only G3's immediate escape was the unavoidable part. Failed -- the destination end (nearest existing SPI_MOSI copper, ~47.6mm away) sits inside MDBT531's own dense pin field, an equally tight second pinch point unrelated to U14 at all.
- Bisected the actual electrical minimum needed: 0.02mm routes, 0.025mm already fails outright (visited=46, immediately boxed in again). This is a hard cliff, not a gradient -- confirms there is no clearance value that is simultaneously routable and mask-safe (mask needs >=0.1mm; routing needs <0.025mm). Not a tuning gap to close, a real physical conflict between this WLCSP-22's pin density and the board's mask-web rule.

Reported this to the user plainly (including that a bridge here would show up immediately as a dead/shorted SPI bus on first power-on, testable and reworkable, not a silent long-term failure) and they explicitly approved shipping anyway for a dev board.

**Second placement attempt fixed two real bugs found by real DRC, not assumed clean:** (1) the destination pad turned out to be on **B.Cu**, not F.Cu -- the first attempt's F.Cu-only track just touched that XY coordinate without a via, so it never actually connected (`track_dangling`). Added the missing via. (2) Forgot `hole_clearance` rules for SPI_CLK/SPI_CS (same category-is-separate-from-clearance lesson as SPI_MISO/SPI_MOSI_SD earlier this session) -- the route's vias landed too close to their existing vias' drill holes. Added both. Final DRC diff: exactly the 14 solder-mask-bridge violations (already disclosed and approved) plus the intended unconnected-item closure, 0 zero/negative-clearance actual overlaps confirmed by scanning every violation's `actual` value. Commit `cf0f301`.

**This closes every item from this session's "keep trying" round.** The only remaining genuinely-open items are: GND's G7-E6, V_LS's A2-B5, TMS, the fully-interior BGA/DSBGA list, and `#ERROR` on Q2 pin 1 (netlist issue, not routing) -- all previously confirmed as not fixable by any technique tried this session.

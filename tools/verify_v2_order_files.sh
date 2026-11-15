#!/usr/bin/env bash
# Re-run the checks that decide whether the v2 fab files are safe to upload to JLCPCB.
#   1. KiCad DRC + schematic parity on each board (0 violations, 0 unconnected, 0 parity issues)
#   2. The fab export is current: regenerate it in a scratch copy and diff against fab/v2_<board>/
#   3. Pod only: DRC again with JLCPCB's published limits added (informational; see ORDER_READINESS.md)
# Needs kicad-cli 9 and KiCad's python (pcbnew). Writes nothing into the repo; scratch files go under
# $TMPDIR (default /tmp) in a folder named at the end of the run. Delete it when done.
# Usage: tools/verify_v2_order_files.sh [pod] [inear] [case]
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BOARDS=("$@"); [ ${#BOARDS[@]} -eq 0 ] && BOARDS=(pod inear case)
WORK="$(mktemp -d "${TMPDIR:-/tmp}/haven_verify.XXXXXX")"
FAIL=0
strip() { grep -vE '^(G04|%TF\.(CreationDate|GenerationSoftware|ProjectId))|date |CreationDate|^%TF'; }

echo "== 1. DRC and schematic parity"
for b in "${BOARDS[@]}"; do
  kicad-cli pcb drc --schematic-parity --severity-all --format report -o "$WORK/drc_$b.rpt" \
    "$ROOT/kicad_v2_$b/haven_v2_$b.kicad_pcb" > "$WORK/drc_$b.log" 2>&1
  v=$(grep -m1 "Found .* DRC violations" "$WORK/drc_$b.rpt" | grep -oE '[0-9]+' | head -1)
  u=$(grep -m1 "unconnected pads" "$WORK/drc_$b.rpt" | grep -oE '[0-9]+' | head -1)
  f=$(grep -m1 "Footprint errors" "$WORK/drc_$b.rpt" | grep -oE '[0-9]+' | head -1)
  p=$(grep -m1 "schematic parity issues" "$WORK/drc_$b.log" | grep -oE '[0-9]+' | head -1)
  echo "   $b: violations=$v unconnected=$u footprint_errors=$f parity=$p"
  [ "${v:-1}" = 0 ] && [ "${u:-1}" = 0 ] && [ "${f:-1}" = 0 ] && [ "${p:-1}" = 0 ] || FAIL=1
done

echo "== 1b. Part handedness against datasheet top views (mirrored footprints)"
HB=(); for b in "${BOARDS[@]}"; do [ "$b" = case ] || HB+=("$b"); done
if [ ${#HB[@]} -gt 0 ]; then python3 "$ROOT/tools/check_footprint_handedness.py" "${HB[@]}" 2>/dev/null | grep -v "Debug:" || true
  python3 "$ROOT/tools/check_footprint_handedness.py" "${HB[@]}" >/dev/null 2>&1 || FAIL=1; fi
echo "== 2. Fab files current with the boards"
mkdir -p "$WORK/copy" && cp -r "$ROOT/tools" "$ROOT"/kicad_v2_* "$ROOT/fab" "$WORK/copy/"
( cd "$WORK/copy" && python3 tools/export_v2_fab.py "${BOARDS[@]}" >/dev/null 2>&1 ) || { echo "   export script failed"; FAIL=1; }
for b in "${BOARDS[@]}"; do
  bad=0
  for f in "$ROOT/fab/v2_$b/gerbers/"*; do
    n=$(basename "$f")
    diff -q <(strip < "$f") <(strip < "$WORK/copy/fab/v2_$b/gerbers/$n") >/dev/null 2>&1 || { echo "   $b: $n differs"; bad=1; }
  done
  for x in bom cpl; do
    diff -q "$ROOT/fab/v2_$b/haven_v2_${b}_$x.csv" "$WORK/copy/fab/v2_$b/haven_v2_${b}_$x.csv" >/dev/null || { echo "   $b: $x differs"; bad=1; }
  done
  [ $bad = 0 ] && echo "   $b: current" || FAIL=1
done

case " ${BOARDS[*]} " in *" pod "*)
  echo "== 3. Pod against JLCPCB's published limits (informational)"
  mkdir -p "$WORK/jlc" && cp "$ROOT"/kicad_v2_pod/haven_v2_pod.kicad_pcb "$ROOT"/kicad_v2_pod/haven_v2_pod.kicad_pro "$WORK/jlc/"
  cp -r "$ROOT/kicad_v2_pod/footprints.pretty" "$ROOT/kicad_v2_pod/fp-lib-table" "$WORK/jlc/" 2>/dev/null
  cp "$ROOT/tools/jlc_extra_rules.kicad_dru" "$WORK/jlc/haven_v2_pod.kicad_dru"
  kicad-cli pcb drc --severity-all --format report -o "$WORK/jlc/jlc.rpt" "$WORK/jlc/haven_v2_pod.kicad_pcb" >/dev/null 2>&1
  echo "   pad-to-pad (different nets) under 0.15 mm: $(grep -c "^\[.*JLC pad to pad" "$WORK/jlc/jlc.rpt")"
  echo "   via hole within 0.2 mm of copper:          $(grep -c "^\[.*JLC via hole" "$WORK/jlc/jlc.rpt")"
  echo "   (Not a pass/fail: JLCPCB's own design review decides. Baseline 2026-11-07: 92 and about 205 (the second varies by a few between runs).)" ;;
esac

echo
[ $FAIL = 0 ] && echo "RESULT: checks 1 and 2 passed" || echo "RESULT: FAILED, see above"
echo "scratch folder: $WORK"
exit $FAIL

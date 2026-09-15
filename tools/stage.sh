#!/bin/bash
# One placement stage, DRC-gated: stage.sh <tag> <prev.json> <ref> <ic> "<cleanup windows: xmin xmax ymin ymax net;...>" [extra move args]
# Run from kicad/. Leaves the board modified only if zero new violation identities and unconnected not worse.
set -u
TAG=$1; PREV=$2; REF=$3; IC=$4; WINS=$5; shift 5; EXTRA="$@"
KCLI=$(cat /tmp/kicad_cli.txt); PY=$(cat /tmp/kicad_py.txt); VPY=../../../venv/bin/python
START=/tmp/board_stage_${TAG}_start.kicad_pcb; OUTJ=../routing-evidence/placement-fix/after_${TAG}.json
cp haven_dev_board.kicad_pcb "$START"
"$PY" ../tools/move_two_terminal.py --ref "$REF" --ic "$IC" --start "$START" $EXTRA 2>&1 | grep -v 'wxApp\|stdpbase\|memory leak\|Debug:\|assert ""false""' | tail -2 || true
if cmp -s "$START" haven_dev_board.kicad_pcb; then echo "STAGE $TAG: no solution, board unchanged"; exit 2; fi
"$KCLI" pcb drc --format json --severity-all --all-track-errors --output "$OUTJ" haven_dev_board.kicad_pcb >/dev/null 2>&1
IFS=';' read -ra W <<< "$WINS"
for w in "${W[@]}"; do [ -z "$w" ] && continue; bash ../tools/clean_dangling.sh "$PREV" "$OUTJ" $w 2>&1 | grep -v 'wxApp\|stdpbase\|memory leak\|Debug:\|assert ""false""' | grep -i 'removing' || true; done
"$KCLI" pcb drc --format json --severity-all --all-track-errors --output "$OUTJ" haven_dev_board.kicad_pcb >/dev/null 2>&1
if $VPY ../tools/drc_diff.py "$PREV" "$OUTJ"; then echo "STAGE $TAG: CLEAN"; exit 0; else echo "STAGE $TAG: NOT CLEAN -- restoring"; cp "$START" haven_dev_board.kicad_pcb; exit 1; fi

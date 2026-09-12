#!/bin/bash
# Iteratively delete NEW track_dangling items (vs baseline) inside a window, by uuid, then refill zones.
# Usage (from kicad/): clean_dangling.sh baseline.json after.json xmin xmax ymin ymax [netname]
set -e
BASE=$1; AFTER=$2; XMIN=$3; XMAX=$4; YMIN=$5; YMAX=$6; NET=${7:-}
KCLI=$(cat /tmp/kicad_cli.txt); PY=$(cat /tmp/kicad_py.txt); VPY=../../../venv/bin/python
for i in 1 2 3 4 5 6 7 8; do
  "$KCLI" pcb drc --format json --severity-all --all-track-errors --output "$AFTER" haven_dev_board.kicad_pcb >/dev/null 2>&1
  UUIDS=$($VPY - "$BASE" "$AFTER" "$XMIN" "$XMAX" "$YMIN" "$YMAX" "$NET" <<'PYEOF'
import json,sys
base,after=sys.argv[1],sys.argv[2]; xmin,xmax,ymin,ymax=map(float,sys.argv[3:7]); net=sys.argv[7]
def key(v): return (v['type'],v.get('description'),tuple((i.get('description'),i['pos']['x'],i['pos']['y']) for i in v['items']))
bk={key(v) for v in json.load(open(base))['violations']}
out=[]
for v in json.load(open(after))['violations']:
    if v['type']=='track_dangling' and key(v) not in bk:
        for it in v['items']:
            if xmin<=it['pos']['x']<=xmax and ymin<=it['pos']['y']<=ymax and (not net or f'[{net}]' in it['description']): out.append(it['uuid'])
print(' '.join(out))
PYEOF
)
  if [ -z "$UUIDS" ]; then echo "pass $i: clean"; break; fi
  echo "pass $i: removing $UUIDS"; python3 ../tools/remove_items_by_uuid.py haven_dev_board.kicad_pcb $UUIDS
done
"$PY" - <<'PYEOF' 2>&1 | grep -v 'wxApp\|stdpbase\|memory leak\|Debug:'
import sys; sys.path.insert(0,'../tools'); import pcbnew, route_lib as rl
b=pcbnew.LoadBoard('haven_dev_board.kicad_pcb'); rl.refill_zones(b); b.Save('haven_dev_board.kicad_pcb'); print('refilled+saved')
PYEOF
"$KCLI" pcb drc --format json --severity-all --all-track-errors --output "$AFTER" haven_dev_board.kicad_pcb 2>&1 | grep Found

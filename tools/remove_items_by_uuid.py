#!/usr/bin/env python3
"""Delete top-level (segment ...)/(via ...) blocks from a .kicad_pcb by uuid,
at the text level (no pcbnew). Usage: remove_items_by_uuid.py board.kicad_pcb uuid [uuid...]"""
import re, sys
path, uuids = sys.argv[1], set(sys.argv[2:])
s = open(path).read(); n = 0
for u in uuids:
    m = re.search(r'\n\t\((segment|via)\b(?:(?!\n\t\().)*?\(uuid "' + re.escape(u) + r'"\)\s*\n\t\)', s, re.S)
    if m: s = s[:m.start()] + s[m.end():]; n += 1
    else: print('not found:', u, file=sys.stderr)
open(path, 'w').write(s); print(f'removed {n}/{len(uuids)}')

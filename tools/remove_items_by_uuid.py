#!/usr/bin/env python3
"""Delete top-level (segment ...) / (via ...) blocks from a .kicad_pcb by uuid
(full uuid or a unique prefix), at the text level -- no pcbnew, so it is
immune to the pcbnew-9 SWIG proxy breakage seen after board.Remove().
Usage: remove_items_by_uuid.py board.kicad_pcb uuid_or_prefix [...]"""
import re
import sys

path, uuids = sys.argv[1], sys.argv[2:]
s = open(path).read()
n = 0
for u in uuids:
    pat = (r'\n\t\((?:segment|via)\b'          # block opener at top level (one tab)
           r'(?:(?!\n\t\().)*?'                # anything, but never into the next top-level block
           r'\(uuid "' + re.escape(u) + r'[^"]*"\)\s*\n\t\)')
    m = re.search(pat, s, re.S)
    if m:
        s = s[:m.start()] + s[m.end():]
        n += 1
    else:
        print('not found:', u, file=sys.stderr)
open(path, 'w').write(s)
print(f'removed {n}/{len(uuids)}')

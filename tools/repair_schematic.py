"""Give the port's schematic the metadata kicad-cli needs for a BOM.

The generator (extracted/gen_symbols_and_schematic.py) wrote placed symbols
with no in_bom/on_board flags, no Footprint property and no (instances ...)
block, so `kicad-cli sch export bom` returned zero rows. Adds all three,
taking each footprint name from the board. Safe to re-run.
Usage: python3 tools/repair_schematic.py kicad/haven_dev_board.kicad_sch kicad/haven_dev_board.kicad_pcb
"""
import re, sys
import pcbnew

sch_path, pcb_path = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(pcb_path)
fpname = {f.GetReference(): str(f.GetFPID().GetUniStringLibId()) for f in board.GetFootprints()}
text = open(sch_path).read()
lib = None
m = re.search(r'\(lib_id "([^":]+):', text)
if m:
    lib = m.group(1)
    text = re.sub(r'^    \(symbol "([^":]+)"', rf'    (symbol "{lib}:\1"', text, flags=re.M)
root = re.search(r'\(uuid "([^"]+)"\)', text).group(1)
project = sch_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]

out, i, fixed = [], 0, 0
pat = re.compile(r'  \(symbol \(lib_id "[^"]+"\) \(at [^)]*\) \(unit 1\)\n(?:    .*\n)*?  \)\n')
for m in pat.finditer(text):
    block = m.group(0)
    out.append(text[i:m.start()])
    i = m.end()
    ref = re.search(r'\(property "Reference" "([^"]+)"', block).group(1)
    if "(in_bom" not in block:
        block = block.replace("(unit 1)\n", "(unit 1) (in_bom yes) (on_board yes)\n", 1)
    if '(property "Footprint"' not in block and ref in fpname:
        at = re.search(r'\(property "Value" "[^"]*" \(at ([^)]*)\)', block).group(1)
        lines = block.rstrip("\n").split("\n")
        lines.insert(-1, f'    (property "Footprint" "{fpname[ref]}" (at {at}) (effects (font (size 1.27 1.27)) hide))')
        block = "\n".join(lines) + "\n"
    if "(instances" not in block:
        lines = block.rstrip("\n").split("\n")
        lines.insert(-1, f'    (instances (project "{project}" (path "/{root}" (reference "{ref}") (unit 1))))')
        block = "\n".join(lines) + "\n"
    fixed += 1
    out.append(block)
out.append(text[i:])
open(sch_path, "w").write("".join(out))
print(f"symbols repaired: {fixed}")

"""Rev A schematic edits matching tools/rev_a_trim.py.

Removes the deleted parts' symbols and the net labels the generator placed
right after each one, sets R21 to 0R and marks J1 do-not-populate.
Usage: python3 tools/rev_a_schematic.py kicad/haven_dev_board.kicad_sch
"""
import re, sys

REMOVE = {"CARD1", "U10", "U9", "Q3", "R1", "R15", "R20", "C6", "C8", "C26", "C28",
          "U14", "U1", "R10", "R11", "U6", "R17", "C23", "R19", "CN1"}
path = sys.argv[1]
text = open(path).read()
head, body = text.split("\n  (symbol (lib_id", 1)
body = "  (symbol (lib_id" + body
# each chunk = one placed symbol plus the labels written after it
chunks = re.split(r"(?m)^(?=  \(symbol \(lib_id )", body)
kept, removed = [], 0
for ch in chunks:
    m = re.search(r'\(property "Reference" "([^"]+)"', ch)
    ref = m.group(1) if m else None
    if ref in REMOVE:
        tail = ch.rstrip().endswith(")\n)") or ch.rstrip().endswith("\n)")
        # keep the file's closing paren if it sits at the end of the last chunk
        if ch.rstrip().endswith("\n)") and not re.search(r"(?m)^\)$", "".join(kept)):
            kept.append(")\n")
        removed += 1
        continue
    if ref == "R21":
        ch = re.sub(r'(\(property "Value" ")[^"]*(")', r"\g<1>0R\2", ch, count=1)
    if ref == "J1" and "(dnp yes)" not in ch:
        ch = ch.replace("(in_bom yes) (on_board yes)", "(in_bom no) (on_board yes) (dnp yes)", 1)
    kept.append(ch)
out = head + "\n" + "".join(kept)
if not out.rstrip().endswith(")"):
    out = out.rstrip() + "\n)\n"
open(path, "w").write(out)
print(f"removed {removed} symbols")

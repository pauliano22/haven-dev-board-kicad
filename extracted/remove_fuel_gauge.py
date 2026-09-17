"""
Actually remove U6 (BQ27220 fuel gauge) from the schematic -- the doc's
TL;DR already says "fuel gauge dropped entirely, confirmed nothing reads
it" but that was a decision that was never actually executed as a real
edit. Found this by cross-checking the full schematic/PCB reference list
against what the doc claims, not assumed.

Two of U6's nets ($1N74 at R17, $1N70 at C23) are otherwise-anonymous
bias/decoupling nets whose only other member is a passive that existed
solely to support U6. Leaving R17/C23 in place as vestigial rather than
also removing them -- same convention as the earlier BQ25120A removal
(C9/C16 left in place there too) -- correctly pruning a whole local bias
network requires more circuit understanding than a "nothing reads this
chip" justification covers.
"""
from kiutils.schematic import Schematic

SRC = "/home/paul22iac/projects/active/haven_dev_board_kicad/kicad/haven_dev_board.kicad_sch"
OUT = "/tmp/claude-1000/-home-paul22iac/de6df91d-5626-4f43-95cb-adf67fb0294d/scratchpad/haven_dev_board_sch_NOFUELGAUGE.kicad_sch"

sch = Schematic.from_file(SRC)

inst = next(i for i in sch.schematicSymbols
            if next((p.value for p in i.properties if p.key == 'Reference'), '') == 'U6')
symname = inst.libId.split(':')[-1]
sym = next(s for s in sch.libSymbols if s.libId == symname)
ox, oy = inst.position.X, inst.position.Y
coords = []
for unit in sym.units:
    for p in unit.pins:
        coords.append((ox + p.position.X, oy + p.position.Y))

removed = 0
kept = []
for lbl in sch.labels:
    hit = any(abs(lbl.position.X - x) < 0.01 and abs(lbl.position.Y - y) < 0.01 for x, y in coords)
    if hit:
        removed += 1
    else:
        kept.append(lbl)
sch.labels = kept
sch.schematicSymbols = [i for i in sch.schematicSymbols if i is not inst]
sch.libSymbols = [s for s in sch.libSymbols if s.libId != symname]

print(f"Removed U6 ({symname}): {removed} labels (expected {len(coords)} pins)")
sch.to_file(OUT)
print("Wrote", OUT)

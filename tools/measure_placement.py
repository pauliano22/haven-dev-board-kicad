#!/usr/bin/env python3
"""Footprint-centre distances for the pairs in HAVEN_HARDWARE_REVIEW.md §0.7,
parsed from the .kicad_pcb text (no pcbnew). Usage: measure_placement.py board.kicad_pcb [board2 ...]"""
import re, sys, math
PAIRS=[("X1","MDBT531"),("X1","C2"),("X1","C14"),("CRYSTAL1","U15"),("CRYSTAL1","C45"),("CRYSTAL1","C46"),("R28","U15"),
       ("U15","C33"),("U15","C1"),("U2","L2"),("U2","C16"),("U2","C18"),("U2","C22"),("U6","C21"),("U14","C31")]
def load(path):
    s=open(path).read(); fps={}
    for m in re.finditer(r'\(footprint\s+"[^"]*"(.*?)\n\t\)\n', s, re.S):
        body=m.group(1); at=re.search(r'\n\t\t\(at\s+([-\d.]+)\s+([-\d.]+)', body); ref=re.search(r'\(property\s+"Reference"\s+"([^"]+)"', body)
        if at and ref: fps[ref.group(1)]=(float(at.group(1)),float(at.group(2)))
    return fps
boards=[load(p) for p in sys.argv[1:]]
print("| pair | "+" | ".join(sys.argv[1:])+" |"); print("|---|"+"---|"*len(boards))
for a,b in PAIRS:
    vals=[]
    for f in boards:
        vals.append(f"{math.hypot(f[a][0]-f[b][0],f[a][1]-f[b][1]):.1f} mm" if a in f and b in f else "n/a")
    print(f"| {a} ↔ {b} | "+" | ".join(vals)+" |")

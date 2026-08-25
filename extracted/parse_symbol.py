#!/usr/bin/env python3
"""Parse an EasyEDA .esym file into a clean pin list: [{num, name, x, y, rot}]"""
import json, sys
from collections import defaultdict

def parse_esym(path):
    pins = {}  # pin_id -> {x,y,rot,length}
    attrs = defaultdict(dict)
    bbox = None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            tag = d[0]
            if tag == "PIN":
                # ["PIN", id, electric?, ?, x, y, length, rot, ?, ?, ?, ?]
                pid = d[1]
                pins[pid] = {"x": d[4], "y": d[5], "length": d[6], "rot": d[7]}
            elif tag == "ATTR":
                if len(d) > 4:
                    attrs[d[2]][d[3]] = d[4]
            elif tag == "PART":
                if len(d) > 2 and isinstance(d[2], dict):
                    bbox = d[2].get("BBOX")

    result = []
    for pid, p in pins.items():
        a = attrs.get(pid, {})
        result.append({
            "number": a.get("NUMBER", "?"),
            "name": a.get("NAME", "?"),
            "x": p["x"], "y": p["y"], "rot": p["rot"], "length": p["length"],
        })
    result.sort(key=lambda r: (r["y"] is None, -(r["y"] or 0), r["x"] or 0))
    return {"bbox": bbox, "pins": result}

if __name__ == "__main__":
    out = parse_esym(sys.argv[1])
    print(f"bbox={out['bbox']}  pin_count={len(out['pins'])}")
    for p in out["pins"]:
        print(f"  {p['number']:>4}  {p['name']:<30} x={p['x']} y={p['y']} rot={p['rot']} len={p['length']}")

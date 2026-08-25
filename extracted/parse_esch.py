#!/usr/bin/env python3
import json, sys
from collections import defaultdict

path = "stock_openearable/SHEET/f608cfd613e24ea7937ea7eb0aab41a1/1.esch"

components = {}  # id -> {x,y,rot,mirror, attrs:{}}
wires = []
attrs_by_comp = defaultdict(dict)

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
        if tag == "COMPONENT":
            # ["COMPONENT", id, name, x, y, rot, mirror, {}, layer]
            cid = d[1]
            components[cid] = {
                "name": d[2] if len(d) > 2 else None,
                "x": d[3] if len(d) > 3 else None,
                "y": d[4] if len(d) > 4 else None,
                "rot": d[5] if len(d) > 5 else None,
            }
        elif tag == "ATTR":
            # ["ATTR", attrId, parentCompId, key, value, ...]
            if len(d) > 4:
                parent = d[2]
                key = d[3]
                val = d[4]
                attrs_by_comp[parent][key] = val
        elif tag == "WIRE":
            wires.append(d)

# merge attrs into components
for cid, attrs in attrs_by_comp.items():
    if cid in components:
        components[cid]["attrs"] = attrs
    else:
        # attribute on something not tracked as a COMPONENT (could be a net label, power symbol, etc.)
        components.setdefault(cid, {"name": None, "attrs": {}})
        components[cid]["attrs"] = attrs

# Print real, meaningful parts: those with a non-empty "Name" or "Device" or "Value"/"Symbol" attr
print(f"Total COMPONENT records: {len(components)}")
print(f"Total WIRE records: {len(wires)}")
print()
print("=== Components with Name attribute ===")
named = []
for cid, c in components.items():
    a = c.get("attrs", {})
    nm = a.get("Name")
    if nm:
        named.append((cid, nm, a))

for cid, nm, a in sorted(named, key=lambda x: x[1]):
    val = a.get("Value") or a.get("@Value") or ""
    dev = a.get("Device", "")
    footprint = a.get("Footprint", "")
    designator = a.get("Designator") or a.get("@Designator") or ""
    print(f"{cid}\tName={nm!r}\tValue={val!r}\tDesignator={designator!r}\tFootprint={footprint!r}")

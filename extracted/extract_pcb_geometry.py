#!/usr/bin/env python3
"""
Full geometry extraction from the real, manufactured stock-OpenEarable PCB
layer (.epcb). This is a 6-copper-layer board per LAYER_PHYS records:
  TOP(1) / prepreg / L15 GROUND PLANE / core / L16 Inner1 / prepreg /
  L17 Inner2 / core / L18 POWER PLANE / prepreg / BOTTOM(2)
Units: raw coordinates are in mils (1 unit = 0.0254 mm) -- verified against
overall board span (~530x1051 raw units -> ~13.5x26.7mm, a plausible small
in-ear wearable PCB size), independent from the .esch schematic-space units
(10 mil per raw grid unit there).
"""
import json
from collections import defaultdict

BASE = "stock_openearable"
EPCB = f"{BASE}/PCB/7be1a0d4b47a427b935eec6c7480da3e.epcb"

MM_PER_UNIT = 0.0254

KICAD_LAYER = {
    1: "F.Cu", 2: "B.Cu",
    15: "In1.Cu", 16: "In2.Cu", 17: "In3.Cu", 18: "In4.Cu",
    3: "F.SilkS", 4: "B.SilkS",
    5: "F.Mask", 6: "B.Mask",
    7: "F.Paste", 8: "B.Paste",
    11: "Edge.Cuts",
    13: "Cmts.User", 14: "Cmts.User",
    10: "Cmts.User",  # bottom assembly -> generic comment layer
}

lines_, vias, polys, pours = [], [], [], []

with open(EPCB) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        tag = d[0]
        if tag == "LINE":
            # ["LINE", id, ?, net, layer, x1, y1, x2, y2, width, ?]
            _, lid, _, net, layer, x1, y1, x2, y2, width, *_ = d
            lines_.append({"net": net, "layer": layer, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "width": width})
        elif tag == "VIA":
            # ["VIA", id, ?, net, ?, x, y, padsize, drill, ?, ...] -- pad
            # (outer copper) diameter must exceed the drill diameter; the
            # raw field order is (pad, drill), not (size, drill) as first
            # assumed.
            _, vid, _, net, _lyr, x, y, padsize, drill, *_ = d
            vias.append({"net": net, "x": x, "y": y, "size": padsize, "drill": drill})
        elif tag == "POLY":
            # ["POLY", id, ?, net, layer, width, [points...], ?]
            _, pid, _, net, layer, width, pts, *_ = d
            polys.append({"net": net, "layer": layer, "width": width, "pts": pts})
        elif tag == "POUR":
            # ["POUR", id, ?, net, layer, width, groupid, ?, [ [poly points] ], style, ?, ?]
            _, poid, _, net, layer, width, *rest = d
            poly_pts = None
            for item in rest:
                if isinstance(item, list) and item and isinstance(item[0], list):
                    poly_pts = item[0]
                    break
            pours.append({"net": net, "layer": layer, "width": width, "pts": poly_pts})

print(f"LINE (trace segments): {len(lines_)}")
print(f"VIA: {len(vias)}")
print(f"POLY: {len(polys)}")
print(f"POUR (copper zones): {len(pours)}")

by_layer = defaultdict(int)
for l in lines_:
    by_layer[l["layer"]] += 1
print("Trace segments by layer:", dict(by_layer))

poly_by_layer = defaultdict(int)
for p in polys:
    poly_by_layer[p["layer"]] += 1
print("POLY by layer:", dict(poly_by_layer))

pour_nets = defaultdict(int)
for p in pours:
    pour_nets[(p["net"], p["layer"])] += 1
print("POUR by (net, layer):", dict(pour_nets))

json.dump({"lines": lines_, "vias": vias, "polys": polys, "pours": pours},
          open("pcb_geometry.json", "w"))
print("Wrote pcb_geometry.json")

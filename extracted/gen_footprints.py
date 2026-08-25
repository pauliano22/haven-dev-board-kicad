#!/usr/bin/env python3
"""
Generate real KiCad footprints (.kicad_mod) from the stock OpenEarable
EasyEDA .efoo footprint files -- one per unique footprint UUID actually
referenced by a BOM part. Pad number/position/rotation/shape/size are read
directly from the real footprint data (not approximated), except POLY-shape
pads (rare -- edge/castellated pads on connectors) which are simplified to
their bounding rectangle; this is flagged in the README.

Units: footprint-local coordinates are in mils (1 unit = 0.0254 mm), same
convention verified for the PCB layer.
"""
import json, os, math

MM = 0.0254
BASE = "stock_openearable"
OUT_DIR = "../kicad/footprints.pretty"
os.makedirs(OUT_DIR, exist_ok=True)

bom = json.load(open("bom.json"))
pcb_placement = json.load(open("pcb_placement.json")) if os.path.exists("pcb_placement.json") else {}

def footprint_uuid_for(des, c):
    return c.get("footprint") or pcb_placement.get(des, {}).get("footprint")

footprints_needed = sorted(set(
    fp for des, c in bom.items() if (fp := footprint_uuid_for(des, c))
))

# map footprint uuid -> a friendly name (prefer the "Origin Footprint" BOM attr
# from whichever component uses it, else fall back to the uuid)
friendly_name = {}
for des, c in bom.items():
    fp = footprint_uuid_for(des, c)
    of = (c.get("attrs") or {}).get("Origin Footprint")
    if fp and of and fp not in friendly_name:
        friendly_name[fp] = of.replace("/", "-").replace(" ", "_")
for des, c in bom.items():
    fp = footprint_uuid_for(des, c)
    if fp and fp not in friendly_name:
        friendly_name[fp] = fp

def parse_pads(path):
    pads = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if not d or d[0] != "PAD":
                continue
            _, pid, _flag, net, layer, number, x, y, rot, hole, shape, *rest = d
            pads.append({
                "number": number, "x": x, "y": y, "rot": rot or 0,
                "hole": hole, "shape": shape,
            })
    return pads

def pad_geometry(shape):
    kind = shape[0]
    if kind == "RECT":
        w, h, corner_r = shape[1], shape[2], (shape[3] if len(shape) > 3 else 0)
        return ("roundrect" if corner_r else "rect"), w * MM, h * MM, corner_r
    if kind == "ELLIPSE":
        w, h = shape[1], shape[2]
        return ("circle" if abs(w - h) < 1e-6 else "oval"), w * MM, h * MM, 0
    if kind == "OVAL":
        w, h = shape[1], shape[2]
        return "oval", w * MM, h * MM, 0
    if kind == "POLY":
        pts_raw = shape[1]
        xs = [p for i, p in enumerate(pts_raw) if isinstance(p, (int, float)) and i % 2 == 0]
        ys = [p for i, p in enumerate(pts_raw) if isinstance(p, (int, float)) and i % 2 == 1]
        # pts_raw mixes numbers and "L"/"ARC" command tokens; filter numerics
        nums = [p for p in pts_raw if isinstance(p, (int, float))]
        xs = nums[0::2]
        ys = nums[1::2]
        w = (max(xs) - min(xs))
        h = (max(ys) - min(ys))
        return "rect", w * MM, h * MM, 0  # bounding-box approximation
    raise ValueError(f"unknown pad shape {kind}")

count = 0
for fp_uuid in footprints_needed:
    path = f"{BASE}/FOOTPRINT/{fp_uuid}.efoo"
    if not os.path.exists(path):
        print(f"WARN: missing footprint file for {fp_uuid}")
        continue
    pads = parse_pads(path)
    name = friendly_name.get(fp_uuid, fp_uuid)
    lines = []
    lines.append(f'(footprint "{name}" (version 20221018) (generator haven_kicad_port)')
    lines.append('  (layer "F.Cu")')
    lines.append('  (attr smd)')
    lines.append(f'  (fp_text reference "REF**" (at 0 -1.5) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))')
    lines.append(f'  (fp_text value "{name}" (at 0 1.5) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))')
    for p in pads:
        shape_kind, w, h, corner_r = pad_geometry(p["shape"])
        x, y = p["x"] * MM, p["y"] * MM
        rot = p["rot"]
        num = p["number"] or "?"
        extra = ""
        if shape_kind == "roundrect":
            ratio = min(0.5, (corner_r * MM) / min(w, h)) if min(w, h) > 0 else 0
            extra = f" (roundrect_rratio {ratio:.3f})"
        at = f"(at {x:.4f} {y:.4f}{' ' + str(rot) if rot else ''})"
        lines.append(
            f'  (pad "{num}" smd {shape_kind} {at} (size {w:.4f} {h:.4f}){extra} '
            f'(layers "F.Cu" "F.Paste" "F.Mask"))'
        )
    lines.append(")")
    out_name = f"{OUT_DIR}/{name}.kicad_mod"
    with open(out_name, "w") as f:
        f.write("\n".join(lines) + "\n")
    count += 1

print(f"Generated {count} footprints into {OUT_DIR}")
json.dump(friendly_name, open("footprint_names.json", "w"), indent=1)

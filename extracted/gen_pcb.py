#!/usr/bin/env python3
"""
Generate haven_dev_board.kicad_pcb -- a faithful port of the real,
manufactured stock-OpenEarable board: real component placement (position +
rotation, read directly from the .epcb COMPONENT records), real pad
geometry (from the .efoo footprint files), real copper routing (LINE ->
segment, VIA -> via, POUR -> zone), and the real board outline (POLY on the
OUTLINE layer -> Edge.Cuts).

Coordinate strategy: every footprint instance is placed at rotation 0 with
(at compX*MM compY*MM 0); the component's real rotation is baked directly
into each pad's own local coordinate via rotate_ccw(). This sidesteps any
uncertainty about whether KiCad's own per-instance rotation transform
matches EasyEDA's convention -- validated instead by construction (same
technique used for the schematic). The rotation math itself (plain
standard-orientation CCW) was independently validated against real trace/
via endpoints to ~0.01 unit (see extracted/ session notes): U13 pin
positions landed within 0.01 mil of real GND/V_SD trace endpoints with no
extra mirroring needed, even for back-layer (layer=2) parts.
"""
import json, math, os

MM = 0.0254  # PCB-space raw unit -> mm
BASE = "stock_openearable"
OUT = "../kicad/haven_dev_board.kicad_pcb"

bom = json.load(open("bom.json"))
placement = json.load(open("pcb_placement.json"))
netlist = json.load(open("pcb_netlist.json"))
geom = json.load(open("pcb_geometry.json"))
friendly_name = json.load(open("footprint_names.json"))

pin2net = {}
for net, pins in netlist.items():
    for des, pin in pins:
        pin2net[(des, pin)] = net

net_names = sorted(n for n in netlist.keys() if n != "")
net_id = {"": 0}
for i, n in enumerate(net_names, start=1):
    net_id[n] = i

def rotate_ccw(x, y, rot):
    rad = math.radians(rot or 0)
    return x * math.cos(rad) - y * math.sin(rad), x * math.sin(rad) + y * math.cos(rad)

def esc(s):
    return str(s).replace('"', '\\"')

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
            pads.append({"number": number, "x": x, "y": y, "rot": rot or 0, "shape": shape})
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
        nums = [p for p in shape[1] if isinstance(p, (int, float))]
        xs, ys = nums[0::2], nums[1::2]
        return "rect", (max(xs) - min(xs)) * MM, (max(ys) - min(ys)) * MM, 0
    raise ValueError(f"unknown pad shape {kind}")

def arc_center(sx, sy, ex, ey, angle_deg):
    dx, dy = ex - sx, ey - sy
    c = math.hypot(dx, dy)
    mx, my = (sx + ex) / 2, (sy + ey) / 2
    theta = math.radians(angle_deg)
    h = (c / 2) / math.tan(theta / 2)
    perp = (-dy / c, dx / c)
    return mx + h * perp[0], my + h * perp[1]

def arc_midpoint(sx, sy, cx, cy, angle_deg):
    half = math.radians(angle_deg) / 2
    vx, vy = sx - cx, sy - cy
    rx = vx * math.cos(half) - vy * math.sin(half)
    ry = vx * math.sin(half) + vy * math.cos(half)
    return cx + rx, cy + ry

lines_out = []
lines_out.append('(kicad_pcb (version 20221018) (generator haven_kicad_port)')
lines_out.append('  (general (thickness 1.6))')
lines_out.append('  (paper "A3")')
lines_out.append('  (layers')
lines_out.append('    (0 "F.Cu" signal)')
lines_out.append('    (1 "In1.Cu" signal)')
lines_out.append('    (2 "In2.Cu" signal)')
lines_out.append('    (3 "In3.Cu" signal)')
lines_out.append('    (4 "In4.Cu" signal)')
lines_out.append('    (31 "B.Cu" signal)')
lines_out.append('    (32 "B.Adhes" user)')
lines_out.append('    (33 "F.Adhes" user)')
lines_out.append('    (34 "B.Paste" user)')
lines_out.append('    (35 "F.Paste" user)')
lines_out.append('    (36 "B.SilkS" user)')
lines_out.append('    (37 "F.SilkS" user)')
lines_out.append('    (38 "B.Mask" user)')
lines_out.append('    (39 "F.Mask" user)')
lines_out.append('    (44 "Edge.Cuts" user)')
lines_out.append('    (49 "F.Fab" user)')
lines_out.append('    (50 "B.Fab" user)')
lines_out.append('  )')
lines_out.append('  (setup (pad_to_mask_clearance 0))')
lines_out.append('  (net 0 "")')
for n in net_names:
    lines_out.append(f'  (net {net_id[n]} "{esc(n)}")')

# ---- Board outline (Edge.Cuts) from POLY layer 11 ----
cur = None
for p in geom["polys"]:
    if p["layer"] != 11:
        continue
    pts = p["pts"]
    i = 0
    sx, sy = pts[0], pts[1]
    i = 2
    x, y = sx, sy
    while i < len(pts):
        cmd = pts[i]
        if cmd == "L":
            ex, ey = pts[i + 1], pts[i + 2]
            lines_out.append(
                f'  (gr_line (start {x*MM:.4f} {y*MM:.4f}) (end {ex*MM:.4f} {ey*MM:.4f}) '
                f'(stroke (width 0.15) (type solid)) (layer "Edge.Cuts"))'
            )
            x, y = ex, ey
            i += 3
        elif cmd == "ARC":
            angle, ex, ey = pts[i + 1], pts[i + 2], pts[i + 3]
            cx, cy = arc_center(x, y, ex, ey, angle)
            mx, my = arc_midpoint(x, y, cx, cy, angle)
            lines_out.append(
                f'  (gr_arc (start {x*MM:.4f} {y*MM:.4f}) (mid {mx*MM:.4f} {my*MM:.4f}) '
                f'(end {ex*MM:.4f} {ey*MM:.4f}) (stroke (width 0.15) (type solid)) (layer "Edge.Cuts"))'
            )
            x, y = ex, ey
            i += 4
        else:
            break

# ---- Footprint instances ----
missing_footprint = 0
pad_total = pad_matched = 0
for des, comp in placement.items():
    fp_uuid = bom.get(des, {}).get("footprint") or comp.get("footprint")
    fp_name = friendly_name.get(fp_uuid)
    fp_path = f"{BASE}/FOOTPRINT/{fp_uuid}.efoo" if fp_uuid else None
    if not fp_name or not fp_path or not os.path.exists(fp_path):
        missing_footprint += 1
        continue
    pads = parse_pads(fp_path)
    is_back = comp["layer"] == 2
    fcu, fmask, fpaste = ("B.Cu", "B.Mask", "B.Paste") if is_back else ("F.Cu", "F.Mask", "F.Paste")
    fsilk = "B.SilkS" if is_back else "F.SilkS"
    ffab = "B.Fab" if is_back else "F.Fab"
    board_layer = "B.Cu" if is_back else "F.Cu"
    value = bom[des]["name"] or ""
    ox, oy = comp["x"] * MM, comp["y"] * MM
    lines_out.append(f'  (footprint "haven_footprints:{esc(fp_name)}" (layer "{board_layer}") (at {ox:.4f} {oy:.4f})')
    lines_out.append(f'    (property "Reference" "{esc(des)}" (at 0 -1.5 0) (layer "{fsilk}") (effects (font (size 0.8 0.8) (thickness 0.12))))')
    lines_out.append(f'    (property "Value" "{esc(value)}" (at 0 1.5 0) (layer "{ffab}") (effects (font (size 0.8 0.8) (thickness 0.12))))')
    lines_out.append('    (attr smd)')
    for p in pads:
        pad_total += 1
        shape_kind, w, h, corner_r = pad_geometry(p["shape"])
        lx, ly = rotate_ccw(p["x"], p["y"], comp["rot"])
        lx, ly = lx * MM, ly * MM
        net = pin2net.get((des, p["number"]), "")
        nid = net_id.get(net, 0)
        extra = ""
        if shape_kind == "roundrect":
            ratio = min(0.5, (corner_r * MM) / min(w, h)) if min(w, h) > 0 else 0
            extra = f" (roundrect_rratio {ratio:.3f})"
        net_clause = f' (net {nid} "{esc(net)}")' if net else ""
        if net:
            pad_matched += 1
        lines_out.append(
            f'    (pad "{esc(p["number"])}" smd {shape_kind} (at {lx:.4f} {ly:.4f}) (size {w:.4f} {h:.4f}){extra} '
            f'(layers "{fcu}" "{fpaste}" "{fmask}"){net_clause})'
        )
    lines_out.append('  )')

# ---- Copper traces ----
KICAD_COPPER = {1: "F.Cu", 2: "B.Cu", 15: "In1.Cu", 16: "In2.Cu", 17: "In3.Cu", 18: "In4.Cu"}
trace_dropped = 0
for l in geom["lines"]:
    layer = KICAD_COPPER.get(l["layer"])
    if not layer:
        trace_dropped += 1
        continue
    nid = net_id.get(l["net"], 0)
    lines_out.append(
        f'  (segment (start {l["x1"]*MM:.4f} {l["y1"]*MM:.4f}) (end {l["x2"]*MM:.4f} {l["y2"]*MM:.4f}) '
        f'(width {l["width"]*MM:.4f}) (layer "{layer}") (net {nid}))'
    )

# ---- Vias (assumed through, F.Cu-B.Cu, per empty layer-span field) ----
for v in geom["vias"]:
    nid = net_id.get(v["net"], 0)
    lines_out.append(
        f'  (via (at {v["x"]*MM:.4f} {v["y"]*MM:.4f}) (size {v["size"]*MM:.4f}) (drill {v["drill"]*MM:.4f}) '
        f'(layers "F.Cu" "B.Cu") (net {nid}))'
    )

# ---- Copper pours (ground/power planes) ----
for i, po in enumerate(geom["pours"]):
    if not po["pts"] or not po["net"]:
        continue
    layer = KICAD_COPPER.get(po["layer"])
    if not layer:
        continue
    nid = net_id.get(po["net"], 0)
    nums = [p for p in po["pts"] if isinstance(p, (int, float))]
    xs, ys = nums[0::2], nums[1::2]
    pts_str = " ".join(f'(xy {x*MM:.4f} {y*MM:.4f})' for x, y in zip(xs, ys))
    lines_out.append(f'  (zone (net {nid}) (net_name "{esc(po["net"])}") (layer "{layer}") (hatch edge 0.5)')
    lines_out.append('    (connect_pads (clearance 0.2))')
    lines_out.append('    (min_thickness 0.2)')
    lines_out.append('    (fill yes)')
    lines_out.append(f'    (polygon (pts {pts_str}))')
    lines_out.append('  )')

lines_out.append(')')

os.makedirs("../kicad", exist_ok=True)
with open(OUT, "w") as f:
    f.write("\n".join(lines_out) + "\n")

print(f"Wrote {OUT}")
print(f"Footprint instances placed: {len(placement) - missing_footprint} (missing: {missing_footprint})")
print(f"Pads total: {pad_total}, assigned a real net: {pad_matched} ({100*pad_matched/pad_total:.1f}%)")
print(f"Trace segments dropped (unmapped layer): {trace_dropped}")
print(f"Distinct nets: {len(net_names)}")

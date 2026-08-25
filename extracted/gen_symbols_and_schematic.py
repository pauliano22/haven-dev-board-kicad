#!/usr/bin/env python3
"""
Generate haven_dev_board.kicad_sym (one symbol per BOM designator, no
sharing) and haven_dev_board.kicad_sch.

Connectivity source: pcb_netlist.json (the authoritative, ground-truth
per-pad net assignment read directly from the real board's PAD_NET
records) rather than the schematic-label-proximity heuristic
(netlist.json) -- it has materially better coverage (84% of pads vs ~64%)
and both were cross-validated to agree on every net checked.

Placement source: bom.json's schematic-space x/y/rot (this is a SCHEMATIC
capture, so components are laid out in schematic-logical space, not
physical board space).

Coordinate strategy, same self-consistent-baking technique as the PCB
generator: every symbol instance is placed at rotation 0
(at compX*SCALE compY*SCALE 0); each pin's real rotation is baked directly
into its own local "at" coordinate via rotate_ccw(). A local label is then
placed at exactly (instance position + pin local), which is bit-identical
to the pin's real final position by construction, so it always lands
exactly on the pin regardless of any KiCad-internal rotation-convention
question. Net names ARE net identity on a single sheet in KiCad (same-name
local labels connect without a drawn wire) -- this mirrors the original
EasyEDA schematic's own net-label-only style.
"""
import json, math, html, re, os
from collections import defaultdict
from parse_symbol import parse_esym

SCALE = 0.254  # schematic-space raw unit -> mm (10 units = 2.54mm pin pitch)
BASE = "stock_openearable"
OUT_DIR = "../kicad"
os.makedirs(OUT_DIR, exist_ok=True)

RESERVED_PIN_NAMES = {"DECR", "DCC", "DECD", "DCCD", "DCCH"}

def base_name_of(name):
    return re.sub(r"\.\d+$", "", name or "")

def rotate_ccw(x, y, rot):
    rot = (rot or 0) % 360
    if rot == 0:
        return x, y
    if rot == 90:
        return -y, x
    if rot == 180:
        return -x, -y
    if rot == 270:
        return y, -x
    rad = math.radians(rot)
    return x * math.cos(rad) - y * math.sin(rad), x * math.sin(rad) + y * math.cos(rad)

def esc(s):
    return str(s).replace('"', '\\"')

bom = json.load(open("bom.json"))
proj = json.load(open(f"{BASE}/project.json"))
netlist = json.load(open("pcb_netlist.json"))

title_to_uid = {info["title"]: uid for uid, info in proj["symbols"].items()}
title_to_uid_unescaped = {html.unescape(t): uid for t, uid in title_to_uid.items()}

pin2net = {}
for net, pins in netlist.items():
    for des, pin in pins:
        pin2net[(des, pin)] = net

symcache = {}
def get_symbol(base_name):
    uid = title_to_uid.get(base_name) or title_to_uid_unescaped.get(base_name)
    if not uid:
        return None
    if uid not in symcache:
        symcache[uid] = parse_esym(f"{BASE}/SYMBOL/{uid}.esym")
    return symcache[uid]

# ---------- symbol library ----------
sym_lines = ['(kicad_symbol_lib (version 20211014) (generator haven_kicad_port)']
missing_symbol = []
per_designator_pins = {}  # des -> [{number,name,local_x,local_y}]

for des, c in bom.items():
    base_name = base_name_of(c["name"])
    sym = get_symbol(base_name)
    if not sym:
        missing_symbol.append(des)
        continue
    pins = []
    for p in sym["pins"]:
        if des == "MDBT531" and p["name"] in RESERVED_PIN_NAMES:
            continue
        lx, ly = rotate_ccw(p["x"], p["y"], c["rot"] or 0)
        pins.append({"number": p["number"], "name": p["name"], "x": lx * SCALE, "y": ly * SCALE})
    per_designator_pins[des] = pins

    xs = [p["x"] for p in pins] or [0]
    ys = [p["y"] for p in pins] or [0]
    bx1, bx2 = min(xs) + 2.54, max(xs) - 2.54
    by1, by2 = min(ys) + 2.54, max(ys) - 2.54
    if bx1 > bx2:
        bx1, bx2 = -2.54, 2.54
    if by1 > by2:
        by1, by2 = -2.54, 2.54

    ref_prefix = re.sub(r"\d+$", "", des) or "U"
    sym_lines.append(f'  (symbol "{esc(des)}" (in_bom yes) (on_board yes)')
    sym_lines.append(f'    (property "Reference" "{esc(ref_prefix)}" (at {bx1:.3f} {by2+2.54:.3f} 0) (effects (font (size 1.27 1.27))))')
    sym_lines.append(f'    (property "Value" "{esc(base_name)}" (at {bx1:.3f} {by1-2.54:.3f} 0) (effects (font (size 1.27 1.27))))')
    sym_lines.append(f'    (symbol "{esc(des)}_0_1"')
    sym_lines.append(f'      (rectangle (start {bx1:.3f} {by1:.3f}) (end {bx2:.3f} {by2:.3f}) (stroke (width 0.254) (type default)) (fill (type background)))')
    sym_lines.append('    )')
    sym_lines.append(f'    (symbol "{esc(des)}_1_1"')
    for p in pins:
        sym_lines.append(
            f'      (pin passive line (at {p["x"]:.3f} {p["y"]:.3f} 0) (length 2.54)'
            f' (name "{esc(p["name"])}" (effects (font (size 1.27 1.27))))'
            f' (number "{esc(p["number"])}" (effects (font (size 1.27 1.27)))))'
        )
    sym_lines.append('    )')
    sym_lines.append('  )')

sym_lines.append(')')
with open(f"{OUT_DIR}/haven_dev_board.kicad_sym", "w") as f:
    f.write("\n".join(sym_lines) + "\n")

print(f"Symbols generated: {len(per_designator_pins)}; missing: {missing_symbol}")

# ---------- schematic ----------
sch_lines = []
sch_lines.append('(kicad_sch (version 20221018) (generator haven_kicad_port)')
sch_lines.append('  (uuid "00000000-0000-0000-0000-000000000001")')
sch_lines.append('  (paper "A2")')
sch_lines.append('  (lib_symbols')
# duplicate the same symbol defs inline (kicad_sch requires lib_symbols cache)
for line in sym_lines[1:-1]:
    sch_lines.append("  " + line)
sch_lines.append('  )')

uuid_ctr = [1]
def next_uuid():
    uuid_ctr[0] += 1
    return f"00000000-0000-0000-0000-{uuid_ctr[0]:012d}"

label_count = 0
pin_total = 0
for des, c in bom.items():
    pins = per_designator_pins.get(des)
    if pins is None:
        continue
    ox, oy = c["x"] * SCALE, c["y"] * SCALE
    sch_lines.append(f'  (symbol (lib_id "haven_dev_board:{esc(des)}") (at {ox:.3f} {oy:.3f} 0) (unit 1)')
    sch_lines.append(f'    (uuid "{next_uuid()}")')
    sch_lines.append(f'    (property "Reference" "{esc(des)}" (at {ox:.3f} {oy-5:.3f} 0) (effects (font (size 1.27 1.27))))')
    sch_lines.append(f'    (property "Value" "{esc(base_name_of(c["name"]))}" (at {ox:.3f} {oy+5:.3f} 0) (effects (font (size 1.27 1.27))))')
    sch_lines.append('  )')
    for p in pins:
        pin_total += 1
        net = pin2net.get((des, p["number"]))
        if not net:
            continue
        lx, ly = ox + p["x"], oy + p["y"]
        sch_lines.append(f'  (label "{esc(net)}" (at {lx:.3f} {ly:.3f} 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{next_uuid()}"))')
        label_count += 1

sch_lines.append('  (sheet_instances (path "/" (page "1")))')
sch_lines.append(')')

with open(f"{OUT_DIR}/haven_dev_board.kicad_sch", "w") as f:
    f.write("\n".join(sch_lines) + "\n")

print(f"Schematic: {len(bom)} components, {pin_total} pins, {label_count} net labels placed ({100*label_count/pin_total:.1f}%)")

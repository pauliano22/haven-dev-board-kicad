#!/usr/bin/env python3
"""
Independent audit of our OWN generated haven_dev_board.kicad_sch --
re-parses the actual file (not the generator's in-memory state or the
original EasyEDA intermediates) to catch bugs introduced during file
generation itself: dangling pins, orphan labels, degenerate symbols,
metadata cruft.
"""
import json, sys
from collections import defaultdict
from sexp_parser import parse, find_all, get, get_all_immediate

SCH_PATH = "../kicad/haven_dev_board.kicad_sch"
tree = parse(open(SCH_PATH).read())[0]

# ---- 1. library symbol pin geometry (from the embedded lib_symbols cache) ----
lib_symbols_node = get(tree, "lib_symbols")
sym_pins = {}   # ref_designator -> [{number, name, x, y}]
sym_defs = get_all_immediate(lib_symbols_node, "symbol")
for sdef in sym_defs:
    name = sdef[1]  # e.g. "MDBT531"
    pins = []
    for unit in get_all_immediate(sdef, "symbol"):
        for pin in get_all_immediate(unit, "pin"):
            at = get(pin, "at")
            x, y = float(at[1]), float(at[2])
            num_node = get(pin, "number")
            name_node = get(pin, "name")
            pins.append({"number": num_node[1], "name": name_node[1], "x": x, "y": y})
    sym_pins[name] = pins

print(f"Library symbol definitions found: {len(sym_defs)}")
zero_pin_symbols = [n for n, p in sym_pins.items() if len(p) == 0]
if zero_pin_symbols:
    print(f"WARN: {len(zero_pin_symbols)} symbol(s) with zero pins: {zero_pin_symbols}")

# ---- 2. component instances (top-level (symbol (lib_id ...) (at ...))) ----
instances = []
for node in tree:
    if isinstance(node, list) and node and node[0] == "symbol":
        lib_id = get(node, "lib_id")
        if lib_id is None:
            continue  # this is a lib_symbols cache entry, not a placed instance
        at = get(node, "at")
        ref_prop = None
        val_prop = None
        for prop in get_all_immediate(node, "property"):
            if prop[1] == "Reference":
                ref_prop = prop[2]
            elif prop[1] == "Value":
                val_prop = prop[2]
        instances.append({
            "lib_id": lib_id[1], "x": float(at[1]), "y": float(at[2]),
            "reference": ref_prop, "value": val_prop,
        })

print(f"Component instances placed: {len(instances)}")

# sanity: reference designator should match the tail of lib_id, and a symbol def should exist
mismatches = []
for inst in instances:
    des = inst["lib_id"].split(":")[-1]
    if inst["reference"] != des:
        mismatches.append((inst["lib_id"], inst["reference"]))
    if des not in sym_pins:
        mismatches.append((inst["lib_id"], "NO SYMBOL DEF"))
if mismatches:
    print(f"WARN: {len(mismatches)} lib_id/reference/symbol-def mismatches: {mismatches[:10]}")
else:
    print("OK: every instance's Reference matches its lib_id, and a symbol def exists for each.")

# ---- 3. net labels ----
labels = []
for node in find_all(tree, "label"):
    net_name = node[1]
    at = get(node, "at")
    labels.append({"net": net_name, "x": round(float(at[1]), 3), "y": round(float(at[2]), 3)})
print(f"Net labels placed: {len(labels)}")

label_by_pos = defaultdict(list)
for l in labels:
    label_by_pos[(l["x"], l["y"])].append(l["net"])

dupe_pos = {k: v for k, v in label_by_pos.items() if len(v) > 1}
if dupe_pos:
    print(f"WARN: {len(dupe_pos)} coordinate(s) carry more than one label (possible net collision or duplicate): {list(dupe_pos.items())[:5]}")

# ---- 4. cross-check every instance pin against the label set ----
pin_total = 0
pin_labeled = 0
dangling_by_ref = defaultdict(list)
unresolved_labels = set(label_by_pos.keys())

for inst in instances:
    des = inst["lib_id"].split(":")[-1]
    pins = sym_pins.get(des, [])
    for p in pins:
        pin_total += 1
        ax, ay = round(inst["x"] + p["x"], 3), round(inst["y"] + p["y"], 3)
        if (ax, ay) in label_by_pos:
            pin_labeled += 1
            unresolved_labels.discard((ax, ay))
        else:
            dangling_by_ref[inst["reference"]].append((p["number"], p["name"]))

print(f"\nPins total: {pin_total}, labeled (connected to a named net): {pin_labeled} ({100*pin_labeled/pin_total:.1f}%)")
print(f"Orphan label positions (label present, no pin found there): {len(unresolved_labels)}")
if unresolved_labels:
    for pos in list(unresolved_labels)[:10]:
        print("  ORPHAN:", pos, label_by_pos[pos])

dangling_total = sum(len(v) for v in dangling_by_ref.values())
print(f"\nDangling (unlabeled) pins: {dangling_total} across {len(dangling_by_ref)} components")
for ref, pins in sorted(dangling_by_ref.items(), key=lambda kv: -len(kv[1]))[:15]:
    print(f"  {ref}: {len(pins)} unlabeled -> {pins[:6]}{'...' if len(pins)>6 else ''}")

# ---- 5. metadata cruft check ----
empty_value_refs = [i["reference"] for i in instances if not i["value"]]
if empty_value_refs:
    print(f"\nWARN: {len(empty_value_refs)} component(s) with empty Value property: {empty_value_refs}")

json.dump({
    "pin_total": pin_total, "pin_labeled": pin_labeled,
    "dangling_by_ref": dangling_by_ref,
    "instances": instances,
    "labels": labels,
}, open("audit_schematic_result.json", "w"), indent=1)

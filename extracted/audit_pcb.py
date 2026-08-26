#!/usr/bin/env python3
"""Independent audit of our OWN generated haven_dev_board.kicad_pcb."""
import json
from collections import defaultdict
from sexp_parser import parse, find_all, get, get_all_immediate

PCB_PATH = "../kicad/haven_dev_board.kicad_pcb"
tree = parse(open(PCB_PATH).read())[0]

# ---- net table ----
net_decls = get_all_immediate(tree, "net")
net_id_to_name = {}
for n in net_decls:
    nid = int(n[1])
    name = n[2] if len(n) > 2 else ""
    net_id_to_name[nid] = name
print(f"Declared nets: {len(net_decls)} (including net 0 = no-net)")

# ---- footprints ----
footprints = get_all_immediate(tree, "footprint")
print(f"Footprint instances: {len(footprints)}")

pad_total = 0
pad_with_net = 0
undeclared_net_refs = []
ref_pad_count = {}
zero_pad_refs = []
for fp in footprints:
    ref = None
    for prop in get_all_immediate(fp, "property"):
        if prop[1] == "Reference":
            ref = prop[2]
    pads = get_all_immediate(fp, "pad")
    ref_pad_count[ref] = len(pads)
    if len(pads) == 0:
        zero_pad_refs.append(ref)
    for pad in pads:
        pad_total += 1
        net_node = get(pad, "net")
        if net_node:
            pad_with_net += 1
            nid = int(net_node[1])
            if nid not in net_id_to_name:
                undeclared_net_refs.append((ref, pad[1], nid))

print(f"Pads total: {pad_total}, with a net assignment: {pad_with_net} ({100*pad_with_net/pad_total:.1f}%)")
if undeclared_net_refs:
    print(f"WARN: {len(undeclared_net_refs)} pad(s) reference an undeclared net id: {undeclared_net_refs[:10]}")
else:
    print("OK: every pad's net id is declared in the net table.")
if zero_pad_refs:
    print(f"WARN: {len(zero_pad_refs)} footprint instance(s) with zero pads: {zero_pad_refs}")

# ---- traces/vias referencing undeclared nets ----
segments = find_all(tree, "segment")
vias = find_all(tree, "via")
bad_seg_nets = set()
for s in segments:
    net_node = get(s, "net")
    if net_node:
        nid = int(net_node[1])
        if nid not in net_id_to_name:
            bad_seg_nets.add(nid)
bad_via_nets = set()
for v in vias:
    net_node = get(v, "net")
    if net_node:
        nid = int(net_node[1])
        if nid not in net_id_to_name:
            bad_via_nets.add(nid)
print(f"\nCopper segments: {len(segments)}, vias: {len(vias)}")
if bad_seg_nets or bad_via_nets:
    print(f"WARN: undeclared net ids referenced by copper: segments={bad_seg_nets}, vias={bad_via_nets}")
else:
    print("OK: all copper (segments+vias) reference declared nets.")

# ---- per-net pad count vs copper presence (nets with pads but zero copper = fully unrouted) ----
net_pad_count = defaultdict(int)
for fp in footprints:
    for pad in get_all_immediate(fp, "pad"):
        net_node = get(pad, "net")
        if net_node:
            net_pad_count[int(net_node[1])] += 1

net_has_copper = defaultdict(bool)
for s in segments:
    net_node = get(s, "net")
    if net_node:
        net_has_copper[int(net_node[1])] = True
for v in vias:
    net_node = get(v, "net")
    if net_node:
        net_has_copper[int(net_node[1])] = True
zone_nets = set()
for z in find_all(tree, "zone"):
    net_node = get(z, "net")
    if net_node:
        zone_nets.add(int(net_node[1]))
        net_has_copper[int(net_node[1])] = True

unrouted = [(net_id_to_name[nid], cnt) for nid, cnt in net_pad_count.items()
            if cnt >= 2 and not net_has_copper.get(nid)]
print(f"\nNets with >=2 pads but NO copper at all (segments/vias/zone) -- i.e. unrouted: {len(unrouted)}")
for name, cnt in sorted(unrouted, key=lambda x: -x[1])[:20]:
    print(f"  {name}: {cnt} pads, 0 copper")

# ---- board outline sanity ----
edge_lines = [l for l in find_all(tree, "gr_line") if get(l, "layer") and get(l, "layer")[1] == "Edge.Cuts"]
edge_arcs = [l for l in find_all(tree, "gr_arc") if get(l, "layer") and get(l, "layer")[1] == "Edge.Cuts"]
print(f"\nBoard outline: {len(edge_lines)} straight segments, {len(edge_arcs)} arcs")

json.dump({
    "ref_pad_count": ref_pad_count,
    "net_pad_count": {net_id_to_name.get(k, k): v for k, v in net_pad_count.items()},
    "unrouted": unrouted,
}, open("audit_pcb_result.json", "w"), indent=1)

#!/usr/bin/env python3
"""
Authoritative netlist + placement extraction from the PCB layer itself.

Unlike parse_netlist2.py (which reconstructs connectivity from schematic
net-label proximity -- a heuristic, since EasyEDA .esch doesn't store an
explicit netlist), the .epcb file stores PAD_NET records that give the
actual resolved net name for every real pad instance directly, plus
COMPONENT records giving each part's real placed position/rotation on the
actual board. This is ground truth, not a reconstruction.
"""
import json
from collections import defaultdict

BASE = "stock_openearable"
EPCB = f"{BASE}/PCB/7be1a0d4b47a427b935eec6c7480da3e.epcb"

designator_of = {}   # componentId -> "U13"
comp_placement = {}  # componentId -> {x,y,rot,layer}
comp_footprint = {}  # componentId -> footprint uuid
pad_net = []          # (componentId, pinNumber, netName)

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
        if tag == "COMPONENT":
            cid = d[1]
            comp_placement[cid] = {"layer": d[3], "x": d[4], "y": d[5], "rot": d[6]}
        elif tag == "ATTR" and len(d) > 8:
            cid = d[3]
            key = d[7] if isinstance(d[7], str) else None
            val = d[8]
            if key == "Designator":
                designator_of[cid] = val
            elif key == "Footprint":
                comp_footprint[cid] = val
        elif tag == "PAD_NET":
            # ["PAD_NET", componentId, pinNumber, netName, padId] -- the 2nd
            # field matches COMPONENT's own id directly (verified: PAD_NET
            # "e1101" pin "5" net "V_LS" lines up with COMPONENT "e1101" =
            # U13/microphone), not a separate pad-id namespace.
            _, cid, pinnum, net, padId = d[:5]
            pad_net.append((cid, pinnum, net))

print(f"COMPONENT records: {len(comp_placement)}")
print(f"Designators resolved: {len(designator_of)}")
print(f"PAD_NET records: {len(pad_net)}")

# Build final netlist keyed by real net name -> [(designator, pin)]
nets = defaultdict(list)
unresolved_component = 0
for cid, pinnum, net in pad_net:
    des = designator_of.get(cid)
    if not des:
        unresolved_component += 1
        continue
    nets[net].append((des, pinnum))

print(f"PAD_NET rows with no resolvable Designator: {unresolved_component}")
print(f"Distinct nets: {len(nets)}")

out_nets = {name: sorted(set(pins)) for name, pins in nets.items()}
json.dump(out_nets, open("pcb_netlist.json", "w"), indent=1)

# Placement export: designator -> {x, y, rot, layer, footprint}
placement = {}
for cid, des in designator_of.items():
    p = comp_placement.get(cid)
    if p:
        placement[des] = {**p, "footprint": comp_footprint.get(cid)}
json.dump(placement, open("pcb_placement.json", "w"), indent=1)
print(f"Placements resolved: {len(placement)}")

print("\n=== nets with >=2 pins (first 80) ===")
for name, pins in sorted(out_nets.items())[:80]:
    if len(pins) >= 2:
        print(f"{name}: {pins}")

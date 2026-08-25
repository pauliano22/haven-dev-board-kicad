#!/usr/bin/env python3
"""
Reconstruct nets from the EasyEDA schematic.
Strategy:
 - Every COMPONENT with a Name but no Designator and no Footprint is a net
   label / power flag placed at (x,y) -- its Name IS the net name.
 - Every real component (has Designator) contributes its pins at
   (compX + pinX_local, compY + pinY_local) accounting for rotation, using
   the already-extracted symbol pin lists (parse_symbol.py output).
 - A net label placed exactly at a pin's absolute coordinate (or touching
   the wire network that pin is on) ties that pin to the named net.
 - WIRE segments union pins/labels that are physically connected end to end
   (Union-Find over rounded coordinates).
This is a best-effort reconstruction, not a guaranteed-perfect one --
documented as such in the README.
"""
import json, sys, math
from collections import defaultdict

sys.path.insert(0, ".")
from parse_symbol import parse_esym

BASE = "stock_openearable"
ESCH = f"{BASE}/SHEET/f608cfd613e24ea7937ea7eb0aab41a1/1.esch"

with open("bom.json") as f:
    bom = json.load(f)

proj = json.load(open(f"{BASE}/project.json"))
symbol_title_to_uuid = {info["title"]: uid for uid, info in proj["symbols"].items()}

def rotate(x, y, rot):
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

def rnd(x, y):
    return (round(x, 1), round(y, 1))

# Union-Find
parent = {}
def find(a):
    parent.setdefault(a, a)
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb

point_owner = defaultdict(list)  # (x,y) -> [("PIN", des, pinnum) or ("LABEL", name)]

# 1. Place every real component's pins at absolute coords
symcache = {}
for des, c in bom.items():
    name = (c["name"] or "").rstrip(".1").rstrip(".0")
    # names in bom have trailing ".1" from EasyEDA part variant suffix; strip generically
    base_name = c["name"].split(".")[0] if c["name"] else ""
    uid = symbol_title_to_uuid.get(base_name)
    if not uid:
        continue
    if uid not in symcache:
        try:
            symcache[uid] = parse_esym(f"{BASE}/SYMBOL/{uid}.esym")
        except FileNotFoundError:
            symcache[uid] = {"pins": []}
    sym = symcache[uid]
    cx, cy, crot = c["x"], c["y"], c["rot"] or 0
    for p in sym["pins"]:
        lx, ly = rotate(p["x"], p["y"], crot)
        ax, ay = cx + lx, cy + ly
        pt = rnd(ax, ay)
        point_owner[pt].append(("PIN", des, p["number"], p["name"]))

# 2. Place net labels (components with a Name, no Designator, no Footprint,
#    and not a generic "={Value}"/"Anonymous..." placeholder)
attrs_by_comp = defaultdict(dict)
comp_pos = {}
with open(ESCH) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d[0] == "COMPONENT":
            comp_pos[d[1]] = (d[3], d[4])
        elif d[0] == "ATTR" and len(d) > 4:
            attrs_by_comp[d[2]][d[3]] = d[4]

net_label_points = defaultdict(set)
for cid, a in attrs_by_comp.items():
    nm = a.get("Name")
    des = a.get("Designator", "")
    fp = a.get("Footprint", "")
    if nm and not des and not fp and cid in comp_pos and "={" not in nm and "Anonymous" not in nm:
        x, y = comp_pos[cid]
        pt = rnd(x, y)
        point_owner[pt].append(("LABEL", nm))
        net_label_points[nm].add(pt)

# 3. Union pins/labels that share the exact same point
for pt, owners in point_owner.items():
    keys = [o for o in owners]
    for i in range(1, len(keys)):
        union(keys[0], keys[i])

# 4. Union via WIRE segments (endpoint-to-endpoint, and endpoint touching any
#    point that already has a pin/label)
all_known_points = set(point_owner.keys())
wire_segs = []
with open(ESCH) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d[0] == "WIRE":
            # ["WIRE", id, x1, y1, x2, y2, ...] -- exact index layout TBD, scan for 4 numeric coords
            nums = [v for v in d[2:] if isinstance(v, (int, float))]
            if len(nums) >= 4:
                wire_segs.append((rnd(nums[0], nums[1]), rnd(nums[2], nums[3])))

# naive endpoint unioning: if a wire endpoint is within snapping distance of
# a known pin/label point, union that wire's OTHER endpoint's owners (if any)
# together with it. Since wires may chain, also union wire-to-wire endpoints.
wire_point_registry = defaultdict(list)
for i, (p1, p2) in enumerate(wire_segs):
    wire_point_registry[p1].append(("WIRE", i, 0))
    wire_point_registry[p2].append(("WIRE", i, 1))
    union(("WIREPT", p1), ("WIREPT", p2))
    if p1 in point_owner:
        union(("WIREPT", p1), point_owner[p1][0])
    if p2 in point_owner:
        union(("WIREPT", p2), point_owner[p2][0])
    for owner in point_owner.get(p1, []):
        union(owner, point_owner[p1][0])
    for owner in point_owner.get(p2, []):
        union(owner, point_owner[p2][0])

# also directly union all owners at the same point (already done above) and
# additionally connect any owner at p1 with any owner at p2 through the wire
for p1, p2 in wire_segs:
    o1 = point_owner.get(p1, [("WIREPT", p1)])
    o2 = point_owner.get(p2, [("WIREPT", p2)])
    union(o1[0], o2[0])

# 5. Build final net groups
groups = defaultdict(list)
for pt, owners in point_owner.items():
    for o in owners:
        groups[find(o)].append(o)

# Determine a human name for each group: prefer a LABEL owner
nets = {}
for root, owners in groups.items():
    labels = sorted(set(o[1] for o in owners if o[0] == "LABEL"))
    pins = sorted(set((o[1], o[2]) for o in owners if o[0] == "PIN"))
    if not pins:
        continue
    name = labels[0] if labels else f"NET_{abs(hash(root)) % 10000}"
    if name not in nets:
        nets[name] = set()
    for p in pins:
        nets[name].add(p)

# merge: if two different "unnamed" nets end up representing the same pins due
# to hash collisions this is fine since we key by name string primarily
out = {name: sorted(list(pins)) for name, pins in nets.items()}
with open("netlist.json", "w") as f:
    json.dump(out, f, indent=1)

print(f"Reconstructed {len(out)} named nets covering pins.")
multi = {k: v for k, v in out.items() if len(v) >= 2}
print(f"Nets with >=2 pins (real connections): {len(multi)}")
single = {k: v for k, v in out.items() if len(v) == 1}
print(f"Nets with only 1 pin found (likely incomplete reconstruction): {len(single)}")

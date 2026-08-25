#!/usr/bin/env python3
"""
Simpler, more robust net reconstruction: group real-component pins by the
nearest net-label instance (within SNAP radius), then group all pins whose
nearest label shares the same text -- since net-label text IS the net
identity in this kind of schematic, we don't need to trace wire topology.
Calibrated against a known-correct case (MDBT53 pin 60 / P0.28 <-> "DIN"
label, ~5 units apart) -- SNAP=25 gives comfortable margin.
"""
import json, math, re, html
from collections import defaultdict
from parse_symbol import parse_esym

def base_name_of(name):
    # Strip only a trailing ".<digits>" variant suffix (e.g. "5.1kΩ.1" -> "5.1kΩ"),
    # not a naive split on the first dot which mangles decimal values.
    return re.sub(r"\.\d+$", "", name or "")

SNAP = 25.0

# nRF5340 (MDBT53) dedicated DC-DC regulator / decoupling pins. Per the
# nRF5340 datasheet these connect ONLY to a local decoupling capacitor next
# to the pin, never to a routed signal net -- so proximity-based label
# matching produces false positives here (confirmed: DECR(58) picked up the
# neighboring LRCLK label, DCCD(50)/DECD(52) picked up FLASH_RESET/
# SD_ENABLE). Exclude by symbol pin name, not by (designator, pin number),
# so this stays correct if the schematic renumbers pins.
RESERVED_PIN_NAMES = {"DECR", "DCC", "DECD", "DCCD", "DCCH"}
BASE = "stock_openearable"
ESCH = f"{BASE}/SHEET/f608cfd613e24ea7937ea7eb0aab41a1/1.esch"

bom = json.load(open("bom.json"))
proj = json.load(open(f"{BASE}/project.json"))
symbol_title_to_uuid = {info["title"]: uid for uid, info in proj["symbols"].items()}
symbol_title_to_uuid_unescaped = {html.unescape(t): uid for t, uid in symbol_title_to_uuid.items()}

def rotate(x, y, rot):
    rot = (rot or 0) % 360
    if rot == 0: return x, y
    if rot == 90: return -y, x
    if rot == 180: return -x, -y
    if rot == 270: return y, -x
    rad = math.radians(rot)
    return x * math.cos(rad) - y * math.sin(rad), x * math.sin(rad) + y * math.cos(rad)

# 1. absolute pin positions for every real component
symcache = {}
pin_points = []  # (x, y, des, pinnum, pinname)
for des, c in bom.items():
    base_name = base_name_of(c["name"])
    uid = symbol_title_to_uuid.get(base_name) or symbol_title_to_uuid_unescaped.get(base_name)
    if not uid:
        print(f"WARN: no symbol found for {des} ({base_name})")
        continue
    if uid not in symcache:
        try:
            symcache[uid] = parse_esym(f"{BASE}/SYMBOL/{uid}.esym")
        except FileNotFoundError:
            symcache[uid] = {"pins": []}
    for p in symcache[uid]["pins"]:
        if p["name"] in RESERVED_PIN_NAMES:
            continue
        lx, ly = rotate(p["x"], p["y"], c["rot"] or 0)
        pin_points.append((c["x"] + lx, c["y"] + ly, des, p["number"], p["name"]))

# 2. net label instances
attrs_by_comp = defaultdict(dict)
comp_pos = {}
with open(ESCH) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        if d[0] == "COMPONENT":
            comp_pos[d[1]] = (d[3], d[4])
        elif d[0] == "ATTR" and len(d) > 4:
            attrs_by_comp[d[2]][d[3]] = d[4]

labels = []  # (x, y, name)
for cid, a in attrs_by_comp.items():
    nm = a.get("Name")
    des = a.get("Designator", "")
    fp = a.get("Footprint", "")
    if nm and not des and not fp and cid in comp_pos and "={" not in nm and "Anonymous" not in nm:
        x, y = comp_pos[cid]
        labels.append((x, y, nm))

print(f"{len(pin_points)} pin instances, {len(labels)} net-label instances")

# 3. for each pin, find nearest label within SNAP
def dist2(ax, ay, bx, by):
    return (ax - bx) ** 2 + (ay - by) ** 2

nets = defaultdict(list)
unmatched = []
for px, py, des, pinnum, pinname in pin_points:
    best = None
    bestd = SNAP * SNAP
    for lx, ly, nm in labels:
        d = dist2(px, py, lx, ly)
        if d <= bestd:
            bestd = d
            best = nm
    if best:
        nets[best].append((des, pinnum, pinname))
    else:
        unmatched.append((des, pinnum, pinname, px, py))

print(f"Pins matched to a named net: {sum(len(v) for v in nets.values())}")
print(f"Pins with no nearby label (unlabeled/direct-wire only): {len(unmatched)}")
print(f"Distinct net names: {len(nets)}")

out = {name: sorted(set((d, p) for d, p, _ in members)) for name, members in nets.items()}
json.dump(out, open("netlist.json", "w"), indent=1)
json.dump(
    [{"designator": d, "pin": p, "pin_name": pn, "x": x, "y": y} for d, p, pn, x, y in unmatched],
    open("unmatched_pins.json", "w"), indent=1,
)

print("\n=== nets with >=2 pins ===")
for name, members in sorted(out.items()):
    if len(members) >= 2:
        print(f"{name}: {members}")

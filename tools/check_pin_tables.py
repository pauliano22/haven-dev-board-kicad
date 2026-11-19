#!/usr/bin/env python3
"""Datasheet pin-table check for the v3 pod (2026-11-19). Turns the manual audit (kicad_v3_pod/AUDIT_2026-11-19.md)
into something that runs on every board change.

    python3 tools/check_pin_tables.py [SCH] [PCB]       (defaults: kicad_v3_pod/haven_v3_pod.*)

Inputs (pin_tables/):
  <MPN>.csv          pin table from the datasheet (tools/extract_pin_tables.py; never from our schematic)
  parts.csv          which datasheet each table came from, and whether a machine read it (parsed) or a person (manual)
  variants.csv       part-number families whose suffix picks a variant, and the one suffix we may use
  design_rules.csv   pins whose connection is a design decision tied to a datasheet table (straps, NC, rails)

Checks, per part with a manufacturer part number:
  1  variant: the MPN is the one allowed suffix of its family
  2  pin set: every datasheet pin is a schematic pin and a board pad, and nothing extra
  3  pin names: the schematic's pin name matches the datasheet's
  4  datasheet electrical: ground-named pins on GND, same-named power pins on one net, NC pins open
  5  design rules
  6  board pad nets equal schematic nets
  7  passives: the value encoded in the MPN equals the schematic value (Murata GRM, Samsung CL, Yageo RC,
     Walsin WR, Royalohm CQ / CR, Panasonic ERJ, Murata DFE)
Ends with what it did NOT check. Exit status 1 if anything failed.
"""
import collections
import csv
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TAB = os.path.join(ROOT, "pin_tables")
SCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "kicad_v3_pod", "haven_v3_pod.kicad_sch")
PCB = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "kicad_v3_pod", "haven_v3_pod.kicad_pcb")

GROUND_NAMES = {"GND", "GROUND", "AGND", "DGND", "HPGND", "AVSS", "PVSS"}
GND_NET = "/GND"
# Symbol names that are a different spelling of the datasheet's name, per part
ALIASES = {"TPD1E05U06DYAR": {"K": "I/O", "A": "GND"}, "CN4024M57620001": {"1": "XTAL", "3": "XTAL"}}

fails, passes, notes = [], collections.Counter(), []


def fail(ref, msg):
    fails.append(f"{ref}: {msg}")


def ok(kind):
    passes[kind] += 1


def read_csv(name):
    with open(os.path.join(TAB, name), newline="") as f:
        return list(csv.DictReader(f))


def norm(name):
    """Primary name only ("P0.26/AIN5" -> "P0.26"), upper case, no active-low marks."""
    n = name.split("/")[0].upper().replace("#", "")
    return {"GROUND": "GND"}.get(n, n)


# --- schematic netlist
tmp = os.path.join(tempfile.mkdtemp(), "net.xml")
subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "-o", tmp, SCH],
               check=True, capture_output=True)
t = ET.parse(tmp)
comps = {}
for c in t.iter("comp"):
    f = {x.get("name"): (x.text or "") for x in c.iter("field")}
    comps[c.get("ref")] = dict(value=c.findtext("value") or "", mpn=f.get("MPN", "").strip())
sch_pins = collections.defaultdict(dict)          # ref -> pin -> (name, net or None)
for n in t.iter("net"):
    name = n.get("name")
    for nd in n.iter("node"):
        net = None if name.startswith("unconnected-") else name
        sch_pins[nd.get("ref")][nd.get("pin")] = (nd.get("pinfunction") or "", net)

# --- board
import pcbnew                                       # noqa: E402 (KiCad's module; slow, so after the netlist)
board = pcbnew.LoadBoard(PCB)
pcb_pads = collections.defaultdict(dict)          # ref -> pad number -> net ("" if none)
for fp in board.GetFootprints():
    for p in fp.Pads():
        if p.GetNumber():
            pcb_pads[fp.GetReference()][p.GetNumber()] = p.GetNetname()

tables = {r["mpn"]: r for r in read_csv("parts.csv")}
variants = read_csv("variants.csv")
rules = collections.defaultdict(list)
for r in read_csv("design_rules.csv"):
    rules[r["ref"]].append(r)

# --- 1-6: parts with pin tables
covered = set()
for ref in sorted(comps):
    mpn = comps[ref]["mpn"]
    if not mpn:
        continue
    for v in variants:
        if re.match(v["family_regex"], mpn, re.I):
            if mpn.upper() != v["required_mpn"].upper():
                fail(ref, f"MPN {mpn} is not {v['required_mpn']}: {v['reason']}")
            else:
                ok("variant")
    if mpn not in tables:
        continue
    covered.add(ref)
    table = {r["pin"]: r for r in read_csv(mpn + ".csv")}
    sp, bp = sch_pins.get(ref, {}), pcb_pads.get(ref, {})
    for label, have in (("schematic pin", sp), ("board pad", bp)):
        missing, extra = set(table) - set(have), set(have) - set(table)
        if missing or extra:
            fail(ref, f"{label}s differ from the {mpn} datasheet: missing {sorted(missing)}, extra {sorted(extra)}")
        else:
            ok("pin set")
    alias = ALIASES.get(mpn, {})
    by_name = collections.defaultdict(list)
    for pin, row in table.items():
        if pin not in sp:
            continue
        sname, net = sp[pin]
        want = norm(row["name"])
        if norm(alias.get(sname, sname)) != want:
            fail(ref, f"pin {pin} is '{sname}' in the schematic, '{row['name']}' in the datasheet ({row['source']})")
        else:
            ok("pin name")
        if want in GROUND_NAMES or want == "GND":
            if net != GND_NET:
                fail(ref, f"pin {pin} {row['name']} is a ground pin but is on {net or 'nothing'}")
            else:
                ok("ground pin")
        elif want == "NC":
            if net:
                fail(ref, f"pin {pin} is NC in the datasheet but is on {net}")
            else:
                ok("NC pin")
        elif row["type"].upper() in ("POWER", "PWR"):
            by_name[want].append((pin, net))
    for name, lst in by_name.items():
        nets = {n for _, n in lst}
        if len(lst) > 1:
            if len(nets) != 1 or None in nets:
                fail(ref, f"power pins named {name} {[p for p, _ in lst]} are on different nets {sorted(map(str, nets))}")
            else:
                ok("power pins tied")
    for r in rules.get(ref, []):
        net = sp.get(r["pin"], ("", "?"))[1]
        exp = r["expect"]
        if exp == "NC":
            good, show = net is None, "unconnected"
        elif exp.startswith("="):
            other = sp.get(exp[1:], ("", "?"))[1]
            good, show = net is not None and net == other, f"the net of pin {exp[1:]} ({other})"
        else:
            good, show = net == exp, exp
        if good:
            ok("design rule")
        else:
            fail(ref, f"pin {r['pin']} should be {show}, is {net or 'unconnected'}: {r['reason']}")
for r in rules:
    if r not in covered:
        fail(r, "has design rules but no pin table (or no MPN)")

# --- 6: board nets equal schematic nets, every part
for ref, pads in pcb_pads.items():
    for pad, pnet in pads.items():
        if ref not in sch_pins or pad not in sch_pins[ref]:
            continue
        snet = sch_pins[ref][pad][1] or ""
        if pnet.startswith("unconnected-"):
            pnet = ""
        if pnet != snet:
            fail(ref, f"pad {pad} is on {pnet or 'nothing'} on the board, {snet or 'nothing'} in the schematic")
        else:
            ok("board net")

# --- 7: passives
SI = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "m": 1e-3, "": 1, "R": 1, "k": 1e3, "K": 1e3, "M": 1e6}


def parse_value(v):
    m = re.match(r"\s*([\d.]+)\s*([pnuµmkKMR]?)", v)
    return float(m[1]) * SI[m[2]] if m else None


def code3(c, unit):
    """'105' -> 10e5 pF etc. 'R' marks the decimal point ('2R2' = 2.2). unit is the code's base (pF or ohm)."""
    if "R" in c:
        return float(c.replace("R", ".")) * unit
    return int(c[:-1]) * 10 ** int(c[-1]) * unit


def mpn_value(mpn):
    m = re.match(r"GRM\d{3}\w{2}\w{2}(\d{3}|\dR\d)", mpn)
    if m:
        return code3(m[1], 1e-12)
    m = re.match(r"CL\d{2}\w(\d{3}|\dR\d)", mpn)
    if m:
        return code3(m[1], 1e-12)
    m = re.match(r"RC\d{4}[A-Z]R-\d{2}([\dRKM.]+?)L$", mpn)
    if m:
        s = m[1]
        for k, mul in (("K", 1e3), ("M", 1e6), ("R", 1)):
            if k in s:
                a, b = s.split(k)
                return float(f"{a or 0}.{b or 0}") * mul
    m = re.match(r"WR\d{2}X(\d{3}|\dR\d)", mpn)
    if m:
        return code3(m[1], 1)
    m = re.match(r"C[QR]0[12]\w{2,3}?(\d{4})", mpn)           # Royalohm: 4-digit code, last digit = exponent
    if m:
        return code3(m[1], 1)
    m = re.match(r"ERJ\w{3}F(\d{2,3}R\d|\d{4})", mpn)
    if m:
        return float(m[1].replace("R", ".")) if "R" in m[1] else code3(m[1], 1)
    m = re.match(r"DFE\d{6}\w-(\dR\d)", mpn)
    if m:
        return float(m[1].replace("R", ".")) * 1e-6
    return None


passive_unchecked = []
for ref in sorted(comps):
    if not re.match(r"[CRL]\d", ref):
        continue
    mpn, val = comps[ref]["mpn"], parse_value(comps[ref]["value"])
    mv = mpn_value(mpn) if mpn else None
    if mv is None or val is None:
        passive_unchecked.append(f"{ref} {comps[ref]['value']} {mpn or '(no MPN)'}")
    elif abs(mv - val) > 1e-6 * val:
        fail(ref, f"value {comps[ref]['value']} but MPN {mpn} encodes {mv:g}")
    else:
        ok("passive value")

# --- report
print(f"Schematic {os.path.relpath(SCH, ROOT)}, board {os.path.relpath(PCB, ROOT)}")
print("Passed: " + ", ".join(f"{k} {v}" for k, v in passes.items()))
print("Pin tables used: " + ", ".join(f"{m} ({r['provenance']})" for m, r in tables.items()))
no_table = sorted(r for r in comps if comps[r]["mpn"] and r not in covered and not re.match(r"[CRL]\d", r))
print("\nNOT checked by this script:")
print("  parts with an MPN but no pin table: " + (", ".join(f"{r} {comps[r]['mpn']}" for r in no_table) or "none"))
print("  parts with no MPN (pads, test points, wires): " +
      ", ".join(r for r in sorted(comps) if not comps[r]["mpn"]))
if passive_unchecked:
    print("  passive values not decodable from the MPN: " + "; ".join(passive_unchecked))
unv = [m for m, r in tables.items() if r["provenance"] != "parsed"]
print("  tables typed in by hand from drawings (a person read them, not this script): " + ", ".join(unv))
print("  land-pattern pad sizes and positions, voltage ratings, support-part values (see AUDIT_2026-11-19.md),")
print("  firmware pin assignments, crystal load settings, layout rules from the datasheets")
if fails:
    print(f"\nFAILED ({len(fails)}):")
    for f in fails:
        print("  " + f)
    sys.exit(1)
print("\nNo failures in what was checked.")

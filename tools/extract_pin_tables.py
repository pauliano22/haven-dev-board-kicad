#!/usr/bin/env python3
"""Build pin_tables/*.csv from the datasheets themselves (2026-11-19).

The point: the pin tables must NOT come from our schematic, or checking the schematic against them proves nothing.
Where the datasheet's pin table is text, it is parsed from the PDF here. Where it is only a drawing (mic, LED,
MOSFET, crystal), the rows are typed in below from the named page, with that provenance written into the CSV so a
reader knows which tables a machine read and which a person read.

    python3 tools/extract_pin_tables.py          (datasheets in ~/.cache/haven_datasheets/)

Writes pin_tables/<MPN>.csv (pin,name,type,source) and pin_tables/parts.csv (which datasheet, its sha256).
"""
import csv
import hashlib
import os
import re
import subprocess

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "pin_tables")
DS = os.path.expanduser("~/.cache/haven_datasheets")


def pdftext(pdf, first=None, last=None):
    cmd = ["pdftotext", "-layout"]
    if first:
        cmd += ["-f", str(first), "-l", str(last or first)]
    return subprocess.run(cmd + [os.path.join(DS, pdf), "-"], check=True, capture_output=True, text=True).stdout


def npm1100():
    """PS v1.5 section 8.1.1, Table 23 (pages 45-46): WLCSP ball assignments."""
    rows = []
    for line in pdftext("npm1100_ps.pdf", 45, 46).splitlines():
        if "Table 23" in line:
            break
        m = re.match(r"\s*([A-E][1-5])\s+(\S+)\s+(Power|Digital I/O|Digital OUT|Analog input)\b", line)
        if m:
            rows.append((m[1], m[2], m[3], "nPM1100 PS v1.5 Table 23"))
    assert len(rows) == 25, len(rows)
    return rows


def adau1860():
    """Data sheet Rev C, Table 13 Pin Function Descriptions (pages 17-19)."""
    rows, pend = [], None
    for line in pdftext("adau1860.pdf").splitlines():
        m = re.match(r"([A-G][1-8])\s+(\S+)\s+(D_IO|PWR|A_OUT|A_IN|D_IN)\b", line)
        if m:
            rows.append([m[1], m[2], m[3], "ADAU1860 Rev C Table 13"])
            pend = rows[-1] if m[2].endswith("/") else None
        elif pend and line.strip():
            pend[1] += line.split()[0]          # "SDA/MISO/" continues as "UART_CTRL_TX" on the next line
            pend = None
    seen = {}
    for r in rows:
        seen.setdefault(r[0], r)                # the table is printed once; keep the first hit per ball
    rows = sorted(seen.values())
    assert len(rows) == 56, len(rows)
    return [tuple(r) for r in rows]


def raytac():
    """MDBT53V-1M spec section 2.5 Pin assignment. A multi-function pin prints its first name on the line above "(n)"."""
    lines = pdftext("raytac_MDBT53V-1M_spec.pdf").splitlines()
    start = next(i for i, l in enumerate(lines) if re.match(r"\s*Pin No\.\s+Name", l))
    rows, prev = [], None
    for line in lines[start:]:
        if "Main chip solution" in line:
            break
        m = re.match(r"\s*\((\d+)\)\s*(\S+)?\s*(.*)", line)
        if m:
            if m[2]:
                name, kind = m[2], m[3].split("  ")[0].strip()
            else:
                name, kind = prev.split()[0], " ".join(prev.split()[1:3])
            rows.append((m[1], name, kind, "Raytac MDBT53V-1M spec 2.5"))
        elif line.strip():
            prev = line
    assert [int(r[0]) for r in rows] == list(range(1, 40)), [r[0] for r in rows]
    return rows


def ap22916():
    """Diodes DS44758 Rev 2-2 page 2, Pin Descriptions."""
    rows = []
    for line in pdftext("ap22916.pdf", 2, 2).splitlines():
        m = re.match(r"\s*(VOUT|VIN|GND|ON)\s+([AB][12])\b", line)
        if m:
            rows.append((m[2], m[1], "", "AP22916 DS44758 Pin Descriptions"))
    assert len(rows) == 4, rows
    return rows


def tpd1e05u06():
    """TI SLVSCF7 Table 4-1 (DPY and DYA)."""
    rows = []
    for line in pdftext("audit_dl/tpd1e05u06.pdf").splitlines():
        m = re.match(r"\s*(GND|I/O)\s+([12])\s+(Ground|I/O)", line)
        if m:
            rows.append((m[2], m[1], m[3], "TPD1E05U06 Table 4-1"))
    rows = sorted(set(rows))
    assert len(rows) == 2, rows
    return rows


# Pin tables that are drawings, not text. Typed in from the page named; "manual" in parts.csv.
MANUAL = {
    "SPK0641HT4H-1": ("spk0641ht4h.pdf", [
        ("1", "DATA", "Digital O"), ("2", "CLOCK", "Digital I"), ("3", "SELECT", "Non-Digital Input"),
        ("4", "VDD", "Power"), ("5", "GROUND", "Power"), ("6", "GROUND", "Power"), ("7", "GROUND", "Power"),
        ("8", "GROUND", "Power")], "SPK0641HT4H-1 Rev D-1 page 7 pin table (image)"),
    "XL-0201SURC": ("led/xl0201surc.pdf", [("1", "K", ""), ("2", "A", "")],
                    "Xinglight XL-0201SURC page 7 drawing (image): 1 = cathode"),
    "CSD15380F3": ("audit_dl/csd15380f3.pdf", [("1", "G", ""), ("2", "S", ""), ("3", "D", "")],
                   "TI CSD15380F3 page 1 drawing (image): positions checked; NUMBERS from the LCSC footprint"),
}
# Parts whose pin table we do not have from the maker. Listed so the report says so instead of skipping them.
UNVERIFIED = {
    "CN4024M57620001": [("1", "XTAL", ""), ("2", "GND", ""), ("3", "XTAL", ""), ("4", "GND", "")],
}

PARSED = {
    "NPM1100-CAAA-E-R": ("npm1100_ps.pdf", npm1100),
    "ADAU1860BCBZRL": ("adau1860.pdf", adau1860),
    "MDBT53V-1M": ("raytac_MDBT53V-1M_spec.pdf", raytac),
    "AP22916CCA4-7": ("ap22916.pdf", ap22916),
    "TPD1E05U06DYAR": ("audit_dl/tpd1e05u06.pdf", tpd1e05u06),
}


def sha(pdf):
    return hashlib.sha256(open(os.path.join(DS, pdf), "rb").read()).hexdigest()[:16]


def write(mpn, rows):
    with open(os.path.join(OUT, mpn + ".csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pin", "name", "type", "source"])
        w.writerows(rows)


os.makedirs(OUT, exist_ok=True)
parts = []
for mpn, (pdf, fn) in PARSED.items():
    write(mpn, fn())
    parts.append((mpn, pdf, sha(pdf), "parsed"))
for mpn, (pdf, rows, src) in MANUAL.items():
    write(mpn, [r + (src,) for r in rows])
    parts.append((mpn, pdf, sha(pdf), "manual"))
for mpn, rows in UNVERIFIED.items():
    write(mpn, [r + ("LCSC footprint only; maker drawing not seen",) for r in rows])
    parts.append((mpn, "", "", "unverified"))
with open(os.path.join(OUT, "parts.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["mpn", "datasheet", "sha256_16", "provenance"])
    w.writerows(parts)
for p in parts:
    print(*p)

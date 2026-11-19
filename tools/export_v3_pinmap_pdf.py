#!/usr/bin/env python3
"""Readable pin map of the v3 pod for outside reviewers (2026-11-19). The generated schematic connects everything by
net labels, which is hard to follow; this lists, per chip, every pin, its net, and the parts on that net.

    python3 tools/export_v3_pinmap_pdf.py  ->  fab/v3_review/haven_v3_pod_pinmap.pdf
"""
import collections
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCH = os.path.join(ROOT, "kicad_v3_pod", "haven_v3_pod.kicad_sch")
OUT = os.path.join(ROOT, "fab", "v3_review", "haven_v3_pod_pinmap.pdf")

tmp = os.path.join(tempfile.mkdtemp(), "net.xml")
subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "-o", tmp, SCH], check=True, capture_output=True)
t = ET.parse(tmp)
comps = {c.get("ref"): c.findtext("value") for c in t.iter("comp")}
pins = collections.defaultdict(list)      # ref -> [(pin, function, net)]
members = collections.defaultdict(list)   # net -> [ref.pin]
for n in t.iter("net"):
    name = n.get("name").lstrip("/")
    for nd in n.iter("node"):
        pins[nd.get("ref")].append((nd.get("pin"), nd.get("pinfunction") or "", name))
        members[name].append(nd.get("ref"))

INTRO = """Haven v3 pod: behind-the-ear hearing-comfort prototype (personal, non-commercial). Board 9.6 x 27 mm, 6 layers, 0.8 mm.

Power path
  VBUS 5 V from a charging cradle through two spring pins (P1 = VBUS, P2 = GND), TPD1E05U06 ESD diode D1.
  U2 nPM1100-CAAA-E-R (WLCSP): fixed 100 mA VBUS limit (ISET = D- = AVSS, D+ open), VTERMSET = VSYS -> 4.20 V,
    ICHG 30 k -> 20 mA, NTC replaced by 10 k, MODE = AVSS (automatic), VOUTBSET = 00 -> VOUTB 1.8 V.
  Cell: 3.7 V 40 mAh LiPo pouch with its own protection board (TinyCircuits ASR00072), soldered to TP8 / TP9.
  +1V8 (VOUTB) supplies the Raytac MDBT53V-1M (nRF5340) on VDD and VDDH tied together (normal-voltage mode),
    module regulators in LDO mode (DCC, DECR, DCCD, DECD, DCCH unconnected). No 32.768 kHz crystal: LFRC.
  U3 AP22916CCA4-7 load switch (ON = nRF P1.11) -> V_LS: ADAU1860 AVDD / HPVDD / HPVDD_L / IOVDD and the mic.

Audio
  U15 ADAU1860 (WLCSP-56, 0.35 mm), own 24.576 MHz crystal (CL 20 pF, 33 pF caps, 220 ohm series), I2C at 0x64
    (ADDR0/1 low), REG_EN high (internal DVDD), PD# = nRF P0.04. I2S: nRF is master (P0.13 BCLK, P0.14 LRCK,
    P0.15 SDOUT -> SDATAI_0, P0.31 SDIN <- SDATAO_0).
  U14 SPK0641HT4H-1 top-port PDM mic on DMIC_CLK / DMIC01 (SELECT low).
  Speaker: 16 ohm, on two wires from HPOUTP / HPOUTN (pads W5 / W6), 220 ohm in series at the speaker.

Charger status to the nRF: CHG P0.10, ERR P0.11 (internal pull-ups), SHPACT P0.12. ADC: VSYS/2.8 on AIN1, VBUS divider on AIN4.

Pages that follow: every pin of U2, U1, U15, U3, U14, then every passive. "Also on net" lists the other parts on that net."""


def table_page(pdf, title, rows, cols, widths):
    per = 44
    for k in range(0, max(len(rows), 1), per):
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.text(0.05, 0.965, title + (f" (cont.)" if k else ""), fontsize=11, weight="bold", va="top")
        ax = fig.add_axes([0.05, 0.03, 0.9, 0.9]); ax.axis("off")
        chunk = rows[k:k + per]
        tb = ax.table(cellText=chunk, colLabels=cols, colWidths=widths, loc="upper left", cellLoc="left")
        tb.auto_set_font_size(False); tb.set_fontsize(6.6); tb.scale(1, 1.18)
        for (r, c), cell in tb.get_celld().items():
            cell.set_linewidth(0.3)
            if r == 0:
                cell.set_text_props(weight="bold"); cell.set_facecolor("#e8e8e8")
        pdf.savefig(fig); plt.close(fig)


def sort_pin(p):
    s = p[0]
    return (s[0].isdigit(), s.rjust(4) if s.isdigit() else (s[0], int(s[1:]) if s[1:].isdigit() else 0))


with PdfPages(OUT) as pdf:
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.text(0.05, 0.965, "Haven v3 pod: circuit summary and pin map (2026-11-19)", fontsize=12, weight="bold", va="top")
    fig.text(0.05, 0.93, INTRO, fontsize=7.4, va="top", family="monospace", linespacing=1.35)
    pdf.savefig(fig); plt.close(fig)
    for ref in ("U2", "U1", "U15", "U3", "U14", "U4", "Q2", "CRYSTAL1"):
        rows = []
        for pin, fn, net in sorted(pins[ref], key=sort_pin):
            others = sorted({r for r in members[net] if r != ref}) if not net.startswith("unconnected") else []
            shown = ", ".join(f"{r} ({comps[r]})" if r[0] in "CRL" else r for r in others[:8]) + (" ..." if len(others) > 8 else "")
            rows.append([pin, fn, "not connected" if net.startswith("unconnected") else net, shown if net != "GND" else "(ground)"])
        table_page(pdf, f"{ref}  {comps[ref]}", rows, ["Pin", "Name", "Net", "Also on net"], [0.07, 0.25, 0.17, 0.51])
    rows = []
    for ref in sorted(comps, key=lambda r: (r.rstrip("0123456789"), int(''.join(ch for ch in r if ch.isdigit()) or 0))):
        if ref[0] in "CRLD" and not ref.startswith("CRYSTAL"):
            nets = " / ".join(net for _, _, net in sorted(pins[ref], key=sort_pin))
            rows.append([ref, comps[ref], nets])
    table_page(pdf, "Passives and diodes", rows, ["Ref", "Value", "Pin 1 / pin 2 nets"], [0.1, 0.25, 0.65])
print(OUT, f"{os.path.getsize(OUT) / 1e6:.2f} MB")

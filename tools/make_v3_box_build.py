#!/usr/bin/env python3
"""Collect everything a turnkey (box build) supplier needs for the first v3 pair into one zip (2026-11-15).

    python3 tools/make_v3_box_build.py   ->  fab/v3_box_build/haven_v3_box_build_<date>.zip

Run after: tools/export_v2_fab.py v3podpanel, tools/gen_cradle_v3_pcb.py, the shell / in-ear / cradle scripts, and a
fresh haven_v2 LFRC firmware build in ~/.cache/haven_builds/haven_v3_lfrc (CLAUDE.md build command with
-DFILE_SUFFIX=lfrc). It refuses to run if any input is missing or older than its source.
Contains no personal or health information: only design files, firmware and the instructions.
"""
import datetime
import os
import sys
import zipfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
WS = os.path.dirname(ROOT)
MECH = os.path.join(WS, "hardware", "mechanical_cad", "v3_slim")
FW = os.path.expanduser("~/.cache/haven_builds/haven_v3_lfrc")
OUT = os.path.join(ROOT, "fab", "v3_box_build")
FILES = {
    "BUILD_INSTRUCTIONS.md": os.path.join(OUT, "BUILD_INSTRUCTIONS.md"),
    "BOM_bought_parts.csv": os.path.join(OUT, "BOM_bought_parts.csv"),
    "PLACEMENT_CHECK.md": os.path.join(ROOT, "fab", "v3_pod", "PLACEMENT_CHECK.md"),
    "pcb/pod_panel/haven_v3_pod_panel_gerbers.zip": os.path.join(ROOT, "fab", "v3_pod_panel", "haven_v3_pod_panel_gerbers.zip"),
    "pcb/pod_panel/haven_v3_pod_panel_bom.csv": os.path.join(ROOT, "fab", "v3_pod_panel", "haven_v3_pod_panel_bom.csv"),
    "pcb/pod_panel/haven_v3_pod_panel_cpl.csv": os.path.join(ROOT, "fab", "v3_pod_panel", "haven_v3_pod_panel_cpl.csv"),
    "pcb/cradle/haven_v3_cradle_gerbers.zip": os.path.join(ROOT, "fab", "v3_cradle", "haven_v3_cradle_gerbers.zip"),
    "pcb/cradle/haven_v3_cradle_bom.csv": os.path.join(ROOT, "fab", "v3_cradle", "haven_v3_cradle_bom.csv"),
    "pcb/cradle/haven_v3_cradle_cpl.csv": os.path.join(ROOT, "fab", "v3_cradle", "haven_v3_cradle_cpl.csv"),
    "firmware/haven_app_core.hex": os.path.join(FW, "haven_zephyr_app", "zephyr", "zephyr.hex"),
    "firmware/haven_net_core.hex": os.path.join(FW, "ipc_radio", "zephyr", "zephyr.hex"),
}
for name in ("pod_v3_shell_tray_R.stl", "pod_v3_shell_lid_R.stl", "inear_v3_body.stl", "inear_v3_cap.stl",
             "inear_v3_body.step", "inear_v3_cap.step", "cradle_v3_base.stl", "cradle_v3_frame.stl", "cradle_v3_lid.stl"):
    FILES["print/" + name] = os.path.join(MECH, name)

missing = [k for k, p in FILES.items() if not os.path.exists(p)]
if missing:
    sys.exit("missing: " + ", ".join(missing))
src_newer = []
for out_key, src in (("print/pod_v3_shell_tray_R.stl", os.path.join(MECH, "pod_v3_shell.py")),
                     ("print/cradle_v3_frame.stl", os.path.join(MECH, "cradle_v3.py")),
                     ("pcb/cradle/haven_v3_cradle_gerbers.zip", os.path.join(ROOT, "tools", "gen_cradle_v3_pcb.py")),
                     ("pcb/pod_panel/haven_v3_pod_panel_gerbers.zip", os.path.join(ROOT, "kicad_v3_pod", "haven_v3_pod.kicad_pcb"))):
    if os.path.getmtime(src) > os.path.getmtime(FILES[out_key]):
        src_newer.append(f"{out_key} is older than {os.path.basename(src)}")
# Firmware: the hex must be newer than the firmware repo's last commit (added 2026-11-19; until then nothing checked it).
import subprocess
fw_repo = os.path.join(WS, "firmware", "haven_zephyr_app")
last_commit = int(subprocess.run(["git", "-C", fw_repo, "log", "-1", "--format=%ct"], capture_output=True, text=True,
                                 check=True).stdout.strip())
for key in ("firmware/haven_app_core.hex", "firmware/haven_net_core.hex"):
    if os.path.getmtime(FILES[key]) < last_commit:
        src_newer.append(f"{key} is older than the last firmware commit (rebuild: see the docstring)")
dirty = subprocess.run(["git", "-C", fw_repo, "status", "--porcelain", "--untracked-files=no"], capture_output=True,
                       text=True, check=True).stdout.strip()
if dirty:
    src_newer.append("firmware repo has uncommitted changes: " + dirty.replace("\n", ", "))
if src_newer:
    sys.exit("stale: " + "; ".join(src_newer))

zpath = os.path.join(OUT, f"haven_v3_box_build_{datetime.date.today():%Y-%m-%d}.zip")
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for arc, p in FILES.items():
        z.write(p, arc)
print(f"{zpath}: {len(FILES)} files, {os.path.getsize(zpath) / 1e6:.1f} MB")

#!/usr/bin/env python3
"""Autoroute the placed pod board with Freerouting, import the result, fill zones, run DRC.

    python3 tools/route_v2_pod_pcb.py [max_passes]

Freerouting needs Java 17+; this uses ~/tools/jdk25 and ~/tools/freerouting.jar. Work files go
to ~/.cache/haven_builds/pod_pcb/.
"""
import os
import subprocess
import sys

import pcbnew

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PCB = os.path.join(ROOT, "kicad_v2_pod", "haven_v2_pod.kicad_pcb")
WORK = os.path.expanduser("~/.cache/haven_builds/pod_pcb")
JAVA = os.path.expanduser("~/tools/jdk25/bin/java")
JAR = os.path.expanduser("~/tools/freerouting.jar")


def main():
    passes = sys.argv[1] if len(sys.argv) > 1 else "40"
    os.makedirs(WORK, exist_ok=True)
    dsn, ses = os.path.join(WORK, "pod.dsn"), os.path.join(WORK, "pod.ses")
    b = pcbnew.LoadBoard(PCB)
    if not pcbnew.ExportSpecctraDSN(b, dsn):
        raise SystemExit("DSN export failed")
    if os.path.exists(ses):
        os.remove(ses)
    cmd = [JAVA, "-Djava.awt.headless=true", "-jar", JAR, "-de", dsn, "-do", ses, "-mp", passes, "-mt", "1"]
    print(" ".join(cmd), flush=True)
    with open(os.path.join(WORK, "freerouting.log"), "w") as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=False)
    if not os.path.exists(ses):
        raise SystemExit("Freerouting wrote no session file; see freerouting.log")
    b = pcbnew.LoadBoard(PCB)
    if not pcbnew.ImportSpecctraSES(b, ses):
        raise SystemExit("SES import failed")
    b.Save(PCB)
    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(PCB)
    rpt = os.path.join(WORK, "drc.rpt")
    subprocess.run(["kicad-cli", "pcb", "drc", "--schematic-parity", "--severity-error", "--severity-warning",
                    "-o", rpt, PCB], check=False, stdout=subprocess.DEVNULL)
    print(open(rpt).read().count("\n[") , "DRC items; report", rpt)


if __name__ == "__main__":
    main()

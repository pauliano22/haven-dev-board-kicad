#!/usr/bin/env python3
"""Autoroute the case board with Freerouting (same flow as route_v2_pod_pcb.py).

    python3 tools/route_v2_case_pcb.py [max_passes]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import route_v2_pod_pcb as r  # noqa: E402

r.PCB = os.path.join(r.ROOT, "kicad_v2_case", "haven_v2_case.kicad_pcb")
r.WORK = os.path.expanduser("~/.cache/haven_builds/case_pcb")

if __name__ == "__main__":
    r.main()

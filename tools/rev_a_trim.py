"""Rev A: delete OpenEarable parts Haven doesn't use, from the native board.

Removes the microSD path (CARD1, U10 level shifter, U9 load switch, Q3/R1
card detect, pull-ups and V_SD decoupling), the flash (U14), the IMU (U1,
plus its SCL2/SDA2 pull-ups R10/R11), the fuel gauge (U6 and its R17/C23),
and the flex-board connector (CN1). R21, the fuel gauge's 10 mOhm sense
resistor in the battery path, becomes a 0 Ohm jumper on the same footprint.
J1 (Samtec SWD/JTAG) stays as do-not-populate test pads: its copper still
reaches SWDIO/SWCLK/RESETN/+1.8V/GND, so no new routing is needed.

Copper: nets left with fewer than two pads lose all their tracks and vias;
nets that keep two or more pads lose only the stubs that now dangle.
Usage: python3 tools/rev_a_trim.py kicad/haven_dev_board.kicad_pcb
"""
import collections, sys
import pcbnew

REMOVE = ["CARD1", "U10", "U9", "Q3", "R1", "R15", "R20", "C6", "C8", "C26", "C28",
          "U14", "U1", "R10", "R11", "U6", "R17", "C23", "R19", "CN1"]

b = pcbnew.LoadBoard(sys.argv[1])
fps = {f.GetReference(): f for f in b.GetFootprints()}
touched = set()
removed_pad_points = []
for ref in REMOVE:
    f = fps[ref]
    for p in f.Pads():
        if p.GetNetname():
            touched.add(p.GetNetname())
            for L in (pcbnew.F_Cu, pcbnew.B_Cu):
                if p.IsOnLayer(L):
                    removed_pad_points.append((p.GetPosition(), L, p.GetNetname()))
    b.Remove(f)

r21 = fps["R21"]
r21.SetValue("0R")
j1 = fps["J1"]
j1.SetDNP(True)
j1.SetExcludedFromBOM(True)
j1.SetExcludedFromPosFiles(True)

pads_on = collections.Counter()
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname():
            pads_on[p.GetNetname()] += 1

removed_tracks = removed_vias = 0
dead = {n for n in touched if pads_on[n] < 2 and n != "GND"}
for t in list(b.GetTracks()):
    if t.GetNetname() in dead:
        if t.GetClass() == "PCB_VIA":
            removed_vias += 1
        else:
            removed_tracks += 1
        b.Remove(t)

TOL = pcbnew.FromMM(0.01)
live = touched - dead


def held(pos, layer, net, skip):
    """True if anything other than `skip` on this net touches pos: a pad,
    a via, any point of a track (T-junctions included), or a filled zone."""
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() == net and p.IsOnLayer(layer) and p.HitTest(pos):
                return True
    for t in b.GetTracks():
        if t is skip or t.GetNetname() != net:
            continue
        if t.GetClass() == "PCB_VIA":
            if (t.GetPosition() - pos).EuclideanNorm() <= max(TOL, t.GetWidth(pcbnew.F_Cu) // 2):
                return True
        elif t.GetLayer() == layer and t.HitTest(pos, TOL):
            return True
    for z in b.Zones():
        if z.GetNetname() == net and z.IsOnLayer(layer) and z.HitTestFilledArea(layer, pos):
            return True
    return False


# Walk outward only from where removed pads were: a segment ending on a
# removed pad goes; its far end is then checked the same way.
frontier = [(pos, layer, net) for pos, layer, net in removed_pad_points if net in live and net != "GND"]
while frontier:
    pos, layer, net = frontier.pop()
    for t in list(b.GetTracks()):
        if t.GetNetname() != net:
            continue
        if t.GetClass() == "PCB_VIA":
            if (t.GetPosition() - pos).EuclideanNorm() <= TOL:
                others = [s for s in b.GetTracks() if s is not t and s.GetClass() != "PCB_VIA"
                          and s.GetNetname() == net and s.HitTest(t.GetPosition(), TOL)]
                if not others and not any(z.GetNetname() == net for z in b.Zones()):
                    b.Remove(t); removed_vias += 1
            continue
        if t.GetLayer() != layer:
            continue
        for a, other in ((t.GetStart(), t.GetEnd()), (t.GetEnd(), t.GetStart())):
            if (a - pos).EuclideanNorm() <= TOL and not held(a, layer, net, t):
                b.Remove(t); removed_tracks += 1
                frontier.append((other, layer, net))
                for v in b.GetTracks():
                    if v.GetClass() == "PCB_VIA" and v.GetNetname() == net and (v.GetPosition() - other).EuclideanNorm() <= TOL:
                        for L in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu):
                            frontier.append((other, L, net))
                break

# Stubs that ended on a removed pad's edge rather than its centre, or chains
# of overlapping segments that only touch each other: ask KiCad's own
# connectivity engine which ends dangle, on affected nets only, until none.
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
while True:
    b.BuildConnectivity()
    conn = b.GetConnectivity()
    stubs = [t for t in b.GetTracks() if t.GetClass() != "PCB_VIA" and t.GetNetname() in live
             and conn.TestTrackEndpointDangling(t, False)]
    if not stubs:
        break
    for t in stubs:
        b.Remove(t); removed_tracks += 1

pcbnew.SaveBoard(sys.argv[1], b)
print(f"removed {len(REMOVE)} footprints, {removed_tracks} track segments, {removed_vias} vias")
print("dead nets:", sorted(dead))

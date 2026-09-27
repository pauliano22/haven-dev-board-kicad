"""Group C: bring the 24.576 MHz codec crystal (CRYSTAL1 + C45/C46 + R28) from
~6 mm to ~1.3 mm pad-to-ball by re-doing the XTALI/XTALO BGA escape.

Why the previous attempt stopped at 6 mm: the only exits from U15's B6/B7
balls are their existing via-in-pads. From there, on B.Cu TDO's escape track
runs 0.17 mm east of the XTALI via and walls the pocket off; on In4 SCL1's
escape diagonal does the same. The inner GND layer In2 has nothing in this
corner except the through-via field, and XTALI/XTALO already carry the
per-pair `.kicad_dru` exceptions (XTALI vs TDO 0.015 mm, XTALO vs TMS/TDO/
XTALI 0.03-0.05 mm + matching hole rules) that the via field demands. So:

  ball -> existing via-in-pad -> short In2 run east -> new exit via -> B.Cu
  stub -> crystal pad, with the crystal on B.Cu in the pocket east of the
  BGA (x 60.2-62.1, y 111-113.4) bounded by TDO (W), SDA1 (NE), PDMDIN/PDMCLK
  (S). XTALO leaves its via-in-pad south-west (the only gap in the ring of
  TMS/TDO/XTALI vias), runs under row A on In2 and exits south of the crystal
  next to R28.

Each new via and segment is checked against copper clearance (with the
board's own pair exceptions, never looser), hole clearance (0.15 mm default,
pair rules where they exist) and hole-to-hole (0.20 mm edge) BEFORE being
added; the real gate is `kicad-cli pcb drc` + `tools/drc_diff.py` afterwards.
Run from kicad/ with KiCad's python:  python3 ../routing-evidence/crystal-escape/group_c_crystal_escape.py [--in-layer In2.Cu]
"""
import sys, math, re, argparse, shutil
sys.path.insert(0, '../tools')
import pcbnew, placement_lib as pl, route_lib as rl

ap = argparse.ArgumentParser()
ap.add_argument('--board', default='haven_dev_board.kicad_pcb')
ap.add_argument('--in-layer', default='In2.Cu', choices=['In1.Cu', 'In2.Cu', 'In3.Cu', 'In4.Cu'])
ap.add_argument('--clearance', type=float, default=0.215)
ap.add_argument('--crystal-anchor', default='61.3,112.2')
ap.add_argument('--max-cands', type=int, default=40)
ap.add_argument('--phase', default='place', choices=['strip', 'place'], help='pcbnew 9 breaks the board object after Remove(); strip in one process, place in another')
A = ap.parse_args()

LAYERS = {'F.Cu': pcbnew.F_Cu, 'B.Cu': pcbnew.B_Cu, 'In1.Cu': pcbnew.In1_Cu, 'In2.Cu': pcbnew.In2_Cu, 'In3.Cu': pcbnew.In3_Cu, 'In4.Cu': pcbnew.In4_Cu}
IN = LAYERS[A.in_layer]
W = 0.09; HALF_W = W / 2
VIA_D, VIA_DRILL = 0.20, 0.10
HOLE_CLR_DEFAULT = 0.15   # board setup min_hole_clearance
HOLE2HOLE = 0.20          # board setup min_hole_to_hole (edge to edge)
B7 = (59.49, 112.148); B6 = (59.14, 112.148)
XTALI_VIP = (59.403, 112.168)   # existing XTALI via-in-pad (kept)
XTALO_VIP = (59.14, 112.148)    # existing XTALO via-in-pad (kept)


def d(a, c):
    return math.hypot(a[0] - c[0], a[1] - c[1])


def mm(v):
    return (pcbnew.ToMM(v.x), pcbnew.ToMM(v.y))


def load_dru(path='haven_dev_board.kicad_dru'):
    """{net: {other: clearance_mm}} and {net: {other: hole_clearance_mm}} from
    the pair rules; also blanket single-net clearance rules (A.NetName=='X' || B.NetName=='X')."""
    clr, hole = {}, {}
    txt = open(path).read()
    for m in re.finditer(r"\(rule\s+\"[^\"]+\"\s*\(condition\s+\"([^\"]+)\"\)\s*\(constraint\s+(clearance|hole_clearance)\s+\(min\s+([\d.]+)mm\)\)", txt, re.S):
        cond, kind, val = m.group(1), m.group(2), float(m.group(3))
        nets = re.findall(r"NetName\s*==\s*'([^']*)'", cond)
        tgt = clr if kind == 'clearance' else hole
        if '||' in cond and '&&' not in cond and len(set(nets)) == 1:
            e = tgt.setdefault(nets[0], {}); e['*'] = min(e.get('*', 9), val)   # blanket for this net
        elif len(nets) >= 2:
            a, b_ = nets[0], nets[1]
            for x, y in ((a, b_), (b_, a)):
                tgt.setdefault(x, {}); tgt[x][y] = min(tgt[x].get(y, 9), val)
    return clr, hole


CLR_EXC, HOLE_EXC = load_dru()


def exc_for(net):
    e = dict(CLR_EXC.get(net, {}))
    e.pop('*', None)
    return e


def default_clr(net):
    return min(A.clearance, CLR_EXC.get(net, {}).get('*', 9)) if CLR_EXC.get(net, {}).get('*') else A.clearance


def hole_req(net, other):
    return HOLE_EXC.get(net, {}).get(other, HOLE_EXC.get(net, {}).get('*', HOLE_CLR_DEFAULT))


class Checker:
    """Copper / hole checks against the CURRENT board (rebuild after every add)."""
    def __init__(self, b, net, layer, x0, x1, y0, y1):
        self.b, self.net, self.layer = b, net, layer
        self.obs = rl.collect_obstacles_mixed(b, layer, net, x0, x1, y0, y1, exc_for(net), default_clr(net), pad=1.5)
        self.vias = [(mm(t.GetPosition()), pcbnew.ToMM(t.GetDrillValue()) / 2, t.GetNetname()) for t in b.GetTracks() if isinstance(t, pcbnew.PCB_VIA)]
        self.other = []   # (shape, layer, netname) of other-net copper for hole checks of NEW vias
        for fp in b.GetFootprints():
            for p in fp.Pads():
                if p.GetNetname() == net: continue
                q = mm(p.GetPosition())
                if x0 - 1.5 <= q[0] <= x1 + 1.5 and y0 - 1.5 <= q[1] <= y1 + 1.5:
                    for L in LAYERS.values():
                        if p.IsOnLayer(L): self.other.append((p.GetEffectiveShape(L), L, p.GetNetname()))
        for t in b.GetTracks():
            if t.GetNetname() == net: continue
            q = mm(t.GetPosition() if isinstance(t, pcbnew.PCB_VIA) else t.GetStart())
            q2 = q if isinstance(t, pcbnew.PCB_VIA) else mm(t.GetEnd())
            if max(q[0], q2[0]) < x0 - 1.5 or min(q[0], q2[0]) > x1 + 1.5 or max(q[1], q2[1]) < y0 - 1.5 or min(q[1], q2[1]) > y1 + 1.5: continue
            if isinstance(t, pcbnew.PCB_VIA):
                for L in LAYERS.values(): self.other.append((t.GetEffectiveShape(L), L, t.GetNetname()))
            else:
                self.other.append((t.GetEffectiveShape(t.GetLayer()), t.GetLayer(), t.GetNetname()))

    def seg_ok(self, p1, p2):
        if not rl.seg_clear_mixed(p1, p2, self.obs, half_w=HALF_W): return False
        # hole clearance: other-net drill holes vs this copper
        for (v, dr, vnet) in self.vias:
            if vnet == self.net: continue
            if dist_pt_seg(v, p1, p2) - dr - HALF_W < hole_req(self.net, vnet) - 1e-6: return False
        return True


def dist_pt_seg(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def via_ok(b, pt, net):
    """New 0.20/0.10 via of `net` at pt: copper clearance on every layer under the
    net's exceptions, hole-to-hole vs every via (real drills), and hole clearance
    (my hole vs their copper, their holes vs my annulus)."""
    exc = exc_for(net); dflt = default_clr(net)
    probe = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(pcbnew.FromMM(pt[0]), pcbnew.FromMM(pt[1])), pcbnew.FromMM(VIA_D / 2))
    hole = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(pcbnew.FromMM(pt[0]), pcbnew.FromMM(pt[1])), pcbnew.FromMM(VIA_DRILL / 2))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net: continue
            if d(mm(p.GetPosition()), pt) > 1.5: continue
            for L in LAYERS.values():
                if not p.IsOnLayer(L): continue
                sh = p.GetEffectiveShape(L)
                if sh.Collide(probe, pcbnew.FromMM(exc.get(p.GetNetname(), dflt))): return False, ('pad', fp.GetReference(), p.GetNumber())
                if sh.Collide(hole, pcbnew.FromMM(hole_req(net, p.GetNetname()))): return False, ('pad-hole', fp.GetReference(), p.GetNumber())
    for t in b.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            q = mm(t.GetPosition()); dr = pcbnew.ToMM(t.GetDrillValue()) / 2
            if d(q, pt) - dr - VIA_DRILL / 2 < HOLE2HOLE - 1e-6: return False, ('hole2hole', t.GetNetname(), q)
            if t.GetNetname() == net: continue
            if d(q, pt) > 1.5: continue
            for L in LAYERS.values():
                sh = t.GetEffectiveShape(L)
                if sh.Collide(probe, pcbnew.FromMM(exc.get(t.GetNetname(), dflt))): return False, ('via', t.GetNetname(), q)
            # their hole vs my annulus / my hole vs their annulus
            if d(q, pt) - dr - VIA_D / 2 < hole_req(net, t.GetNetname()) - 1e-6: return False, ('via-hole', t.GetNetname(), q)
        else:
            if t.GetNetname() == net: continue
            s, e = mm(t.GetStart()), mm(t.GetEnd())
            if dist_pt_seg(pt, s, e) > 1.5: continue
            sh = t.GetEffectiveShape(t.GetLayer())
            if sh.Collide(probe, pcbnew.FromMM(exc.get(t.GetNetname(), dflt))): return False, ('track', t.GetNetname(), s)
            if sh.Collide(hole, pcbnew.FromMM(hole_req(net, t.GetNetname()))): return False, ('track-hole', t.GetNetname(), s)
    for z in b.Zones():
        if z.GetIsRuleArea() and z.GetDoNotAllowVias():
            for L in LAYERS.values():
                if z.IsOnLayer(L) and z.Outline().Collide(probe, pcbnew.FromMM(dflt)): return False, ('keepout', z.GetZoneName())
    return True, None


def start_on_annulus(b, net, vip, layer, r=0.14):
    """A track has to *touch* the via-in-pad, not start at its centre: the TMS via is
    0.27-0.28 mm from both via-in-pads, so a start cap at the centre would sit
    inside default clearance of it. Pick the point on a circle of radius r around
    the via whose track start-cap is clear of everything on `layer`."""
    ck = Checker(b, net, layer, vip[0] - 1.0, vip[0] + 1.0, vip[1] - 1.0, vip[1] + 1.0)
    best = None
    for ang in range(0, 360, 10):
        a = math.radians(ang)
        pt = (round(vip[0] + r * math.cos(a), 3), round(vip[1] + r * math.sin(a), 3))
        if ck.seg_ok(pt, pt):
            # prefer the point that keeps the most distance from the nearest other-net via
            m = min((d(pt, v) - dr for (v, dr, vn) in ck.vias if vn != net), default=9)
            if best is None or m > best[0]: best = (m, pt)
    return best[1] if best else None


def route(b, net, layer, start, end, margin=1.2, cell=0.05, iters=300000):
    x0, x1 = min(start[0], end[0]) - margin, max(start[0], end[0]) + margin
    y0, y1 = min(start[1], end[1]) - margin, max(start[1], end[1]) + margin
    ck = Checker(b, net, layer, x0, x1, y0, y1)
    path, st = rl.astar_mixed(start, end, ck.obs, cell=cell, margin=margin, max_iters=iters, half_w=HALF_W)
    if path is None: return None, st
    path[0] = start; path[-1] = end
    simp = rl.simplify_mixed(path, ck.obs, half_w=HALF_W)
    simp[0] = start; simp[-1] = end
    for p1, p2 in zip(simp, simp[1:]):
        if not ck.seg_ok(p1, p2): return None, f'hole/clearance fail on {p1}->{p2}'
    return simp, 'ok'


def lay(b, net, layer_name, path):
    for p1, p2 in zip(path, path[1:]):
        if d(p1, p2) > 0.005: pl.add_seg(b, net, layer_name, p1, p2, W)


def add_via(b, net, pt):
    return pl.add_via(b, net, pt, VIA_D, VIA_DRILL)


def find_via_spot(b, net, near, toward, dists=(0.45, 0.55, 0.65, 0.75, 0.9), angs=(0, 20, -20, 40, -40, 60, -60, 80, -80, 100, -100)):
    base = math.atan2(toward[1] - near[1], toward[0] - near[0])
    for dist in dists:
        for ang in angs:
            a = base + math.radians(ang)
            pt = (round(near[0] + dist * math.cos(a), 3), round(near[1] + dist * math.sin(a), 3))
            ok, why = via_ok(b, pt, net)
            if ok: return pt
    return None


def pads_of(b, ref):
    fp = b.FindFootprintByReference(ref)
    return {p.GetNumber(): (p.GetNetname(), mm(p.GetPosition())) for p in fp.Pads()}


def strip_old(b):
    """Remove the previous crystal-group copper, keeping only the two via-in-pads
    (+ XTALI's F.Cu stub). One pass, removed after collection (pcbnew 9 quirk)."""
    victims = []
    for t in list(b.GetTracks()):
        n = t.GetNetname()
        if isinstance(t, pcbnew.PCB_VIA):
            q = mm(t.GetPosition())
            if n == 'XTALI' and d(q, XTALI_VIP) < 0.02: continue
            if n == 'XTALO' and d(q, XTALO_VIP) < 0.02: continue
            if n in ('XTALI', 'XTALO', '$1N16368'): victims.append(t)
            elif n == 'GND' and any(d(q, g) < 0.02 for g in [(62.716, 109.612), (63.241, 109.104), (61.672, 106.946), (64.544, 106.32)]): victims.append(t)
        else:
            s, e = mm(t.GetStart()), mm(t.GetEnd())
            if n == 'XTALI' and t.GetLayer() == pcbnew.F_Cu and (d(s, B7) < 0.02 or d(e, B7) < 0.02): continue  # ball -> via-in-pad stub
            if n in ('XTALI', 'XTALO', '$1N16368'): victims.append(t)
            elif n == 'GND' and t.GetLayer() == pcbnew.B_Cu and all(61.5 <= p[0] <= 64.7 and 106.1 <= p[1] <= 109.9 for p in (s, e)): victims.append(t)
    for t in victims: b.Remove(t)
    return len(victims)


# ---------------------------------------------------------------- main
if A.phase == 'strip':
    b = pcbnew.LoadBoard(A.board)
    n = strip_old(b)
    print(f'stripped {n} old crystal-group items')
    b.Save('/tmp/board_c_stripped.kicad_pcb')
    sys.exit(0)
b = pcbnew.LoadBoard('/tmp/board_c_stripped.kicad_pcb')

ax, ay = map(float, A.crystal_anchor.split(','))
# The pocket is a diagonal band between SDA1's and PDMDIN's slope-1 escapes
# (3.5 mm across); the 1.9 x 2.3 mm crystal only fits with its long axis along
# the band, i.e. at a 45-degree multiple. Rank spots by XTALI-pad-to-B7 distance.
raw, ncand = pl.find_spot(b, 'CRYSTAL1', 'B.Cu', (ax, ay), radius=0.9, step=0.05, rots=(0, 45, 90, 135, 180, 225, 270, 315), limit=2000)
cands = []
for dist, x, y, rot in raw:
    pl.move(b, 'CRYSTAL1', x, y, rot, 'B.Cu')
    P = pads_of(b, 'CRYSTAL1'); xi = [q for (nn, q) in P.values() if nn == 'XTALI'][0]
    cands.append((round(d(xi, B7), 3), x, y, rot))
cands.sort()
print(f'crystal candidates near ({ax},{ay}): {ncand}; best XTALI->B7 {cands[0][0] if cands else None} mm')

def try_candidate(cx, cy, rot):
    bb = pcbnew.LoadBoard('/tmp/board_c_stripped.kicad_pcb')
    pl.move(bb, 'CRYSTAL1', cx, cy, rot, 'B.Cu')
    P = pads_of(bb, 'CRYSTAL1')
    xi = [q for (nn, q) in P.values() if nn == 'XTALI'][0]
    x3 = [q for (nn, q) in P.values() if nn == '$1N16368'][0]
    gnds = [q for (nn, q) in P.values() if nn == 'GND']
    if d(xi, B7) > d(x3, B7): return None, 'XTALI pad not the nearer one'
    log = [f'CRYSTAL1 at ({cx},{cy}) rot {rot}: XTALI pad {xi} ({d(xi, B7):.2f} mm to B7), pad3 {x3}']
    xi_start = start_on_annulus(bb, 'XTALI', XTALI_VIP, IN); xo_start = start_on_annulus(bb, 'XTALO', XTALO_VIP, IN)
    if not xi_start or not xo_start: return None, f'no clear start on via annulus (XTALI {xi_start}, XTALO {xo_start})'
    log.append(f'  inner-layer starts: XTALI {xi_start}, XTALO {xo_start}')
    # --- XTALI: via-in-pad -> IN layer -> exit via near the XTALI pad -> B.Cu stub
    e1 = None
    for dist in (0.45, 0.55, 0.65, 0.75, 0.85):
        for ang in (0, 15, -15, 30, -30, 45, -45, 60, -60, 90, -90):
            base = math.atan2(B7[1] - xi[1], B7[0] - xi[0]) + math.radians(ang)
            pt = (round(xi[0] + dist * math.cos(base), 3), round(xi[1] + dist * math.sin(base), 3))
            if not via_ok(bb, pt, 'XTALI')[0]: continue
            pin, st = route(bb, 'XTALI', IN, xi_start, pt, margin=0.8)
            if pin is None: continue
            pb, st2 = route(bb, 'XTALI', pcbnew.B_Cu, pt, xi, margin=0.6)
            if pb is None: continue
            e1 = (pt, pin, pb); break
        if e1: break
    if not e1: return None, 'no XTALI exit'
    pt, pin, pb = e1
    lay(bb, 'XTALI', A.in_layer, pin); add_via(bb, 'XTALI', pt); lay(bb, 'XTALI', 'B.Cu', pb)
    log.append(f'  XTALI: {A.in_layer} {len(pin)-1} segs to exit via {pt}, B.Cu {len(pb)-1} segs; path len {sum(d(p,q) for p,q in zip(pin,pin[1:]))+sum(d(p,q) for p,q in zip(pb,pb[1:])):.2f} mm')
    # --- R28 near pad3, on B.Cu; then XTALO: via-in-pad -> IN -> exit via -> B.Cu stub -> R28.2 ; R28.1 -> pad3
    rraw, _ = pl.find_spot(bb, 'R28', 'B.Cu', x3, radius=1.5, step=0.05, rots=(0, 45, 90, 135, 180, 225, 270, 315), limit=3000)
    rc = []
    for _, rx, ry, rr in rraw:
        pl.move(bb, 'R28', rx, ry, rr, 'B.Cu'); R = pads_of(bb, 'R28')
        r1 = [q for (nn, q) in R.values() if nn == '$1N16368'][0]; r2 = [q for (nn, q) in R.values() if nn == 'XTALO'][0]
        if d(r1, x3) > 1.3: continue                     # R28.1 must stay close to the crystal pad
        rc.append((round(d(r2, B6) + 0.5 * d(r1, x3), 3), rx, ry, rr))   # rank: short XTALO leg, then short pad3 leg
    rc.sort(); rc = rc[:60]
    placed = False
    for _, rx, ry, rr in rc:
        snap = '/tmp/board_c_afterxtali.kicad_pcb'; bb.Save(snap); bb = pcbnew.LoadBoard(snap)
        pl.move(bb, 'R28', rx, ry, rr, 'B.Cu')
        R = pads_of(bb, 'R28'); r1 = [q for (nn, q) in R.values() if nn == '$1N16368'][0]; r2 = [q for (nn, q) in R.values() if nn == 'XTALO'][0]
        p13, st = route(bb, '$1N16368', pcbnew.B_Cu, r1, x3, margin=0.7)
        if p13 is None: continue
        lay(bb, '$1N16368', 'B.Cu', p13)
        e2 = None
        for dist in (0.45, 0.55, 0.65, 0.8, 0.95, 1.1):
            for ang in (0, 20, -20, 40, -40, 60, -60, 90, -90, 120, -120):
                base = math.atan2(B6[1] - r2[1], B6[0] - r2[0]) + math.radians(ang)
                pt2 = (round(r2[0] + dist * math.cos(base), 3), round(r2[1] + dist * math.sin(base), 3))
                if not via_ok(bb, pt2, 'XTALO')[0]: continue
                pin2, st = route(bb, 'XTALO', IN, xo_start, pt2, margin=0.8, iters=400000)
                if pin2 is None: continue
                pb2, st2 = route(bb, 'XTALO', pcbnew.B_Cu, pt2, r2, margin=0.6)
                if pb2 is None: continue
                e2 = (pt2, pin2, pb2); break
            if e2: break
        if not e2:
            bb = pcbnew.LoadBoard(snap); continue
        pt2, pin2, pb2 = e2
        lay(bb, 'XTALO', A.in_layer, pin2); add_via(bb, 'XTALO', pt2); lay(bb, 'XTALO', 'B.Cu', pb2)
        log.append(f'  R28 at ({rx},{ry}) rot {rr}; XTALO: {A.in_layer} {len(pin2)-1} segs to exit via {pt2}, B.Cu {len(pb2)-1} segs; R28.2->B6 {d(r2,B6):.2f} mm; path len {sum(d(p,q) for p,q in zip(pin2,pin2[1:]))+sum(d(p,q) for p,q in zip(pb2,pb2[1:]))+sum(d(p,q) for p,q in zip(p13,p13[1:])):.2f} mm')
        placed = True; break
    if not placed: return None, 'no R28/XTALO solution'
    # --- load caps: C46 (XTALI/GND) next to the XTALI pad, C45 ($1N16368/GND) next to pad3; each: rail route + GND via
    def place_cap(bb, ref, net, target_pad):
        snap = f'/tmp/board_c_before_{ref}.kicad_pcb'; bb.Save(snap); bb = pcbnew.LoadBoard(snap)
        craw, _ = pl.find_spot(bb, ref, 'B.Cu', target_pad, radius=1.6, step=0.05, rots=(0, 45, 90, 135, 180, 225, 270, 315), limit=4000)
        cc = []
        for _, x, y, rot in craw:
            pl.move(bb, ref, x, y, rot, 'B.Cu'); Pc = pads_of(bb, ref)
            rp = [q for (nn, q) in Pc.values() if nn == net][0]
            cc.append((round(d(rp, target_pad), 3), x, y, rot))
        cc.sort(); cc = cc[:80]
        for _, x, y, rot in cc:
            bb = pcbnew.LoadBoard(snap); pl.move(bb, ref, x, y, rot, 'B.Cu')
            Pc = pads_of(bb, ref); rp = [q for (nn, q) in Pc.values() if nn == net][0]; gp = [q for (nn, q) in Pc.values() if nn == 'GND'][0]
            pr, st = route(bb, net, pcbnew.B_Cu, target_pad, rp, margin=0.6)
            if pr is None: continue
            lay(bb, net, 'B.Cu', pr)
            gv = find_via_spot(bb, 'GND', gp, (2 * gp[0] - rp[0], 2 * gp[1] - rp[1]))
            if not gv: continue
            pg, st = route(bb, 'GND', pcbnew.B_Cu, gp, gv, margin=0.5)
            if pg is None: continue
            lay(bb, 'GND', 'B.Cu', pg); add_via(bb, 'GND', gv)
            log.append(f'  {ref} at ({x},{y}) rot {rot}: {net} pad {d(rp,target_pad):.2f} mm from crystal pad; GND via {gv}')
            return bb
        return None
    bb2 = place_cap(bb, 'C46', 'XTALI', xi)
    if bb2 is None: return None, 'C46 unplaceable'
    bb = bb2
    bb2 = place_cap(bb, 'C45', '$1N16368', x3)
    if bb2 is None: return None, 'C45 unplaceable'
    bb = bb2
    # --- crystal case/GND pads -> plane vias
    for g in gnds:
        gv = find_via_spot(bb, 'GND', g, (2 * g[0] - cx, 2 * g[1] - cy))
        if not gv: return None, f'no GND via for crystal pad {g}'
        pg, st = route(bb, 'GND', pcbnew.B_Cu, g, gv, margin=0.5)
        if pg is None: return None, f'no GND route for crystal pad {g}'
        lay(bb, 'GND', 'B.Cu', pg); add_via(bb, 'GND', gv); log.append(f'  crystal GND pad {g} -> via {gv}')
    return bb, '\n'.join(log)

def quality(bb):
    P = pads_of(bb, 'CRYSTAL1'); xi = [q for (nn, q) in P.values() if nn == 'XTALI'][0]; x3 = [q for (nn, q) in P.values() if nn == '$1N16368'][0]
    R = pads_of(bb, 'R28'); r2 = [q for (nn, q) in R.values() if nn == 'XTALO'][0]
    c46 = [q for (nn, q) in pads_of(bb, 'C46').values() if nn == 'XTALI'][0]; c45 = [q for (nn, q) in pads_of(bb, 'C45').values() if nn == '$1N16368'][0]
    return {'xtali_pad_to_B7': d(xi, B7), 'r28_to_B6': d(r2, B6), 'c46_to_pad': d(c46, xi), 'c45_to_pad': d(c45, x3)}

tried = 0; best = None
for dist, cx, cy, rot in cands[:A.max_cands]:
    tried += 1
    res, msg = try_candidate(cx, cy, rot)
    if res is None:
        if tried <= 15 or tried % 10 == 0: print(f'  cand {tried} ({cx},{cy},{rot}): {msg}', flush=True)
        continue
    q = quality(res); score = q['xtali_pad_to_B7'] + 0.5 * q['r28_to_B6'] + q['c46_to_pad'] + 0.5 * q['c45_to_pad']
    print(msg); print(f'  quality {q} score {score:.2f}', flush=True)
    snap = f'/tmp/board_c_solution_{tried}.kicad_pcb'; res.Save(snap)
    if best is None or score < best[0]: best = (score, snap, msg, q)
    if q['xtali_pad_to_B7'] <= 1.3 and q['r28_to_B6'] <= 3.0 and q['c46_to_pad'] <= 1.2 and q['c45_to_pad'] <= 1.5:
        print('meets targets -- stopping'); break
if best is None: print('NO SOLUTION'); sys.exit(1)
score, snap, msg, q = best
# Refill from the PROJECT directory: a board loaded from /tmp has no .kicad_pro/.kicad_dru
# alongside, and ZONE_FILLER then fills with different settings (islands lost, phantom
# dangling vias) -- see CODEX_NOTES.md and routing-evidence/crystal-escape/README.md.
shutil.copy(snap, A.board)
res = pcbnew.LoadBoard(A.board); rl.refill_zones(res); res.Save(A.board)
print(f'BEST (score {score:.2f}) after {tried} candidates:\n{msg}\n  quality {q}\nsaved')

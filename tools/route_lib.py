# Shared pathfinding helpers for hand-routing tight escapes on the Haven
# board, built up over the course of the routing sessions logged in
# CODEX_NOTES.md. Load from a script run via pcbnew's Python (e.g.
# `python3 -c "import sys; sys.path.insert(0,'../tools'); import route_lib
# as rl; ..."` from the kicad/ directory, or the reverse relative path if
# running from tools/ itself) -- always operate on the real
# haven_dev_board.kicad_pcb in place, or a copy inside kicad/ alongside the
# real .kicad_pro and footprints.pretty/ library, never a bare copy in /tmp
# (see CODEX_NOTES.md's entry on why that silently corrupts the project's
# design rules when the result gets saved back).
#
# Core pattern for any new net: sweep real escape depth at multiple
# clearances (collect_obstacles + seg_clear, not just a single point check)
# before assuming a pad is escapable or blocked; use find_route_on_layer for
# single-layer pathfinding, multilayer_route.py's multilayer_astar when a
# via hop is likely needed; use the *_mixed variants (collect_obstacles_mixed
# / astar_mixed / simplify_mixed) whenever relaxed clearance is needed
# against ONE specific neighbor net, not everything nearby -- a single
# global set_clearance() call relaxes clearance against every obstacle in
# range, which has caused real, DRC-caught mistakes when a route incidentally
# passed close to unrelated copper. Always verify the exact placed geometry
# with a real `kicad-cli pcb drc` diff before and after -- this project's
# rule is zero new violations per change, checked by type+description count,
# not assumed from the pathfinder's own "clear" result.
import pcbnew
import heapq
import math
import sys

CLEARANCE_MM = 0.20
TRACK_W_MM = 0.09
HALF_W = TRACK_W_MM / 2
CLEARANCE_IU = pcbnew.FromMM(CLEARANCE_MM)
VIA_LAYERS = [pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu]


def set_clearance(mm):
    """CLEARANCE_IU is derived, not the source of truth -- always go through
    this instead of assigning CLEARANCE_MM directly, or stale IU values will
    silently keep using whatever clearance was active at import time."""
    global CLEARANCE_MM, CLEARANCE_IU
    CLEARANCE_MM = mm
    CLEARANCE_IU = pcbnew.FromMM(mm)


def collect_obstacles(board, layer, net_name, xmin, xmax, ymin, ymax, pad=2.0):
    obstacles = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net_name:
                continue
            if not p.IsOnLayer(layer):
                continue
            pos = p.GetPosition()
            px, py = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
            if not (xmin - pad <= px <= xmax + pad and ymin - pad <= py <= ymax + pad):
                continue
            obstacles.append(p.GetEffectiveShape(layer))
    for t in board.GetTracks():
        if t.GetNetname() == net_name:
            continue
        if isinstance(t, pcbnew.PCB_VIA):
            if layer not in VIA_LAYERS or not t.IsOnLayer(layer):
                continue
            pos = t.GetPosition()
            px, py = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
            if not (xmin - pad <= px <= xmax + pad and ymin - pad <= py <= ymax + pad):
                continue
            obstacles.append(t.GetEffectiveShape(layer))
            continue
        if t.GetLayer() != layer:
            continue
        sx, sy = pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y)
        ex, ey = pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y)
        if max(sx, ex) < xmin - pad or min(sx, ex) > xmax + pad or max(sy, ey) < ymin - pad or min(sy, ey) > ymax + pad:
            continue
        obstacles.append(t.GetEffectiveShape(layer))
    for zone in board.Zones():
        if not zone.GetIsRuleArea():
            continue
        if not (zone.GetDoNotAllowTracks() or zone.GetDoNotAllowVias()):
            continue
        if not zone.IsOnLayer(layer):
            continue
        zbbox = zone.GetBoundingBox()
        zxmin, zxmax = pcbnew.ToMM(zbbox.GetLeft()), pcbnew.ToMM(zbbox.GetRight())
        zymin, zymax = pcbnew.ToMM(zbbox.GetTop()), pcbnew.ToMM(zbbox.GetBottom())
        if zxmax < xmin - pad or zxmin > xmax + pad or zymax < ymin - pad or zymin > ymax + pad:
            continue
        obstacles.append(zone.Outline())
    return obstacles


def make_blocked(obstacles, half_w=HALF_W):
    def blocked(x, y):
        probe = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)), pcbnew.FromMM(half_w))
        for shape in obstacles:
            if shape.Collide(probe, CLEARANCE_IU):
                return True
        return False
    return blocked


def astar(start, end, blocked, cell=0.1, margin=2.0, max_iters=400000, obstacles=None, half_w=HALF_W):
    """If `obstacles` is given, edges are validated by a full-segment
    collision check (seg_clear), not just a point check at the destination
    -- a point-only check can let a diagonal step clip a corner neither
    endpoint touches, which passes the search but fails re-verification."""
    xmin = min(start[0], end[0]) - margin
    xmax = max(start[0], end[0]) + margin
    ymin = min(start[1], end[1]) - margin
    ymax = max(start[1], end[1]) + margin
    nx = int((xmax - xmin) / cell) + 1
    ny = int((ymax - ymin) / cell) + 1

    def to_cell(pt):
        return (round((pt[0] - xmin) / cell), round((pt[1] - ymin) / cell))

    def to_coord(c):
        return (xmin + c[0] * cell, ymin + c[1] * cell)

    start_c = to_cell(start)
    end_c = to_cell(end)
    if blocked(*start):
        return None, 'start blocked'
    if blocked(*end):
        return None, 'end blocked'

    def heuristic(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def edge_ok(c1, c2):
        if obstacles is not None:
            return seg_clear(to_coord(c1), to_coord(c2), obstacles, half_w)
        return not blocked(*to_coord(c2))

    open_set = [(0, start_c)]
    came_from = {}
    gscore = {start_c: 0}
    visited = set()
    neighbors8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    found = False
    iters = 0
    while open_set:
        iters += 1
        if iters > max_iters:
            break
        _, current = heapq.heappop(open_set)
        if current in visited:
            continue
        visited.add(current)
        if current == end_c or heuristic(current, end_c) < 1.5:
            found = True
            end_c = current
            break
        for dx, dy in neighbors8:
            nb = (current[0] + dx, current[1] + dy)
            if not (0 <= nb[0] <= nx and 0 <= nb[1] <= ny):
                continue
            if nb in visited:
                continue
            if not edge_ok(current, nb):
                continue
            step = cell * (1.414 if dx and dy else 1.0)
            tentative = gscore[current] + step
            if nb not in gscore or tentative < gscore[nb]:
                gscore[nb] = tentative
                came_from[nb] = current
                heapq.heappush(open_set, (tentative + heuristic(nb, end_c), nb))

    if not found:
        return None, f'not found, visited={len(visited)}'
    path = [end_c]
    while path[-1] != start_c:
        path.append(came_from[path[-1]])
    path.reverse()
    return [to_coord(c) for c in path], 'ok'


def seg_clear(p1, p2, obstacles, half_w=HALF_W):
    x1, y1 = pcbnew.FromMM(p1[0]), pcbnew.FromMM(p1[1])
    x2, y2 = pcbnew.FromMM(p2[0]), pcbnew.FromMM(p2[1])
    seg = pcbnew.SHAPE_SEGMENT(pcbnew.VECTOR2I(x1, y1), pcbnew.VECTOR2I(x2, y2), pcbnew.FromMM(half_w * 2))
    for shape in obstacles:
        if shape.Collide(seg, CLEARANCE_IU):
            return False
    return True


def collect_obstacles_mixed(board, layer, net_name, xmin, xmax, ymin, ymax, exceptions, default_clearance_mm, pad=2.0):
    """Like collect_obstacles, but returns (shape, clearance_iu) pairs so
    specific other nets (e.g. an already-scoped .kicad_dru exception) can
    use a tighter clearance than everything else -- collect_obstacles'
    single global CLEARANCE_MM is too blunt once a route needs to stay at
    standard clearance from most things but relaxed from one specific
    neighbor net. `exceptions` is {net_name: clearance_mm}."""
    default_iu = pcbnew.FromMM(default_clearance_mm)
    exceptions_iu = {n: pcbnew.FromMM(c) for n, c in exceptions.items()}
    obstacles = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net_name:
                continue
            if not p.IsOnLayer(layer):
                continue
            pos = p.GetPosition()
            px, py = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
            if not (xmin - pad <= px <= xmax + pad and ymin - pad <= py <= ymax + pad):
                continue
            clr = exceptions_iu.get(p.GetNetname(), default_iu)
            obstacles.append((p.GetEffectiveShape(layer), clr))
    for t in board.GetTracks():
        if t.GetNetname() == net_name:
            continue
        if isinstance(t, pcbnew.PCB_VIA):
            if layer not in VIA_LAYERS or not t.IsOnLayer(layer):
                continue
            pos = t.GetPosition()
            px, py = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
            if not (xmin - pad <= px <= xmax + pad and ymin - pad <= py <= ymax + pad):
                continue
            clr = exceptions_iu.get(t.GetNetname(), default_iu)
            obstacles.append((t.GetEffectiveShape(layer), clr))
            continue
        if t.GetLayer() != layer:
            continue
        sx, sy = pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y)
        ex, ey = pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y)
        if max(sx, ex) < xmin - pad or min(sx, ex) > xmax + pad or max(sy, ey) < ymin - pad or min(sy, ey) > ymax + pad:
            continue
        clr = exceptions_iu.get(t.GetNetname(), default_iu)
        obstacles.append((t.GetEffectiveShape(layer), clr))
    for zone in board.Zones():
        if not zone.GetIsRuleArea():
            continue
        if not (zone.GetDoNotAllowTracks() or zone.GetDoNotAllowVias()):
            continue
        if not zone.IsOnLayer(layer):
            continue
        zbbox = zone.GetBoundingBox()
        zxmin, zxmax = pcbnew.ToMM(zbbox.GetLeft()), pcbnew.ToMM(zbbox.GetRight())
        zymin, zymax = pcbnew.ToMM(zbbox.GetTop()), pcbnew.ToMM(zbbox.GetBottom())
        if zxmax < xmin - pad or zxmin > xmax + pad or zymax < ymin - pad or zymin > ymax + pad:
            continue
        obstacles.append((zone.Outline(), default_iu))
    return obstacles


def seg_clear_mixed(p1, p2, obstacles_mixed, half_w=HALF_W):
    x1, y1 = pcbnew.FromMM(p1[0]), pcbnew.FromMM(p1[1])
    x2, y2 = pcbnew.FromMM(p2[0]), pcbnew.FromMM(p2[1])
    seg = pcbnew.SHAPE_SEGMENT(pcbnew.VECTOR2I(x1, y1), pcbnew.VECTOR2I(x2, y2), pcbnew.FromMM(half_w * 2))
    for shape, clr_iu in obstacles_mixed:
        if shape.Collide(seg, clr_iu):
            return False
    return True


def astar_mixed(start, end, obstacles_mixed, cell=0.1, margin=2.0, max_iters=400000, half_w=HALF_W):
    xmin = min(start[0], end[0]) - margin
    xmax = max(start[0], end[0]) + margin
    ymin = min(start[1], end[1]) - margin
    ymax = max(start[1], end[1]) + margin
    nx = int((xmax - xmin) / cell) + 1
    ny = int((ymax - ymin) / cell) + 1

    def to_cell(pt):
        return (round((pt[0] - xmin) / cell), round((pt[1] - ymin) / cell))

    def to_coord(c):
        return (xmin + c[0] * cell, ymin + c[1] * cell)

    def pt_clear(pt):
        probe = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(pcbnew.FromMM(pt[0]), pcbnew.FromMM(pt[1])), pcbnew.FromMM(half_w))
        for shape, clr_iu in obstacles_mixed:
            if shape.Collide(probe, clr_iu):
                return False
        return True

    start_c = to_cell(start)
    end_c = to_cell(end)
    if not pt_clear(start):
        return None, 'start blocked'
    if not pt_clear(end):
        return None, 'end blocked'

    def heuristic(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    open_set = [(0, start_c)]
    came_from = {}
    gscore = {start_c: 0}
    visited = set()
    neighbors8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    found = False
    iters = 0
    while open_set:
        iters += 1
        if iters > max_iters:
            break
        _, current = heapq.heappop(open_set)
        if current in visited:
            continue
        visited.add(current)
        if current == end_c or heuristic(current, end_c) < 1.5:
            found = True
            end_c = current
            break
        for dx, dy in neighbors8:
            nb = (current[0] + dx, current[1] + dy)
            if not (0 <= nb[0] <= nx and 0 <= nb[1] <= ny):
                continue
            if nb in visited:
                continue
            if not seg_clear_mixed(to_coord(current), to_coord(nb), obstacles_mixed, half_w):
                continue
            step = cell * (1.414 if dx and dy else 1.0)
            tentative = gscore[current] + step
            if nb not in gscore or tentative < gscore[nb]:
                gscore[nb] = tentative
                came_from[nb] = current
                heapq.heappush(open_set, (tentative + heuristic(nb, end_c), nb))

    if not found:
        return None, f'not found, visited={len(visited)}'
    path = [end_c]
    while path[-1] != start_c:
        path.append(came_from[path[-1]])
    path.reverse()
    return [to_coord(c) for c in path], 'ok'


def simplify_mixed(path, obstacles_mixed, half_w=HALF_W):
    simplified = [path[0]]
    i = 0
    n = len(path)
    while i < n - 1:
        j = n - 1
        while j > i + 1 and not seg_clear_mixed(simplified[-1], path[j], obstacles_mixed, half_w):
            j -= 1
        simplified.append(path[j])
        i = j
    return simplified


def simplify(path, obstacles, half_w=HALF_W):
    simplified = [path[0]]
    i = 0
    n = len(path)
    while i < n - 1:
        j = n - 1
        while j > i + 1 and not seg_clear(simplified[-1], path[j], obstacles, half_w):
            j -= 1
        simplified.append(path[j])
        i = j
    return simplified


def find_route_on_layer(board, layer, net_name, start, end, cell=0.1):
    xmin = min(start[0], end[0]) - 2
    xmax = max(start[0], end[0]) + 2
    ymin = min(start[1], end[1]) - 2
    ymax = max(start[1], end[1]) + 2
    obstacles = collect_obstacles(board, layer, net_name, xmin, xmax, ymin, ymax)
    blocked = make_blocked(obstacles)
    path, status = astar(start, end, blocked, cell=cell, obstacles=obstacles)
    if path is None:
        return None, status, obstacles
    simplified = simplify(path, obstacles)
    # verify
    for k in range(len(simplified) - 1):
        if not seg_clear(simplified[k], simplified[k + 1], obstacles):
            return None, 'simplify verify failed', obstacles
    return simplified, 'ok', obstacles


VIA_DRILL_R_MM = 0.05  # matches SetDrill(FromMM(0.10)) used everywhere a via is placed
MIN_HOLE_EDGE_MM = 0.1995  # this board's actual board-setup hole-to-hole constraint


def hole_to_hole_ok(board, pos, drill_r_mm=VIA_DRILL_R_MM, min_edge_mm=MIN_HOLE_EDGE_MM):
    """Mechanical drill-to-drill spacing against EVERY existing via,
    regardless of net -- via_clear() deliberately skips same-net copper
    (correct for electrical clearance: two same-net features touching is
    fine), but a drilled hole needs physical separation from every other
    hole on the board no matter whose net it's on. Confirmed missing the
    hard way: a new via placed 0.023mm from a pre-existing same-net via
    passed every check in this file, then failed real DRC with
    hole_to_hole (required ~0.1995mm edge-to-edge, actual 0.0000mm).
    Call this ALONGSIDE via_clear() before placing any new via -- neither
    one substitutes for the other."""
    for t in board.GetTracks():
        if not isinstance(t, pcbnew.PCB_VIA):
            continue
        vpos = pcbnew.ToMM(t.GetPosition())
        center_dist = math.hypot(vpos[0] - pos[0], vpos[1] - pos[1])
        if center_dist - 2 * drill_r_mm < min_edge_mm:
            return False
    return True


def via_clear(board, pos, net_name, via_r=0.10):
    for layer in VIA_LAYERS:
        probe = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(pcbnew.FromMM(pos[0]), pcbnew.FromMM(pos[1])), pcbnew.FromMM(via_r))
        for fp in board.GetFootprints():
            for p in fp.Pads():
                if p.GetNetname() == net_name:
                    continue
                if not p.IsOnLayer(layer):
                    continue
                if p.GetEffectiveShape(layer).Collide(probe, CLEARANCE_IU):
                    return False, (layer, 'PAD', fp.GetReference(), p.GetNumber())
        for t in board.GetTracks():
            if t.GetNetname() == net_name:
                continue
            if isinstance(t, pcbnew.PCB_VIA):
                if not t.IsOnLayer(layer):
                    continue
            elif t.GetLayer() != layer:
                continue
            if t.GetEffectiveShape(layer).Collide(probe, CLEARANCE_IU):
                return False, (layer, 'TRACK/VIA', t.GetNetname())
    return True, None


def find_clear_via_near(board, orig, net_name, via_r=0.10):
    """Finds a position that is BOTH electrically clear (via_clear, against
    other nets) AND mechanically clear (hole_to_hole_ok, against every
    existing via regardless of net) -- a candidate passing only the first
    check can still fail real DRC's hole-to-hole constraint."""
    def ok_at(pt):
        return via_clear(board, pt, net_name, via_r)[0] and hole_to_hole_ok(board, pt)
    if ok_at(orig):
        return orig
    for dist in [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5]:
        for ang_deg in range(0, 360, 10):
            ang = math.radians(ang_deg)
            cand = (orig[0] + dist * math.cos(ang), orig[1] + dist * math.sin(ang))
            if ok_at(cand):
                return cand
    return None


def refill_zones(board):
    """Recompute every zone's filled-copper polygons in-memory. MUST be
    called after adding any track/via and before board.Save() + the real
    DRC check whenever a fillable copper-pour zone (e.g. a GND/power plane
    on an inner layer) exists anywhere on the board -- confirmed on Haven's
    SDA route attempt: two of the four inner layers are near-full-board GND
    pours, and a new via always punches through every inner layer, so its
    clearance is only ever correct once the pour's fill polygon is
    regenerated around it. The stale fill (from before the new copper was
    added) is NOT a real placement obstacle -- checking a candidate via
    against it produces false "no via possible anywhere nearby" results
    (every direction/distance looks blocked, because the whole pour reads
    as one solid mass) even though a normal via there is completely
    routine once refilled. Do not add filled-zone polygons to
    collect_obstacles/via_clear's obstacle lists for this reason; refill
    instead, then let real DRC be the judge."""
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

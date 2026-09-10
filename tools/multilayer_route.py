import sys, os, math, heapq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import route_lib as rl
import pcbnew

LAYERS = [pcbnew.F_Cu, pcbnew.B_Cu]
ALL_VIA_LAYERS = [pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu]
VIA_PENALTY_MM = 0.4  # equivalent path-length cost per layer change, discourages via spam
VIA_R_MM = 0.10  # via radius for the standard 0.20mm/0.10mm via used throughout this board

def multilayer_astar(board, net, start, end, clearance_mm, cell=0.1, margin=2.0, max_iters=600000):
    rl.set_clearance(clearance_mm)
    xmin = min(start[0], end[0]) - margin
    xmax = max(start[0], end[0]) + margin
    ymin = min(start[1], end[1]) - margin
    ymax = max(start[1], end[1]) + margin

    obs_by_layer = {
        layer: rl.collect_obstacles(board, layer, net, xmin, xmax, ymin, ymax)
        for layer in LAYERS
    }
    # precompute ALL 6 layers' obstacles once -- a through-via spans every
    # layer, so checking via placement correctly needs all of them, but we
    # must not re-scan every footprint/track on every single node expansion
    via_obs_by_layer = {
        layer: (obs_by_layer[layer] if layer in obs_by_layer
                else rl.collect_obstacles(board, layer, net, xmin, xmax, ymin, ymax))
        for layer in ALL_VIA_LAYERS
    }

    def via_clear_fast(pt):
        probe = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(pcbnew.FromMM(pt[0]), pcbnew.FromMM(pt[1])), pcbnew.FromMM(VIA_R_MM))
        for layer in ALL_VIA_LAYERS:
            for shape in via_obs_by_layer[layer]:
                if shape.Collide(probe, rl.CLEARANCE_IU):
                    return False
        return True

    def to_cell(pt):
        return (round((pt[0]-xmin)/cell), round((pt[1]-ymin)/cell))
    def to_coord(c):
        return (xmin+c[0]*cell, ymin+c[1]*cell)

    nx = int((xmax-xmin)/cell)+1
    ny = int((ymax-ymin)/cell)+1

    start_c = to_cell(start)
    end_c = to_cell(end)

    # figure out which layer(s) start/end are usable on
    def usable_layers(pt):
        layers = []
        for li, layer in enumerate(LAYERS):
            obs = obs_by_layer[layer]
            if not rl.make_blocked(obs)(*pt):
                layers.append(li)
        return layers

    start_layers = usable_layers(start)
    end_layers = usable_layers(end)
    if not start_layers or not end_layers:
        return None, f'start_layers={start_layers} end_layers={end_layers}'

    def heuristic(state):
        x, y, li = state
        return math.hypot(to_coord((x,y))[0]-end[0], to_coord((x,y))[1]-end[1])

    starts = [(start_c[0], start_c[1], li) for li in start_layers]
    open_set = [(heuristic(s), s) for s in starts]
    heapq.heapify(open_set)
    gscore = {s: 0 for s in starts}
    came_from = {}
    visited = set()
    neighbors8 = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]

    found_end = None
    iters = 0
    while open_set:
        iters += 1
        if iters > max_iters:
            break
        _, current = heapq.heappop(open_set)
        if current in visited:
            continue
        visited.add(current)
        cx, cy, cli = current
        if (cx, cy) == end_c and cli in end_layers:
            found_end = current
            break
        coord = to_coord((cx, cy))
        obs = obs_by_layer[LAYERS[cli]]
        blocked_fn = rl.make_blocked(obs)
        # same-layer moves
        for dx, dy in neighbors8:
            nb = (cx+dx, cy+dy, cli)
            if not (0 <= nb[0] <= nx and 0 <= nb[1] <= ny):
                continue
            if nb in visited:
                continue
            ncoord = to_coord((nb[0], nb[1]))
            if not rl.seg_clear(coord, ncoord, obs):
                continue
            step = cell * (1.414 if dx and dy else 1.0)
            tentative = gscore[current] + step
            if nb not in gscore or tentative < gscore[nb]:
                gscore[nb] = tentative
                came_from[nb] = current
                heapq.heappush(open_set, (tentative + heuristic(nb), nb))
        # layer-change (via) at this exact point
        for other_li in range(len(LAYERS)):
            if other_li == cli:
                continue
            nb = (cx, cy, other_li)
            if nb in visited:
                continue
            if not via_clear_fast(coord):
                continue
            tentative = gscore[current] + VIA_PENALTY_MM
            if nb not in gscore or tentative < gscore[nb]:
                gscore[nb] = tentative
                came_from[nb] = current
                heapq.heappush(open_set, (tentative + heuristic(nb), nb))

    if found_end is None:
        return None, f'not found, visited={len(visited)}'

    path_states = [found_end]
    while path_states[-1] in came_from:
        path_states.append(came_from[path_states[-1]])
    path_states.reverse()

    # convert to list of (x,y,layer_index) with coords
    out = []
    for (cx, cy, li) in path_states:
        out.append({'pt': to_coord((cx,cy)), 'layer': li})
    return out, 'ok'


def multilayer_astar_mixed(board, net, start, end, exceptions, default_clearance_mm, cell=0.1, margin=2.0, max_iters=600000):
    """Like multilayer_astar, but each obstacle can require a different
    clearance (exceptions = {other_net_name: clearance_mm}, everything
    else at default_clearance_mm) -- needed for bus members that must run
    tight to each other (e.g. 0.05mm apart) while keeping standard
    clearance from unrelated copper. See route_lib.collect_obstacles_mixed
    for why a single global clearance value isn't enough here."""
    xmin = min(start[0], end[0]) - margin
    xmax = max(start[0], end[0]) + margin
    ymin = min(start[1], end[1]) - margin
    ymax = max(start[1], end[1]) + margin

    obs_by_layer = {
        layer: rl.collect_obstacles_mixed(board, layer, net, xmin, xmax, ymin, ymax, exceptions, default_clearance_mm)
        for layer in LAYERS
    }
    via_obs_by_layer = {
        layer: (obs_by_layer[layer] if layer in obs_by_layer
                else rl.collect_obstacles_mixed(board, layer, net, xmin, xmax, ymin, ymax, exceptions, default_clearance_mm))
        for layer in ALL_VIA_LAYERS
    }

    def via_clear_mixed_fast(pt):
        probe = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(pcbnew.FromMM(pt[0]), pcbnew.FromMM(pt[1])), pcbnew.FromMM(VIA_R_MM))
        for layer in ALL_VIA_LAYERS:
            for shape, clr_iu in via_obs_by_layer[layer]:
                if shape.Collide(probe, clr_iu):
                    return False
        return True

    def to_cell(pt):
        return (round((pt[0]-xmin)/cell), round((pt[1]-ymin)/cell))
    def to_coord(c):
        return (xmin+c[0]*cell, ymin+c[1]*cell)

    nx = int((xmax-xmin)/cell)+1
    ny = int((ymax-ymin)/cell)+1

    start_c = to_cell(start)
    end_c = to_cell(end)

    def pt_clear_mixed(pt, obs):
        probe = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(pcbnew.FromMM(pt[0]), pcbnew.FromMM(pt[1])), pcbnew.FromMM(rl.HALF_W))
        for shape, clr_iu in obs:
            if shape.Collide(probe, clr_iu):
                return False
        return True

    def usable_layers(pt):
        return [li for li, layer in enumerate(LAYERS) if pt_clear_mixed(pt, obs_by_layer[layer])]

    start_layers = usable_layers(start)
    end_layers = usable_layers(end)
    if not start_layers or not end_layers:
        return None, f'start_layers={start_layers} end_layers={end_layers}'

    def heuristic(state):
        x, y, li = state
        return math.hypot(to_coord((x,y))[0]-end[0], to_coord((x,y))[1]-end[1])

    starts = [(start_c[0], start_c[1], li) for li in start_layers]
    open_set = [(heuristic(s), s) for s in starts]
    heapq.heapify(open_set)
    gscore = {s: 0 for s in starts}
    came_from = {}
    visited = set()
    neighbors8 = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]

    found_end = None
    iters = 0
    while open_set:
        iters += 1
        if iters > max_iters:
            break
        _, current = heapq.heappop(open_set)
        if current in visited:
            continue
        visited.add(current)
        cx, cy, cli = current
        if (cx, cy) == end_c and cli in end_layers:
            found_end = current
            break
        coord = to_coord((cx, cy))
        obs = obs_by_layer[LAYERS[cli]]
        for dx, dy in neighbors8:
            nb = (cx+dx, cy+dy, cli)
            if not (0 <= nb[0] <= nx and 0 <= nb[1] <= ny):
                continue
            if nb in visited:
                continue
            ncoord = to_coord((nb[0], nb[1]))
            if not rl.seg_clear_mixed(coord, ncoord, obs):
                continue
            step = cell * (1.414 if dx and dy else 1.0)
            tentative = gscore[current] + step
            if nb not in gscore or tentative < gscore[nb]:
                gscore[nb] = tentative
                came_from[nb] = current
                heapq.heappush(open_set, (tentative + heuristic(nb), nb))
        for other_li in range(len(LAYERS)):
            if other_li == cli:
                continue
            nb = (cx, cy, other_li)
            if nb in visited:
                continue
            if not via_clear_mixed_fast(coord):
                continue
            tentative = gscore[current] + VIA_PENALTY_MM
            if nb not in gscore or tentative < gscore[nb]:
                gscore[nb] = tentative
                came_from[nb] = current
                heapq.heappush(open_set, (tentative + heuristic(nb), nb))

    if found_end is None:
        return None, f'not found, visited={len(visited)}'

    path_states = [found_end]
    while path_states[-1] in came_from:
        path_states.append(came_from[path_states[-1]])
    path_states.reverse()

    out = []
    for (cx, cy, li) in path_states:
        out.append({'pt': to_coord((cx,cy)), 'layer': li})
    return out, 'ok'

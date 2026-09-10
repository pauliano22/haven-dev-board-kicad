# Bus-aware router: plans several nets that share one tight escape
# corridor TOGETHER instead of one at a time.
#
# Why this exists: routing a group of related signals (e.g. a JTAG bus,
# or several pins escaping the same corner of a BGA) net-by-net works
# right up until the *last* net finds the one viable lane already
# occupied by an earlier one -- confirmed this exact failure mode on
# Haven's TCK/TDI/TDO/TMS group (see CODEX_NOTES.md): TCK's own placed
# trace ran straight through the only 0.2-0.4mm gap all four signals
# needed, and no amount of retrying TDI/TDO/TMS individually could work
# around copper that was already there.
#
# The fix (first version, here) is the first half of standard autorouter
# practice: route hardest-first (the pin with the least local room goes
# first, since it has the fewest alternatives), and have each net see
# every already-placed member of the group as a real obstacle -- this
# falls out for free, since collect_obstacles only excludes a track's own
# net. If a later net still fails despite going in a sensible order, this
# version reports that failure rather than automatically ripping up and
# retrying an earlier member -- that's the natural next step if ordering
# alone isn't enough, not yet implemented.
#
# Usage (from kicad/, with tools/ one level up):
#   import sys; sys.path.insert(0, '../tools')
#   import route_lib as rl
#   import multilayer_route as mr
#   import bus_router as br
#   import pcbnew
#   board = pcbnew.LoadBoard('haven_dev_board.kicad_pcb')
#   members = [
#       {'net': 'TCK', 'start': (58.7904, 112.4979), 'end': (78.4102, 53.0977)},
#       {'net': 'TDI', 'start': (59.8404, 112.4979), 'end': (76.0102, 53.0977)},
#       ...
#   ]
#   results = br.route_bus(board, members, clearance_mm=0.15)
#   # results[net] = {'status': 'ok'|'failed', 'placed': [...]} -- inspect,
#   # verify with a real kicad-cli pcb drc diff, THEN board.Save(...).
#
# Every placement this makes is added to the in-memory `board` object
# immediately (not just returned), so later members in the same call see
# earlier ones as obstacles. Nothing is saved to disk -- call board.Save()
# yourself after inspecting the results and running a real DRC diff, per
# this project's standing rule (never trust a pathfinder's "found" result
# as proof the geometry is correct).

import sys
import os
import math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import route_lib as rl
import multilayer_route as mr
import pcbnew


def _pad_layer(board, pos, tol=0.05):
    """Best-effort: which real copper layer (F_Cu or B_Cu) actually has a
    pad at this XY. Used to auto-detect the right layer for a start/end
    point instead of trusting whichever layer the pathfinder happens to
    consider 'not blocked' there (empty board is not blocked either, and
    landing on the wrong layer's empty space has been a real, repeated
    bug this session)."""
    for fp in board.GetFootprints():
        for p in fp.Pads():
            pp = p.GetPosition()
            if abs(pcbnew.ToMM(pp.x) - pos[0]) < tol and abs(pcbnew.ToMM(pp.y) - pos[1]) < tol:
                if p.IsOnLayer(pcbnew.F_Cu):
                    return pcbnew.F_Cu
                if p.IsOnLayer(pcbnew.B_Cu):
                    return pcbnew.B_Cu
    return None


def escape_difficulty(board, net, pos, layer, exceptions=None, clearance_mm=0.20, probe_dist=1.0):
    """Lower score = harder = route first. Counts how many of 24 evenly
    spaced directions are clear at probe_dist from pos, using mixed
    clearance if exceptions is given."""
    exceptions = exceptions or {}
    if exceptions:
        obs = rl.collect_obstacles_mixed(board, layer, net, pos[0] - 2, pos[0] + 2, pos[1] - 2, pos[1] + 2, exceptions, clearance_mm)
        clear_fn = lambda p1, p2: rl.seg_clear_mixed(p1, p2, obs)
    else:
        rl.set_clearance(clearance_mm)
        obs = rl.collect_obstacles(board, layer, net, pos[0] - 2, pos[0] + 2, pos[1] - 2, pos[1] + 2)
        clear_fn = lambda p1, p2: rl.seg_clear(p1, p2, obs)
    count = 0
    for ang_deg in range(0, 360, 15):
        ang = math.radians(ang_deg)
        end = (pos[0] + probe_dist * math.cos(ang), pos[1] + probe_dist * math.sin(ang))
        if clear_fn(pos, end):
            count += 1
    return count


def _route_one(board, net, start, end, clearance_mm, exceptions, max_iters):
    """Try single-layer both ways, then multi-layer. Returns
    (segments, status) where segments is a list of (layer_index, points)
    using LAYERS=[F_Cu, B_Cu], or (None, reason) on failure. Does not
    place anything."""
    exceptions = exceptions or {}
    start_layer = _pad_layer(board, start) or pcbnew.F_Cu
    end_layer = _pad_layer(board, end) or pcbnew.F_Cu

    if exceptions:
        # Single-layer mixed attempt on either layer first (fast, and
        # correct even when start/end are on different real layers --
        # same reasoning as the non-exceptions case below: a single-layer
        # search only cares about that layer's own geometry, and
        # _fix_endpoint_layers corrects whichever end lands "wrong" after).
        for layer, li in [(pcbnew.F_Cu, 0), (pcbnew.B_Cu, 1)]:
            obs = rl.collect_obstacles_mixed(board, layer, net, min(start[0], end[0]) - 2, max(start[0], end[0]) + 2,
                                              min(start[1], end[1]) - 2, max(start[1], end[1]) + 2, exceptions, clearance_mm)
            path, status = rl.astar_mixed(start, end, obs)
            if status == 'ok':
                simp = rl.simplify_mixed(path, obs)
                return [(li, simp)], 'ok'
        result, status = mr.multilayer_astar_mixed(board, net, start, end, exceptions, clearance_mm, max_iters=max_iters)
        if status != 'ok':
            return None, status
        segments = []
        cur_layer = result[0]['layer']
        cur_pts = [result[0]['pt']]
        for s in result[1:]:
            if s['layer'] == cur_layer:
                cur_pts.append(s['pt'])
            else:
                segments.append((cur_layer, cur_pts))
                cur_layer = s['layer']
                cur_pts = [s['pt']]
        segments.append((cur_layer, cur_pts))
        LAYERS = [pcbnew.F_Cu, pcbnew.B_Cu]
        simplified = []
        for li, pts in segments:
            layer = LAYERS[li]
            obs = rl.collect_obstacles_mixed(board, layer, net, min(p[0] for p in pts) - 1, max(p[0] for p in pts) + 1,
                                              min(p[1] for p in pts) - 1, max(p[1] for p in pts) + 1, exceptions, clearance_mm)
            simplified.append((li, rl.simplify_mixed(pts, obs)))
        return simplified, 'ok'

    rl.set_clearance(clearance_mm)
    # Try single-layer on F.Cu and B.Cu even when start/end are on
    # different real layers -- a single-layer search only cares whether
    # the coordinate is geometrically free on that layer, so it can find
    # a real path whose far end just happens to need a via to reach the
    # true (different-layer) pad. This is faster than the general
    # multi-layer search and is exactly how TCK routed successfully by
    # hand earlier this session; _fix_endpoint_layers corrects whichever
    # end lands on the "wrong" layer afterward.
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        path, status, obs = rl.find_route_on_layer(board, layer, net, start, end)
        if status == 'ok':
            li = 0 if layer == pcbnew.F_Cu else 1
            return [(li, path)], 'ok'

    result, status = mr.multilayer_astar(board, net, start, end, clearance_mm=clearance_mm, max_iters=max_iters)
    if status != 'ok':
        return None, status
    segments = []
    cur_layer = result[0]['layer']
    cur_pts = [result[0]['pt']]
    for s in result[1:]:
        if s['layer'] == cur_layer:
            cur_pts.append(s['pt'])
        else:
            segments.append((cur_layer, cur_pts))
            cur_layer = s['layer']
            cur_pts = [s['pt']]
    segments.append((cur_layer, cur_pts))
    LAYERS = [pcbnew.F_Cu, pcbnew.B_Cu]
    simplified = []
    for li, pts in segments:
        layer = LAYERS[li]
        obs = rl.collect_obstacles(board, layer, net, min(p[0] for p in pts) - 1, max(p[0] for p in pts) + 1,
                                    min(p[1] for p in pts) - 1, max(p[1] for p in pts) + 1)
        simplified.append((li, rl.simplify(pts, obs)))
    return simplified, 'ok'


def _fix_endpoint_layers(board, net, segments, start, end, clearance_mm, exceptions):
    """Segments from _route_one may land on the wrong layer at either end
    (empty board space at the pad's XY instead of the real copper) -- the
    single most common mistake made by hand this session. Detect it and
    build a via + a real, separately-verified connecting jog track to the
    real pad layer wherever it happens.

    Returns (fix, 'ok') or (None, reason). `fix` is a dict:
      start_ok / end_ok : True if that end's segment already lands on the
          real pad layer, so _place should just overwrite that endpoint
          with the exact start/end coordinate (no jog needed).
      jogs  : list of (p1, p2, layer) tracks to add when NOT start_ok/end_ok
      vias  : list of via positions to add for those jogs
    A jog is a REAL, separate track -- never fold it into overwriting the
    original segment's endpoint, since that segment is on the WRONG layer
    for the true start/end and overwriting its coordinate there would
    silently disconnect it from the via."""
    LAYERS = [pcbnew.F_Cu, pcbnew.B_Cu]
    jogs = []
    vias = []
    rl.set_clearance(clearance_mm)

    real_start_layer = _pad_layer(board, start)
    layer_ok_start = real_start_layer is None or LAYERS[segments[0][0]] == real_start_layer
    start_ok = layer_ok_start
    if layer_ok_start and real_start_layer is not None and list(start) != list(segments[0][1][0]):
        # Same layer, but the pathfinder's early-exit-within-1.5mm behavior
        # (see CODEX_NOTES.md) means its reported endpoint can still be off
        # by a fraction of a mm -- verify the real connecting segment
        # instead of assuming coincidence-in-name means coincidence-in-fact.
        near_pt = segments[0][1][0]
        obs = rl.collect_obstacles(board, real_start_layer, net, min(start[0], near_pt[0]) - 1, max(start[0], near_pt[0]) + 1,
                                    min(start[1], near_pt[1]) - 1, max(start[1], near_pt[1]) + 1)
        if not rl.seg_clear(start, near_pt, obs):
            return None, 'start same-layer connector blocked'
        start_ok = False
        jogs.append((start, near_pt, real_start_layer))
    if not layer_ok_start:
        via_pt = segments[0][1][0]
        ok, _ = rl.via_clear(board, via_pt, net)
        obs = rl.collect_obstacles(board, real_start_layer, net, min(start[0], via_pt[0]) - 1, max(start[0], via_pt[0]) + 1,
                                    min(start[1], via_pt[1]) - 1, max(start[1], via_pt[1]) + 1)
        if not (ok and rl.seg_clear(start, via_pt, obs)):
            return None, 'start-layer fix jog blocked'
        jogs.append((start, via_pt, real_start_layer))
        vias.append(via_pt)

    real_end_layer = _pad_layer(board, end)
    layer_ok_end = real_end_layer is None or LAYERS[segments[-1][0]] == real_end_layer
    end_ok = layer_ok_end
    if layer_ok_end and real_end_layer is not None and list(end) != list(segments[-1][1][-1]):
        near_pt = segments[-1][1][-1]
        obs = rl.collect_obstacles(board, real_end_layer, net, min(end[0], near_pt[0]) - 1, max(end[0], near_pt[0]) + 1,
                                    min(end[1], near_pt[1]) - 1, max(end[1], near_pt[1]) + 1)
        if not rl.seg_clear(near_pt, end, obs):
            return None, 'end same-layer connector blocked'
        end_ok = False
        jogs.append((near_pt, end, real_end_layer))
    if not layer_ok_end:
        via_pt = segments[-1][1][-1]
        ok, _ = rl.via_clear(board, via_pt, net)
        obs = rl.collect_obstacles(board, real_end_layer, net, min(end[0], via_pt[0]) - 1, max(end[0], via_pt[0]) + 1,
                                    min(end[1], via_pt[1]) - 1, max(end[1], via_pt[1]) + 1)
        if not (ok and rl.seg_clear(via_pt, end, obs)):
            return None, 'end-layer fix jog blocked'
        jogs.append((via_pt, end, real_end_layer))
        vias.append(via_pt)

    return {'start_ok': start_ok, 'end_ok': end_ok, 'jogs': jogs, 'vias': vias}, 'ok'


def _place(board, net_obj, segments, start, end, fix, width_mm):
    """Actually add the tracks/vias to the board object (in-memory)."""
    LAYERS = [pcbnew.F_Cu, pcbnew.B_Cu]
    segments = [(li, list(pts)) for li, pts in segments]
    if fix['start_ok']:
        segments[0][1][0] = list(start)
    if fix['end_ok']:
        segments[-1][1][-1] = list(end)

    def add_track(p1, p2, layer):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(p1[0]), pcbnew.FromMM(p1[1])))
        t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(p2[0]), pcbnew.FromMM(p2[1])))
        t.SetWidth(pcbnew.FromMM(width_mm))
        t.SetLayer(layer)
        t.SetNet(net_obj)
        board.Add(t)

    def add_via(pos):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(pos[0]), pcbnew.FromMM(pos[1])))
        v.SetWidth(pcbnew.FromMM(0.20))
        v.SetDrill(pcbnew.FromMM(0.10))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(net_obj)
        board.Add(v)

    for li, pts in segments:
        layer = LAYERS[li]
        for i in range(len(pts) - 1):
            add_track(pts[i], pts[i + 1], layer)
    for i in range(len(segments) - 1):
        add_via(segments[i][1][-1])
    for p1, p2, layer in fix['jogs']:
        add_track(p1, p2, layer)
    for pos in fix['vias']:
        add_via(pos)


def route_bus(board, members, clearance_mm=0.20, width_mm=0.09, max_iters=150000, verbose=True, mutual_clearance_mm=None):
    """members: list of {'net', 'start', 'end', optional 'exceptions'}.
    Routes hardest-first, each member added to `board` in-memory as soon
    as it succeeds so later members see it as a real obstacle. Returns
    {net_name: {'status': 'ok'|reason, 'segments': [...] or None}}.
    Caller is responsible for ZONE_FILLER + Save + a real DRC diff.

    mutual_clearance_mm: if set, every member's exceptions dict is
    extended (not overridden) to require only this clearance against
    every OTHER member of the group -- standard practice for a real bus,
    where sibling traces routinely run tighter to each other than to
    unrelated copper. Without this, ordering alone only helps when the
    shared corridor is wide enough for one member at a time; with it,
    several can occupy the same corridor side by side if there's
    physically enough width at the tighter spacing."""
    all_nets = [m['net'] for m in members]
    scored = []
    for m in members:
        exceptions = dict(m.get('exceptions', {}))
        if mutual_clearance_mm is not None:
            for other in all_nets:
                if other != m['net']:
                    exceptions.setdefault(other, mutual_clearance_mm)
        m = dict(m)
        m['exceptions'] = exceptions
        start_layer = _pad_layer(board, m['start']) or pcbnew.F_Cu
        score = escape_difficulty(board, m['net'], m['start'], start_layer, exceptions, clearance_mm)
        scored.append((score, m))
    scored.sort(key=lambda x: x[0])

    if verbose:
        print('routing order (hardest first):', [(m['net'], s) for s, m in scored])

    results = {}
    for score, m in scored:
        net = m['net']
        exceptions = m.get('exceptions', {})
        segments, status = _route_one(board, net, m['start'], m['end'], clearance_mm, exceptions, max_iters)
        if status != 'ok':
            if verbose:
                print(f'{net}: FAILED ({status})')
            results[net] = {'status': status, 'segments': None}
            continue
        fix, fix_status = _fix_endpoint_layers(board, net, segments, m['start'], m['end'], clearance_mm, exceptions)
        if fix_status != 'ok':
            if verbose:
                print(f'{net}: FAILED at endpoint-layer fix ({fix_status})')
            results[net] = {'status': fix_status, 'segments': None}
            continue
        net_obj = board.FindNet(net)
        _place(board, net_obj, segments, m['start'], m['end'], fix, width_mm)
        if verbose:
            print(f'{net}: placed ({len(segments)} layer segment(s), {len(fix["vias"])} extra via(s))')
        results[net] = {'status': 'ok', 'segments': segments}
    return results

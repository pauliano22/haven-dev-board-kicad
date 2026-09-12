"""Footprint-relocation helpers built on route_lib's collision primitives.
Run with KiCad's bundled python from the kicad/ project directory (see
CODEX_NOTES.md on why the board must be loaded from the real project dir)."""
import math, pcbnew
import route_lib as rl

def layer_id(name):
    return {'F.Cu': pcbnew.F_Cu, 'B.Cu': pcbnew.B_Cu}[name]

def other_copper(board, layer, exclude_refs=(), exclude_nets=()):
    """(shape, netname) for every pad on `layer`, every track on `layer`
    and every via (all layers), excluding given footprints/nets."""
    out = []
    for fp in board.GetFootprints():
        if fp.GetReference() in exclude_refs:
            continue
        for p in fp.Pads():
            if p.IsOnLayer(layer):
                out.append((p.GetEffectiveShape(layer), p.GetNetname(), 'pad', fp.GetReference()))
    for t in board.GetTracks():
        if t.GetNetname() in exclude_nets:
            continue
        if isinstance(t, pcbnew.PCB_VIA):
            out.append((t.GetEffectiveShape(layer), t.GetNetname(), 'via', ''))
        elif t.GetLayer() == layer:
            out.append((t.GetEffectiveShape(layer), t.GetNetname(), 'seg', ''))
    return out

def fp_collisions(board, fp, layer, obstacles, clearance_mm=0.20, courtyard_mm=0.15):
    """Collisions of `fp` (at its current position) against `obstacles`:
    each pad vs everything at `clearance_mm`, plus the footprint's pad bbox
    grown by courtyard_mm vs other footprints' pads (parts must not overlap)."""
    hits = []
    clr = pcbnew.FromMM(clearance_mm)
    pads = list(fp.Pads())
    for p in pads:
        shp = p.GetEffectiveShape(layer)
        for shape, net, kind, ref in obstacles:
            if kind != 'pad' and net == p.GetNetname():
                continue  # same-net copper touching a pad is fine
            if shp.Collide(shape, clr):
                hits.append((p.GetNumber(), kind, ref, net))
    bb = fp.GetBoundingBox(False, False)
    grow = pcbnew.FromMM(courtyard_mm)
    rect = pcbnew.SHAPE_RECT(pcbnew.VECTOR2I(bb.GetLeft() - grow, bb.GetTop() - grow), bb.GetWidth() + 2 * grow, bb.GetHeight() + 2 * grow)
    for shape, net, kind, ref in obstacles:
        if kind == 'pad' and rect.Collide(shape, 0):
            hits.append(('body', 'pad', ref, net))
    return hits

def find_spot(board, ref, layer_name, anchor, radius=3.0, step=0.1, rots=(0, 90, 180, 270), exclude_refs=(), exclude_nets=(), limit=8):
    layer = layer_id(layer_name)
    fp = board.FindFootprintByReference(ref)
    orig_pos, orig_rot, orig_layer = fp.GetPosition(), fp.GetOrientationDegrees(), fp.GetLayerName()
    # Test the candidate on the layer it will actually be placed on: move() flips
    # the footprint when the layer changes, which mirrors the pad positions, so a
    # collision check done un-flipped evaluates a different geometry than the
    # final placement (caught by DRC: a pad landed 0.193 mm from a via that the
    # un-flipped check had cleared).
    if orig_layer != layer_name:
        fp.Flip(fp.GetPosition(), False)
    obstacles = other_copper(board, layer, exclude_refs=set(exclude_refs) | {ref}, exclude_nets=set(exclude_nets))
    edge = board.GetBoardEdgesBoundingBox()
    cands = []
    n = int(radius / step)
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            d = math.hypot(i * step, j * step)
            if d > radius:
                continue
            x, y = anchor[0] + i * step, anchor[1] + j * step
            for rot in rots:
                fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
                fp.SetOrientationDegrees(rot)
                bb = fp.GetBoundingBox(False, False)
                if bb.GetLeft() < edge.GetLeft() + pcbnew.FromMM(0.5) or bb.GetRight() > edge.GetRight() - pcbnew.FromMM(0.5) or bb.GetTop() < edge.GetTop() + pcbnew.FromMM(0.5) or bb.GetBottom() > edge.GetBottom() - pcbnew.FromMM(0.5):
                    continue
                if not fp_collisions(board, fp, layer, obstacles):
                    cands.append((round(d, 3), round(x, 3), round(y, 3), rot))
    if fp.GetLayerName() != orig_layer:
        fp.Flip(fp.GetPosition(), False)
    fp.SetPosition(orig_pos); fp.SetOrientationDegrees(orig_rot)
    cands.sort()
    return cands[:limit], len(cands)

def move(board, ref, x, y, rot, layer_name):
    fp = board.FindFootprintByReference(ref)
    if fp.GetLayerName() != layer_name:
        fp.Flip(fp.GetPosition(), False)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    fp.SetOrientationDegrees(rot)
    return fp

def pad_center(board, ref, num):
    fp = board.FindFootprintByReference(ref)
    p = fp.FindPadByNumber(num)
    pos = p.GetPosition()
    return (pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y))

def add_seg(board, net, layer_name, p1, p2, width_mm):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(p1[0]), pcbnew.FromMM(p1[1])))
    t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(p2[0]), pcbnew.FromMM(p2[1])))
    t.SetWidth(pcbnew.FromMM(width_mm)); t.SetLayer(layer_id(layer_name)); t.SetNet(board.FindNet(net))
    board.Add(t); return t

def add_via(board, net, pos, size_mm=0.30, drill_mm=0.15):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(pos[0]), pcbnew.FromMM(pos[1])))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetWidth(pcbnew.FromMM(size_mm)); v.SetDrill(pcbnew.FromMM(drill_mm)); v.SetNet(board.FindNet(net))
    board.Add(v); return v

def remove_net_copper(board, nets, keep_uuids=()):
    """Delete every segment/via whose net is in `nets`, except uuids whose
    prefix is in keep_uuids. Gathers victims in ONE pass and removes them
    afterwards; call this LAST in a script -- pcbnew 9's GetTracks() has been
    seen returning an unwrapped SWIG object once items were removed mid-loop."""
    victims = []
    for t in list(board.GetTracks()):
        if t.GetNetname() not in nets:
            continue
        u = str(t.m_Uuid.AsString())
        if any(u.startswith(k) for k in keep_uuids):
            continue
        victims.append(t)
    for t in victims:
        board.Remove(t)
    return len(victims)

def seg_ok(board, net, layer_name, p1, p2, width_mm, clearance_mm=0.20, exceptions=None):
    layer = layer_id(layer_name)
    xmin, xmax = min(p1[0], p2[0]), max(p1[0], p2[0]); ymin, ymax = min(p1[1], p2[1]), max(p1[1], p2[1])
    obs = rl.collect_obstacles_mixed(board, layer, net, xmin, xmax, ymin, ymax, exceptions or {}, clearance_mm)
    return rl.seg_clear_mixed(p1, p2, obs, half_w=width_mm / 2)

def via_ok(board, net, pos, via_r_mm=0.15, clearance_mm=0.20):
    rl.set_clearance(clearance_mm)
    ok, why = rl.via_clear(board, pos, net, via_r=via_r_mm)
    return ok and rl.hole_to_hole_ok(board, pos, drill_r_mm=0.075), why

def _near(a, b, tol=0.02):
    return math.hypot(a[0]-b[0], a[1]-b[1]) <= tol

def plan_dangling_chain(board, net, start_pt, tracks, pads_by_net, max_steps=20):
    """Return the list of `net` segments forming an unbranched dead-end chain
    starting at `start_pt` (an old pad centre with no pad any more). Pure
    query -- pass one `tracks` snapshot (list(board.GetTracks())) and remove
    all planned victims together afterwards, then Save()+LoadBoard() before
    touching the board again (pcbnew 9 GetTracks() breaks after Remove)."""
    pt = tuple(start_pt); victims = []
    for _ in range(max_steps):
        here = [t for t in tracks if t not in victims and t.GetNetname() == net and not isinstance(t, pcbnew.PCB_VIA)
                and (_near(pcbnew.ToMM(t.GetStart()), pt) or _near(pcbnew.ToMM(t.GetEnd()), pt))]
        vias_here = [t for t in tracks if t.GetNetname() == net and isinstance(t, pcbnew.PCB_VIA) and _near(pcbnew.ToMM(t.GetPosition()), pt)]
        pads_here = [p for p in pads_by_net.get(net, []) if _near(p, pt, 0.3)]
        if vias_here or pads_here or len(here) != 1:
            break
        seg = here[0]
        s, e = pcbnew.ToMM(seg.GetStart()), pcbnew.ToMM(seg.GetEnd())
        pt = e if _near(s, pt) else s
        victims.append(seg)
    return victims

def pads_by_net(board):
    d = {}
    for fp in board.GetFootprints():
        for p in fp.Pads():
            d.setdefault(p.GetNetname(), []).append(pcbnew.ToMM(p.GetPosition()))
    return d

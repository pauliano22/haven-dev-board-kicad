"""Relocate a two-terminal part (decoupling cap / inductor) next to the IC it
serves and re-route both pads, DRC-clean by construction:
  * candidate spots from placement_lib.find_spot around the IC pins the part's
    nets land on (closest first, both outer layers unless --layer given);
  * each pad is routed with multilayer_astar_mixed (0.20 mm, board's per-pair
    exceptions optional) to the nearest same-net anchor: an IC pad of that net
    or an existing via/track endpoint of that net within --reach mm; the pad
    end is forced onto the part's own layer so no copper dangles on the wrong
    side;
  * a GND pad instead gets its own 0.20/0.10 via into the planes;
  * routes are laid as they are found; on any failure the board is reloaded
    from --start and the next spot is tried.
Old copper that used to reach the part's previous position is NOT touched here
-- run tools/clean_dangling.sh on the old position afterwards (it only deletes
track_dangling items that are new relative to the previous DRC report).
Run from kicad/ with KiCad's python:
  python3 ../tools/move_two_terminal.py --ref C33 --ic U15 --start /tmp/x.kicad_pcb
"""
import sys, math, time, shutil, argparse; sys.path.insert(0,'../tools')
import pcbnew, placement_lib as pl, route_lib as rl, multilayer_route as mr
ap=argparse.ArgumentParser()
ap.add_argument('--ref',required=True); ap.add_argument('--ic',required=True); ap.add_argument('--start',required=True)
ap.add_argument('--out',default='haven_dev_board.kicad_pcb'); ap.add_argument('--layer',default=None)
ap.add_argument('--radius',type=float,default=3.0); ap.add_argument('--reach',type=float,default=4.0)
ap.add_argument('--budget',type=float,default=420); ap.add_argument('--max-cands',type=int,default=60); ap.add_argument('--verbose',action='store_true'); ap.add_argument('--clearance',type=float,default=0.215,help='routing clearance; a hair over the 0.20 rule absorbs 0.1 mm grid + simplification rounding')
A=ap.parse_args()
LAYNAME={0:'F.Cu',1:'B.Cu'}; W=0.09
import re as _re
def load_dru_exceptions(path='haven_dev_board.kicad_dru'):
    """{net: {other_net: min_clearance_mm}} from every `clearance (min X)` rule
    whose condition is the usual (A.NetName == 'X' && B.NetName == 'Y') pair --
    i.e. route new copper under exactly the exceptions the board already grants,
    never looser. hole_clearance / hole_to_hole rules are ignored here (no new
    vias are placed inside those escape fields)."""
    exc={}
    try: txt=open(path).read()
    except FileNotFoundError: return exc
    for m in _re.finditer(r"\(rule\s+\"[^\"]+\"\s*\(condition\s+\"([^\"]+)\"\)\s*\(constraint\s+clearance\s+\(min\s+([\d.]+)mm\)\)", txt, _re.S):
        cond,val=m.group(1),float(m.group(2))
        nets=_re.findall(r"NetName\s*==\s*'([^']*)'",cond)
        if len(nets)>=2:
            a,b_=nets[0],nets[1]
            exc.setdefault(a,{}); exc.setdefault(b_,{})
            exc[a][b_]=min(exc[a].get(b_,9),val); exc[b_][a]=min(exc[b_].get(a,9),val)
    return exc
EXC_BY_NET=load_dru_exceptions()
def EXCF(net): return EXC_BY_NET.get(net,{})
def d(a,c): return math.hypot(a[0]-c[0],a[1]-c[1])
mr.VIA_PENALTY_MM=1.5   # discourage via hops: a decoupling route should stay on one layer where it can
MIN_VIA_SPACING=0.45    # two of the path's own vias closer than this would fail hole_to_hole (0.1995 mm edge + 2*0.05 drill)
def route_ml(b,net,a,c,end_layer,margin=1.5,iters=150000):
    path,st=mr.multilayer_astar_mixed(b,net,a,c,EXCF(net),A.clearance,cell=0.1,margin=margin,max_iters=iters)
    if st!='ok' or path[-1]['layer']!=end_layer: return None
    vias=[p0['pt'] for p0,p1 in zip(path,path[1:]) if p0['layer']!=p1['layer']]
    for u,v in zip(vias,vias[1:]):
        if d(u,v)<MIN_VIA_SPACING: return None   # the A* only checks new vias against pre-existing holes, not against each other
    for u in vias:
        if not hole_ok_real(b,u): return None
    return path
def simplify_ml(b,net,path):
    out=[]; i=0
    while i<len(path):
        j=i
        while j+1<len(path) and path[j+1]['layer']==path[i]['layer']: j+=1
        run=path[i:j+1]; layer=[pcbnew.F_Cu,pcbnew.B_Cu][run[0]['layer']]
        xs=[q['pt'][0] for q in run]; ys=[q['pt'][1] for q in run]
        obs=rl.collect_obstacles_mixed(b,layer,net,min(xs),max(xs),min(ys),max(ys),EXCF(net),A.clearance)
        k=0; keep=[run[0]]
        while k<len(run)-1:
            m=len(run)-1
            while m>k+1 and not rl.seg_clear_mixed(run[k]['pt'],run[m]['pt'],obs): m-=1
            keep.append(run[m]); k=m
        out.extend(keep); i=j+1
    return out
def lay_ml(b,net,path):
    path=simplify_ml(b,net,path)
    for p0,p1 in zip(path,path[1:]):
        if p0['layer']!=p1['layer']: pl.add_via(b,net,p0['pt'],0.20,0.10)
        elif d(p0['pt'],p1['pt'])>0.01: pl.add_seg(b,net,LAYNAME[p0['layer']],p0['pt'],p1['pt'],W)
def anchors(b,net,near,reach):
    """same-net targets sorted by distance, each as (point, required_start_layer):
    IC pads (their own layer -- U2 is a B.Cu part, so a route to its pad must
    start on B.Cu; the first stage-F attempt laid F.Cu copper from a B.Cu pad
    and connected nothing), through-vias (either layer), outer-layer track ends."""
    out=[]
    for p in b.FindFootprintByReference(A.ic).Pads():
        if p.GetNetname()==net:
            q=pcbnew.ToMM(p.GetPosition()); pl_=0 if p.IsOnLayer(pcbnew.F_Cu) else 1
            out.append((d(q,near),0,(q,pl_)))
    for t in b.GetTracks():
        if t.GetNetname()!=net: continue
        if isinstance(t,pcbnew.PCB_VIA):
            q=pcbnew.ToMM(t.GetPosition()); dd=d(q,near)
            if dd<reach: out.append((dd,1,(q,None)))
        else:
            if t.GetLayer() not in (pcbnew.F_Cu,pcbnew.B_Cu):
                # inner-layer run of this net: sample it -- a NEW through-via
                # stitched onto it is a legal attachment point away from the
                # BGA escape field (where pads and escape vias are hemmed in)
                sp=pcbnew.ToMM(t.GetStart()); ep=pcbnew.ToMM(t.GetEnd()); L=d(sp,ep); n=max(1,int(L/0.3))
                bb=b.FindFootprintByReference(A.ic).GetBoundingBox(False,False); m=pcbnew.FromMM(0.6)
                for k in range(n+1):
                    q=(sp[0]+(ep[0]-sp[0])*k/n, sp[1]+(ep[1]-sp[1])*k/n); dd=d(q,near)
                    qi=pcbnew.VECTOR2I(pcbnew.FromMM(q[0]),pcbnew.FromMM(q[1]))
                    if bb.GetLeft()-m<=qi.x<=bb.GetRight()+m and bb.GetTop()-m<=qi.y<=bb.GetBottom()+m: continue  # under/next to the BGA: no room for a via
                    if 0.6<dd<reach: out.append((dd+0.5,3,(q,'stitch')))   # slight penalty vs direct anchors
                continue
            tl=0 if t.GetLayer()==pcbnew.F_Cu else 1
            for q in (pcbnew.ToMM(t.GetStart()),pcbnew.ToMM(t.GetEnd())):
                dd=d(q,near)
                if dd<reach: out.append((dd,2,(q,tl)))
    out.sort(); return [x for _,_,x in out]
def hole_ok_real(b,pos,drill_mm=0.10,min_edge=0.1995+0.01):
    """hole-to-hole against every existing via using its REAL drill (route_lib's
    hole_to_hole_ok assumes 0.10 mm everywhere; the board also has 0.15 mm drills,
    which produced a 0.1806 mm DRC miss in stage D's first attempt)"""
    for t in b.GetTracks():
        if isinstance(t,pcbnew.PCB_VIA):
            q=pcbnew.ToMM(t.GetPosition()); dr=pcbnew.ToMM(t.GetDrillValue())/2.0
            if d(q,pos)-dr-drill_mm/2.0<min_edge: return False
    return True
def gnd_via(b,padpt,away,lay_idx):
    dx,dy=padpt[0]-away[0],padpt[1]-away[1]; base=math.atan2(dy,dx)
    for dist in (0.45,0.6,0.75,0.9,1.1,1.3):
        for ang in (0,30,-30,60,-60,90,-90,120,-120):
            a=base+math.radians(ang); cand=(round(padpt[0]+math.cos(a)*dist,3),round(padpt[1]+math.sin(a)*dist,3))
            v=rl.find_clear_via_near(b,cand,'GND',via_r=0.10)
            if not v or not hole_ok_real(b,v): continue
            r=route_ml(b,'GND',v,padpt,lay_idx,margin=1.0,iters=40000)   # via end free, pad end on the part's layer
            if r: return v,r
    return None,None
b0=pcbnew.LoadBoard(A.start); part=b0.FindFootprintByReference(A.ref)
pads=[(p.GetNumber(),p.GetNetname()) for p in part.Pads()]
assert len(pads)==2, pads
ic_pads={}
for p in b0.FindFootprintByReference(A.ic).Pads(): ic_pads.setdefault(p.GetNetname(),[]).append(pcbnew.ToMM(p.GetPosition()))
rail_nets=[n for _,n in pads if n!='GND']
tgt_pts=[q for n in rail_nets for q in ic_pads.get(n,[])]
assert tgt_pts, f'{A.ic} has no pad on {rail_nets}'
anchor=(sum(q[0] for q in tgt_pts)/len(tgt_pts), sum(q[1] for q in tgt_pts)/len(tgt_pts))
layers=[A.layer] if A.layer else ['B.Cu','F.Cu']
cands=[]
for L in layers:
    c,_=pl.find_spot(b0,A.ref,L,anchor,radius=A.radius,step=0.2,rots=(0,90,180,270),limit=A.max_cands)
    cands+=[(dist,x,y,rot,L) for dist,x,y,rot in c]
cands.sort(); print(f'{A.ref}: dru exceptions for {rail_nets}: {[EXCF(n) for n in rail_nets]}'); print(f'{A.ref}: {len(cands)} candidate spots around {A.ic} pads {rail_nets} anchor {tuple(round(v,2) for v in anchor)}'); del b0
t0=time.time(); ok=False
for i,(dist,cx,cy,rot,L) in enumerate(cands):
    if time.time()-t0>A.budget: print('budget exhausted at',i); break
    shutil.copy(A.start,A.out); b=pcbnew.LoadBoard(A.out); pl.move(b,A.ref,cx,cy,rot,L); li=0 if L=='F.Cu' else 1
    pre_vias={str(t.m_Uuid.AsString())[:8] for t in b.GetTracks() if isinstance(t,pcbnew.PCB_VIA)}
    good=True
    for num,net in pads:
        pp=pl.pad_center(b,A.ref,num)
        if net=='GND':
            other=pl.pad_center(b,A.ref,[n for n,_ in pads if n!=num][0])
            v,r=gnd_via(b,pp,other,li)
            if not v:
                if A.verbose: print(f'  cand {i} ({cx},{cy},{rot},{L}): GND via/route failed for pad {num}')
                good=False; break
            pl.add_via(b,'GND',v,0.20,0.10); lay_ml(b,'GND',r)
        else:
            routed=False
            tried=[]
            for tgt,start_layer in anchors(b,net,pp,A.reach)[:30]:
                if start_layer=='stitch':
                    rl.set_clearance(A.clearance)
                    okc,why=rl.via_clear(b,tgt,net,via_r=0.10)
                    if not okc or not hole_ok_real(b,tgt): tried.append(('stitch',tuple(round(v,2) for v in tgt),'via blocked',str(why)[:40])); continue
                    r=route_ml(b,net,tgt,pp,li,margin=1.5,iters=120000)
                    if not r: tried.append(('stitch',tuple(round(v,2) for v in tgt),'no route')); continue
                    pl.add_via(b,net,tgt,0.20,0.10); lay_ml(b,net,r); routed=True; break
                r=route_ml(b,net,tgt,pp,li,margin=1.5,iters=120000)
                if r and start_layer is not None and r[0]['layer']!=start_layer: tried.append((start_layer,tuple(round(v,2) for v in tgt),'wrong start layer')); r=None
                elif not r: tried.append((start_layer,tuple(round(v,2) for v in tgt),'no route'))
                if r: lay_ml(b,net,r); routed=True; break
            if not routed and A.verbose: print(f'  cand {i} ({cx},{cy},{rot},{L}): {net} pad {num} unrouted; tried {tried}')
            if not routed: good=False; break
    if not good: continue
    # re-verify every via this candidate added against the FINAL board (part placed,
    # all routes laid): electrical clearance on every layer + real hole spacing
    rl.set_clearance(A.clearance); bad=False
    for t in list(b.GetTracks()):
        if isinstance(t,pcbnew.PCB_VIA) and str(t.m_Uuid.AsString())[:8] not in pre_vias:
            q=pcbnew.ToMM(t.GetPosition())
            okc,_=rl.via_clear(b,q,t.GetNetname(),via_r=0.10)
            if not okc: bad=True; break
    if bad: print(f'cand {i}: a new via fails final clearance re-check'); continue
    q=pcbnew.ToMM(b.FindFootprintByReference(A.ref).GetPosition())
    print(f'SOLUTION cand {i}: {A.ref} -> ({q[0]:.3f},{q[1]:.3f}) rot {rot} {L}; dist to anchor {dist:.2f} mm; {time.time()-t0:.0f}s')
    rl.refill_zones(b); b.Save(A.out); ok=True; break
if not ok: shutil.copy(A.start,A.out); print('NO SOLUTION -- board restored'); sys.exit(1)

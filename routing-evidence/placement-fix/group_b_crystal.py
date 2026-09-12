"""Group B: CRYSTAL1 (24.576 MHz) + C45/C46 (33 pF) + R28 (220 R in series on
XTALO) moved from 8-21 mm away to the free B.Cu pocket just north-east of U15,
next to the two escape vias kept from the original routing
(XTALI via (60.0,108.5); XTALO via (59.84,110.05)).

Why the first attempt failed: the XTALO escape hugs a TDO track at ~0.11 mm,
which the board's .kicad_dru allows through per-pair exceptions
(tight_clearance_XTALO_vs_TDO 0.05 mm, _vs_V_LS 0.05, _vs_SDA1 0.05,
_vs_XTALI 0.03; tight_clearance_TDO_vs_XTALI 0.015). A plain 0.20 mm A*
therefore saw the via's own start point as blocked. This version routes with
multilayer_astar_mixed using exactly those exceptions, lays each route the
moment it is found (so later routes see it), and reloads the start board on
any failure before trying the next crystal spot. GND pads get their own
through-vias into the GND planes (as group A did). Run from kicad/ with
KiCad's python; START must be the group-A board with the stale crystal copper
stripped (what the previous session saved as /tmp/board_b_stripped2)."""
import sys, math, time, shutil; sys.path.insert(0,'../tools')
import pcbnew, placement_lib as pl, route_lib as rl, multilayer_route as mr
START='/tmp/board_b_work_start.kicad_pcb'; OUT='haven_dev_board.kicad_pcb'
LAYNAME={0:'F.Cu',1:'B.Cu'}; LAY='B.Cu'; W=0.09
XTALI_VIA=(60.0,108.5); XTALO_VIA=(59.8404,110.0479)
EXC={'XTALO':{'TDO':0.05,'V_LS':0.05,'SDA1':0.05,'XTALI':0.03,'':0.05},
     'XTALI':{'TDO':0.015,'XTALO':0.03},
     '$1N16368':{}, 'GND':{}}
def d(a,c): return math.hypot(a[0]-c[0],a[1]-c[1])
def route(b,net,a,c,margin=1.5,iters=120000):
    """single-layer B.Cu route (every group-B part lives on B.Cu; no vias wanted)
    with the board's per-pair clearance exceptions; returns a point list or None"""
    xs=(a[0],c[0]); ys=(a[1],c[1])
    obs=rl.collect_obstacles_mixed(b,pcbnew.B_Cu,net,min(xs),max(xs),min(ys),max(ys),EXC.get(net,{}),0.20)
    path,st=rl.astar_mixed(a,c,obs,cell=0.1,margin=margin,max_iters=iters)
    if st!='ok': return None
    path=rl.simplify_mixed(path,obs)
    if d(path[-1],c)>0.01: path.append(c)   # astar_mixed stops within 1.5 cells of the goal
    if d(path[0],a)>0.01: path.insert(0,a)
    return path
def lay(b,net,path):
    for p0,p1 in zip(path,path[1:]):
        if d(p0,p1)>0.01: pl.add_seg(b,net,LAY,p0,p1,W)

def route_ml(b,net,a,c,margin=1.5,iters=150000):
    """XTALI/XTALO only: their escape vias sit in a B.Cu pocket walled off by
    TDO/SDA1/DOUT diagonals, so the hop east must go over TDO on F.Cu and drop
    back to B.Cu with one new via. The via start may be used on either layer
    (through-via); the SMD pad end must be reached on B.Cu."""
    path,st=mr.multilayer_astar_mixed(b,net,a,c,EXC.get(net,{}),0.20,cell=0.1,margin=margin,max_iters=iters)
    if st!='ok' or path[-1]['layer']!=1: return None
    return path
def simplify_ml(b,net,path):
    out=[]; i=0
    while i<len(path):
        j=i
        while j+1<len(path) and path[j+1]['layer']==path[i]['layer']: j+=1
        run=path[i:j+1]; layer=[pcbnew.F_Cu,pcbnew.B_Cu][run[0]['layer']]
        xs=[q['pt'][0] for q in run]; ys=[q['pt'][1] for q in run]
        obs=rl.collect_obstacles_mixed(b,layer,net,min(xs),max(xs),min(ys),max(ys),EXC.get(net,{}),0.20)
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
def P(b,ref,num): return pl.pad_center(b,ref,num)
def gnd_via(b,padpt,away):
    dx,dy=padpt[0]-away[0],padpt[1]-away[1]; base=math.atan2(dy,dx)
    for dist in (0.45,0.6,0.75,0.9,1.1):
        for ang in (0,30,-30,60,-60,90,-90):
            a=base+math.radians(ang); cand=(round(padpt[0]+math.cos(a)*dist,3),round(padpt[1]+math.sin(a)*dist,3))
            v=rl.find_clear_via_near(b,cand,'GND',via_r=0.10)
            if not v: continue
            r=route(b,'GND',padpt,v,margin=1.0,iters=40000)
            if r: return v,r
    return None,None
def place_cap(b,ref,net,netpad,gndpad,padpt,ccen):
    tgt=(padpt[0]+(padpt[0]-ccen[0])*1.4, padpt[1]+(padpt[1]-ccen[1])*1.4)
    cc,_=pl.find_spot(b,ref,LAY,tgt,radius=1.6,step=0.2,rots=(0,90,180,270),limit=40)
    for _,x,y,rot in cc:
        pl.move(b,ref,x,y,rot,LAY); rp=P(b,ref,netpad); gp=P(b,ref,gndpad)
        r=route(b,net,padpt,rp,margin=1.0,iters=60000)
        if not r: continue
        lay(b,net,r)
        v,gr=gnd_via(b,gp,rp)
        if not v: return False
        pl.add_via(b,'GND',v,0.20,0.10); lay(b,'GND',gr); return True
    return False
b0=pcbnew.LoadBoard(START)
cands,_=pl.find_spot(b0,'CRYSTAL1',LAY,(61.9,108.6),radius=2.2,step=0.2,rots=(0,90,180,270),limit=400)
print('crystal candidates',len(cands)); del b0
t_start=time.time(); success=False
for i,(dist,cx,cy,rot) in enumerate(cands):
    if time.time()-t_start>480: print('time budget exhausted at candidate',i); break
    shutil.copy(START,OUT); b=pcbnew.LoadBoard(OUT)
    pl.move(b,'CRYSTAL1',cx,cy,rot,LAY)
    p_xi=P(b,'CRYSTAL1','1'); p_x3=P(b,'CRYSTAL1','3'); g2=P(b,'CRYSTAL1','2'); g4=P(b,'CRYSTAL1','4'); ccen=(cx,cy)
    r=route_ml(b,'XTALI',XTALI_VIA,p_xi)
    if not r: continue
    lay_ml(b,'XTALI',r)
    rc,_=pl.find_spot(b,'R28',LAY,((XTALO_VIA[0]+p_x3[0])/2,(XTALO_VIA[1]+p_x3[1])/2),radius=1.6,step=0.2,rots=(0,90,180,270),limit=12)
    ok=False
    for _,rx,ry,rrot in rc:
        pl.move(b,'R28',rx,ry,rrot,LAY); r1=P(b,'R28','1'); r2=P(b,'R28','2')
        a=route_ml(b,'XTALO',XTALO_VIA,r2)
        if not a: continue
        c=route(b,'$1N16368',r1,p_x3,margin=1.0,iters=60000)
        if not c: continue
        lay_ml(b,'XTALO',a); lay(b,'$1N16368',c); ok=True; break
    if not ok: print(f'cand {i} {(cx,cy,rot)}: XTALI ok, R28/XTALO failed'); continue
    if not place_cap(b,'C46','XTALI','2','1',p_xi,ccen): print(f'cand {i}: C46 failed'); continue
    if not place_cap(b,'C45','$1N16368','1','2',p_x3,ccen): print(f'cand {i}: C45 failed'); continue
    v2,r2g=gnd_via(b,g2,ccen); v4,r4g=gnd_via(b,g4,ccen)
    if not (v2 and v4): print(f'cand {i}: crystal GND vias failed'); continue
    pl.add_via(b,'GND',v2,0.20,0.10); lay(b,'GND',r2g); pl.add_via(b,'GND',v4,0.20,0.10); lay(b,'GND',r4g)
    for ref in ('CRYSTAL1','R28','C45','C46'):
        f=b.FindFootprintByReference(ref); q=pcbnew.ToMM(f.GetPosition()); print(f'{ref} -> ({q[0]:.3f},{q[1]:.3f}) rot {f.GetOrientationDegrees()} {f.GetLayerName()}')
    rl.refill_zones(b); b.Save(OUT); success=True
    import subprocess
    # GND pad stubs left behind at CRYSTAL1's and C46's old positions (text-level delete, then refill)
    subprocess.run([sys.executable.replace('Frameworks/Python.framework/Versions/Current/bin/python3','') and '/usr/bin/python3','../tools/remove_items_by_uuid.py',OUT,'d7fd5439','fff4e726'],check=False)
    b=pcbnew.LoadBoard(OUT); rl.refill_zones(b); b.Save(OUT)
    print(f'SOLUTION at candidate {i} after {time.time()-t_start:.0f}s'); break
if not success:
    shutil.copy(START,OUT); print('NO SOLUTION -- board restored to start state'); sys.exit(1)

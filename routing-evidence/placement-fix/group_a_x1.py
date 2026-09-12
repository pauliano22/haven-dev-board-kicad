"""Group A: move X1 (32.768 kHz) + C2/C14 (9 pF) from ~30 mm away to directly
behind MDBT531 pins 34/36 on B.Cu, reusing the two existing F.Cu pin stubs +
through-vias at the module edge. Run from kicad/ with KiCad's python.
Order: place -> route (with route_lib checks) -> delete stale copper -> refill -> save."""
import sys; sys.path.insert(0,'../tools')
import pcbnew, placement_lib as pl, route_lib as rl
b=pcbnew.LoadBoard('haven_dev_board.kicad_pcb')
VIA1=(85.820,70.601); VIA2=(85.796,71.529)   # existing XL1 / XL2 through-vias (kept)
X1=(87.10,70.90); pl.move(b,'X1',X1[0],X1[1],0,'B.Cu')
p1=pl.pad_center(b,'X1','1'); p2=pl.pad_center(b,'X1','2'); print('X1 pads XL1',p1,'XL2',p2)
pl.move(b,'C14',88.40,p1[1],0,'B.Cu'); pl.move(b,'C2',88.40,p2[1],0,'B.Cu')
c14r=pl.pad_center(b,'C14','2'); c14g=pl.pad_center(b,'C14','1'); c2r=pl.pad_center(b,'C2','2'); c2g=pl.pad_center(b,'C2','1')
print('C14 rail/gnd',c14r,c14g,' C2 rail/gnd',c2r,c2g)
W=0.20
def seg(net,a,c,layer='B.Cu'):
    ok=pl.seg_ok(b,net,layer,a,c,W); print(f'  seg {net} {tuple(round(v,3) for v in a)}->{tuple(round(v,3) for v in c)} clear={ok}'); assert ok,(net,a,c); pl.add_seg(b,net,layer,a,c,W)
seg('XL1',VIA1,p1); seg('XL2',VIA2,p2); seg('XL1',p1,c14r); seg('XL2',p2,c2r)
for gp in (c14g,c2g):
    cand=(gp[0]+0.45,gp[1]); ok,why=pl.via_ok(b,'GND',cand); print(f'  GND via at {cand} ok={ok} {why}'); assert ok
    pl.add_via(b,'GND',cand,0.30,0.15); seg('GND',gp,cand)
keep={'09c69f3c','2ca599eb','5e990703','c0dbb053','0c045eb1','25468b96','3eca2ac0','58a3555d'}
# new copper has fresh uuids that don't collide with these prefixes, but protect it explicitly:
new_uuids={str(t.m_Uuid.AsString())[:8] for t in b.GetTracks() if t.GetNetname() in ('XL1','XL2') and not any(str(t.m_Uuid.AsString()).startswith(k) for k in keep)}
# identify stale copper = XL copper that is NOT the kept stubs and NOT what we just added: we added exactly 4 XL segments
import math
added=set()
for t in b.GetTracks():
    if t.GetNetname() in ('XL1','XL2') and not isinstance(t,pcbnew.PCB_VIA):
        s=pcbnew.ToMM(t.GetStart()); e=pcbnew.ToMM(t.GetEnd())
        if min(s[0],e[0])>85.5 and max(s[0],e[0])<89.0 and t.GetLayer()==pcbnew.B_Cu: added.add(str(t.m_Uuid.AsString())[:8])
print('new XL segments protected:',len(added))
print('removed stale XL copper:', pl.remove_net_copper(b,{'XL1','XL2'}, keep|added))
rl.refill_zones(b); b.Save('haven_dev_board.kicad_pcb'); print('saved')

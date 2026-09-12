"""One explicitly reviewed capacitor repair per invocation, with DRC rollback.
No search or autorouter. Geometry and DRC evidence persist for rejected attempts.
"""
import pathlib,sys,json,subprocess,shutil
import pcbnew as p
ROOT=pathlib.Path('C:/Work/haven-board');EV=ROOT/'routing-evidence/session5';BOARD=ROOT/'kicad/haven_dev_board.kicad_pcb'
CLI='C:/Users/pmi/AppData/Local/Programs/KiCad/9.0/bin/kicad-cli.exe'
sys.path.insert(0,str(ROOT/'routing-evidence'))
from escape_helpers import obstacles,point
name=sys.argv[1];spec=json.loads((EV/(name+'.spec.json')).read_text());before=BOARD.read_bytes()
b=p.LoadBoard(str(BOARD));log=[];tracks=list(b.GetTracks())
for uid in spec.get('remove',[]):
 t=next(t for t in tracks if t.m_Uuid.AsString()==uid)
 log.append(['remove',uid,t.GetNetname(),[p.ToMM(v) for v in [t.GetStart().x,t.GetStart().y,t.GetEnd().x,t.GetEnd().y]]]);b.Remove(t)
for s in spec.get('segments',[]):
 net,layer,coords,width=s
 for a,z in zip(coords,coords[1:]):
  t=p.PCB_TRACK(b);t.SetStart(point(*a));t.SetEnd(point(*z));t.SetWidth(p.FromMM(width));t.SetLayer(b.GetLayerID(layer));t.SetNetCode(b.FindNet(net).GetNetCode())
  hits=obstacles(b,t);log.append(['segment',net,layer,a,z,'hits',hits]);b.Add(t)
for net,xy in spec.get('vias',[]):
 v=p.PCB_VIA(b);v.SetPosition(point(*xy));v.SetWidth(p.FromMM(.3));v.SetDrill(p.FromMM(.15));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNetCode(b.FindNet(net).GetNetCode())
 hits=obstacles(b,v);log.append(['via',net,xy,'hits',hits]);b.Add(v)
(EV/(name+'.geometry.json')).write_text(json.dumps(log,indent=2))
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(BOARD),b)
r=subprocess.run([CLI,'pcb','drc','--format','json','-o',str(EV/(name+'.json')),str(BOARD)],capture_output=True,text=True)
(EV/(name+'.stdout')).write_text(r.stdout+r.stderr);print(r.stdout+r.stderr)
prev=json.loads((EV/(spec['before']+'.json')).read_text());cur=json.loads((EV/(name+'.json')).read_text())
def key(v):return v['type'],tuple(sorted(i['uuid'] for i in v['items']))
old={key(v) for v in prev['violations']};new=[v for v in cur['violations'] if key(v) not in old]
(EV/(name+'.new-violations.json')).write_text(json.dumps(new,indent=2))
accepted=not new and len(cur['unconnected_items'])<=len(prev['unconnected_items'])
if not accepted: BOARD.write_bytes(before)
print('ACCEPTED' if accepted else 'REJECTED; board restored', 'new violations',len(new),'links',len(prev['unconnected_items']),'->',len(cur['unconnected_items']))
print(json.dumps(new)[:7000])
print('Geometry:',json.dumps(log))

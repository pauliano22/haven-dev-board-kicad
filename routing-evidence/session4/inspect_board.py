import json,sys,pathlib,subprocess
import pcbnew as p
root=pathlib.Path('C:/Work/haven-board')
b=p.LoadBoard(str(root/'kicad/haven_dev_board.kicad_pcb'))
refs=sys.argv[1:] or ['C6','C8','C9','C13','C22','C34','C38','C44','C46']
data={}
for ref in refs:
 f=next(f for f in b.GetFootprints() if f.GetReference()==ref)
 pads=[dict(pin=a.GetNumber(),net=a.GetNetname(),x=p.ToMM(a.GetPosition().x),y=p.ToMM(a.GetPosition().y)) for a in f.Pads()]
 data[ref]=pads
 print(ref,pads)
 cx=sum(a['x'] for a in pads)/len(pads);cy=sum(a['y'] for a in pads)/len(pads)
 for t in b.GetTracks():
  x,y=p.ToMM(t.GetStart().x),p.ToMM(t.GetStart().y);ex,ey=p.ToMM(t.GetEnd().x),p.ToMM(t.GetEnd().y)
  if min((x-cx)**2+(y-cy)**2,(ex-cx)**2+(ey-cy)**2)<2.6**2:
   print(t.m_Uuid.AsString(),t.GetClass(),t.GetNetname(),b.GetLayerName(t.GetLayer()),(x,y),(ex,ey),'width',p.ToMM(t.GetWidth(p.F_Cu) if isinstance(t,p.PCB_VIA) else t.GetWidth()))
(root/'routing-evidence/session4/pads.json').write_text(json.dumps(data,indent=2))

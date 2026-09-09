"""Local per-pad routing primitives with KiCad shape collision checks.
No path search or bulk router. Every route is an explicit reviewed polyline.
Existing zones refill; pads/tracks/vias are checked on every shared copper layer.
"""
import pcbnew as p
LAYERS=[p.F_Cu,p.In1_Cu,p.In2_Cu,p.In3_Cu,p.In4_Cu,p.B_Cu]
def point(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
def obstacles(b,item):
 hits=[]
 for other in list(b.GetTracks())+[a for f in b.GetFootprints() for a in f.Pads()]:
  if other.GetNetCode()==item.GetNetCode():continue
  for layer in LAYERS:
   if item.IsOnLayer(layer) and other.IsOnLayer(layer):
    if other.GetEffectiveShape(layer).Collide(item.GetEffectiveShape(layer),p.FromMM(.2)):
     hits.append((other.m_Uuid.AsString(),other.GetNetname(),b.GetLayerName(layer)));break
 # Conservative rectangle test includes the full width of added copper.
 box=item.GetBoundingBox();x0,y0=p.ToMM(box.GetX()),p.ToMM(box.GetY());x1,y1=x0+p.ToMM(box.GetWidth()),y0+p.ToMM(box.GetHeight())
 if x0<75.01 and x1>71.11 and y0<74.728 and y1>65.227999:hits.append(('ANTENNA','keepout','all'))
 return hits

def escape(b,ref,pin,coords,width=.1,via=True):
 f=next(f for f in b.GetFootprints() if f.GetReference()==ref);a=next(a for a in f.Pads() if a.GetNumber()==pin)
 layer=p.B_Cu if a.IsOnLayer(p.B_Cu) else p.F_Cu;items=[]
 for start,end in zip(coords,coords[1:]):
  t=p.PCB_TRACK(b);t.SetStart(point(*start));t.SetEnd(point(*end));t.SetWidth(p.FromMM(width));t.SetLayer(layer);t.SetNetCode(a.GetNetCode());items.append(t)
 if via:
  v=p.PCB_VIA(b);v.SetPosition(point(*coords[-1]));v.SetWidth(p.FromMM(.3));v.SetDrill(p.FromMM(.15));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNetCode(a.GetNetCode());items.append(v)
 hits=[(i,obstacles(b,item)) for i,item in enumerate(items) if obstacles(b,item)]
 if hits: print('BLOCKED',ref,pin,a.GetNetname(),hits);return False
 for item in items:b.Add(item)
 print('ADDED',ref,pin,a.GetNetname(),coords);return True

def save(b):
 b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard('kicad/haven_dev_board.kicad_pcb',b)

def segment(b,net,layer,start,end,width=.1):
 t=p.PCB_TRACK(b);t.SetStart(point(*start));t.SetEnd(point(*end));t.SetWidth(p.FromMM(width));t.SetLayer(layer);t.SetNetCode(b.FindNet(net).GetNetCode())
 hits=obstacles(b,t)
 if hits:print('BLOCKED segment',net,hits);return False
 b.Add(t);print('ADDED segment',net,start,end);return True

"""Visually selected GND escapes. Start outer U15 traces at pad edges."""
import pcbnew as p
b=p.LoadBoard('kicad/haven_dev_board.kicad_pcb')
# ref,pin,start offset x/y,end offset x/y,width
routes=[('U2','A1',0,0,.6,.3,.15),('U2','A5',0,0,.7,-.1271,.15),('CN1','10',0,0,0,-.8,.10)]
for pin,dx,dy in [('A1',0,1),('A4',0,1),('F1',-1,0),('G3',0,-1),('G7',0,-1)]:
 routes.append(('U15',pin,dx*.124,dy*.124,dx*.6,dy*.6,.09))
for ref,pin,sx,sy,dx,dy,width in routes:
 f=next(f for f in b.GetFootprints() if f.GetReference()==ref);a=next(a for a in f.Pads() if a.GetNumber()==pin)
 assert a.GetNetname()=='GND'
 at=a.GetPosition();start=p.VECTOR2I(at.x+p.FromMM(sx),at.y+p.FromMM(sy));end=p.VECTOR2I(at.x+p.FromMM(dx),at.y+p.FromMM(dy))
 t=p.PCB_TRACK(b);t.SetStart(start);t.SetEnd(end);t.SetWidth(p.FromMM(width));t.SetLayer(p.B_Cu if a.IsOnLayer(p.B_Cu) else p.F_Cu);t.SetNetCode(a.GetNetCode());b.Add(t)
 v=p.PCB_VIA(b);v.SetPosition(end);v.SetWidth(p.FromMM(.3));v.SetDrill(p.FromMM(.15));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNetCode(a.GetNetCode());b.Add(v)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard('kicad/haven_dev_board.kicad_pcb',b)

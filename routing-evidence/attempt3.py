"""Explicit outward dogbones; run from repository root using system Python."""
import pcbnew as p
b=p.LoadBoard('kicad/haven_dev_board.kicad_pcb')
# Reference, pad, displacement in mm. Preserve pads and routing constraints.
escapes=[('U2','A1',.6,.3),('U2','B5',0,-.7)]
for ref,pin,dx,dy in escapes:
 f=next(f for f in b.GetFootprints() if f.GetReference()==ref)
 a=next(a for a in f.Pads() if a.GetNumber()==pin)
 start=a.GetPosition(); end=p.VECTOR2I(start.x+p.FromMM(dx),start.y+p.FromMM(dy))
 t=p.PCB_TRACK(b);t.SetStart(start);t.SetEnd(end);t.SetWidth(p.FromMM(.15));t.SetLayer(p.B_Cu if a.IsOnLayer(p.B_Cu) else p.F_Cu);t.SetNetCode(a.GetNetCode());b.Add(t)
 v=p.PCB_VIA(b);v.SetPosition(end);v.SetWidth(p.FromMM(.3));v.SetDrill(p.FromMM(.15));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNetCode(a.GetNetCode());b.Add(v)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard('kicad/haven_dev_board.kicad_pcb',b)

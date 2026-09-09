import pcbnew as p
b=p.LoadBoard('/home/paul22iac/haven-dev-board-kicad/kicad/haven_dev_board.kicad_pcb')
for f in b.GetFootprints():
 for a in f.Pads():
  if (f.GetReference()=='U15' and a.GetNetname() in ['GND','V_LS']) or (f.GetReference()=='U2' and a.GetNumber() in ['A1','A5','B5']):
   v=p.PCB_VIA(b); v.SetPosition(a.GetPosition()); v.SetWidth(p.FromMM(.25)); v.SetDrill(p.FromMM(.15)); v.SetViaType(p.VIATYPE_THROUGH); v.SetLayerPair(p.F_Cu,p.B_Cu); v.SetNetCode(a.GetNetCode()); b.Add(v)
b.BuildConnectivity(); p.ZONE_FILLER(b).Fill(b.Zones()); p.SaveBoard('/tmp/haven-attempt1.kicad_pcb',b)

import pcbnew, os, sys
P=os.environ["HAVEN_PCB"]; b=pcbnew.LoadBoard(P)
x0,x1,y0,y1=[float(v) for v in sys.argv[1:5]]; lay=b.GetLayerID(sys.argv[5])
inw=lambda p: x0<=p.x/1e6<=x1 and y0<=p.y/1e6<=y1
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.IsOnLayer(lay) and inw(p.GetPosition()):
            s=p.GetSize(lay) if hasattr(p,'GetSize') else None
            print("PAD",fp.GetReference(),p.GetNumber(),p.GetNetname(),round(p.GetPosition().x/1e6,3),round(p.GetPosition().y/1e6,3),round(s.x/1e6,2),round(s.y/1e6,2), int(fp.GetOrientationDegrees()))
for t in b.GetTracks():
    if t.GetClass()=="PCB_VIA":
        if inw(t.GetPosition()): print("VIA",t.GetNetname(),round(t.GetPosition().x/1e6,3),round(t.GetPosition().y/1e6,3),round(t.GetWidth(lay)/1e6,2))
    elif t.GetLayer()==lay and (inw(t.GetStart()) or inw(t.GetEnd())):
        print("TRK",t.GetNetname(),round(t.GetStart().x/1e6,3),round(t.GetStart().y/1e6,3),round(t.GetEnd().x/1e6,3),round(t.GetEnd().y/1e6,3))
sys.stdout.flush(); os._exit(0)

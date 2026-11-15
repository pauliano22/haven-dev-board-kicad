import pcbnew, os, sys
from PIL import Image, ImageDraw
P=os.environ["HAVEN_PCB"]; b=pcbnew.LoadBoard(P)
x0,x1,y0,y1=[float(v) for v in sys.argv[1:5]]; out=sys.argv[5]; layers=sys.argv[6].split(",")
S=int(sys.argv[7]) if len(sys.argv)>7 else 300
col={"F.Cu":(220,40,40),"In2.Cu":(40,160,40),"In3.Cu":(230,150,0),"In4.Cu":(150,60,200),"B.Cu":(40,90,230)}
W,H=int((x1-x0)*S),int((y1-y0)*S)
im=Image.new("RGB",(W,H),"white"); d=ImageDraw.Draw(im,"RGBA")
X=lambda v:(v/1e6-x0)*S; Y=lambda v:(v/1e6-y0)*S
for ln in layers:
    lay=b.GetLayerID(ln); c=col[ln]+(150,)
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.IsOnLayer(lay):
                bb=p.GetBoundingBox(); 
                if bb.GetRight()/1e6<x0 or bb.GetLeft()/1e6>x1 or bb.GetBottom()/1e6<y0 or bb.GetTop()/1e6>y1: continue
                d.rectangle([X(bb.GetLeft()),Y(bb.GetTop()),X(bb.GetRight()),Y(bb.GetBottom())],fill=c,outline=(0,0,0,255))
                d.text((X(bb.GetLeft())+2,Y(bb.GetTop())+1),f"{fp.GetReference()}.{p.GetNumber()} {p.GetNetname().lstrip('/')[:9]}",fill=(0,0,0,255))
    for t in b.GetTracks():
        if t.GetClass()=="PCB_VIA": continue
        if t.GetLayer()!=lay: continue
        d.line([X(t.GetStart().x),Y(t.GetStart().y),X(t.GetEnd().x),Y(t.GetEnd().y)],fill=c,width=max(2,int(t.GetWidth()/1e6*S)))
        mx,my=(t.GetStart().x+t.GetEnd().x)/2,(t.GetStart().y+t.GetEnd().y)/2
        if x0<mx/1e6<x1 and y0<my/1e6<y1 and t.GetLength()/1e6>0.5: d.text((X(mx)+3,Y(my)+3),t.GetNetname().lstrip('/')[:8],fill=col[ln]+(255,))
for t in b.GetTracks():
    if t.GetClass()=="PCB_VIA":
        p=t.GetPosition(); r=t.GetWidth(pcbnew.F_Cu)/2e6*S
        if x0<p.x/1e6<x1 and y0<p.y/1e6<y1:
            d.ellipse([X(p.x)-r,Y(p.y)-r,X(p.x)+r,Y(p.y)+r],outline=(0,0,0,255),width=2); d.text((X(p.x)-r,Y(p.y)+r),t.GetNetname().lstrip('/')[:6],fill=(90,90,90,255))
for gx in range(int(x0*2),int(x1*2)+1):
    d.line([(gx/2-x0)*S,0,(gx/2-x0)*S,H],fill=(0,0,0,40)); d.text(((gx/2-x0)*S+2,H-12),str(gx/2),fill=(0,0,0,255))
for gy in range(int(y0*2),int(y1*2)+1):
    d.line([0,(gy/2-y0)*S,W,(gy/2-y0)*S],fill=(0,0,0,40)); d.text((2,(gy/2-y0)*S+2),str(gy/2),fill=(0,0,0,255))
im.save(out); sys.stdout.flush(); os._exit(0)

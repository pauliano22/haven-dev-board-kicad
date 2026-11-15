"""Remove dead-end tracks one at a time; keep each removal only if the open-connection count does not rise."""
import os, re, subprocess, sys, shutil, pcbnew
P=os.environ["HAVEN_PCB"]; W=os.environ["HAVEN_WORK"]; rpt=os.path.join(W,"drc_prune.rpt")
def drc():
    subprocess.run(["kicad-cli","pcb","drc","--severity-error","--severity-warning","-o",rpt,P],stdout=subprocess.DEVNULL)
    s=open(rpt).read()
    k={}
    for m in re.findall(r"^\[(\w+)\]",s,re.M): k[m]=k.get(m,0)+1
    d=re.findall(r"^\[track_dangling\].*?\n.*?\n\s*@\(([-\d.]+) mm, ([-\d.]+) mm\): Track \[([^\]]+)\] on ([\w.]+)",s,re.M)
    return k,d
k,d=drc(); base=k.get("unconnected_items",0); bad0=sum(v for n,v in k.items() if n in("clearance","shorting_items","tracks_crossing","hole_clearance"))
print("start",k,flush=True); tried=set()
for _ in range(60):
    todo=[x for x in d if x not in tried]
    if not todo: break
    x,y,net,lay=todo[0]; tried.add(todo[0])
    shutil.copy(P,P+".bak"); b=pcbnew.LoadBoard(P); q=pcbnew.VECTOR2I_MM(float(x),float(y)); L=b.GetLayerID(lay); hit=None
    for t in b.GetTracks():
        if t.GetClass()=="PCB_TRACK" and t.GetNetname()==net and t.GetLayer()==L and (t.GetStart()-q).EuclideanNorm()<2000: hit=t; break
    if hit is None: continue
    b.Remove(hit); pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.Save(P)
    k2,d2=drc(); bad=sum(v for n,v in k2.items() if n in("clearance","shorting_items","tracks_crossing","hole_clearance"))
    if k2.get("unconnected_items",0)<=base and bad<=bad0:
        print("  removed",net,lay,x,y,"->",k2.get("track_dangling",0),"dead ends left",flush=True); d=d2; bad0=bad
    else:
        shutil.copy(P+".bak",P); print("  kept (in use)",net,lay,x,y,flush=True)
os.remove(P+".bak") if os.path.exists(P+".bak") else None
print("end",drc()[0],flush=True); sys.stdout.flush(); os._exit(0)

#!/usr/bin/env python3
"""Compare two kicad-cli DRC JSON reports by (type, severity, description)
multiset -- the project's acceptance rule is zero NEW violation identities,
not merely an equal or lower total. Usage: drc_diff.py before.json after.json"""
import json, sys, collections
def load(p):
    d=json.load(open(p))
    v=collections.Counter((x['type'],x.get('severity',''),x.get('description','')) for x in d.get('violations',[]))
    u=collections.Counter(tuple(sorted(i.get('description','') for i in x.get('items',[]))) for x in d.get('unconnected_items',[]))
    return v,u,len(d.get('violations',[])),len(d.get('unconnected_items',[]))
bv,bu,bn,bun=load(sys.argv[1]); av,au,an,aun=load(sys.argv[2])
new=av-bv; gone=bv-av; newu=au-bu; goneu=bu-au
print(f"violations {bn} -> {an}; unconnected {bun} -> {aun}")
print(f"NEW violation identities: {sum(new.values())}")
for k,n in new.items(): print(f"  +{n} {k[0]} [{k[1]}] {k[2][:110]}")
print(f"resolved violation identities: {sum(gone.values())}")
for k,n in list(gone.items())[:15]: print(f"  -{n} {k[0]} [{k[1]}] {k[2][:110]}")
print(f"NEW unconnected: {sum(newu.values())}"); [print("  +",k) for k in newu]
print(f"resolved unconnected: {sum(goneu.values())}"); [print("  -",k) for k in goneu]
sys.exit(1 if (new or newu) else 0)

"""Check original copper preservation, footprint geometry, keepout and DRC delta."""
import sys,subprocess,json,re,collections
from pathlib import Path
sys.path.insert(0,'extracted')
from sexp_parser import parse,get,get_all_immediate
base=parse(subprocess.check_output(['git','show','b535d54:kicad/haven_dev_board.kicad_pcb'],text=True))[0]
now=parse(Path('kicad/haven_dev_board.kicad_pcb').read_text())[0]
def nodes(board,tag):return get_all_immediate(board,tag)
def indexed(board,tag):return {get(n,'uuid')[1]:n for n in nodes(board,tag)}
for tag in ['footprint','segment','via']:
 old=indexed(base,tag);new=indexed(now,tag)
 missing=old.keys()-new.keys();changed=[k for k in old.keys()&new.keys() if old[k]!=new[k]]
 print(tag,'original',len(old),'added',len(new.keys()-old.keys()),'removed',len(missing),'changed',len(changed))
 assert not missing and not changed,(tag,changed[:3])
for tag in ['setup','layers','general']:
 assert nodes(base,tag)==nodes(now,tag),tag
print('setup/layers/general unchanged')
old=[z for z in nodes(base,'zone') if get(z,'keepout')];new=[z for z in nodes(now,'zone') if get(z,'keepout')]
assert old==new
print('antenna keepout exactly unchanged')
import pcbnew as p
b=p.LoadBoard('kicad/haven_dev_board.kicad_pcb')
orig=set(indexed(base,'segment'))|set(indexed(base,'via'))
for t in b.GetTracks():
 if t.m_Uuid.AsString() in orig:continue
 box=t.GetBoundingBox();x0,y0=p.ToMM(box.GetX()),p.ToMM(box.GetY());x1,y1=x0+p.ToMM(box.GetWidth()),y0+p.ToMM(box.GetHeight())
 assert not (x0<75.01 and x1>71.11 and y0<74.728 and y1>65.227999),'new copper in antenna keepout'
print('all new copper bounding boxes outside antenna keepout')
a=json.loads(Path('routing-evidence/baseline.json').read_text());z=json.loads(Path('routing-evidence/final.json').read_text())
def key(v):return(v['type'],tuple(sorted(i['uuid'] for i in v['items'])))
assert not {key(v) for v in z['violations']}-{key(v) for v in a['violations']}
print('no new DRC violation identities')
def nets(j):return {re.search(r'\[(.*?)\]',i['description'])[1] for v in j['unconnected_items'] for i in v['items'] if '[' in i['description']}
print('missing links',len(a['unconnected_items']),'->',len(z['unconnected_items']))
print('open nets',len(nets(a)),'->',len(nets(z)))
print('fully closed nets',sorted(nets(a)-nets(z)))

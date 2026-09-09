import sys,pathlib,subprocess,json,re
root=pathlib.Path('C:/Work/haven-board');ev=root/'routing-evidence/session5'
sys.path.insert(0,str(root/'extracted'))
from sexp_parser import parse,get,get_all_immediate as nodes
base=parse(subprocess.check_output(['git','-C',str(root),'show','d3858b4:kicad/haven_dev_board.kicad_pcb'],text=True))[0]
now=parse((root/'kicad/haven_dev_board.kicad_pcb').read_text())[0]
def index(b,tag):return {get(n,'uuid')[1]:n for n in nodes(b,tag)}
for tag in ['footprint','via','segment']:
 a,z=index(base,tag),index(now,tag);changed=[k for k in a.keys()&z.keys() if a[k]!=z[k]]
 print(tag,'original',len(a),'added',len(z.keys()-a.keys()),'removed',len(a.keys()-z.keys()),'changed',len(changed))
 assert not changed
 if tag in ['footprint','via']:assert not a.keys()-z.keys()
 if tag=='footprint':assert a==z
for tag in ['setup','layers','general']:assert nodes(base,tag)==nodes(now,tag),tag
assert [z for z in nodes(base,'zone') if get(z,'keepout')]==[z for z in nodes(now,'zone') if get(z,'keepout')]
print('All footprints, existing vias, setup, layers, general and antenna keepout unchanged.')
orig=set(index(base,'segment'))|set(index(base,'via'))
for tag in ['segment','via']:
 for uid,t in index(now,tag).items():
  if uid in orig:continue
  if tag=='via':pts=[get(t,'at')[1:3]];w=float(get(t,'size')[1])
  else:pts=[get(t,'start')[1:3],get(t,'end')[1:3]];w=float(get(t,'width')[1])
  xs=[float(v[0]) for v in pts];ys=[float(v[1]) for v in pts]
  assert not(min(xs)-w/2<75.01 and max(xs)+w/2>71.11 and min(ys)-w/2<74.728 and max(ys)+w/2>65.227999)
print('All new copper outside antenna keepout.')
a=json.loads((ev/'baseline.json').read_text());z=json.loads((ev/'final.json').read_text())
def key(v):return v['type'],tuple(sorted(i['uuid'] for i in v['items']))
assert not {key(v) for v in z['violations']}-{key(v) for v in a['violations']}
def nets(j):return {re.search(r'\[(.*?)\]',i['description'])[1] for v in j['unconnected_items'] for i in v['items'] if '[' in i['description']}
print('Violations',len(a['violations']),'->',len(z['violations']),'no new identities')
print('Missing links',len(a['unconnected_items']),'->',len(z['unconnected_items']))
print('Open nets',len(nets(a)),'->',len(nets(z)),'closed:',sorted(nets(a)-nets(z)))
refs=['C23','R6']
for ref in refs:
 items=[i for v in z['unconnected_items'] for i in v['items'] if re.search(r' of '+ref+r'\b',i['description'])]
 print(ref,'remaining DRC endpoints',len(items));assert not items
r13=[i for v in z['unconnected_items'] for i in v['items'] if 'Pad 2 [VUSB] of R13 ' in i['description']]
print('R13 VUSB remaining endpoints',len(r13));assert not r13

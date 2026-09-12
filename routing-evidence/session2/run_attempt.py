"""Run one explicit reviewed attempt, capture raw output; never auto-accept."""
import sys,pathlib,subprocess,shutil,json
name=sys.argv[1];root=pathlib.Path('routing-evidence/session2');board=pathlib.Path('kicad/haven_dev_board.kicad_pcb')
shutil.copyfile(board,'/tmp/haven-'+name+'-before.kicad_pcb')
r=subprocess.run(['/usr/bin/python3',str(root/(name+'.py'))],text=True,capture_output=True)
(root/(name+'.geometry.txt')).write_text(r.stdout+r.stderr);print(r.stdout+r.stderr)
c=subprocess.run(['kicad-cli','pcb','drc','--format','json','-o',str(root/(name+'.json')),str(board)],text=True,capture_output=True)
(root/(name+'.stdout')).write_text(c.stdout+c.stderr);print(c.stdout+c.stderr)
prev=json.loads(pathlib.Path(sys.argv[2]).read_text());cur=json.loads((root/(name+'.json')).read_text())
def key(v):return(v['type'],tuple(sorted(i['uuid'] for i in v['items'])))
old={key(v) for v in prev['violations']};new=[v for v in cur['violations'] if key(v) not in old]
(root/(name+'.new-violations.json')).write_text(json.dumps(new,indent=2))
print('NEW VIOLATIONS',len(new));print(json.dumps(new)[:6000])

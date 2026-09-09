import pathlib,json,sys,re,subprocess
name,before=sys.argv[1:3];root=pathlib.Path('routing-evidence/session2');meta=json.loads((root/(name+'.meta.json')).read_text());a=json.loads(pathlib.Path(before+'.json').read_text());b=json.loads((root/(name+'.json')).read_text())
def nets(j):return {re.search(r'\[(.*?)\]',i['description'])[1] for v in j['unconnected_items'] for i in v['items'] if '[' in i['description']}
new=json.loads((root/(name+'.new-violations.json')).read_text())
if meta.get('retained',True):assert not new
entry=f"\n### Codex/Astra — 2026-09-09 — {name}\n**Goal this session**: {meta['goal']}\n**What I tried**: {meta['what']}\n**Result** (paste real DRC output, not a summary):\nBefore:\n```\n{pathlib.Path(before+'.stdout').read_text().strip()}\n```\nAfter:\n```\n{(root/(name+'.stdout')).read_text().strip()}\n```\n**Unrouted count before -> after**: {len(a['unconnected_items'])} -> {len(b['unconnected_items'])} missing links; {len(nets(a))} -> {len(nets(b))} distinct open nets. Newly closed: {', '.join(sorted(nets(a)-nets(b))) or 'none'}. New violation identities: {len(new)}.\n**Blockers / questions for the other side**: {meta['blockers']}\n"
with open('CODEX_NOTES.md','a') as f:f.write(entry)
print(entry)

"""Use Codex's real local app-server parser (no model/network prompt)."""
import argparse
import json
import os
from pathlib import Path
import selectors
import subprocess
import time

p=argparse.ArgumentParser();p.add_argument('--codex',default='codex');p.add_argument('--repo',required=True);p.add_argument('--output',required=True);args=p.parse_args()
out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
with (out/'appserver.stderr').open('w') as errors:
 proc=subprocess.Popen([args.codex,'app-server'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,text=True,env=os.environ.copy())
 selector=selectors.DefaultSelector();selector.register(proc.stdout,selectors.EVENT_READ)
 def request(i,method,params):
  proc.stdin.write(json.dumps({'id':i,'method':method,'params':params})+'\n');proc.stdin.flush()
  deadline=time.monotonic()+30
  while time.monotonic()<deadline:
   if selector.select(timeout=1):
    line=proc.stdout.readline()
    if not line: raise RuntimeError('app-server exited')
    value=json.loads(line)
    if value.get('id')==i:
     if 'error' in value: raise RuntimeError(value)
     return value['result']
  raise TimeoutError(method)
 try:
  init=request(1,'initialize',{'clientInfo':{'name':'seagent-freecad-local-validation','version':'0.1.0'},'capabilities':{'experimentalApi':True}})
  proc.stdin.write(json.dumps({'method':'initialized'})+'\n');proc.stdin.flush()
  plugin=request(2,'plugin/read',{'pluginName':'seagent-freecad','marketplacePath':str(Path(args.repo).resolve()/'.agents/plugins/marketplace.json')})
  skills=request(3,'skills/list',{'cwds':[str(Path(args.repo).resolve())],'forceReload':True})
  (out/'plugin-read.json').write_text(json.dumps(plugin,ensure_ascii=False,indent=2)+'\n')
  (out/'skills-list.json').write_text(json.dumps(skills,ensure_ascii=False,indent=2)+'\n')
  found=[s for group in skills['data'] for s in group['skills'] if s.get('pluginId')=='seagent-freecad@seagent-freecad-local']
  expected={'seagent-project-init'}
  assert {s['name'].split(':',1)[-1] for s in found}==expected, found
  cache=Path(os.environ['CODEX_HOME']).resolve()/'plugins/cache/seagent-freecad-local/seagent-freecad/0.1.0'
  assert all(Path(s['path']).is_relative_to(cache) and Path(s['path']).is_file() and s['enabled'] for s in found), found
  assert plugin['plugin']['onboardingSkill']['name']=='seagent-freecad:seagent-project-init', plugin
  assert plugin['plugin']['summary']['installed'] and plugin['plugin']['summary']['enabled']
  (out/'summary.json').write_text(json.dumps({'initialized':init,'plugin_read':True,'skills_detected':True},indent=2)+'\n')
  print('Codex app-server parsed plugin and found bundled skills')
 finally:
  proc.terminate();proc.wait(timeout=10)

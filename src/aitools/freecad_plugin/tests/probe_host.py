"""Isolated CLI app-server discovery only. Never bind/start/call upstream CAD."""
import argparse
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--project',required=True);p.add_argument('--output',required=True);p.add_argument('--codex',default='codex');a=p.parse_args()
home=Path(os.environ['CODEX_HOME']).resolve();data=Path(a.data).resolve();project=Path(a.project).resolve();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
installed=json.loads((data/'deployment.json').read_text())
cache=Path(installed['cache']).resolve()
assert cache.is_relative_to(home) and cache.is_dir()
assert not (data/'binding.json').exists(), 'Probe must remain unbound'
config=json.loads((cache/'mcp.json').read_text())['mcpServers']['freecad']
assert config['command']=='./scripts/launch.sh' or config['command']=='powershell.exe'
launcher=cache/('scripts/launch.ps1' if os.name=='nt' else 'scripts/launch.sh')
assert 'bridge.py' in launcher.read_text(encoding='utf-8-sig') and str(data) in launcher.read_text(encoding='utf-8-sig')
project.mkdir(parents=True,exist_ok=True)
with (out/'stderr.txt').open('w') as errors:
 proc=subprocess.Popen([a.codex,'--no-daemon','app-server'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,text=True,encoding='utf-8',env=os.environ.copy())
 q=queue.Queue()
 def reader():
  for line in proc.stdout:q.put(json.loads(line))
 threading.Thread(target=reader,daemon=True).start()
 def request(id,method,params):
  proc.stdin.write(json.dumps({'id':id,'method':method,'params':params})+'\n');proc.stdin.flush()
  end=time.monotonic()+45
  while time.monotonic()<end:
   v=q.get(timeout=max(.1,end-time.monotonic()))
   if v.get('id')==id:
    if 'error'in v:raise RuntimeError(v['error'])
    return v['result']
  raise TimeoutError(method)
 try:
  request(1,'initialize',{'clientInfo':{'name':'freecad-isolated-discovery','version':'0.2.0'},'capabilities':{'experimentalApi':True}})
  proc.stdin.write(json.dumps({'method':'initialized'})+'\n');proc.stdin.flush()
  plugin=request(2,'plugin/read',{'pluginName':'seagent-freecad','marketplacePath':str(data/'marketplace/.agents/plugins/marketplace.json')})
  skills=request(3,'skills/list',{'cwds':[str(project)],'forceReload':True})
  found=[s for g in skills['data'] for s in g['skills'] if s.get('pluginId')=='seagent-freecad@seagent-freecad-private']
  assert len(found)==7 and all(Path(s['path']).is_relative_to(cache) for s in found), found
  started=request(4,'thread/start',{'cwd':str(project),'ephemeral':True})
  status=request(5,'mcpServerStatus/list',{'detail':'full','threadId':started['thread']['id']})
  (out/'status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2))
  (out/'plugin.json').write_text(json.dumps(plugin,ensure_ascii=False,indent=2))
  servers=[s for s in status['data'] if s.get('pluginId')=='seagent-freecad@seagent-freecad-private']
  assert len(servers)==1 and servers[0]['runtimeStatus']=='connected',servers
  assert len(servers[0]['tools'])==18, servers
  assert not(data/'binding.json').exists()
  summary={'skills':len(found),'tools':len(servers[0]['tools']),'unbound_bridge_connected':True,'cache_under_isolated_home':True,'cad_calls':0,'gui_started':False,'cli':'0.163.0','desktop_first_use':'待验证'}
  (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
  print(json.dumps(summary,ensure_ascii=False))
 finally:
  proc.stdin.close()
  try:proc.wait(timeout=10)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10)

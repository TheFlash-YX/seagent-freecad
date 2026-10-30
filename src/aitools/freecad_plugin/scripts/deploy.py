"""Generate a project-independent local marketplace and use official Codex CLI."""
import argparse
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import manage


def run(exe,*args):
    if Path(exe).suffix.lower() in ('.cmd','.bat'):raise RuntimeError('请使用原生codex.exe，不经shell执行包装器')
    p=subprocess.run([exe,'--no-daemon',*args],capture_output=True,text=True,encoding='utf-8',timeout=60)
    if p.returncode:raise RuntimeError('Codex命令失败：'+' '.join(args[:3])+'；'+p.stderr[:400])
    return p.stdout


def source_files():
    repo=manage.PACKAGE.parents[2]
    manifest=manage.read(repo/'delivery-files.json')['files']
    prefix='src/aitools/freecad_plugin/'
    return [(n[len(prefix):],repo/n) for n in manifest if n.startswith(prefix)]


def generate(data):
    c=manage.read(data/'machine.json');manage.validate_runtime(data)
    dest=data/'marketplace';plugin=dest/'plugin'
    expected={n:src.read_bytes() for n,src in source_files()}
    manifest=manage.read(manage.PACKAGE/'plugin.json');manifest['version']='0.2.0'
    expected['machine-locator.json']=(json.dumps({'data':str(data)},ensure_ascii=False)+'\n').encode()
    expected['plugin.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    if os.name=='nt':
        ps="'"+c['runtime_python'].replace("'","''")+"'"
        bp="'"+str(plugin/'scripts/bridge.py').replace("'","''")+"'"
        dp="'"+str(data).replace("'","''")+"'"
        # PS5's native pipeline is text-oriented. Pump raw BaseStreams with .NET tasks.
        native_args=subprocess.list2cmdline([str(plugin/'scripts/bridge.py'),'--data',str(data)]).replace("'","''")
        launcher=("$ErrorActionPreference='Stop'\n"
                  "$info=New-Object Diagnostics.ProcessStartInfo\n"
                  "$info.FileName="+ps+"\n"
                  "$info.Arguments='"+native_args+"'\n"
                  "$info.UseShellExecute=$false\n$info.CreateNoWindow=$true\n"
                  "$info.RedirectStandardInput=$true\n$info.RedirectStandardOutput=$true\n$info.RedirectStandardError=$true\n"
                  "$p=New-Object Diagnostics.Process\n$p.StartInfo=$info\n[void]$p.Start()\n"
                  "$inputTask=[Console]::OpenStandardInput().CopyToAsync($p.StandardInput.BaseStream)\n"
                  "$outputTask=$p.StandardOutput.BaseStream.CopyToAsync([Console]::OpenStandardOutput())\n"
                  "$errorTask=$p.StandardError.BaseStream.CopyToAsync([Console]::OpenStandardError())\n"
                  "while (!$p.WaitForExit(50)) { if ($inputTask.IsCompleted) { $p.StandardInput.Close() } }\n"
                  "$outputTask.Wait()\n$errorTask.Wait()\nexit $p.ExitCode\n")
        expected['scripts/launch.ps1']=launcher.encode('utf-8-sig')
        command='powershell.exe';args=['-NoProfile','-NonInteractive','-File',str(plugin/'scripts/launch.ps1')]
    else:
        launcher='#!/bin/sh\nset -eu\nROOT=$(CDPATH=\'\' cd -- "$(dirname -- "$0")/.." && pwd)\nexec '+shlex.quote(c['runtime_python'])+' "$ROOT/scripts/bridge.py" --data '+shlex.quote(str(data))+'\n'
        expected['scripts/launch.sh']=launcher.encode()
        command='./scripts/launch.sh';args=[]
    mcp={'$schema':'https://agent-plugins.org/schemas/1.0.0/mcp.schema.json','mcpServers':{'freecad':{'type':'stdio','command':command,'args':args,'cwd':'./'}}}
    expected['mcp.json']=(json.dumps(mcp,ensure_ascii=False,indent=2)+'\n').encode()
    if plugin.exists():
        actual={str(p.relative_to(plugin)):p.read_bytes() for p in plugin.rglob('*') if p.is_file() and '__pycache__'not in p.parts}
        if actual!=expected:raise RuntimeError('已有不同生成包，保留不覆盖；更新请新机器根/版本目录')
    else:
        for n,v in expected.items():
            p=plugin/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(v)
            if n.endswith('.sh'):p.chmod(0o755)
    cat={'name':'seagent-freecad-private','plugins':[{'name':'seagent-freecad','source':{'source':'local','path':'./plugin'}}]}
    cp=dest/'.agents/plugins/marketplace.json'
    if cp.exists() and manage.read(cp)!=cat:raise RuntimeError('已有不同marketplace，拒绝覆盖')
    manage.write(cp,cat)
    return dest,plugin


def deploy(data,codex,install=False):
    exe=shutil.which(codex) if not Path(codex).is_absolute() else codex
    if not exe:raise RuntimeError('找不到Codex CLI，请提供实际原生可执行文件')
    version=run(exe,'--version').strip()
    for args in [('plugin','add','--help'),('plugin','marketplace','add','--help')]:run(exe,*args)
    dest,plugin=generate(data)
    summary={'codex':exe,'version':version,'marketplace':str(dest),'plugin':str(plugin),'project_required':False,'gui_started':False}
    if not install:return summary
    catalogs=json.loads(run(exe,'plugin','marketplace','list','--json'))
    if not isinstance(catalogs.get('marketplaces'),list):raise RuntimeError('未知marketplace JSON结构')
    matched=[x for x in catalogs['marketplaces'] if x.get('name')=='seagent-freecad-private']
    if matched and any(Path(x.get('root','')).resolve()!=dest.resolve() for x in matched):raise RuntimeError('同名marketplace已存在于其他路径，拒绝覆盖')
    before=json.loads(run(exe,'plugin','list','--json'))
    if not isinstance(before.get('installed'),list):raise RuntimeError('未知plugin JSON结构')
    ours=[x for x in before['installed'] if x.get('name')=='seagent-freecad' or x.get('pluginId','').startswith('seagent-freecad@')]
    selector='seagent-freecad@seagent-freecad-private'
    for x in ours:
        if x.get('pluginId')!=selector:raise RuntimeError('已有同名FreeCAD插件，保留不覆盖')
    if not matched:run(exe,'plugin','marketplace','add',str(dest),'--json')
    if ours:
        # No reinstall/overwrite. Verify actual existing installation below.
        candidates=[Path(x['installedPath']) for x in ours if x.get('installedPath')]
        if not candidates and (data/'deployment.json').is_file():
            receipt=manage.read(data/'deployment.json')
            if receipt.get('selector')==selector and Path(receipt.get('marketplace','')).resolve()==dest.resolve() and all(Path(x.get('source',{}).get('path','')).resolve()==plugin.resolve() for x in ours):candidates=[Path(receipt['cache'])]
        if not candidates:raise RuntimeError('现插件安装路径未知，拒绝覆盖；请核对本机deployment记录')
        cache=candidates[0]
    else:
        installed=json.loads(run(exe,'plugin','add',selector,'--json'))
        candidate=installed.get('installedPath')
        if not candidate:raise RuntimeError('安装命令未返回installedPath，请保留现场诊断')
        cache=Path(candidate)
    wanted={str(p.relative_to(plugin)):manage.digest(p) for p in plugin.rglob('*') if p.is_file() and '__pycache__'not in p.parts}
    if not cache.is_dir() or any(not(cache/n).is_file() or manage.digest(cache/n)!=h for n,h in wanted.items()):raise RuntimeError('实际安装缓存与生成源码不一致')
    manage.write(data/'deployment.json',dict(selector=selector,marketplace=str(dest),cache=str(cache),files=wanted,codex=exe))
    summary.update(installed=True,installedPath=str(cache),verified_files=len(wanted),note='注册成功不等于CAD已连接；首次项目使用按setup握手')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['check','install']);p.add_argument('--data');p.add_argument('--codex',default='codex');a=p.parse_args()
    try:print(json.dumps(deploy(manage.root(a.data),a.codex,a.action=='install'),ensure_ascii=False,indent=2))
    except Exception as e:print(str(e),file=sys.stderr);sys.exit(1)

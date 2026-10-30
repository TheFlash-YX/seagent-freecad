"""Machine lifecycle and explicit project binding. No CAD business operations."""
from contextlib import contextmanager
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import shlex
import socket
import subprocess
import sys
import time
import uuid

PACKAGE = Path(__file__).resolve().parents[1]


def root(value=None):
    locator=PACKAGE/'machine-locator.json'
    if not value and locator.is_file():value=read(locator)['data']
    if value:
        p = Path(value).expanduser()
        if not p.is_absolute():
            raise ValueError('机器目录必须是绝对路径')
        return p.resolve()
    if os.name == 'nt':
        if not os.environ.get('LOCALAPPDATA'):
            raise ValueError('缺少LOCALAPPDATA，请指定--data')
        return Path(os.environ['LOCALAPPDATA']) / 'SEAgent/FreeCAD'
    return Path.home() / 'Library/Application Support/SEAgent/FreeCAD'


@contextmanager
def locked(data):
    data.mkdir(parents=True,exist_ok=True)
    lock=data/'lifecycle.lock'
    try: lock.mkdir()
    except FileExistsError: raise RuntimeError('另一个管理动作进行中，或保留中断锁；停止并人工检查，不自动清锁')
    try:
        write(lock/'owner.json',{'pid':os.getpid(),'identity':identity(os.getpid())})
        yield
    finally:
        (lock/'owner.json').unlink(missing_ok=True);lock.rmdir()


def prepare(data, project):
    b=bind(data,project)
    receipt=dict(b,marker=uuid.uuid4().hex)
    write(data/'prepare.json',receipt)
    return receipt


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def write(p, v):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    temp = p.with_name(p.name + '.' + uuid.uuid4().hex + '.tmp')
    temp.write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.chmod(0o600); temp.replace(p)


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def separated(*paths):
    for i, a in enumerate(paths):
        for b in paths[i+1:]:
            if a == b or a in b.parents or b in a.parents:
                raise ValueError('源码、机器数据和业务目录必须分离且不能互相包含')


def occupied():
    with socket.socket() as s:
        s.settimeout(.3)
        return s.connect_ex(('127.0.0.1', 9875)) == 0


def powershell(code):
    return subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', code],
                          capture_output=True, text=True, check=True, timeout=15).stdout.strip()


def identity(pid):
    if os.name == 'nt':
        # PID is an integer, never shell text supplied by callers.
        code = f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId={int(pid)}'; if($p){{@{{pid=$p.ProcessId;created=$p.CreationDate.ToUniversalTime().ToString('o');exe=$p.ExecutablePath;command=$p.CommandLine}}|ConvertTo-Json -Compress}}"
        out = powershell(code)
        v=json.loads(out) if out else None
        if v and not all(v.get(k) for k in ('pid','created','exe','command')):raise RuntimeError('进程身份字段不可读，拒绝连接')
        return v
    p = subprocess.run(['/bin/ps','-p',str(int(pid)),'-o','lstart=,command='], capture_output=True,text=True)
    return p.stdout.strip() if p.returncode == 0 else None


def listeners():
    if os.name == 'nt':
        out = powershell("$ErrorActionPreference='Stop'; @(Get-NetTCPConnection -ErrorAction Stop | Where-Object { $_.LocalPort -eq 9875 -and $_.State -eq 'Listen' } | Select-Object -ExpandProperty OwningProcess -Unique)|ConvertTo-Json -Compress")
        v = json.loads(out) if out else []
        return set(v if isinstance(v,list) else [v])
    p = subprocess.run(['/usr/sbin/lsof','-nP','-t','-iTCP:9875','-sTCP:LISTEN'],capture_output=True,text=True)
    if p.returncode not in (0,1):
        raise RuntimeError('无法读取监听归属')
    return {int(x) for x in p.stdout.split()}


def live_instance(data):
    p = data/'instance.json'
    if not p.exists(): return None
    v = read(p)
    return v if identity(v['pid']) == v['identity'] else None


def pending(data):
    return read(data/'pending.json') if (data/'pending.json').exists() else {}


def idle(data):
    if pending(data):
        raise RuntimeError('仍有在途/异步/headless任务或未知状态；先查询到终态，不强杀，不把超时当完成')


def validate_runtime(data):
    ready = read(data/'runtime/READY.json')
    lock = read(PACKAGE/'upstream.lock.json')
    if ready['commit'] != lock['commit']: raise RuntimeError('运行时版本不匹配')
    src = data/'runtime/upstream'
    manifest = read(data/'runtime/upstream-files.json')
    if not manifest or any(not (src/n).is_file() or digest(src/n)!=h for n,h in manifest.items()):
        raise RuntimeError('固定上游文件不一致，保留原状')
    return ready


def file_version(path):
    if os.name=='nt':
        quoted=str(path).replace("'","''")
        try:return powershell("$ErrorActionPreference='Stop'; [Diagnostics.FileVersionInfo]::GetVersionInfo('"+quoted+"').FileVersion") or '待验证：文件无版本信息'
        except subprocess.SubprocessError:return '待验证：无法读取文件版本'
    for parent in Path(path).parents:
        if parent.suffix=='.app':
            try:
                with (parent/'Contents/Info.plist').open('rb') as f:v=plistlib.load(f)
                return v.get('CFBundleShortVersionString') or v.get('CFBundleVersion') or '待验证：app无版本'
            except (OSError,ValueError):return '待验证：无法读取Info.plist'
    return '待验证：非app布局，无静态版本信息'


def configure(data, gui, cmd):
    gui, cmd = Path(gui).expanduser().resolve(strict=True), Path(cmd).expanduser().resolve(strict=True)
    if not gui.is_file() or not cmd.is_file(): raise ValueError('请提供FreeCAD GUI和FreeCADCmd实际可执行文件')
    separated(PACKAGE.parents[2], data)
    ready=validate_runtime(data)
    if os.name == 'nt' and gui.parent != cmd.parent: raise ValueError('Windows GUI/FreeCADCmd应来自同一发行目录')
    v={'schema':1,'source_root':str(PACKAGE.parents[2]),'gui':str(gui),'freecadcmd':[str(cmd)],'runtime_python':ready['python'],'commit':ready['commit'],'gui_version':file_version(gui),'freecadcmd_version':file_version(cmd),'gui_python_version':'待真实FreeCAD环境验证'}
    p=data/'machine.json'
    if p.exists() and read(p)!=v: raise RuntimeError('已有不同机器配置，拒绝覆盖；显式升级需保留旧配置')
    write(p,v)
    return {'machine_ready':True,'project_bound':False,'cad_started':False}


def bind(data, project):
    p=Path(project).expanduser()
    if not p.is_absolute(): raise ValueError('项目必须来自宿主实际cwd绝对路径')
    p=p.resolve(strict=True)
    if not p.is_dir(): raise ValueError('项目不是文件夹')
    separated(Path(read(data/'machine.json')['source_root']).resolve(), data, p)
    if not (data/'machine.json').exists(): raise RuntimeError('先完成机器安装')
    old=read(data/'binding.json') if (data/'binding.json').exists() else None
    if old and old['project']==str(p): return old
    idle(data)
    if live_instance(data) or occupied(): raise RuntimeError('切项目前请保存并自行退出旧FreeCAD；未知9875不接管')
    v={'schema':1,'project':str(p),'generation':uuid.uuid4().hex}
    write(data/'binding.json',v)
    return v


def guard(data, snapshot):
    current=read(data/'binding.json')
    if current!=snapshot: raise RuntimeError('旧项目连接已失效；不能控制新项目，请在当前项目建立新连接')
    inst=live_instance(data)
    if not inst or inst['generation']!=snapshot['generation'] or inst['project']!=snapshot['project']:
        raise RuntimeError('当前项目没有可信受管FreeCAD实例；先用管理脚本start')
    if listeners()!={inst['pid']}: raise RuntimeError('9875监听归属不匹配，拒绝RPC')
    receipt=read(data/'receipt.json')
    if receipt.get('generation')!=snapshot['generation'] or receipt.get('pid')!=inst['pid'] or receipt.get('cwd')!=snapshot['project']:
        raise RuntimeError('启动回执与项目身份不一致')
    validate_runtime(data)
    return inst


def start(data):
    c=read(data/'machine.json'); b=read(data/'binding.json')
    old=live_instance(data)
    if old:
        guard(data,b)
        return {'reused':True,'pid':old['pid'],'project':b['project']}
    idle(data)
    if occupied(): raise RuntimeError('9875未知监听，拒绝连接/接管/换端口；保留已有实例')
    validate_runtime(data)
    profile=data/'profile';profile.mkdir(exist_ok=True)
    if (profile/'Mod/FreeCADMCP').exists(): raise RuntimeError('已有同名Addon，拒绝覆盖')
    addon=data/'runtime/upstream/addon/FreeCADMCP'
    macro=data/'start.FCMacro'
    # Upstream remains unmodified. No document creation/import/save/close.
    code=f'''import sys, os, json\nfrom pathlib import Path\nos.chdir({b['project']!r})\naddon={str(addon)!r}\nif any('rpc_server' in n and getattr(m,'__file__',None) and not str(Path(m.__file__).resolve()).startswith(addon+os.sep) for n,m in list(sys.modules.items())): raise RuntimeError('Conflicting Addon')\nsys.path.insert(0,addon)\nfrom rpc_server import rpc_server, settings\ns=settings.load_settings()\ns['remote_enabled']=False\ns['allowed_ips']='127.0.0.1'\ns['auto_start_rpc']=False\ns['auth_token']=os.environ.get('FREECAD_MCP_TOKEN','')\nsettings.save_settings(s)\nrpc_server.start_rpc_server()\nPath({str(data/'receipt.json')!r}).write_text(json.dumps({{'pid':os.getpid(),'cwd':os.getcwd(),'generation':{b['generation']!r}}}),encoding='utf-8')\n'''
    macro.write_text(code,encoding='utf-8')
    argv=[c['gui'],'--user-cfg',str(profile/'user.cfg'),'--system-cfg',str(profile/'system.cfg'),'-M',str(addon.parent),str(macro)]
    env=os.environ.copy();env.update(FREECAD_USER_HOME=str(profile),FREECAD_USER_DATA=str(profile),PYTHONNOUSERSITE='1')
    (data/'logs').mkdir(exist_ok=True)
    with (data/'logs/freecad.log').open('ab') as out:
        proc=subprocess.Popen(argv,cwd=b['project'],env=env,stdout=out,stderr=out)
    time.sleep(.5); ident=identity(proc.pid)
    if not ident: raise RuntimeError('FreeCAD启动退出；请检查本地日志，不自动重试')
    write(data/'instance.json',dict(pid=proc.pid,identity=ident,argv=argv,project=b['project'],generation=b['generation']))
    return {'start_requested':True,'pid':proc.pid,'rpc_ready':'待连接自检，不等于已就绪'}


def resolve(data,request,reason):
    if not reason.strip():raise ValueError('必须记录人工核验依据，不是超时自动清除')
    if live_instance(data) or occupied():raise RuntimeError('仍有GUI或9875，不能离线解除未知任务')
    if os.name=='nt':
        out=powershell(r"$ErrorActionPreference='Stop'; @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object { $_.Name -match '(?i)^freecad(cmd)?\.exe$' } | Select-Object -ExpandProperty ProcessId)|ConvertTo-Json -Compress")
        if out and json.loads(out):raise RuntimeError('仍有FreeCAD/FreeCADCmd进程，不能解除')
    else:
        p=subprocess.run(['/bin/ps','-axo','comm='],capture_output=True,text=True,check=True)
        if any(Path(x.strip()).name.lower() in ('freecad','freecadcmd') for x in p.stdout.splitlines()):raise RuntimeError('仍有FreeCAD/FreeCADCmd进程，不能解除')
    jobs=pending(data)
    if request not in jobs:raise ValueError('未知任务记录ID')
    audit=data/'recovery-audit.json';history=read(audit) if audit.exists() else []
    history.append({'request':request,'record':jobs.pop(request),'reason':reason,'time':time.time()})
    write(audit,history);write(data/'pending.json',jobs)
    return {'cleared_after_manual_offline_audit':request}


def status(data):
    report={'machine':(data/'machine.json').exists(),'bound':(data/'binding.json').exists(),
            'port_9875_occupied':occupied(),'rpc_queried':False,'pending_tasks':len(pending(data)),
            'binding':read(data/'binding.json') if (data/'binding.json').exists() else None}
    try:
        ready=validate_runtime(data);report['runtime_verified']=True
        report['python_exists']=Path(ready['python']).is_file()
        if report['machine']:
            c=read(data/'machine.json')
            report.update(gui_exists=Path(c['gui']).is_file(),freecadcmd_exists=Path(c['freecadcmd'][0]).is_file(),gui_version=file_version(c['gui']),freecadcmd_version=file_version(c['freecadcmd'][0]),gui_python_version=c.get('gui_python_version','待验证'))
        if (data/'deployment.json').exists():
            v=read(data/'deployment.json');cache=Path(v['cache'])
            report['cache_verified']=cache.is_dir() and all((cache/n).is_file() and digest(cache/n)==h for n,h in v['files'].items())
        else:report['cache_verified']='未注册'
    except (OSError,ValueError,RuntimeError,KeyError) as e:report['check_error']=str(e)
    report['healthy']=bool(report.get('machine') and report.get('runtime_verified') and report.get('python_exists') and report.get('gui_exists') and report.get('freecadcmd_exists') and report.get('cache_verified') is True and not report.get('check_error'))
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--data'); sp=ap.add_subparsers(dest='action',required=True)
    c=sp.add_parser('configure');c.add_argument('--gui',required=True);c.add_argument('--freecadcmd',required=True)
    b=sp.add_parser('bind');b.add_argument('--project',required=True)
    q=sp.add_parser('prepare');q.add_argument('--project',required=True)
    z=sp.add_parser('resolve-offline');z.add_argument('--request',required=True);z.add_argument('--reason',required=True)
    sp.add_parser('start');sp.add_parser('doctor')
    a=ap.parse_args();d=root(a.data)
    try:
        if a.action=='configure':v=configure(d,a.gui,a.freecadcmd)
        elif a.action in ('bind','prepare'):
            with locked(d):v=prepare(d,a.project)
        elif a.action=='start':
            with locked(d):v=start(d)
        elif a.action=='resolve-offline':
            with locked(d):v=resolve(d,a.request,a.reason)
        else:v=status(d)
        print(json.dumps(v,ensure_ascii=False,indent=2));return (0 if v.get('healthy') else 1) if a.action=='doctor' else 0
    except (OSError,ValueError,RuntimeError,KeyError,subprocess.SubprocessError) as e:
        print('SEAgent FreeCAD: '+str(e),file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())

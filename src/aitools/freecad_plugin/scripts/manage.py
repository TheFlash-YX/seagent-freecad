#!/usr/bin/env python3
"""Local installation/process management only; never implements a CAD/MCP tool."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import time

PACKAGE = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('SEAGENT_FREECAD_DATA', str(Path.home() / 'Library/Application Support/SEAgentFreeCAD'))).expanduser().resolve()
# Imported by tests as well as invoked directly from the scripts directory.
sys.path.insert(0, str(PACKAGE / 'scripts'))
from source_integrity import (COMMIT as SHA, OWNER, OWNERS, atomic_json, validate_data,
                              verify_installed, verify_ready, runtime_lease, read_json, refuse_active)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.chmod(0o600)
    temporary.replace(path)


def config():
    return json.loads((DATA / 'config.json').read_text())


def occupied():
    with socket.socket() as sock:
        sock.settimeout(.4)
        return sock.connect_ex(('127.0.0.1', 9875)) == 0


def identity(pid):
    p = subprocess.run(['/bin/ps', '-p', str(pid), '-o', 'lstart=,command='], text=True, capture_output=True)
    return p.stdout.strip() if p.returncode == 0 else None


def listener_pids():
    p = subprocess.run(['/usr/sbin/lsof', '-nP', '-t', '-iTCP:9875', '-sTCP:LISTEN'], capture_output=True, text=True)
    if p.returncode not in (0, 1):
        raise RuntimeError('无法检查9875监听归属，拒绝连接')
    return {int(x) for x in p.stdout.split()}


def owned_listener():
    instance = DATA / 'instance.json'
    if not instance.is_file():
        return False
    old = json.loads(instance.read_text())
    return identity(old['pid']) == old['identity'] and listener_pids() == {old['pid']}


def guard_connection():
    if occupied() and not owned_listener():
        raise RuntimeError('9875监听不属于本插件受管实例，拒绝启动MCP；未ping未知RPC、不接管、不换端口')


def configure(app):
    verify_ready(DATA, PACKAGE)
    app = Path(app).expanduser().resolve()
    gui = app / 'Contents/Resources/bin/freecad'
    cmd = app / 'Contents/Resources/bin/freecadcmd'
    if not gui.is_file() or not cmd.is_file():
        raise RuntimeError('FreeCAD app无预期可执行文件；目前仅支持macOS app布局')
    source = DATA / 'runtime/upstream'
    addon = source / 'addon/FreeCADMCP'
    if not (addon / 'InitGui.py').is_file():
        raise RuntimeError('先运行bootstrap准备固定上游')
    value = {'freecad_app': str(app), 'gui': str(gui), 'freecadcmd': [str(cmd)], 'addon_path': str(addon), 'upstream_commit': SHA}
    current = DATA / 'config.json'
    if current.exists() and json.loads(current.read_text()) != value:
        raise RuntimeError('已有不同配置，保留原文件。请先备份并显式移除config.json后重新configure')
    write_json(current, value)
    print('已配置；未启动FreeCAD。凭据请用原版FREECAD_MCP_TOKEN环境及专用Addon设置，不记录到配置。')


def inventory():
    files = {}
    previous = DATA / 'owned-files.json'
    allowed = None
    if previous.exists():
        own = read_json(previous)
        if own.get('owner') not in OWNERS:
            raise RuntimeError('未知归属清单，拒绝接管')
        allowed = set(own['files'])

    for p in (DATA / 'runtime').rglob('*'):
        name = p.relative_to(DATA).as_posix()
        # Only generated program trees; never enroll arbitrary runtime root/user files.
        if p.relative_to(DATA / 'runtime').parts[0] not in {'uv','python','upstream','.venv'}:
            continue
        if allowed is not None:
            if name in allowed and (p.is_file() or p.is_symlink()):
                files[name] = own['files'][name]  # Do not enroll user edits as new trusted ownership.
            continue
        if p.is_symlink():
            files[str(p.relative_to(DATA))] = {'link': os.readlink(p)}
        elif p.is_file():
            files[str(p.relative_to(DATA))] = {'sha256': digest(p)}
    write_json(DATA / 'owned-files.json', {'owner': OWNER, 'files': files})


def verify_upstream():
    return len(verify_installed(DATA, PACKAGE)[1])


def verify_config():
    c = config()
    if c.get('upstream_commit') != SHA or c.get('addon_path') != str(DATA / 'runtime/upstream/addon/FreeCADMCP'):
        raise RuntimeError('配置来源或Addon路径与本DATA不匹配')
    return c


def doctor():
    report = {'data': str(DATA), 'configured': (DATA / 'config.json').is_file(), 'python': (DATA / 'runtime/.venv/bin/python').is_file(), 'port_9875_occupied': occupied(), 'gui_started_by_doctor': False}
    try:
        report['upstream_unchanged_files'] = verify_upstream()
        verify_ready(DATA, PACKAGE)
    except Exception as exc:
        report['upstream_error'] = str(exc)
    if report['configured']:
        c = config()
        report['freecadcmd_exists'] = bool(c.get('freecadcmd')) and Path(c['freecadcmd'][0]).is_file() and os.access(c['freecadcmd'][0], os.X_OK)
        report['gui_exists'] = Path(c.get('gui','')).is_file() and os.access(c.get('gui',''), os.X_OK)
    if report['port_9875_occupied']:
        report['port_notice'] = '仅检测TCP监听；未调用未知RPC、未接管。start将验证归属或拒绝。'
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['configured'] and report['python'] and report.get('freecadcmd_exists') and report.get('gui_exists') and not report.get('upstream_error') else 1


def start():
    if (DATA / ".bootstrap-lock").exists():
        raise RuntimeError("运行时安装中，拒绝启动")
    lease = runtime_lease(DATA)
    try:
        return _start()
    finally:
        os.close(lease)


def _start():
    verify_ready(DATA, PACKAGE)
    c = verify_config()
    instance = DATA / 'instance.json'
    if instance.exists():
        old = json.loads(instance.read_text())
        if identity(old['pid']) == old['identity']:
            if not occupied():
                raise RuntimeError('受管FreeCAD仍存在但9875未就绪；保留窗口，检查日志，不重复启动')
            guard_connection()
            print('受管FreeCAD及9875监听PID一致；不重复启动。请get_rpc_status/list_documents重新查询。')
            return 0
    if occupied():
        raise RuntimeError('9875已被其他或未知服务占用；不连接、不接管、不杀进程、不换端口。请用户自行释放后再start')
    verify_upstream()
    profile = DATA / 'freecad-profile'
    profile.mkdir(parents=True, exist_ok=True)
    # Never overwrite or load a conflicting same-name addon in this dedicated profile.
    conflicting = profile / 'Mod/FreeCADMCP'
    if conflicting.exists():
        raise RuntimeError('专用profile已有FreeCADMCP Addon，保留并拒绝覆盖')
    macro = DATA / 'start-addon.FCMacro'
    # Only startup of the unmodified addon. No model import, GUI modification or CAD tool wrapper.
    code = f'''import sys\nfrom pathlib import Path\naddon = {c['addon_path']!r}\nif any(getattr(m, '__file__', None) and 'rpc_server' in n and not str(Path(m.__file__).resolve()).startswith(addon + '/') for n, m in list(sys.modules.items())):\n    raise RuntimeError('Conflicting RPC Addon already loaded')\nsys.path.insert(0, addon)\nfrom rpc_server import rpc_server, settings\ns = settings.load_settings()\nimport os\ns['remote_enabled'] = False\ns['allowed_ips'] = '127.0.0.1'\ns['auto_start_rpc'] = False\ns['auth_token'] = os.environ.get('FREECAD_MCP_TOKEN', '')\nsettings.save_settings(s)\nFreeCAD.Console.PrintMessage(str(rpc_server.start_rpc_server()) + '\\n')\n'''
    macro.write_text(code)
    env = os.environ.copy()
    env['FREECAD_USER_HOME'] = str(profile)
    env['FREECAD_USER_DATA'] = str(profile)
    env['PYTHONNOUSERSITE'] = '1'
    logs = DATA / 'logs'
    logs.mkdir(exist_ok=True)
    argv = [c['gui'], '--user-cfg', str(profile / 'user.cfg'), '--system-cfg', str(profile / 'system.cfg'), '-M', str(Path(c['addon_path']).parent), str(macro)]
    with (logs / 'freecad.log').open('ab') as out:
        proc = subprocess.Popen(argv, env=env, stdout=out, stderr=out, start_new_session=True)
    time.sleep(.4)
    fingerprint = identity(proc.pid)
    if not fingerprint:
        raise RuntimeError('FreeCAD启动退出；检查本地logs/freecad.log；未重试')
    write_json(instance, {'pid': proc.pid, 'identity': fingerprint, 'app': c['freecad_app'], 'started_at': time.time(), 'argv': argv})
    print('专用FreeCAD启动请求已发送；未宣称RPC就绪。使用get_rpc_status确认版本，再list_documents；失败查本地日志，不盲重试。')
    return 0


def exec_mcp(extra):
    if (DATA / ".bootstrap-lock").exists():
        raise RuntimeError("运行时安装中，拒绝启动MCP")
    lease = runtime_lease(DATA)  # Deliberately inherited through os.execv until MCP exits.
    verify_ready(DATA, PACKAGE)
    c = verify_config()
    guard_connection()
    verify_upstream()
    executable = DATA / 'runtime/.venv/bin/freecad-mcp'
    if c.get('upstream_commit') != SHA:
        raise RuntimeError('配置上游版本不匹配')
    # Preserve stdio, signals, environment and upstream return status. No GUI startup.
    os.execv(str(executable), [str(executable), '--host', '127.0.0.1', '--freecadcmd', shlex.join(c['freecadcmd']), *extra])


def uninstall(remove_runtime):
    # Never terminate a GUI, remove models, or modify Codex's cache/config ourselves.
    if not remove_runtime:
        print('请用codex plugin remove卸载注册。配置、模型、日志、运行时均保留；需清理自有运行时请显式加--remove-runtime。')
        return
    validate_data(DATA, PACKAGE)
    if (DATA / '.bootstrap-lock').exists():
        raise RuntimeError('运行时安装中，拒绝清理')
    refuse_active(DATA)
    lease = runtime_lease(DATA, exclusive=True)
    try:
        refuse_active(DATA)
        return _remove_owned_runtime()
    finally:
        os.close(lease)


def _remove_owned_runtime():
    own = read_json(DATA / 'owned-files.json')
    if own.get('owner') not in OWNERS:
        raise RuntimeError('归属标记不匹配')
    if (DATA / 'instance.json').exists():
        old = json.loads((DATA / 'instance.json').read_text())
        if identity(old['pid']) == old['identity']:
            raise RuntimeError('专用FreeCAD仍在运行，先自行保存并退出；卸载不自动关闭')
    kept = []
    for name, expected in own['files'].items():
        p = DATA / name
        if not p.is_relative_to(DATA / 'runtime') or '..' in Path(name).parts:
            raise RuntimeError('非法归属清单路径')
        if not p.is_symlink() and not p.resolve().is_relative_to((DATA / 'runtime').resolve()):
            kept.append(name)
            continue
        if p.is_symlink():
            same = expected.get('link') == os.readlink(p)
        elif p.is_file():
            same = expected.get('sha256') == digest(p)
        else:
            continue
        if same:
            p.unlink()
        else:
            kept.append(name)
    for p in sorted((DATA / 'runtime').rglob('*'), key=lambda x: len(x.parts), reverse=True):
        if p.is_dir() and not p.is_symlink():
            try:
                p.rmdir()
            except OSError:
                pass
    print(json.dumps({'removed': 'unchanged_owned_runtime_files_only', 'preserved_modified_files': kept, 'data_preserved': str(DATA)}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    c = sub.add_parser('configure'); c.add_argument('--freecad-app', required=True)
    sub.add_parser('start')
    sub.add_parser('inventory')
    sub.add_parser('verify-upstream')
    e = sub.add_parser('exec-mcp'); e.add_argument('extra', nargs=argparse.REMAINDER)
    u = sub.add_parser('uninstall'); u.add_argument('--remove-runtime', action='store_true')
    args = parser.parse_args()
    try:
        validate_data(DATA, PACKAGE)
        if args.command == 'configure': configure(args.freecad_app)
        elif args.command == 'doctor': return doctor()
        elif args.command == 'start': return start()
        elif args.command == 'inventory': inventory()
        elif args.command == 'verify-upstream': print(verify_upstream())
        elif args.command == 'exec-mcp': exec_mcp(args.extra[1:] if args.extra[:1] == ['--'] else args.extra)
        elif args.command == 'uninstall': uninstall(args.remove_runtime)
    except (OSError, ValueError, RuntimeError, KeyError, ImportError, TypeError) as exc:
        print(f'SEAgent FreeCAD: {exc}', file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

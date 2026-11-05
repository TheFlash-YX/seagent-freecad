"""Vendored source contract. No downloads, CAD imports or environment mutation."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile

COMMIT = '8babe9927ce8e6e8fe7dd6ae2ffa2c93776e845a'
OWNER = 'seagent-freecad-0.1.1'
OWNERS = {OWNER, 'seagent-freecad-0.1.0'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('重复JSON字段：' + key)
        result[key] = value
    return result


def read_json(path):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError('缺失或链接元数据：' + str(path))
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=_unique)


def atomic_json(path, value):
    if path.is_symlink():
        raise RuntimeError('拒绝链接元数据：' + str(path))
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def safe_name(name):
    if not isinstance(name, str) or not name or '\\' in name or '\x00' in name:
        raise ValueError('非法清单路径')
    path = PurePosixPath(name)
    if path.is_absolute() or str(path) != name or any(x in ('.', '..', '.git') for x in path.parts):
        raise ValueError('非法清单路径：' + name)
    return path


def validate_data(data, package):
    """Resolve DATA, reject source overlap and linked runtime/metadata before writes."""
    package = package.resolve()
    # The plugin has a fixed src/aitools/<plugin> layout in this distribution.
    repository = package.parents[2] if package.parent.name == 'aitools' else package
    data = data.expanduser().absolute()
    resolved = data.resolve()
    if resolved == repository or resolved.is_relative_to(repository) or repository.is_relative_to(resolved):
        raise RuntimeError('DATA与插件/项目源码路径重叠')
    for marker in ('.git', 'AGENTS.md', 'pyproject.toml', 'package.json'):
        if (resolved / marker).exists():
            raise RuntimeError('DATA指向其他项目源码：' + marker)
    for relative in ('runtime', 'runtime/upstream', 'runtime/upstream.partial', 'runtime/READY',
                     'runtime/READY.previous', 'runtime-use.lock', 'runtime/python.partial', 'runtime/uv.partial', 'runtime/.venv', 'runtime/python', 'runtime/uv', 'upstream-files.json', 'source-transaction.json', 'downloads'):
        path = resolved / relative
        if path.is_symlink() or not path.resolve().is_relative_to(resolved):
            raise RuntimeError('DATA中存在链接/逃逸路径：' + relative)
    return resolved


def verify_tree(root, files, runtime=False):
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError('源码目录缺失或为链接：' + str(root))
    expected_dirs = {str(parent) for name in files for parent in PurePosixPath(name).parents if str(parent) != '.'}
    actual = set()
    bad = []
    for directory, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            path = Path(directory) / name
            rel = path.relative_to(root).as_posix()
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                bad.append(rel + ' (链接/异常条目)'); continue
            if stat.S_ISDIR(mode):
                cache = runtime and name == '__pycache__' and any(str(PurePosixPath(f).parent) == str(PurePosixPath(rel).parent) and f.endswith('.py') for f in files)
                if rel not in expected_dirs and not cache:
                    bad.append(rel + ' (额外目录)')
                continue
            if rel not in files:
                # Only CPython bytecode for a managed Python module, in its own __pycache__.
                match = re.fullmatch(r'(.+)\.cpython-\d{2,3}(?:\.opt-[12])?\.pyc', name)
                original = (path.parent.parent / (match.group(1) + '.py')).relative_to(root).as_posix() if match else ''
                if not (runtime and path.parent.name == '__pycache__' and match and original in files):
                    bad.append(rel + ' (额外文件)')
                continue
            actual.add(rel)
            record = files[rel]
            gitmode = '100755' if mode & 0o111 else '100644'
            if path.stat().st_size != record['size'] or sha(path) != record['sha256'] or gitmode != record['mode']:
                bad.append(rel + ' (内容/大小/mode)')
    bad.extend(name + ' (缺失)' for name in sorted(set(files) - actual))
    if bad:
        raise RuntimeError('源码不一致：' + ', '.join(bad[:8]))


def expected(package):
    lock = read_json(package / 'upstream.lock.json')
    source = lock.get('source', {})
    if lock.get('schema_version') != 2 or lock.get('commit') != COMMIT or lock.get('version') != '0.1.28' or source.get('type') != 'vendored' or source.get('path') != 'vendor/freecad-mcp' or source.get('manifest') != 'vendor-files.json':
        raise RuntimeError('不支持的内置来源配置')
    manifest_path = package / 'vendor-files.json'
    if manifest_path.is_symlink() or sha(manifest_path) != source['manifest_sha256']:
        raise RuntimeError('内置清单哈希不一致')
    manifest = read_json(manifest_path)
    if manifest.get('schema_version') != 1 or manifest.get('upstream_commit') != COMMIT:
        raise RuntimeError('内置清单版本不一致')
    files = manifest['files']
    if not isinstance(files, dict) or not files:
        raise RuntimeError('内置清单为空')
    for name, record in files.items():
        safe_name(name)
        if set(record) != {'sha256', 'size', 'mode'} or not re.fullmatch('[0-9a-f]{64}', record['sha256']) or type(record['size']) is not int or record['size'] < 0 or record['mode'] not in ('100644', '100755'):
            raise ValueError('非法文件记录：' + name)
    vendor = package / source['path']
    if (package / 'vendor').is_symlink():
        raise RuntimeError('vendor目录为链接')
    verify_tree(vendor, files)
    for path in (vendor / 'uv.lock', package / 'uv.lock'):
        if sha(path) != lock['dependency_lock_sha256']:
            raise RuntimeError('传递依赖锁不一致')
    if sha(package / 'build-requirements.lock') != lock['build_dependency_lock_sha256']:
        raise RuntimeError('构建依赖锁不一致')
    return lock, files


def hashes(files):
    return {name: record['sha256'] for name, record in files.items()}


def verify_installed(data, package):
    data = validate_data(data, package)
    lock, files = expected(package)
    manifest = read_json(data / 'upstream-files.json')
    if manifest != hashes(files):
        raise RuntimeError('已安装清单与当前内置来源不一致；保留旧目录，请使用新DATA或显式迁移')
    verify_tree(data / 'runtime/upstream', files, runtime=True)
    return lock, files


def verify_environment(data, package):
    """Run with the DATA venv Python; reject global/foreign CLI and local project origins."""
    import importlib.metadata
    import sys
    venv = data / 'runtime/.venv'
    if Path(sys.prefix).resolve() != venv.resolve():
        raise RuntimeError('必须使用本DATA的venv Python')
    import freecad_mcp
    import freecad_mcp.server  # Verify the actual CLI server imports and locked runtime dependencies.
    module = Path(freecad_mcp.__file__).resolve()
    if not module.is_relative_to(venv.resolve()):
        raise RuntimeError('实际导入不属于本DATA')
    cli = venv / 'bin/freecad-mcp'
    if cli.is_symlink() or not cli.is_file() or not os.access(cli, os.X_OK):
        raise RuntimeError('CLI缺失或为链接')
    first = cli.read_text().splitlines()
    # uv uses a shell trampoline when the venv path contains spaces.
    if str(venv / 'bin/python') not in '\n'.join(first[:4]):
        raise RuntimeError('CLI解释器不属于本DATA')
    dist = importlib.metadata.distribution('freecad-mcp')
    direct = json.loads(dist.read_text('direct_url.json') or '{}')
    if dist.version != '0.1.28' or direct.get('url') != (data / 'runtime/upstream').as_uri() or direct.get('dir_info', {}).get('editable'):
        raise RuntimeError('安装元数据不是本DATA的本地内置项目')
    return {'module': str(module), 'cli': str(cli), 'version': dist.version, 'direct_url': direct}


def ready_value(package):
    lock, _ = expected(package)
    return {'schema_version': 1, 'plugin_version': read_json(package / 'plugin.json')['version'],
            'upstream_commit': lock['commit'], 'manifest_sha256': lock['source']['manifest_sha256']}


def verify_ready(data, package):
    if read_json(data / 'runtime/READY') != ready_value(package):
        raise RuntimeError('READY不属于当前插件；用新DATA重新bootstrap')
    verify_installed(data, package)
    return verify_environment(data, package)


def process_identity(pid):
    import subprocess
    p = subprocess.run(['/bin/ps', '-p', str(pid), '-o', 'lstart=,command='], text=True, capture_output=True)
    if p.returncode not in (0, 1):
        raise RuntimeError('无法核对受管进程身份')
    return p.stdout.strip() if p.returncode == 0 else None


def refuse_active(data):
    """No RPC calls: protect recorded FreeCAD and detectable legacy runtime processes."""
    import subprocess
    instance = data / 'instance.json'
    if instance.exists():
        old = read_json(instance)
        if process_identity(old['pid']) == old['identity']:
            raise RuntimeError('受管FreeCAD仍在运行；请先保存并退出，拒绝修改源码或venv')
    if not (data / 'runtime/.venv').exists():
        return  # A new DATA has no old MCP environment to modify.
    ready = data / 'runtime/READY'
    if ready.is_file():
        try:
            if read_json(ready).get('plugin_version') == '0.1.1':
                return  # Current launcher holds runtime_lease across exec.
        except (ValueError, AttributeError):
            pass  # Legacy or interrupted READY requires process inspection.
    p = subprocess.run(['/bin/ps', '-axo', 'pid=,command='], text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError('无法检查运行时进程；拒绝修改')
    for line in p.stdout.splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) == 2 and int(fields[0]) != os.getpid() and any(str(data / path) in fields[1] for path in ('runtime/.venv/bin/', 'runtime/python/bin/')):
            raise RuntimeError('检测到本DATA的活动Python/MCP进程；先退出后安装')


def runtime_lease(data, exclusive=False):
    """POSIX nonblocking advisory lease, inherited across MCP exec (macOS support)."""
    import fcntl
    path = data / 'runtime-use.lock'
    if path.is_symlink():
        raise RuntimeError('运行锁为链接')
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        raise RuntimeError('本DATA存在活动MCP/安装租约，拒绝并发修改') from None
    os.set_inheritable(fd, True)
    return fd

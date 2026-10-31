"""Extract and verify the fixed upstream, without touching existing installations."""
import hashlib
import json
from pathlib import Path
import sys
import tarfile

root, package = map(Path, sys.argv[1:])
lock = json.loads((package / 'upstream.lock.json').read_text())
source = root / 'runtime/upstream'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
manifest_path = root / 'upstream-files.json'
if source.exists():
    if not manifest_path.is_file():
        raise SystemExit('已有无来源清单upstream，拒绝覆盖')
    manifest = json.loads(manifest_path.read_text())
    if any(not (source / p).is_file() or sha(source / p) != h for p, h in manifest.items()):
        raise SystemExit('已有上游源被修改，拒绝覆盖')
else:
    staging = root / 'runtime/upstream.partial'
    if staging.exists():
        raise SystemExit('保留中断安装upstream.partial；请检查后显式移除再安装')
    staging.mkdir()
    with tarfile.open(root / 'downloads/upstream.tar.gz') as archive:
        archive.extractall(staging, filter='data')
    extracted = staging / ('freecad-mcp-' + lock['commit'])
    manifest = {str(p.relative_to(extracted)): sha(p) for p in extracted.rglob('*') if p.is_file()}
    if sha(extracted / 'uv.lock') != lock['dependency_lock_sha256']:
        raise SystemExit('传递依赖锁与固定来源不一致')
    extracted.rename(source)
    staging.rmdir()
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
if sha(source / 'uv.lock') != sha(package / 'uv.lock'):
    raise SystemExit('随包与上游依赖锁不一致')

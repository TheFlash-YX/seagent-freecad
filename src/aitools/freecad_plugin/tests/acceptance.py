"""Independent acceptance driver; default has no GUI. Nonzero means failed/blocked.

Use an orchestration Python outside the DATA being tested. Never uses an old venv.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / 'scripts'))
from source_integrity import expected, validate_data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', required=True, type=Path, help='new, exclusive DATA outside repository')
    p.add_argument('--output', required=True, type=Path, help='new evidence directory outside repository/DATA')
    p.add_argument('--artifact-cache', type=Path, help='optional read-only uv.tar.gz/python.tar.gz inputs; no upstream/cache copied')
    p.add_argument('--freecad-app', required=True, type=Path)
    p.add_argument('--gui', action='store_true', help='explicitly start a dedicated GUI and test synthetic box')
    args = p.parse_args()
    data = validate_data(args.data, PACKAGE)
    out = args.output.resolve()
    if data.exists() or out.exists():
        raise RuntimeError('验收必须使用不存在的新DATA和证据目录')
    if out.is_relative_to(PACKAGE.parents[2]) or out.is_relative_to(data) or data.is_relative_to(out):
        raise RuntimeError('证据必须与源码和DATA分离')
    lock, _ = expected(PACKAGE)
    out.mkdir(parents=True); (data/'downloads').mkdir(parents=True)
    results = {'cache': {'upstream_archive': False, 'uv_package_cache_initially_empty': True}, 'commands': [],
               'network_scope':'curl wrapper plus static executable-source audit only; no full process network isolation',
               'gui':'not requested', 'host_plugin':'not tested/changed'}
    env = dict(os.environ, SEAGENT_FREECAD_DATA=str(data), PYTHONDONTWRITEBYTECODE='1')
    def record(): (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    def run(label, command, expected_code=0):
        with (out/(label+'.stdout')).open('w') as stdout, (out/(label+'.stderr')).open('w') as stderr:
            r = subprocess.run([str(x) for x in command], env=env, stdout=stdout, stderr=stderr)
        results['commands'].append({'label':label,'argv':[str(x) for x in command], 'exit_code':r.returncode, 'expected':expected_code})
        record()
        if r.returncode != expected_code:
            raise RuntimeError(label+'失败/阻塞，退出码 '+str(r.returncode))
    try:
        if args.artifact_cache:
            for name in ('uv', 'python'):
                source = args.artifact_cache/(name+'.tar.gz')
                if not source.exists():
                    results['cache'][name+'_distribution_preseeded'] = False
                    continue
                if hashlib.sha256(source.read_bytes()).hexdigest() != lock[name]['sha256']:
                    raise RuntimeError('发行包哈希失败：'+name)
                shutil.copyfile(source, data/'downloads'/source.name)
                results['cache'][name+'_distribution_preseeded'] = True
        real_curl = shutil.which('curl')
        if not real_curl: raise RuntimeError('curl不可用')
        wrapper = out/'bin'; wrapper.mkdir()
        script = wrapper/'curl'
        script.write_text('''#!/bin/sh
for arg do
  case "$arg" in *neka-nat/freecad-mcp*) echo "BLOCKED $arg" >> "$SEAGENT_CURL_AUDIT"; exit 97;; esac
done
printf '%s\\n' "$@" >> "$SEAGENT_CURL_AUDIT"
exec '''+shlex.quote(real_curl)+''' "$@"
''')
        script.chmod(0o755)
        env['PATH']=str(wrapper)+os.pathsep+env.get('PATH','')
        env['SEAGENT_CURL_AUDIT']=str(out/'curl-wrapper-selftest.txt')
        run('curl-wrapper-selftest', [script, lock['archive_url']], expected_code=97)
        env['SEAGENT_CURL_AUDIT']=str(out/'curl-install.txt')
        # Executable installer/launcher sources only. Vendor/docs/lock provenance URLs are allowed.
        active='\n'.join((PACKAGE/'scripts'/f).read_text() for f in ('bootstrap.sh','install.py','manage.py','launch.sh','source_integrity.py'))
        if any(x in active for x in ('neka-nat/freecad-mcp','git clone','git fetch','git+','upstream.tar.gz')):
            raise RuntimeError('可执行安装路径存在上游源码获取引用')
        results['static_source_download_audit']='pass'; record()
        run('download-only', ['/bin/sh', PACKAGE/'scripts/bootstrap.sh', '--download-only'])
        if (data/'runtime/READY').exists() or (data/'runtime/upstream').exists():
            raise RuntimeError('download-only创建了安装状态')
        run('bootstrap', ['/bin/sh', PACKAGE/'scripts/bootstrap.sh'])
        run('reuse-bootstrap', ['/bin/sh', PACKAGE/'scripts/bootstrap.sh'])
        py = data/'runtime/.venv/bin/python'
        for test in ('check_package','test_vendor_install','test_management','test_project_init'):
            run(test, [py, PACKAGE/'tests'/(test+'.py')])
            if 'skipped=' in (out/(test+'.stderr')).read_text():
                raise RuntimeError(test+'包含跳过项，不计为完整通过')
        run('configure', [py, PACKAGE/'scripts/manage.py','configure','--freecad-app',args.freecad_app])
        run('verify-upstream', [py, PACKAGE/'scripts/manage.py','verify-upstream'])
        run('doctor', [py, PACKAGE/'scripts/manage.py','doctor'])
        run('stdio', [py,PACKAGE/'tests/probe_mcp.py','--package',PACKAGE,'--output',out/'mcp'])
        if args.gui:
            results['gui']='requested, not yet passed'; record()
            run('gui-smoke', [py,PACKAGE/'tests/probe_gui.py','--package',PACKAGE,'--output',out/'gui','--start','--close-owned'])
            results['gui']='passed; inspect screenshot manually'; record()
        results['status']='passed within recorded scope'; record()
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        results['status']='failed/blocked'; results['error']=str(exc); record()
        print(str(exc),file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

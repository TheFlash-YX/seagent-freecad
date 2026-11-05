"""Publish verified vendored source. Never downloads or overwrites unknown content."""
import argparse
from pathlib import Path
import shutil
import os
import subprocess
import sys
from source_integrity import (atomic_json, expected, hashes, read_json, validate_data,
                              verify_environment, verify_installed, verify_tree, ready_value, refuse_active, runtime_lease)


def _install(data, package):
    data = validate_data(data, package)
    lock, files = expected(package)  # Verify everything before the first write.
    source = data / 'runtime/upstream'
    staging = data / 'runtime/upstream.partial'
    manifest_path = data / 'upstream-files.json'
    journal = data / 'source-transaction.json'
    transaction = {'schema_version': 1, 'manifest_sha256': lock['source']['manifest_sha256'],
                   'source': str(source), 'package': str(package.resolve())}
    if staging.exists():
        raise RuntimeError('保留中断安装upstream.partial；检查后显式移出，再重试')
    if source.exists():
        if manifest_path.exists():
            verify_installed(data, package)
        else:
            if not journal.exists() or read_json(journal) != transaction:
                raise RuntimeError('已有无来源清单upstream，且无匹配发布事务；拒绝覆盖')
            verify_tree(source, files)  # Recovery only from an exact, unexecuted snapshot.
            atomic_json(manifest_path, hashes(files))
    else:
        if manifest_path.exists() or journal.exists():
            raise RuntimeError('来源元数据存在但源码缺失；保留中断状态，使用新DATA')
        (data / 'runtime').mkdir(parents=True, exist_ok=True)
        atomic_json(journal, transaction)
        staging.mkdir()
        for name, record in files.items():
            dst = staging / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(package / 'vendor/freecad-mcp' / name, dst)
            dst.chmod(0o755 if record['mode'] == '100755' else 0o644)
        verify_tree(staging, files)
        # No replacement of pre-existing directories. DATA must be task/user exclusive.
        if source.exists():
            raise RuntimeError('源码目标在复制期间出现，拒绝覆盖')
        staging.rename(source)
        atomic_json(manifest_path, hashes(files))
    if journal.exists():
        if read_json(journal) != transaction:
            raise RuntimeError('未知发布事务，保留并拒绝')
        journal.unlink()
    return data


def install(data, package):
    data = validate_data(data, package)
    expected(package)
    refuse_active(data)  # Before even creating DATA/lock on a rejected installation.
    data.mkdir(parents=True, exist_ok=True)
    fd = runtime_lease(data, exclusive=True)
    try:
        refuse_active(data)
        return _install(data, package)
    finally:
        os.close(fd)


def environment_run(data, package):
    verify_installed(data, package)
    refuse_active(data)
    fd = runtime_lease(data, exclusive=True)
    try:
        refuse_active(data)
        ready = data / 'runtime/READY'
        if ready.exists(): ready.replace(data / 'runtime/READY.previous')
        python = data / 'runtime/python/bin/python3.12'
        uv = str(data / 'runtime/uv/uv')
        venv = data / 'runtime/.venv'
        env = dict(os.environ, UV_HTTP_TIMEOUT='120', UV_HTTP_RETRIES='2',
                   UV_CACHE_DIR=str(data / 'downloads/uv-cache'), UV_NO_MANAGED_PYTHON='1',
                   UV_PROJECT_ENVIRONMENT=str(venv))
        commands = []
        if not (venv / 'bin/python').is_file():
            commands.append([uv, 'venv', '--python', str(python), str(venv)])
        commands += [[uv, 'pip', 'install', '--python', str(venv / 'bin/python'), '--require-hashes', '-r', str(package / 'build-requirements.lock')],
                     [uv, 'sync', '--frozen', '--no-dev', '--no-editable', '--inexact', '--no-build-isolation', '--python', str(python), '--directory', str(data / 'runtime/upstream')],
                     [str(venv / 'bin/python'), str(package / 'scripts/manage.py'), 'inventory'],
                     [str(venv / 'bin/python'), str(package / 'scripts/install.py'), str(data), str(package), '--action', 'finalize']]
        for command in commands:
            subprocess.run(command, env=env, stdout=sys.stderr, check=True)
    finally:
        os.close(fd)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('data', type=Path); p.add_argument('package', type=Path)
    p.add_argument('--action', choices=['install', 'preflight', 'environment-run', 'finalize'], default='install')
    args = p.parse_args()
    try:
        data = validate_data(args.data, args.package)
        if args.action == 'preflight':
            expected(args.package)
            refuse_active(data)
        elif args.action == 'install':
            install(data, args.package)
        elif args.action == 'environment-run':
            environment_run(data, args.package.resolve())
        elif args.action == 'finalize':
            verify_installed(data, args.package)
            verify_environment(data, args.package)
            atomic_json(data / 'runtime/READY', ready_value(args.package))
        print('内置来源/安装状态校验完成：' + args.action, file=sys.stderr)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, ImportError, subprocess.CalledProcessError) as exc:
        print('SEAgent FreeCAD: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

"""Source, interrupted publication and READY regressions in disposable copies only."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import install
import source_integrity as integrity


class VendorInstall(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vendored-install-')
        self.addCleanup(self.temp.cleanup)
        self.package = Path(self.temp.name).resolve() / 'package'
        shutil.copytree(ROOT, self.package, ignore=shutil.ignore_patterns('__pycache__'))
        self.data = Path(self.temp.name).resolve() / 'data'
        self.vendor = self.package / 'vendor/freecad-mcp'

    def publish(self):
        return install.install(self.data, self.package)

    def action(self, name):
        return subprocess.run([sys.executable, str(self.package / 'scripts/install.py'), str(self.data), str(self.package), '--action', name], capture_output=True, text=True)

    def test_new_source_and_reuse_are_exact(self):
        self.publish()
        p = self.data / 'runtime/upstream/README.md'; before = p.stat().st_mtime_ns
        self.publish()
        self.assertEqual(p.stat().st_mtime_ns, before)
        self.assertEqual(len(integrity.verify_installed(self.data, self.package)[1]), 81)
        self.assertFalse((self.data / 'downloads/upstream.tar.gz').exists())
        self.assertFalse((self.data / 'runtime/READY').exists())

    def test_vendor_deleted_changed_extra_fail_before_data_writes(self):
        original = (self.vendor / 'README.md').read_bytes()
        for change in ('delete', 'modify', 'extra'):
            with self.subTest(change=change):
                target = self.vendor / 'README.md'
                target.write_bytes(original)
                if change == 'delete': target.unlink()
                elif change == 'modify': target.write_text('changed')
                else: (self.vendor / '.unexpected.py').write_text('x=1')
                with self.assertRaisesRegex(RuntimeError, '源码不一致'): self.publish()
                self.assertFalse(self.data.exists())
                if change == 'extra': (self.vendor / '.unexpected.py').unlink()

    def test_manifest_hash_and_dependency_locks_fail(self):
        for name in ('vendor-files.json', 'uv.lock', 'build-requirements.lock'):
            with self.subTest(name=name):
                p = self.package / name; original = p.read_bytes(); p.write_bytes(original + b'\n')
                with self.assertRaises(RuntimeError): self.publish()
                self.assertFalse(self.data.exists()); p.write_bytes(original)

    def test_manifest_commit_traversal_and_duplicate_rejected(self):
        path = self.package / 'vendor-files.json'; original = path.read_text()
        lock = self.package / 'upstream.lock.json'; initial = lock.read_text()
        for kind in ('commit', 'traversal', 'duplicate', 'absolute'):
            with self.subTest(kind=kind):
                manifest = json.loads(original)
                if kind == 'commit': manifest['upstream_commit'] = 'different'
                elif kind in ('traversal','absolute'):
                    manifest['files']['../outside' if kind == 'traversal' else '/outside'] = next(iter(manifest['files'].values()))
                raw = json.dumps(manifest)
                if kind == 'duplicate': raw = raw.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1')
                path.write_text(raw)
                metadata = json.loads(initial); metadata['source']['manifest_sha256'] = integrity.sha(path)
                lock.write_text(json.dumps(metadata))
                with self.assertRaises((RuntimeError, ValueError)): self.publish()
                self.assertFalse(self.data.exists())

    def test_old_self_consistent_source_not_current_is_preserved(self):
        self.publish()
        source = self.data / 'runtime/upstream/README.md'; source.write_text('old self-consistent source')
        manifest = self.data / 'upstream-files.json'; value = json.loads(manifest.read_text()); value['README.md'] = integrity.sha(source); manifest.write_text(json.dumps(value))
        with self.assertRaisesRegex(RuntimeError, '当前内置来源'): self.publish()
        self.assertEqual(source.read_text(), 'old self-consistent source')

    def test_modified_source_missing_manifest_and_unknown_files_preserved(self):
        self.publish()
        source = self.data / 'runtime/upstream/README.md'; original = source.read_bytes(); source.write_text('user edit')
        with self.assertRaisesRegex(RuntimeError, '源码不一致'): self.publish()
        self.assertEqual(source.read_text(), 'user edit'); source.write_bytes(original)
        (self.data / 'upstream-files.json').unlink()
        with self.assertRaisesRegex(RuntimeError, '无来源清单'): self.publish()
        self.assertTrue(source.exists())

    def test_partial_copy_failure_is_retained_and_retry_rejects(self):
        with patch.object(install.shutil, 'copyfile', side_effect=OSError('injected copy failure')):
            with self.assertRaisesRegex(OSError, 'injected'): self.publish()
        self.assertTrue((self.data / 'runtime/upstream.partial').is_dir())
        self.assertFalse((self.data / 'runtime/READY').exists())
        with self.assertRaisesRegex(RuntimeError, '中断安装'): self.publish()

    def test_source_published_manifest_failure_recovers_exact_snapshot(self):
        real = install.atomic_json
        def fail_manifest(path, value):
            if path.name == 'upstream-files.json': raise OSError('injected manifest failure')
            return real(path, value)
        with patch.object(install, 'atomic_json', side_effect=fail_manifest):
            with self.assertRaises(OSError): self.publish()
        self.assertTrue((self.data / 'runtime/upstream').is_dir())
        self.assertFalse((self.data / 'upstream-files.json').exists())
        self.publish()
        self.assertFalse((self.data / 'source-transaction.json').exists())
        integrity.verify_installed(self.data, self.package)

    def test_recovery_rejects_changed_source_and_unknown_transaction(self):
        self.publish(); (self.data / 'upstream-files.json').unlink()
        integrity.atomic_json(self.data / 'source-transaction.json', {'unknown': True})
        with self.assertRaisesRegex(RuntimeError, '无匹配发布事务'): self.publish()

    def test_post_manifest_interruption_recovers_without_recopy(self):
        self.publish()
        lock, _ = integrity.expected(self.package)
        integrity.atomic_json(self.data / 'source-transaction.json', {'schema_version':1, 'manifest_sha256':lock['source']['manifest_sha256'], 'source':str(self.data/'runtime/upstream'), 'package':str(self.package.resolve())})
        self.publish(); self.assertFalse((self.data / 'source-transaction.json').exists())

    def test_ready_invalidated_before_environment_failure(self):
        self.publish(); ready = self.data / 'runtime/READY'; ready.write_text('old READY')
        with patch.object(install.subprocess, 'run', side_effect=subprocess.CalledProcessError(42, ['uv'])):
            with self.assertRaises(subprocess.CalledProcessError): install.environment_run(self.data, self.package)
        self.assertFalse(ready.exists()); self.assertEqual((ready.parent/'READY.previous').read_text(), 'old READY')
        self.assertNotEqual(self.action('finalize').returncode, 0)
        self.assertFalse(ready.exists())

    def test_runtime_bytecode_allowed_extra_importable_and_addon_rejected(self):
        self.publish(); source = self.data / 'runtime/upstream'
        import py_compile
        py_compile.compile(str(source / 'src/freecad_mcp/__init__.py'), doraise=True)
        integrity.verify_installed(self.data, self.package)
        for relative in ('src/freecad_mcp/evil.py', 'src/freecad_mcp/evil.pyc', 'addon/Unknown/InitGui.py', 'src/freecad_mcp/__pycache__/evil.cpython-312.pyc'):
            extra = source / relative; extra.parent.mkdir(parents=True, exist_ok=True); extra.write_text('x=1')
            with self.assertRaisesRegex(RuntimeError, '额外'): integrity.verify_installed(self.data, self.package)
            extra.unlink()
            if 'Unknown' in relative: extra.parent.rmdir()

    def test_symlinks_special_files_and_executable_mode_rejected(self):
        path = self.vendor / 'README.md'; original = path.read_bytes(); path.unlink(); path.symlink_to('/etc/hosts')
        with self.assertRaisesRegex(RuntimeError, '链接'): self.publish()
        path.unlink(); path.write_bytes(original); path.chmod(0o755)
        with self.assertRaisesRegex(RuntimeError, 'mode'): self.publish()
        path.chmod(0o644); os.mkfifo(self.vendor / 'unexpected-fifo')
        with self.assertRaisesRegex(RuntimeError, '异常'): self.publish()

    def test_data_source_overlap_and_runtime_escape_rejected(self):
        for data in (self.package, self.vendor, self.package.parent):
            with self.assertRaisesRegex(RuntimeError, '重叠'): install.install(data, self.package)
        self.data.mkdir(); outside = Path(self.temp.name) / 'outside'; outside.mkdir()
        (self.data / 'runtime').symlink_to(outside)
        with self.assertRaisesRegex(RuntimeError, '链接'): self.publish()
        self.assertEqual(list(outside.iterdir()), [])

    def test_runtime_venv_escape_rejected(self):
        self.publish(); outside = Path(self.temp.name) / 'outside'; outside.mkdir()
        (self.data / 'runtime/.venv').symlink_to(outside)
        with self.assertRaisesRegex(RuntimeError, '链接'): self.publish()
        self.assertEqual(list(outside.iterdir()), [])

    def test_old_ready_and_empty_old_manifest_are_not_accepted(self):
        self.publish(); (self.data / 'upstream-files.json').write_text('{}')
        with self.assertRaisesRegex(RuntimeError, '当前内置来源'): integrity.verify_installed(self.data, self.package)
        (self.data / 'runtime/READY').write_text('SEAgent FreeCAD runtime ready (0.1.0)')
        with self.assertRaises((ValueError, RuntimeError)): integrity.verify_ready(self.data, self.package)

    def test_recorded_instance_identity_blocks_source_and_environment_writes(self):
        self.publish()
        ready = self.data / 'runtime/READY'; ready.write_text('old ready')
        integrity.atomic_json(self.data / 'instance.json', {'pid':12345, 'identity':'fixed process identity'})
        before = (self.data / 'upstream-files.json').read_bytes()
        with patch.object(integrity, 'process_identity', return_value='fixed process identity'):
            with self.assertRaisesRegex(RuntimeError, '受管FreeCAD仍在运行'): self.publish()
            with self.assertRaisesRegex(RuntimeError, '受管FreeCAD仍在运行'): install.environment_run(self.data, self.package)
        self.assertEqual(ready.read_text(), 'old ready')
        self.assertEqual((self.data / 'upstream-files.json').read_bytes(), before)

    def test_process_inspection_denied_preserves_legacy_ready(self):
        self.publish(); (self.data / 'runtime/.venv').mkdir()
        ready = self.data / 'runtime/READY'; ready.write_text('legacy READY')
        with patch('subprocess.run', side_effect=PermissionError('ps sandbox denied')):
            with self.assertRaises(PermissionError): self.publish()
        self.assertEqual(ready.read_text(), 'legacy READY')

    def test_active_mcp_shared_lease_blocks_install(self):
        self.publish()
        program = "import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); from source_integrity import runtime_lease; fd=runtime_lease(Path(sys.argv[2])); print('locked', flush=True); sys.stdin.readline()"
        proc = subprocess.Popen([sys.executable, '-c', program, str(self.package/'scripts'), str(self.data)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(proc.stdout.readline().strip(), 'locked')
            with self.assertRaisesRegex(RuntimeError, '活动MCP/安装租约'): self.publish()
        finally:
            proc.communicate('exit\n', timeout=10)
        self.publish()

    def test_root_project_marker_is_rejected(self):
        self.data.mkdir(); (self.data / 'pyproject.toml').write_text('[project]')
        with self.assertRaisesRegex(RuntimeError, '其他项目源码'): self.publish()
        self.assertFalse((self.data/'runtime').exists())

    def test_dependency_install_failure_leaves_no_current_ready(self):
        self.publish(); ready = self.data / 'runtime/READY'; ready.write_text('previous READY')
        with patch.object(install.subprocess, 'run', side_effect=subprocess.CalledProcessError(42, ['uv', 'venv'])):
            with self.assertRaises(subprocess.CalledProcessError): install.environment_run(self.data, self.package)
        self.assertFalse(ready.exists())
        self.assertEqual((ready.parent/'READY.previous').read_text(), 'previous READY')
        self.assertTrue((self.data/'runtime/upstream').is_dir())


if __name__ == '__main__':
    unittest.main(verbosity=2)

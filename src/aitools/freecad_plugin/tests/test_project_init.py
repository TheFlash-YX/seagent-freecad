"""Synthetic filesystem behavior tests; never initializes the repository."""
import importlib.util
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('project_init', ROOT / 'skills/seagent-project-init/scripts/init_project.py')
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)
TEMPLATE = (ROOT / 'skills/seagent-project-init/assets/SE-SOUL.md').read_bytes()


class ProjectInit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='SE 初始化 ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_missing_relative_link_and_idempotent(self):
        first = mod.initialize(self.root)
        self.assertFalse(first['identity_loaded'])
        self.assertEqual((self.root / 'SE-SOUL.md').read_bytes(), TEMPLATE)
        self.assertEqual((self.root / 'AGENTS.md').readlink(), Path('SE-SOUL.md'))
        self.assertEqual(mod.initialize(self.root)['actions'], [])

    def test_preserve_existing_and_append_once(self):
        soul = self.root / 'SE-SOUL.md'; soul.write_bytes(b'custom soul\r\n')
        agents = self.root / 'AGENTS.md'; original = '自有指令\r\n'.encode(); agents.write_bytes(original)
        mod.initialize(self.root)
        result = agents.read_bytes()
        self.assertTrue(result.startswith(original))
        self.assertEqual(result.count(mod.BEGIN.encode()), 1)
        self.assertIn(b'custom soul\r\n', result)
        self.assertEqual(soul.read_bytes(), b'custom soul\r\n')
        self.assertEqual(mod.initialize(self.root)['actions'], [])
        self.assertEqual(agents.read_bytes(), result)

    def test_override_shadows_entrypoint(self):
        override = self.root / 'AGENTS.override.md'; override.write_bytes(b'keep override')
        with self.assertRaisesRegex(ValueError, 'AGENTS.override.md'):
            mod.initialize(self.root)
        self.assertEqual(override.read_bytes(), b'keep override')
        self.assertFalse((self.root / 'AGENTS.md').exists())
        self.assertFalse((self.root / 'SE-SOUL.md').exists())

    def test_exact_legacy_reference_migration_preserves_user_bytes(self):
        soul = self.root / 'SE-SOUL.md'; soul.write_bytes(TEMPLATE)
        agents = self.root / 'AGENTS.md'
        prefix, suffix = '既有指令\r\n'.encode(), b'\r\nuser suffix'
        agents.write_bytes(prefix + mod.LEGACY_BLOCK.encode() + suffix)
        mod.initialize(self.root)
        result = agents.read_bytes()
        self.assertTrue(result.startswith(prefix)); self.assertTrue(result.endswith(suffix))
        self.assertIn(TEMPLATE, result)
        self.assertNotIn(mod.LEGACY_BLOCK.encode(), result)
        self.assertEqual(mod.initialize(self.root)['actions'], [])

    def test_two_fresh_file_readers_see_full_identity_in_both_forms(self):
        # File-level simulation only: independent readers, no Codex chat or model request.
        for ordinary in (False, True):
            with self.subTest(ordinary=ordinary), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                if ordinary: (root / 'AGENTS.md').write_text('project extras')
                mod.initialize(root)
                for _ in range(2):
                    body = subprocess.check_output([sys.executable, '-c',
                        'from pathlib import Path; import sys; sys.stdout.buffer.write(Path(sys.argv[1]).read_bytes())',
                        str(root / 'AGENTS.md')])
                    self.assertIn(TEMPLATE, body)
                    if ordinary: self.assertIn(b'project extras', body)

    def test_modified_embedded_body_conflicts_without_overwrite(self):
        mod.initialize(self.root)
        agents = self.root / 'AGENTS.md'; agents.unlink()
        agents.write_text('custom\n' + mod.BEGIN + '\nmodified principles\n' + mod.END)
        before = agents.read_bytes()
        with self.assertRaises(ValueError): mod.initialize(self.root)
        self.assertEqual(agents.read_bytes(), before)

    def test_existing_soul_only(self):
        soul = self.root / 'SE-SOUL.md'; soul.write_text('自有原则')
        mod.initialize(self.root)
        self.assertEqual(soul.read_text(), '自有原则')
        self.assertEqual((self.root / 'AGENTS.md').readlink(), Path('SE-SOUL.md'))

    def test_conflicts_do_not_mutate_either_path(self):
        # Each case has a missing counterpart; errors must occur before creation.
        for filename in ('AGENTS.md', 'SE-SOUL.md'):
            for kind in ('empty', 'whitespace', 'directory', 'dangling', 'external', 'correct-but-dangling'):
                with self.subTest(filename=filename, kind=kind), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp); path = root / filename
                    outside = root / 'outside'; outside.write_bytes(b'outside unchanged')
                    if kind == 'empty': path.touch()
                    elif kind == 'whitespace': path.write_bytes(b' \n')
                    elif kind == 'directory': path.mkdir()
                    elif kind == 'dangling': path.symlink_to('missing')
                    elif kind == 'external': path.symlink_to(outside)
                    else: path.symlink_to('SE-SOUL.md' if filename == 'AGENTS.md' else 'AGENTS.md')
                    before = sorted(p.name for p in root.iterdir())
                    link = path.readlink() if path.is_symlink() else None
                    with self.assertRaises(ValueError): mod.initialize(root)
                    self.assertEqual(sorted(p.name for p in root.iterdir()), before)
                    self.assertEqual(outside.read_bytes(), b'outside unchanged')
                    if link is not None: self.assertEqual(path.readlink(), link)

    def test_equivalent_existing_link_preserved(self):
        soul = self.root / 'SE-SOUL.md'; soul.write_text('keep')
        agents = self.root / 'AGENTS.md'; agents.symlink_to('./SE-SOUL.md')
        self.assertEqual(mod.initialize(self.root)['actions'], [])
        self.assertEqual(soul.read_text(), 'keep')
        self.assertEqual(agents.readlink(), Path('SE-SOUL.md'))  # Path normalizes ./; raw link below.
        import os
        self.assertEqual(os.readlink(agents), './SE-SOUL.md')

    def test_external_agents_link_with_existing_soul(self):
        soul = self.root / 'SE-SOUL.md'; soul.write_text('keep soul')
        with tempfile.TemporaryDirectory() as tmp:
            external = Path(tmp) / 'instructions'; external.write_text('keep external')
            agents = self.root / 'AGENTS.md'; agents.symlink_to(external)
            with self.assertRaises(ValueError): mod.initialize(self.root)
            self.assertEqual(external.read_text(), 'keep external')
            self.assertEqual(soul.read_text(), 'keep soul')
            self.assertEqual(agents.readlink(), external)

    def test_malformed_marker_and_relative_workspace(self):
        agents = self.root / 'AGENTS.md'; agents.write_text(mod.BEGIN + '\nmanual edit')
        with self.assertRaises(ValueError): mod.initialize(self.root)
        self.assertFalse((self.root / 'SE-SOUL.md').exists())
        with self.assertRaises(ValueError): mod.initialize(Path('.'))


if __name__ == '__main__':
    unittest.main(verbosity=2)

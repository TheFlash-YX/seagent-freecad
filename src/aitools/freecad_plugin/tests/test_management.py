"""Non-invasive management checks; never claims someone else's RPC listener."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('manage', ROOT/'scripts/manage.py')
manage = importlib.util.module_from_spec(spec);spec.loader.exec_module(manage)

class ManagementTests(unittest.TestCase):
    def test_missing_runtime_no_stdout(self):
        with tempfile.TemporaryDirectory(prefix='seagent-missing-') as d:
            r=subprocess.run(['/bin/sh',str(ROOT/'scripts/launch.sh')],env={**os.environ,'SEAGENT_FREECAD_DATA':d},capture_output=True,text=True)
            self.assertEqual(r.returncode,78);self.assertEqual(r.stdout,'');self.assertIn('README',r.stderr)

    def test_unknown_listener_rejected_without_rpc_or_kill(self):
        with socket.socket() as listener, tempfile.TemporaryDirectory(prefix='seagent-conflict-') as d:
            try:
                listener.bind(('127.0.0.1',9875))
            except OSError:
                self.skipTest('9875 already occupied; no takeover attempted')
            listener.listen(8)
            old=manage.DATA;manage.DATA=Path(d)
            try:
                with self.assertRaisesRegex(RuntimeError,'拒绝启动MCP'):
                    manage.guard_connection()
                # guard only TCP-connect probe, not XML-RPC. No payload sent.
                listener.settimeout(.5);connection,_=listener.accept()
                with connection:
                    connection.settimeout(.5);self.assertEqual(connection.recv(1024),b'')
                self.assertGreater(listener.fileno(),0)
            finally: manage.DATA=old

    def test_modified_and_user_files_preserved_on_uninstall(self):
        with tempfile.TemporaryDirectory(prefix='seagent-uninstall-') as d:
            old=manage.DATA;manage.DATA=Path(d)
            try:
                runtime=Path(d)/'runtime';runtime.mkdir()
                (runtime/'own').write_text('original');(runtime/'modified').write_text('original')
                manage.inventory();(runtime/'modified').write_text('user change')
                (Path(d)/'model.step').write_text('user model')
                with contextlib.redirect_stdout(io.StringIO()):manage.uninstall(True)
                self.assertFalse((runtime/'own').exists());self.assertEqual((runtime/'modified').read_text(),'user change');self.assertTrue((Path(d)/'model.step').is_file())
            finally:manage.DATA=old

    def test_doctor_missing_configured_executables_fails(self):
        with tempfile.TemporaryDirectory(prefix='seagent-doctor-') as d:
            old=manage.DATA;manage.DATA=Path(d)
            try:
                (Path(d)/'runtime/.venv/bin').mkdir(parents=True)
                (Path(d)/'runtime/.venv/bin/python').write_text('dummy')
                (Path(d)/'runtime/upstream').mkdir()
                (Path(d)/'upstream-files.json').write_text('{}')
                manage.write_json(Path(d)/'config.json',{'freecadcmd':['/does-not-exist/freecadcmd'],'gui':'/does-not-exist/freecad'})
                with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(manage.doctor(),1)
            finally:manage.DATA=old

    def test_shlex_freecadcmd_with_chinese_space(self):
        import shlex
        argv=['/路径 空格/FreeCADCmd','arg space'];self.assertEqual(shlex.split(shlex.join(argv)),argv)

if __name__=='__main__':unittest.main(verbosity=2)

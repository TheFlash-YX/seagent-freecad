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
import sys
import shutil
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
                runtime=Path(d)/'runtime/python';runtime.mkdir(parents=True)
                (runtime/'own').write_text('original');(runtime/'modified').write_text('original')
                manage.inventory()
                own=Path(d)/'owned-files.json'; value=json.loads(own.read_text()); value['owner']='seagent-freecad-0.1.0'; own.write_text(json.dumps(value))
                (runtime/'modified').write_text('user change')
                (Path(d)/'model.step').write_text('user model')
                (runtime/'unknown').write_text('unknown user file')
                manage.inventory()
                with contextlib.redirect_stdout(io.StringIO()):manage.uninstall(True)
                self.assertFalse((runtime/'own').exists());self.assertEqual((runtime/'modified').read_text(),'user change');self.assertTrue((Path(d)/'model.step').is_file());self.assertEqual((runtime/'unknown').read_text(),'unknown user file')
            finally:manage.DATA=old

    def test_doctor_missing_configured_executables_fails(self):
        with tempfile.TemporaryDirectory(prefix='seagent-doctor-') as d:
            old=manage.DATA;manage.DATA=Path(d)
            try:
                sys.path.insert(0, str(ROOT/'scripts'))
                from install import install
                install(Path(d), ROOT)
                (Path(d)/'runtime/.venv/bin').mkdir(parents=True)
                (Path(d)/'runtime/.venv/bin/python').write_text('dummy')
                manage.write_json(Path(d)/'config.json',{'freecadcmd':['/does-not-exist/freecadcmd'],'gui':'/does-not-exist/freecad'})
                with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(manage.doctor(),1)
            finally:manage.DATA=old

    def test_shlex_freecadcmd_with_chinese_space(self):
        import shlex
        argv=['/路径 空格/FreeCADCmd','arg space'];self.assertEqual(shlex.split(shlex.join(argv)),argv)

    def test_active_mcp_lease_preserves_runtime_on_uninstall(self):
        with tempfile.TemporaryDirectory(prefix='seagent-active-uninstall-') as d:
            old=manage.DATA;manage.DATA=Path(d).resolve()
            runtime=manage.DATA/'runtime/python';runtime.mkdir(parents=True)
            own=runtime/'owned';own.write_text('must remain')
            manage.inventory()
            program="import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from source_integrity import runtime_lease; fd=runtime_lease(Path(sys.argv[2])); print('locked',flush=True); sys.stdin.readline()"
            proc=subprocess.Popen([sys.executable,'-c',program,str(ROOT/'scripts'),str(manage.DATA)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
            try:
                self.assertEqual(proc.stdout.readline().strip(),'locked')
                with self.assertRaisesRegex(RuntimeError,'活动MCP/安装租约'):manage.uninstall(True)
                self.assertEqual(own.read_text(),'must remain')
            finally:
                proc.communicate('exit\n',timeout=10);manage.DATA=old

if __name__=='__main__':unittest.main(verbosity=2)

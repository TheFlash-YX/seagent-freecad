import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

P=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P/'scripts'))
import manage
import bridge
import bootstrap

class DeliveryTests(unittest.TestCase):
    def test_unbound_protocol_no_runtime_or_gui(self):
        with tempfile.TemporaryDirectory() as d:
            payload=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}},
                     {'jsonrpc':'2.0','method':'notifications/initialized'},
                     {'jsonrpc':'2.0','id':2,'method':'tools/list'},
                     {'jsonrpc':'2.0','id':3,'method':'ping'}]
            r=subprocess.run([sys.executable,str(P/'scripts/bridge.py'),'--data',d],input='\n'.join(map(json.dumps,payload))+'\n',capture_output=True,text=True,timeout=10)
            self.assertEqual(r.returncode,0,r.stderr)
            values=[json.loads(x) for x in r.stdout.splitlines()]
            self.assertEqual(values[0]['result']['protocolVersion'],'2025-06-18')
            self.assertEqual(len(values[1]['result']['tools']),18)
            self.assertEqual(list(Path(d).iterdir()),[])

    def test_old_connection_and_consumed_marker_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            data=Path(d);b={'schema':1,'project':d,'generation':'A'}
            manage.write(data/'binding.json',b);manage.write(data/'prepare.json',dict(b,marker='m'))
            x=bridge.Bridge(data)
            with patch.object(manage,'guard'),patch.object(bridge,'Upstream'):
                x.handshake({'marker':'m'})
            manage.write(data/'binding.json',dict(b,generation='B'))
            manage.write(data/'prepare.json',dict(b,generation='B',marker='new'))
            with self.assertRaisesRegex(RuntimeError,'旧连接'):x.handshake({'marker':'new'})
            with self.assertRaisesRegex(RuntimeError,'旧项目'):manage.guard(data,b)
            manage.write(data/'prepare.json',dict(b,marker='used',consumed_by=99999999))
            manage.write(data/'binding.json',b)
            with patch.object(manage,'guard'):
                with self.assertRaisesRegex(RuntimeError,'消费'):bridge.Bridge(data).handshake({'marker':'used'})

    def test_real_upstream_async_text_ledger(self):
        # Import FIXED newly installed upstream operations, not hand-written JSON fixtures.
        from freecad_mcp.operations.core import execute_code_async_operation,get_async_status_operation
        class Native:
            def execute_code_async(self,code):return {'success':True,'job_id':'job-test'}
            def get_async_status(self,job_id):return {'success':True,'job':{'id':job_id,'state':'done'}}
        started=execute_code_async_operation(Native(),'pass')
        done=get_async_status_operation(Native(),'job-test')
        with tempfile.TemporaryDirectory() as d:
            data=Path(d);x=bridge.Bridge(data);x.snapshot={'schema':1,'project':d,'generation':'A'}
            class Fake:
                value=None
                def call(self,*a):return {'jsonrpc':'2.0','id':'child','result':{'content':[v.model_dump(exclude_none=True) for v in self.value]}}
            x.up=Fake();x.up.value=started
            with patch.object(manage,'guard'),patch.object(bridge,'send'):
                x.call(10,{'name':'execute_code_async','arguments':{'code':'pass'}})
                self.assertIn('job-test',manage.pending(data))
                with self.assertRaisesRegex(RuntimeError,'在途'):manage.idle(data)
                x.up.value=done;x.call(11,{'name':'get_async_status','arguments':{'job_id':'job-test'}})
            self.assertEqual(manage.pending(data),{})

    def test_payload_image_structured_error_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            x=bridge.Bridge(Path(d));x.snapshot={'generation':'g','project':d}
            raw={'jsonrpc':'2.0','id':'child','result':{'content':[{'type':'image','mimeType':'image/png','data':'AAAA'}],'structuredContent':{'a':1},'isError':True}}
            class Fake:
                def call(self,*a):return raw.copy()
            x.up=Fake();sent=[]
            with patch.object(manage,'guard'),patch.object(bridge,'send',side_effect=sent.append):x.call('host-id',{'name':'get_view'})
            self.assertEqual(sent[-1],dict(raw,id='host-id'))

    def test_unknown_timeout_blocks_switch_and_writes(self):
        with tempfile.TemporaryDirectory() as d:
            x=bridge.Bridge(Path(d));x.snapshot={'generation':'g','project':d}
            class Fake:
                def call(self,*a):raise RuntimeError('transport closed')
            x.up=Fake()
            with patch.object(manage,'guard'),patch.object(bridge,'send'):x.call(1,{'name':'execute_code_headless'})
            self.assertTrue(manage.pending(Path(d)))
            with self.assertRaises(RuntimeError):manage.idle(Path(d))

    def test_binding_rejects_unknown_listener_without_rpc(self):
        with tempfile.TemporaryDirectory() as d,tempfile.TemporaryDirectory() as project:
            data=Path(d);manage.write(data/'machine.json',{'source_root':str(P.parents[2])})
            with patch.object(manage,'occupied',return_value=True):
                with self.assertRaisesRegex(RuntimeError,'未知9875'):manage.bind(data,project)
            self.assertFalse((data/'binding.json').exists())

    def test_extract_traversal_and_roundtrip(self):
        import zipfile,shlex
        with tempfile.TemporaryDirectory() as d:
            archive=Path(d)/'bad.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('../outside','bad')
            with self.assertRaises(RuntimeError):bootstrap.extract(archive,Path(d)/'stage')
            self.assertFalse((Path(d)/'outside').exists())
        argv=['C:/路径 空格/FreeCADCmd.exe','extra space']
        self.assertEqual(shlex.split(shlex.join(argv)),argv) # NOT Windows CreateProcess verification.


class MoreBridgeTests(unittest.TestCase):
    def test_unbound_and_unknown_listener_never_construct_upstream(self):
        with tempfile.TemporaryDirectory() as d:
            data=Path(d);x=bridge.Bridge(data)
            with patch.object(bridge,'Upstream') as upstream,patch.object(bridge,'send'):
                x.call(1,{'name':'get_rpc_status'})
                upstream.assert_not_called()
                b={'schema':1,'project':d,'generation':'g'}
                manage.write(data/'binding.json',b);manage.write(data/'prepare.json',dict(b,marker='m'))
                with patch.object(manage,'live_instance',return_value=None),patch.object(manage,'occupied',return_value=True):
                    x.call(2,{'name':'seagent_connect','arguments':{'marker':'m'}})
                upstream.assert_not_called()
            self.assertFalse((data/'connection.json').exists())

    def test_real_upstream_status_list_cancelled_and_success_timeout_text(self):
        from freecad_mcp.operations.core import get_async_status_operation
        class Native:
            def get_async_status(self,job_id):
                return {'success':True,'jobs':[{'id':'job-one','state':'cancelled'}]} if not job_id else {'success':True,'job':{'id':job_id,'state':'cancelled'}}
        for native in (get_async_status_operation(Native(),''),get_async_status_operation(Native(),'job-one')):
            with tempfile.TemporaryDirectory() as d:
                data=Path(d);manage.write(data/'pending.json',{'job-one':{'state':'running'}})
                x=bridge.Bridge(data);x.snapshot={'generation':'g','project':d}
                class Fake:
                    def call(self,*args):return {'jsonrpc':'2.0','id':1,'result':{'content':[v.model_dump(exclude_none=True) for v in native]}}
                x.up=Fake()
                with patch.object(manage,'guard'),patch.object(bridge,'send'):x.call(2,{'name':'get_async_status'})
                self.assertEqual(manage.pending(data),{})
        with tempfile.TemporaryDirectory() as d:
            data=Path(d);x=bridge.Bridge(data);x.snapshot={'generation':'g','project':d}
            class Success:
                def call(self,*args):return {'id':1,'result':{'content':[{'type':'text','text':'timeout setting was read successfully'}]}}
            x.up=Success()
            with patch.object(manage,'guard'),patch.object(bridge,'send'):x.call(3,{'name':'execute_code'})
            self.assertEqual(manage.pending(data),{})

class TransportAndLifecycleTests(unittest.TestCase):
    def test_subprocess_transport_ids_notifications_image(self):
        real_popen=subprocess.Popen
        with tempfile.TemporaryDirectory() as d:
            data=Path(d);manage.write(data/'machine.json',{'freecadcmd':['C:/中文 空格/FreeCADCmd.exe']})
            notifications=[]
            def peer(*args,**kwargs):return real_popen([sys.executable,str(P/'tests/mock_upstream.py')],**kwargs)
            with patch.object(manage,'validate_runtime',return_value={'mcp':'unused'}),patch.object(bridge.subprocess,'Popen',side_effect=peer),patch.object(bridge,'send',side_effect=notifications.append):
                u=bridge.Upstream(data,d,'2025-06-18')
                r=u.call({'method':'tools/call','params':{'name':'get_view','arguments':{'width':123}}},'distinct-id')
                self.assertEqual(r['id'],'distinct-id')
                self.assertEqual(r['result']['structuredContent']['args'],{'width':123})
                self.assertEqual(r['result']['content'][0]['type'],'image')
                self.assertEqual(notifications[0]['method'],'notifications/progress')
                u.close();u.proc.wait(timeout=5);u.proc.stdout.close()

    def test_cache_locator_and_source_separation(self):
        with tempfile.TemporaryDirectory() as d,tempfile.TemporaryDirectory() as source,tempfile.TemporaryDirectory() as project:
            data=Path(d);cache=data/'cache/plugin';cache.mkdir(parents=True)
            manage.write(cache/'machine-locator.json',{'data':d})
            manage.write(data/'machine.json',{'source_root':source})
            with patch.object(manage,'PACKAGE',cache):self.assertEqual(manage.root(),data.resolve())
            with patch.object(manage,'PACKAGE',cache),patch.object(manage,'occupied',return_value=False):
                b=manage.prepare(data,project)
                self.assertEqual(b['project'],str(Path(project).resolve()))
                with self.assertRaises(ValueError):manage.bind(data,source)

    def test_update_pending_and_nested_rejected(self):
        import lifecycle
        with tempfile.TemporaryDirectory() as d,tempfile.TemporaryDirectory() as other:
            data=Path(d);manage.write(data/'pending.json',{'job-one':{'state':'unknown'}})
            with self.assertRaises(RuntimeError):lifecycle.change(data,Path(other))
            with self.assertRaises(ValueError):lifecycle.change(data,data/'nested')

    def test_shared_marketplace_not_removed(self):
        import lifecycle
        with tempfile.TemporaryDirectory() as d,tempfile.TemporaryDirectory() as n:
            old,new=Path(d),Path(n)
            manage.write(new/'machine.json',{})
            calls=[]
            def run(exe,*args):
                calls.append(args)
                return json.dumps({'installed':[{'pluginId':'other@seagent-freecad-private'}]})
            with patch.object(lifecycle,'safe'),patch.object(lifecycle,'owned',return_value={'codex':'codex','selector':'seagent-freecad@seagent-freecad-private'}),patch.object(manage,'validate_runtime'),patch.object(lifecycle.deploy,'generate',return_value=(new,new)),patch.object(lifecycle.deploy,'run',side_effect=run):
                with self.assertRaisesRegex(RuntimeError,'共享'):lifecycle.change(old,new,True)
            self.assertEqual(calls,[('plugin','list','--json')])


class InterruptedWriteTests(unittest.TestCase):
    def test_fixed_operation_rpc_reset_unknown_but_validation_terminal(self):
        from freecad_mcp.operations.core import execute_code_operation
        from freecad_mcp.responses import ErrorResponse
        class Native:
            message='Connection reset by peer'
            def execute_code(self,*a):raise ConnectionResetError(self.message)
        for message,unknown in [('Connection reset by peer',True),('invalid property value',False)]:
            fake=Native();fake.message=message
            response=execute_code_operation(fake,True,'pass')
            self.assertIsInstance(response,ErrorResponse)
            with tempfile.TemporaryDirectory() as d:
                data=Path(d);x=bridge.Bridge(data);x.snapshot={'generation':'g','project':d}
                class Child:
                    def call(self,*a):return {'id':1,'result':{'content':[v.model_dump(exclude_none=True) for v in response],'isError':True}}
                x.up=Child()
                with patch.object(manage,'guard'),patch.object(bridge,'send'):x.call(3,{'name':'execute_code'})
                self.assertEqual(bool(manage.pending(data)),unknown)



class WindowsByteContractTests(unittest.TestCase):
    def test_bridge_utf8_under_ascii_redirected_locale(self):
        import os,threading,queue
        with tempfile.TemporaryDirectory() as d:
            child=subprocess.Popen([sys.executable,str(P/'scripts/bridge.py'),'--data',d],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',env=dict(os.environ,PYTHONIOENCODING='ascii'))
            child.stdin.write(json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'get_rpc_status'}})+'\n');child.stdin.flush()
            lines=queue.Queue();threading.Thread(target=lambda:lines.put(child.stdout.readline()),daemon=True).start()
            line=lines.get(timeout=10)
            self.assertIn('尚未连接',line)
            self.assertTrue(json.loads(line)['result']['isError'])
            child.stdin.close();child.wait(timeout=5);child.stdout.close();child.stderr.close()

    def test_posix_manifest_keys_and_powershell_utf8(self):
        import deploy
        from pathlib import PureWindowsPath
        self.assertEqual(deploy.relative_key(PureWindowsPath('C:/plugin/skills/setup/SKILL.md'),PureWindowsPath('C:/plugin')),'skills/setup/SKILL.md')
        class Process:
            stdout='中文路径'
        with patch.object(manage.subprocess,'run',return_value=Process()) as run:
            self.assertEqual(manage.powershell('test-command'),'中文路径')
            self.assertEqual(run.call_args.kwargs['encoding'],'utf-8')
            self.assertIn('[Console]::OutputEncoding',run.call_args.args[0][-1])

if __name__=='__main__':unittest.main(verbosity=2)

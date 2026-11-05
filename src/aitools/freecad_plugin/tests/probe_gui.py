"""Explicit dedicated-instance synthetic GUI smoke; never touches unknown listeners."""
import argparse
import asyncio
import base64
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main(args):
    package = Path(args.package).resolve()
    sys.path.insert(0, str(package/'scripts'))
    import manage
    from source_integrity import process_identity, read_json
    out = Path(args.output).resolve(); out.mkdir(parents=True, exist_ok=False)
    if manage.occupied():
        raise RuntimeError('GUI验收需要空闲9875；未接管或查询未知RPC')
    # Check the OS identity capability BEFORE requesting a GUI window.
    if not process_identity(os.getpid()): raise RuntimeError('无法核对本机进程身份')
    if not args.start: raise RuntimeError('必须显式--start授权专用GUI')
    manage.start()
    instance = read_json(manage.DATA/'instance.json')
    try:
        for _ in range(60):
            if manage.occupied(): break
            await asyncio.sleep(.5)
        if not manage.owned_listener(): raise RuntimeError('专用GUI未建立可验证的9875监听')
        # Prove reinstall refuses the ACTUAL active managed GUI without changing READY.
        ready = (manage.DATA/'runtime/READY').read_bytes()
        denied = subprocess.run([str(manage.DATA/'runtime/.venv/bin/python'), str(package/'scripts/install.py'),str(manage.DATA),str(package),'--action','environment-run'],capture_output=True,text=True)
        (out/'active-install-refusal.txt').write_text(denied.stderr)
        if denied.returncode == 0 or '受管FreeCAD仍在运行' not in denied.stderr or (manage.DATA/'runtime/READY').read_bytes()!=ready:
            raise RuntimeError('活动GUI安装保护失败')
        params = StdioServerParameters(command='/bin/sh',args=[str(package/'scripts/launch.sh')],env=dict(os.environ))
        with (out/'mcp.stderr').open('w') as log:
            async with stdio_client(params,errlog=log) as (read,write):
                async with ClientSession(read,write) as session:
                    await session.initialize()
                    tools = (await session.list_tools()).tools
                    actual = {t.name:t.inputSchema for t in tools}
                    fixed = {t['name']:t['inputSchema'] for t in json.loads((package/'references/tools.schema.json').read_text())['tools']}
                    if actual!=fixed: raise RuntimeError('工具Schema与固定快照不一致')
                    document = 'VendoringBox_'+uuid.uuid4().hex[:12]
                    async def call(name, arguments):
                        from jsonschema import validate
                        validate(arguments, actual[name])
                        result = await session.call_tool(name, arguments)
                        payload = result.model_dump(mode='json')
                        (out/(name+'.json')).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
                        if result.isError: raise RuntimeError(name+' returned MCP error')
                        return result
                    await call('get_rpc_status', {})
                    await call('create_document', {'name':document})
                    try:
                        await call('create_object', {'doc_name':document,'obj_type':'Part::Box','obj_name':'AcceptanceBox','obj_properties':{'Length':10,'Width':20,'Height':30},'include_screenshot':False})
                        await call('list_documents', {})
                        await call('get_object', {'doc_name':document,'obj_name':'AcceptanceBox','include_screenshot':False})
                        code = f"import FreeCAD, json\nd=FreeCAD.getDocument({document!r})\nb=d.getObject('AcceptanceBox')\nassert (b.Length.Value,b.Width.Value,b.Height.Value)==(10.0,20.0,30.0)\nassert abs(b.Shape.Volume-6000.0)<1e-7\nprint(json.dumps({{'dimensions_mm':[b.Length.Value,b.Width.Value,b.Height.Value], 'volume_mm3':b.Shape.Volume, 'valid':b.Shape.isValid()}}))"
                        result = await call('execute_code', {'code':code,'include_screenshot':False})
                        if not any('6000' in getattr(x,'text','') for x in result.content):
                            raise RuntimeError('未收到合成长方体数值断言结果')
                        image = await call('get_view', {'view_name':'Isometric','width':1000,'height':800,'focus_object':'AcceptanceBox'})
                        blocks = [x for x in image.content if x.type=='image']
                        if not blocks: raise RuntimeError('截图缺失')
                        raw = base64.b64decode(blocks[0].data,validate=True)
                        suffix = '.png' if blocks[0].mimeType=='image/png' else '.jpg'
                        (out/('box'+suffix)).write_bytes(raw)
                        (out/'summary.json').write_text(json.dumps({'document':document,'dimensions_mm':[10,20,30],'volume_mm3':6000,'screenshot':'box'+suffix,'manual_image_review':'required'},indent=2)+'\n')
                    finally:
                        await session.call_tool('execute_code', {'code':f"FreeCAD.closeDocument({document!r})",'include_screenshot':False})
    finally:
        if args.close_owned:
            # Only the exact process created and recorded above; never a foreign listener.
            if process_identity(instance['pid']) == instance['identity']:
                os.kill(instance['pid'],signal.SIGTERM)
    return 0


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',required=True);p.add_argument('--output',required=True);p.add_argument('--start',action='store_true');p.add_argument('--close-owned',action='store_true')
    try: raise SystemExit(asyncio.run(main(p.parse_args())))
    except (OSError, RuntimeError, AssertionError, ValueError) as exc:
        print(str(exc),file=sys.stderr);raise SystemExit(1)

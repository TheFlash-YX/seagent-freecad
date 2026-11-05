"""Integration probe of the actual transparent launcher and unmodified MCP stdio."""
import argparse
import asyncio
import json
import os
import subprocess
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

EXPECTED = {'create_document','list_documents','reload_document','get_objects','get_object','create_object','edit_object','delete_object','get_view','get_parts_list','insert_part_from_library','execute_code','execute_code_async','execute_code_headless','get_async_status','get_rpc_status','run_fem_analysis'}

async def main(args):
    package = Path(args.package).resolve()
    out = Path(args.output).resolve(); out.mkdir(parents=True, exist_ok=True)
    params = StdioServerParameters(command='/bin/sh', args=[str(package / 'scripts/launch.sh')], env=dict(os.environ))
    with (out / 'mcp.stderr').open('w') as errors:
        async with stdio_client(params, errlog=errors) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                payload = tools.model_dump(mode='json')
                (out / 'tools.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n')
                assert {t.name for t in tools.tools} == EXPECTED, [t.name for t in tools.tools]
                # Compare schema from stdio against the fixed installed original server object.
                from freecad_mcp.server import mcp
                original = await mcp.list_tools()
                expected = {t.name: t.inputSchema for t in original}
                actual = {t.name: t.inputSchema for t in tools.tools}
                fixed = {t['name']: t['inputSchema'] for t in json.loads((package/'references/tools.schema.json').read_text())['tools']}
                differences = {name: {'actual':actual.get(name), 'fixed':fixed.get(name)} for name in sorted(set(actual)|set(fixed)) if actual.get(name)!=fixed.get(name)}
                (out/'schema-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
                assert actual == expected
                assert not differences, differences
                import sys
                sys.path.insert(0, str(package/'scripts'))
                from source_integrity import verify_ready
                source = verify_ready(Path(os.environ['SEAGENT_FREECAD_DATA']).resolve(), package)
                (out/'source.json').write_text(json.dumps(source,indent=2)+'\n')
                data = Path(os.environ['SEAGENT_FREECAD_DATA']).resolve()
                ready_before = (data/'runtime/READY').read_bytes()
                refused = subprocess.run([str(data/'runtime/.venv/bin/python'),str(package/'scripts/install.py'),str(data),str(package),'--action','environment-run'],capture_output=True,text=True)
                (out/'active-mcp-install-refusal.txt').write_text(refused.stderr)
                assert refused.returncode != 0 and '活动MCP/安装租约' in refused.stderr, refused.stderr
                assert (data/'runtime/READY').read_bytes() == ready_before
                uninstall = subprocess.run([str(data/'runtime/.venv/bin/python'),str(package/'scripts/manage.py'),'uninstall','--remove-runtime'],capture_output=True,text=True)
                (out/'active-mcp-uninstall-refusal.txt').write_text(uninstall.stderr)
                assert uninstall.returncode != 0 and '活动MCP/安装租约' in uninstall.stderr, uninstall.stderr
                assert (data/'runtime/.venv/bin/freecad-mcp').is_file()
                summary = {'active_mcp_uninstall_refused':True, 'active_mcp_install_refused':True, 'tools_count':len(tools.tools), 'schema_matches_installed_original':True, 'schema_matches_repository_baseline':True}
                (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
                print(json.dumps(summary))

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--package',required=True);p.add_argument('--output',required=True)
    asyncio.run(main(p.parse_args()))

"""Static source/ZIP readiness. Does not initialize upstream or connect RPC."""
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import package
root=package.ROOT
files=package.payload()
assert set(files)==set(json.loads((root/'delivery-files.json').read_text(encoding='utf-8'))['files'])
assert len(list((root/'src/aitools/freecad_plugin/skills').glob('*/SKILL.md')))==7
schema=json.loads(files['src/aitools/freecad_plugin/references/tools.schema.json'])
assert len(schema['tools'])==17
for n,data in files.items():
    if n.endswith('.ps1'):assert data.startswith(b'\xef\xbb\xbf'),n
    if n.endswith('.md'):
        for target in re.findall(r'\]\(([^)]+)\)',data.decode('utf-8')):
            if target.startswith(('https:','http:','#')):continue
            dest=(root/n).parent/unquote(target.split('#')[0])
            assert dest.resolve().is_relative_to(root) and dest.exists(),(n,target)
print(json.dumps({'files':len(files),'skills':7,'upstream_business_schemas':17,'ps1_utf8_bom':True,'links':'PASS'}))

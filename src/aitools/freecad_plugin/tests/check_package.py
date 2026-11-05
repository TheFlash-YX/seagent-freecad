"""Validate portable package references and frozen upstream tool schemas."""
import hashlib
import json
from pathlib import Path
import re
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else Path(__file__).resolve().parents[1]).resolve()
manifest=json.loads((root/'plugin.json').read_text());mcp=json.loads((root/'mcp.json').read_text());lock=json.loads((root/'upstream.lock.json').read_text())
assert manifest['name']=='seagent-freecad'
assert (root/manifest['extensions']['com.openai']['onboardingSkill']).is_file()
assert mcp['mcpServers']['freecad']['command']=='./scripts/launch.sh'
assert not any(k in mcp['mcpServers']['freecad'] for k in ['enabled_tools','disabled_tools'])
assert hashlib.sha256((root/'uv.lock').read_bytes()).hexdigest()==lock['dependency_lock_sha256']
assert hashlib.sha256((root/'build-requirements.lock').read_bytes()).hexdigest()==lock['build_dependency_lock_sha256']
expected={'seagent-project-init'}
skills=list((root/'skills').glob('*/SKILL.md'))
assert {s.parent.name for s in skills}==expected
for path in root.rglob('*.md'):
 if path.is_relative_to(root/'vendor'): continue
 text=path.read_text()
 for target in re.findall(r'\]\(([^)]+)\)',text):
  if target.startswith(('https:','http:','#')):continue
  dest=(path.parent/target.split('#')[0]).resolve()
  assert dest.is_relative_to(root) and dest.exists(),(path,target)
 for target in re.findall(r'(?<!\w)(\.\./(?:[\w./-]+\.(?:md|json)))',text):
  dest=(path.parent/target).resolve();assert dest.is_relative_to(root) and dest.exists(),(path,target)
assert len(json.loads((root/'references/tools.schema.json').read_text())['tools'])==17
print('Package references, 1 skill, 17 tools, dependency hashes: PASS')

sys.path.insert(0, str(root/'scripts'))
from source_integrity import expected
_, files = expected(root)
assert len(files) == 81 and sum(f['size'] for f in files.values()) == 8223860
assert (root/'vendor/freecad-mcp/LICENSE').read_bytes() == (root/'references/UPSTREAM-LICENSE').read_bytes()
assert (root/'vendor/freecad-mcp/assets/make_toycar4.gif').is_file()
repo=root.parents[2]
assert (repo/'SE-SOUL.md').read_bytes()==(root/'skills/seagent-project-init/assets/SE-SOUL.md').read_bytes()
delivery=json.loads((repo/'delivery-files.json').read_text())
actual={p.relative_to(repo).as_posix() for p in repo.rglob('*') if p.is_file() and '.git' not in p.relative_to(repo).parts and '__pycache__' not in p.parts}
assert set(delivery['files']) == actual, {'missing':sorted(actual-set(delivery['files'])),'extra':sorted(set(delivery['files'])-actual)}
assert delivery['version']==manifest['version']=='0.1.1'
print('Complete vendor, LICENSE, SOUL and delivery inventory: PASS')

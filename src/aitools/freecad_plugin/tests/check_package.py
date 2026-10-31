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
 text=path.read_text()
 for target in re.findall(r'\]\(([^)]+)\)',text):
  if target.startswith(('https:','http:','#')):continue
  dest=(path.parent/target.split('#')[0]).resolve()
  assert dest.is_relative_to(root) and dest.exists(),(path,target)
 for target in re.findall(r'(?<!\w)(\.\./(?:[\w./-]+\.(?:md|json)))',text):
  dest=(path.parent/target).resolve();assert dest.is_relative_to(root) and dest.exists(),(path,target)
assert len(json.loads((root/'references/tools.schema.json').read_text())['tools'])==17
print('Package references, 1 skill, 17 tools, dependency hashes: PASS')

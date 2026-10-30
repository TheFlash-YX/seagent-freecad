"""Export exact source allowlist without Git; reject links, traversal, duplicates."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[4]


def payload():
    names=json.loads((ROOT/'delivery-files.json').read_text(encoding='utf-8'))['files']
    if len(names)!=len(set(names)):raise ValueError('重复白名单条目')
    result={}
    for name in names:
        p=Path(name)
        if p.is_absolute() or '..'in p.parts or '\\'in name:raise ValueError('非法路径')
        src=ROOT/p
        if src.is_symlink() or any(x.is_symlink() for x in src.parents if x!=ROOT.parent) or not src.resolve().is_relative_to(ROOT) or not src.is_file():raise ValueError('缺失/不安全文件：'+name)
        result[name]=src.read_bytes()
    return result


def package(output):
    output=Path(output).expanduser().resolve()
    if output.is_relative_to(ROOT):raise ValueError('ZIP放源码外')
    output.parent.mkdir(parents=True,exist_ok=True)
    data=payload()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for name,content in sorted(data.items()):
            i=zipfile.ZipInfo('seagent-freecad/'+name,date_time=(2026,10,30,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED
            i.external_attr=(0o100755 if name.endswith(('.sh','.command')) else 0o100644)<<16
            z.writestr(i,content)
    return {'zip':str(output),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'files':len(data),
            'content_sha256':{n:hashlib.sha256(c).hexdigest() for n,c in sorted(data.items())}}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(package(a.output),ensure_ascii=False,indent=2))

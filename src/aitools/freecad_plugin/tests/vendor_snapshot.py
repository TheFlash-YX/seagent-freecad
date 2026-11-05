"""Maintenance-only fixed archive importer. Never called by bootstrap/launcher.

Inputs: independently obtained fixed tar.gz and recursive Git API tree JSON.
Output must not exist. No network requests. Preserve every blob and executable bit.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

COMMIT='8babe9927ce8e6e8fe7dd6ae2ffa2c93776e845a'
ARCHIVE_SHA='f2d623d0d1dec086a46e156d2d169c0456b52a81db5593134b641e7baa08870f'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',required=True,type=Path);p.add_argument('--git-tree',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    if args.output.exists(): raise ValueError('output must not exist')
    if hashlib.sha256(args.archive.read_bytes()).hexdigest()!=ARCHIVE_SHA: raise ValueError('archive hash mismatch')
    tree=json.loads(args.git_tree.read_text())
    if tree.get('truncated') is not False or tree.get('sha')!=COMMIT: raise ValueError('incomplete/wrong Git tree')
    blobs={}
    for item in tree['tree']:
        if item['type']=='tree': continue
        if item['type']!='blob' or item['mode'] not in ('100644','100755'): raise ValueError('unsupported Git object')
        if item['path'] in blobs: raise ValueError('duplicate Git path')
        blobs[item['path']]=item
    if len(blobs)!=81 or sum(x['size'] for x in blobs.values())!=8223860: raise ValueError('unexpected fixed tree')
    files={}; content={}
    with tarfile.open(args.archive) as archive:
        for member in archive.getmembers():
            path=PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or str(path)!=member.name.rstrip('/') or path.parts[0]!='freecad-mcp-'+COMMIT or not (member.isfile() or member.isdir()):
                raise ValueError('unsafe archive entry: '+member.name)
            rel='/'.join(path.parts[1:])
            if not member.isfile(): continue
            if rel not in blobs or rel in files: raise ValueError('unexpected/duplicate blob: '+rel)
            raw=archive.extractfile(member).read(); item=blobs[rel]
            mode='100755' if member.mode&0o111 else '100644'
            if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=item['sha'] or len(raw)!=item['size'] or mode!=item['mode']:
                raise ValueError('Git blob/mode mismatch: '+rel)
            files[rel]={'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw),'mode':mode};content[rel]=raw
    if set(files)!=set(blobs): raise ValueError('missing blobs')
    root=args.output/'vendor/freecad-mcp';root.mkdir(parents=True)
    for name, raw in content.items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);path.chmod(0o755 if files[name]['mode']=='100755' else 0o644)
    manifest=args.output/'vendor-files.json'
    manifest.write_text(json.dumps({'schema_version':1,'upstream_commit':COMMIT,'files':dict(sorted(files.items()))},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'files':len(files),'bytes':sum(x['size'] for x in files.values()),'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest()}))


if __name__=='__main__':
    main()

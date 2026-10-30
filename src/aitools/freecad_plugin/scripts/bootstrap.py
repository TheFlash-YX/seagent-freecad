"""Complete fixed runtime installation using the separately bootstrapped Python."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
import manage


def fetch(path,url,sha):
    if path.is_file() and manage.digest(path)==sha:return
    tmp=path.with_suffix(path.suffix+'.part')
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url,timeout=60) as response, tmp.open('wb') as out:
                shutil.copyfileobj(response,out)
            if manage.digest(tmp)!=sha:raise RuntimeError('下载SHA256不一致，未执行')
            tmp.replace(path);return
        except (OSError,RuntimeError):
            if attempt==2:raise


def extract(archive,dest):
    if dest.exists():raise RuntimeError('保留中断staging，请检查后显式处理：'+str(dest))
    dest.mkdir()
    if archive.suffix=='.zip':
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                p=Path(info.filename)
                if p.is_absolute() or '..'in p.parts or '\\' in info.filename or (info.external_attr>>16)&0o170000==0o120000:
                    raise RuntimeError('不安全ZIP路径/链接')
            z.extractall(dest)
    else:
        with tarfile.open(archive) as t:t.extractall(dest,filter='data')


def install(data):
    package=manage.PACKAGE;lock=manage.read(package/'upstream.lock.json')
    key=platform.system()+'-'+platform.machine();assets=lock['platforms'].get(key)
    if not assets:raise RuntimeError('仅候选macOS arm64与Windows x64；平台不匹配：'+key)
    manage.separated(package.parents[2],data)
    runtime=data/'runtime';runtime.mkdir(parents=True,exist_ok=True);downloads=data/'downloads';downloads.mkdir(exist_ok=True)
    if (runtime/'READY.json').exists():
        old=manage.validate_runtime(data)
        if old.get('lock_sha256')!=manage.digest(package/'upstream.lock.json'):raise RuntimeError('锁已改变；请新机器根准备版本，禁止原地覆盖')
        return {'ready':True,'reused_verified_runtime':True}
    uvfile=downloads/('uv.zip' if os.name=='nt' else 'uv.tar.gz')
    fetch(uvfile,assets['uv']['url'],assets['uv']['sha256'])
    if not (runtime/'uv').exists():
        stage=runtime/'uv.partial';extract(uvfile,stage)
        children=list(stage.iterdir())
        if len(children)==1 and children[0].is_dir():children[0].rename(runtime/'uv');stage.rmdir()
        else:stage.rename(runtime/'uv')
    archive=downloads/'upstream.tar.gz';fetch(archive,lock['archive_url'],lock['archive_sha256'])
    src=runtime/'upstream'
    if not src.exists():
        stage=runtime/'upstream.partial';extract(archive,stage)
        (stage/('freecad-mcp-'+lock['commit'])).rename(src);stage.rmdir()
        if manage.digest(src/'uv.lock')!=lock['dependency_lock_sha256']:raise RuntimeError('上游锁不一致')
        manage.write(runtime/'upstream-files.json',{str(p.relative_to(src)):manage.digest(p) for p in src.rglob('*') if p.is_file()})
    elif not (runtime/'upstream-files.json').exists():raise RuntimeError('未知已有上游，拒绝覆盖')
    if manage.digest(package/'uv.lock')!=lock['dependency_lock_sha256'] or manage.digest(package/'build-requirements.lock')!=lock['build_dependency_lock_sha256']:raise RuntimeError('随包锁不一致')
    py=runtime/('python/python.exe' if os.name=='nt' else 'python/bin/python3.12')
    uv=runtime/('uv/uv.exe' if os.name=='nt' else 'uv/uv')
    venv=runtime/'.venv';vp=venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    env=os.environ.copy();env.update(UV_HTTP_TIMEOUT='120',UV_HTTP_RETRIES='2',UV_CACHE_DIR=str(downloads/'uv-cache'),UV_NO_MANAGED_PYTHON='1',UV_PROJECT_ENVIRONMENT=str(venv))
    commands=[]
    if not vp.exists():commands.append([str(uv),'venv','--python',str(py),str(venv)])
    commands.extend([[str(uv),'pip','install','--python',str(vp),'--require-hashes','-r',str(package/'build-requirements.lock')],
                     [str(uv),'sync','--frozen','--no-dev','--no-editable','--inexact','--no-build-isolation','--python',str(py),'--directory',str(src)]])
    for cmd in commands:subprocess.run(cmd,env=env,check=True,stdout=sys.stderr,timeout=600)
    exe=venv/('Scripts/freecad-mcp.exe' if os.name=='nt' else 'bin/freecad-mcp')
    manage.write(runtime/'READY.json',dict(python=str(vp),mcp=str(exe),commit=lock['commit'],lock_sha256=manage.digest(package/'upstream.lock.json')))
    manage.validate_runtime(data)
    return {'ready':True,'python':str(vp),'gui_started':False,'project_selected':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data');a=p.parse_args()
    try:
        with manage.locked(manage.root(a.data)):print(json.dumps(install(manage.root(a.data)),ensure_ascii=False))
    except Exception as e:print('依赖准备失败：'+str(e),file=sys.stderr);sys.exit(1)

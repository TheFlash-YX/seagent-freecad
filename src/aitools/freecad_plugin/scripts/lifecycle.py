"""Explicit update/rollback/uninstall. Never closes CAD or deletes business data."""
import argparse
import json
from pathlib import Path
import sys
import manage
import deploy


def safe(data):
    manage.idle(data)
    if manage.live_instance(data) or manage.occupied():raise RuntimeError('先确认任务终态、保存并自行退出FreeCAD；不接管9875')


def owned(data):
    v=manage.read(data/'deployment.json');cache=Path(v['cache'])
    if v['selector']!='seagent-freecad@seagent-freecad-private':raise RuntimeError('插件归属不符')
    if not cache.is_dir() or any(not(cache/n).is_file() or manage.digest(cache/n)!=h for n,h in v['files'].items()):raise RuntimeError('已安装缓存被修改/缺失，保留现场，不卸载')
    catalogs=json.loads(deploy.run(v['codex'],'plugin','marketplace','list','--json'))
    matches=[x for x in catalogs.get('marketplaces',[]) if x.get('name')=='seagent-freecad-private']
    if len(matches)!=1 or Path(matches[0]['root']).resolve()!=Path(v['marketplace']).resolve():raise RuntimeError('marketplace实际归属不符')
    return v


def uninstall(data):
    with manage.locked(data):
        safe(data);v=owned(data)
        deploy.run(v['codex'],'plugin','remove',v['selector'])
        # Marketplace may be shared; leave registration and all data intact.
        manage.write(data/'uninstalled.json',{'selector':v['selector'],'data_preserved':True})
        return {'removed_registration':v['selector'],'all_machine_and_business_data_preserved':True}


def change(old,new,apply=False):
    manage.separated(old.resolve(),new.resolve())
    with manage.locked(old),manage.locked(new):
        safe(old);safe(new);v=owned(old);manage.validate_runtime(new)
        if not (new/'machine.json').exists():raise RuntimeError('先在新机器根完成bootstrap/configure/check')
        dest,plugin=deploy.generate(new)
        summary={'old':str(old),'new':str(new),'apply':apply,'models_moved':False,'binding_migrated':False}
        if not apply:return summary
        # Official mutation only after explicit --apply, ownership checks, idle state and staged new package.
        installed=json.loads(deploy.run(v['codex'],'plugin','list','--json'))
        if any(x.get('pluginId','').endswith('@seagent-freecad-private') and x.get('pluginId')!=v['selector'] for x in installed.get('installed',[])):raise RuntimeError('marketplace仍有其他已安装插件，拒绝删除共享注册')
        catalog=manage.read(Path(v['marketplace'])/'.agents/plugins/marketplace.json')
        if len(catalog.get('plugins',[]))!=1 or catalog['plugins'][0].get('name')!='seagent-freecad':raise RuntimeError('marketplace有共享用途，拒绝删除注册')
        deploy.run(v['codex'],'plugin','marketplace','remove','--help')
        deploy.run(v['codex'],'plugin','remove',v['selector'])
        deploy.run(v['codex'],'plugin','marketplace','remove','seagent-freecad-private')
        try:summary['installed']=deploy.deploy(new,v['codex'],True)
        except Exception:
            manage.write(old/'upgrade-failure.json',{'old':str(old),'new':str(new),'recovery':'Use deploy.py install --data OLD after confirming no conflicting marketplace; all files retained.'})
            raise
        manage.write(new/'previous-version.json',{'data':str(old)})
        return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['uninstall','update','rollback']);p.add_argument('--data',required=True);p.add_argument('--to-data');p.add_argument('--apply',action='store_true');a=p.parse_args()
    try:
        old=manage.root(a.data)
        if a.action=='uninstall':
            if not a.apply:print(json.dumps({'plan':'remove owned plugin registration only; preserve all files'},ensure_ascii=False))
            else:print(json.dumps(uninstall(old),ensure_ascii=False))
        else:
            if not a.to_data:raise ValueError('提供--to-data指定已准备好的另一版本机器根')
            print(json.dumps(change(old,manage.root(a.to_data),a.apply),ensure_ascii=False,indent=2))
    except Exception as e:print(str(e),file=sys.stderr);sys.exit(1)

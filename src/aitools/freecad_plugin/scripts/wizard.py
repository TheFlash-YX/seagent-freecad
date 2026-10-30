"""Beginner machine-only installation; never selects a business folder or starts CAD."""
import argparse
import json
import os
from pathlib import Path
import sys
import manage
import deploy


def candidates():
    paths=[]
    if os.name=='nt':
        for name in ('ProgramFiles','LOCALAPPDATA'):
            base=os.environ.get(name)
            if base:
                for app in Path(base).glob('FreeCAD*'):
                    if (app/'bin/FreeCAD.exe').is_file() and (app/'bin/FreeCADCmd.exe').is_file():paths.append((app/'bin/FreeCAD.exe',app/'bin/FreeCADCmd.exe'))
    else:
        for base in (Path('/Applications'),Path.home()/'Applications'):
            for app in base.glob('FreeCAD*.app'):
                d=app/'Contents/Resources/bin'
                if (d/'freecad').is_file() and (d/'freecadcmd').is_file():paths.append((d/'freecad',d/'freecadcmd'))
    return list(dict.fromkeys(paths))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data');p.add_argument('--codex',default='codex');a=p.parse_args()
    try:
        data=manage.root(a.data);options=candidates()
        print('1/3 依赖已准备。检查FreeCAD，不会打开模型或启动窗口。')
        if len(options)==1:
            gui,cmd=options[0];print('检测到：'+str(gui))
        elif options:
            for i,(gui,_) in enumerate(options):print(f'{i+1}: {gui}')
            gui,cmd=options[int(input('请选择编号：'))-1]
        else:
            print('没有检测到标准安装，请提供实际文件路径（不含外围引号）。')
            gui=Path(input('FreeCAD GUI：'));cmd=Path(input('FreeCADCmd：'))
        manage.configure(data,gui,cmd)
        print('2/3 即将注册插件，不选择业务工作区、不覆盖已有同名插件。')
        if input('输入 y 继续，其他键退出：').lower()!='y':sys.exit(0)
        v=deploy.deploy(data,a.codex,True)
        print('3/3 插件注册完成；尚未连接业务项目。')
        print('在Codex打开你的项目聊天，说“使用FreeCAD”；setup技能将从当前聊天目录绑定。')
        print(json.dumps(v,ensure_ascii=False,indent=2))
    except Exception as e:print('安装未完成：'+str(e)+'\n保留原配置，请按错误说明恢复；不修改执行策略。',file=sys.stderr);sys.exit(1)

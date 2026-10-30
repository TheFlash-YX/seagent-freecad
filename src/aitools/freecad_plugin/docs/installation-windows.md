# Windows x64安装（候选，未实机验收）

预装FreeCAD（GUI与FreeCADCmd同一发行目录）、支持plugin的Codex、系统tar.exe及PowerShell 5.1+。标准用户，无系统Python/Git/uv/npm前提。首次联网到锁文件中的GitHub/astral固定公共来源，不上传模型。Windows版本/架构/GUI Python/Codex实际版本须在首轮记录；ARM64不支持声明。

解压源码ZIP到独立文件夹，不放业务模型。双击根`安装-Windows.cmd`：校验下载独立CPython3.12.13、uv0.11.14和固定原版0.1.28；检测标准FreeCAD路径，只有多个候选才选编号，没有候选时输入真实GUI/FreeCADCmd文件路径。然后确认注册，不选业务文件夹。完成仅表示注册成功，CAD尚未绑定。脚本不会启动FreeCAD或改全局Addon。

PowerShell脚本以UTF-8 BOM保存，兼容5.1读取中文；实际显示仍待Windows验收。执行策略阻止时按公司IT制度处理，脚本不修改策略或默认Bypass。网络失败看具体阶段，检查代理再重跑，缓存须hash一致。`.part`不执行；`.partial`保留现场，请人工检查后移出，不能盲删。首次运行未知程序的系统提示按组织政策处理。

命令行诊断（路径示意，单独参数；不eval）：

```powershell
& '.\src\aitools\freecad_plugin\scripts\bootstrap.ps1' -Data 'D:\工具状态\FreeCAD'
& 'D:\工具状态\FreeCAD\runtime\.venv\Scripts\python.exe' '.\src\aitools\freecad_plugin\scripts\manage.py' --data 'D:\工具状态\FreeCAD' configure --gui 'C:\Program Files\FreeCAD 1.1\bin\FreeCAD.exe' --freecadcmd 'C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe'
& 'D:\工具状态\FreeCAD\runtime\.venv\Scripts\python.exe' '.\src\aitools\freecad_plugin\scripts\deploy.py' check --data 'D:\工具状态\FreeCAD' --codex 'C:\实际路径\codex.exe'
& 'D:\工具状态\FreeCAD\runtime\.venv\Scripts\python.exe' '.\src\aitools\freecad_plugin\scripts\deploy.py' install --data 'D:\工具状态\FreeCAD' --codex 'C:\实际路径\codex.exe'
```

路径只是示意，不能照抄成实际安装身份。同名插件/marketplace不同路径拒绝不覆盖。CLI必须实际支持所调用plugin命令，未知JSON结构停止；不要手改缓存/config.toml。插件协议command只允许bare或包内路径；Windows生成powershell.exe -File稳定机器launch.ps1，Mac生成包内launch.sh，再调用固定Python与bridge。Windows启动器不使用PowerShell文本pipeline或简单 & python透传，使用.NET Process与stdin/stdout/stderr原始BaseStream异步复制，避免UTF-8/图片JSON被文本重编码；CreateProcess参数用Windows规则生成。实际双向stdio/EOF/取消/图片仍待Windows实机验收。安装副本machine-locator定位自定义data，无需依赖宿主环境变量透传。

首次项目聊天按[绑定](workspace-binding.md)使用。Windows的FreeCAD参数/profile隔离、中文空格CreateProcess、PowerShell交互及桌面插件发现全部仍待实机验证，shlex roundtrip单测不是通过证明。

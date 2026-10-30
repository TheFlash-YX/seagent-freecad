# macOS arm64安装

预装FreeCAD及支持plugin的Codex。打开根安装-macOS.command，或终端`/bin/sh src/aitools/freecad_plugin/scripts/bootstrap.sh /绝对机器目录`，随后使用该目录`runtime/.venv/bin/python`运行scripts/wizard.py --data同一目录。无需系统Python/uv，无管理员，不启动CAD。macOS的隔离脚本验证不等于真实桌面/GUI链路通过。

手动configure与deploy参数和Windows文档相同，GUI实际文件常在用户选定app的Contents/Resources/bin/freecad，FreeCADCmd为同目录freecadcmd。不能仅凭app名称启动。默认新根为`~/Library/Application Support/SEAgent/FreeCAD`，与旧试点安装根不同，不迁移或覆盖旧配置。

当前开发机9875有既有实例，禁止为测试启动第二个/换端口/关闭它。真实GUI/首次连接留待用户自行保存退出旧实例或独立机器后验收。

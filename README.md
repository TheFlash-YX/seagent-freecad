# SEAgent FreeCAD 私有交付候选 0.2.0

把本机FreeCAD接入Codex。安装不选择业务工作区；首次项目聊天使用时，技能读取实际聊天cwd并显式建立连接。一个聊天顺序控制一个受管实例，不做并发调度或结果整理。

**Windows x64为源码交付候选，尚未实机验证。当前不是工程师可用验收通过版。** Mac隔离脚本/stdio/ZIP安装验证与真实GUI连接是不同门禁，实际状态见[验证记录](src/aitools/freecad_plugin/docs/validation.md)。17个固定上游业务工具加1个管理握手工具，共18个MCP工具，7个skills；工具可发现不代表工程分析通过。

1. 解压ZIP（不需要Git/GitHub登录），或用你自己的账号clone私有仓库。
2. Windows双击[安装-Windows.cmd](安装-Windows.cmd)；Mac打开[安装-macOS.command](安装-macOS.command)。独立下载Python/依赖，检查FreeCAD，注册插件；不打开模型、不启动CAD、不选择项目。双击/PowerShell/桌面宿主交互仍有平台待验项。
3. 在Codex打开业务项目聊天，说“使用FreeCAD”；setup技能从实际cwd准备绑定，用户明确开始后启动可信专用实例并握手。绑定前正常列工具，CAD请求清晰提示未连接；不通过反复重装恢复。

安装前自行安装FreeCAD及支持plugin的Codex，Windows标准安装需要系统tar.exe、PowerShell 5.1+、联网HTTPS；无需系统Python、uv、Git或管理员。公司策略禁止脚本时按IT规定处理，不全局绕过执行策略。FreeCAD/GUI Python与外部MCP Python环境分开。

- [Windows安装](src/aitools/freecad_plugin/docs/installation-windows.md)、[Mac安装](src/aitools/freecad_plugin/docs/installation-macos.md)
- [项目绑定](src/aitools/freecad_plugin/docs/workspace-binding.md)、[诊断](src/aitools/freecad_plugin/docs/troubleshooting.md)、[更新卸载](src/aitools/freecad_plugin/docs/update-uninstall.md)
- [Windows待验表](src/specs/delivery/validation-windows.md)

源码、机器状态、业务目录分离，三者不能包含彼此。机器默认Windows `%LOCALAPPDATA%\SEAgent\FreeCAD`，Mac `~/Library/Application Support/SEAgent/FreeCAD`；可诊断入口显式--data。内部图文/代码可能发送模型服务，需授权。cwd不是沙箱，不承诺隔离恶意本用户；单连接项目generation保护用于防顺序切换误操作。

[delivery-files.json](delivery-files.json)是逐文件交付白名单。ZIP不含`.git`、runtime、机器配置、token、模型或日志；源码ZIP首次安装需联网下载固定SHA256依赖，不是离线依赖包。私有仓库不意味着向公众开源；上游MIT见[许可说明](src/aitools/freecad_plugin/references/licenses.md)，自有源码未授予公开再分发许可。协作者用各自账号，owner按最小权限手动邀请；不共享凭据。

验证入口：用独立runtime的Python运行 `-m unittest discover -s src/aitools/freecad_plugin/tests -v` 与 `src/aitools/freecad_plugin/tests/check_package.py`。隔离CLI发现probe需要显式独立CODEX_HOME、已安装机器data和空白project，见tests/probe_host.py --help；不要对既有9875直接初始化原版MCP。synthetic_geometry.py只能在之后获准的全新CAD测试会话执行，当前未运行。

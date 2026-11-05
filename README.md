# SEAgent FreeCAD Codex 插件（精简首版）

本仓库以精简首版替换历史 0.2.0 候选内容。当前插件版本为 0.1.1，内置固定上游完整源码；既有安装不自动迁移；旧实现保留在 Git 历史中。

- 内置固定原版 neka-nat/freecad-mcp 0.1.28 完整快照，提供全部 17 个原版 MCP 工具；安装不访问该上游仓库获取源码。
- 仅保留 seagent-project-init 项目初始化技能。
- 已初始化项目通过 AGENTS.md 全文或指向 SE-SOUL.md 的相对链接，让后续会话按 Codex 项目指令机制加载 SE 原则。
- 保留必要安装和实例管理；不包含预制 CAD 操作经验技能、管理桥接工具或 Windows 一键安装。

当前验证环境为 macOS arm64 / FreeCAD 1.1.4。目录作用域、AGENTS.override.md 及指令长度预算会影响身份加载；不承诺任意聊天全局注入。首次初始化当前聊天仍需实际读取原则。

## 安装

先安装 FreeCAD 及支持插件的 Codex，将本私有仓库克隆到本地，然后执行：

```sh
codex plugin marketplace add /绝对路径/seagent-freecad
codex plugin add seagent-freecad@seagent-freecad-local
```

继续按[插件安装与运行说明](src/aitools/freecad_plugin/README.md)准备受管运行时并配置实际 FreeCAD 路径。工程师在项目聊天中请求“初始化当前项目的 SEAgent 身份配置”，完成一次项目初始化；后续调用不重复验证文件。

## 验证

```sh
python3 src/aitools/freecad_plugin/tests/check_package.py
python3 src/aitools/freecad_plugin/tests/test_project_init.py
python3 src/aitools/freecad_plugin/tests/test_management.py
```

[身份原则](SE-SOUL.md) · [分发清单](delivery-files.json) · [变更记录](CHANGELOG.md)。原工具能力不等于工程分析已经验证；内部图文可能进入模型服务，按授权处理。本仓库不包含公司模型、运行时、机器配置或测试会话日志。

源码内置不等于完全离线：仍下载固定 uv、CPython 和 PyPI 锁定依赖。来源契约及独立验收入口见[维护说明](src/aitools/freecad_plugin/references/vendoring.md)；本次[验证记录](src/specs/freecad-mcp-vendoring/validation.md)记录独立安装、38项回归、真实stdio与GUI合成冒烟通过项，以及宿主安装和完整网络审计未验证的边界。

# SEAgent FreeCAD Codex 插件（精简首版）

本仓库以精简首版替换历史 0.2.0 候选内容。插件版本保留为 0.1.0，这是交付范围调整，不是升级兼容承诺；旧实现保留在 Git 历史中。

- 固定原版 neka-nat/freecad-mcp 0.1.28，提供全部 17 个原版 MCP 工具。
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

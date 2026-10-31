---
name: seagent-project-init
description: 首次初始化 SE 工程项目或修复项目身份入口时，建立 AGENTS.md 中的 SE-SOUL 原则正文；普通模型操作不触发。
---

# SE 项目身份初始化

本技能只配置当前项目身份入口，不连接 MCP、不启动 FreeCAD、不执行建模验收。插件安装和启动见 [安装说明](../../README.md)。

确定用户要初始化的 workspace 绝对路径，不能从插件安装位置推断目标。使用 Python 3（可用插件稳定运行时）运行本技能脚本，显式传入目标：

```sh
python3 /实际技能目录/scripts/init_project.py --workspace /明确的项目绝对路径
```

脚本仅在 SE-SOUL.md 缺失时复制随包原文；已有原则保留。AGENTS.md 缺失则创建指向 `SE-SOUL.md` 的相对符号链接；已有非空普通 AGENTS.md 则保留用户原文并追加带标记的 SE-SOUL **全文**，使原则成为宿主读取的指令正文。重复执行不重复追加。仅本插件精确旧读取引用块可以迁移为全文；未知/被修改/与当前 SOUL 不一致的标记块保留并报冲突。原则后续变更时，不自动覆盖已有标记内容，应由用户决定如何同步。

AGENTS.override.md 可能遮蔽入口；空文件、目录、断链、未知链接和标记冲突均保留并报告初始化未完成，不自行删除。等价指向本项目普通 SE-SOUL.md 的现有链接复用，外部目标不改。相对链接仅本机 macOS 已验证，其他平台未验。

脚本成功只表示文件配置完成，**不代表当前聊天已加载身份**。完成后在当前聊天显式读取 AGENTS.md 全文（链接已包含 SOUL 全文；普通文件亦包含项目额外指令），并读取 SE-SOUL.md 核对实际原则。不得只因文件存在宣称已加载。

后续在已初始化项目中启动会话，依赖 Codex 正常加载 AGENTS 正文；不再调用初始化、不逐工具重复检查。该机制受项目/工作目录范围、AGENTS.override.md、嵌套指令及指令大小预算约束，不是插件对任意聊天的全局强制注入。官方说明见 [AGENTS.md 加载机制](https://developers.openai.com/codex/guides/agents-md)。

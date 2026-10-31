# SEAgent FreeCAD Codex 本地插件

首版0.1.0仅提供固定原版 FreeCAD MCP 的 Codex 插件接入，以及已初始化项目的 SE 身份原则入口。原样使用 `neka-nat/freecad-mcp` 0.1.28 / `8babe9927ce8e6e8fe7dd6ae2ffa2c93776e845a`，暴露全部17原工具，不新增 CAD 接口或修改上游。仅保留1个项目初始化技能；操作经验待工程师实际使用后沉淀。

已测环境 macOS arm64 / FreeCAD1.1.4 / 外部CPython3.12.13，桌面内置Codex0.164.0-alpha.11.1，PATH CLI0.163.0；其他平台和第二台干净电脑完整安装未验。FreeCAD 为独立窗口，不是聊天内嵌三维。MCP返回文字/图片可能进入模型服务，内部资料依授权处理。

## 安装与连接

先安装 FreeCAD。在 marketplace 根目录运行：

```sh
codex plugin marketplace add /绝对路径/seagent-freecad
codex plugin add seagent-freecad@seagent-freecad-local
```

从官方安装结果的 installedPath 定位插件根，在该目录执行（不要直接编辑缓存）：

```sh
/bin/sh scripts/bootstrap.sh
"$HOME/Library/Application Support/SEAgentFreeCAD/runtime/.venv/bin/python" scripts/manage.py configure --freecad-app /实际路径/FreeCAD.app
"$HOME/Library/Application Support/SEAgentFreeCAD/runtime/.venv/bin/python" scripts/manage.py doctor
```

bootstrap 下载校验固定 uv、CPython、上游归档和锁定依赖，不要求系统 Python/uv。仅明确开始 CAD 工作时显式启动：

```sh
"$HOME/Library/Application Support/SEAgentFreeCAD/runtime/.venv/bin/python" scripts/manage.py start
```

专用 profile 和原版 Addon 不写全局 Mod。固定9875端口未知占用即拒绝，不接管、不关闭其他实例、不换端口。launcher 仅启动原版 stdio MCP，不启动 CAD。按客户端支持方式刷新插件/新会话，不自动重启桌面。原工具说明与参数以宿主发现结果为准，服务是否可用以原版状态返回为准，不自动运行建模验收。运行目录、保护与恢复说明见 [runtime.md](references/runtime.md)。

## 项目身份

在明确项目目录使用 [seagent-project-init](skills/seagent-project-init/SKILL.md) 初始化一次。SE-SOUL.md 模板为项目原文，缺失时复制，已有文件保留；缺失 AGENTS.md 建相对符号链接，已有普通 AGENTS.md 则保留原文并嵌入带标记的原则全文。旧本插件精确读取引用块可迁移为全文，未知内容不覆盖。空文件、目录、链接和 override 冲突保留并报告。

当前聊天在初始化后仍须实际读取原则；不能把“文件已创建”称为“已加载”。之后会话在**已初始化的目标项目**中按 Codex 的 AGENTS 正文发现机制加载，不依赖模型每次调用技能，不钩住 MCP。该机制受目录范围、override、嵌套指令和默认32KiB指令预算约束，不保证所有项目或所有聊天全局注入。普通引用链接不会被当作自动正文注入。依据：[官方 AGENTS.md 机制](https://developers.openai.com/codex/guides/agents-md)。本机文件解析测试不等于真实模型新会话验收。

## 更新与卸载

仅修改 marketplace 源，通过官方 plugin add 刷新并核对安装副本。保持原版 MCP/Addon 配套，源和依赖锁一致。卸载注册：

```sh
codex plugin remove seagent-freecad@seagent-freecad-local
```

不关闭 FreeCAD、不删除模型和日志。可选自有运行时清理（先按用户意图保存并退出专用实例）：

```sh
"$HOME/Library/Application Support/SEAgentFreeCAD/runtime/.venv/bin/python" /实际插件根/scripts/manage.py uninstall --remove-runtime
```

仅删除归属清单中未改变文件，保留修改过/未知文件及用户配置、profile、模型、日志；不动其他插件。不能把本地执行等同于全部数据留在本地，也不改变宿主审批策略。

## 最小验证

从插件根运行；只检查安装管理、身份文件配置和原工具发现，不运行 CAD 工作流：

```sh
python3 tests/check_package.py
python3 tests/test_management.py
python3 tests/test_project_init.py
"$HOME/Library/Application Support/SEAgentFreeCAD/runtime/.venv/bin/python" tests/probe_mcp.py --package "$PWD" --output /绝对路径/新证据
```

宿主技能发现可使用 `tests/probe_plugin.py --repo /marketplace根 --output /绝对路径/新证据`；不创建测试聊天。已有监听时端口冲突单测 SKIP，不操作监听实例。

历史 CAD/Agent 工作流不属于当前首版必须验收项；本独立交付仓库不包含开发工作区的历史记录和运行数据。许可见 [UPSTREAM-LICENSE](references/UPSTREAM-LICENSE) 与 [licenses.md](references/licenses.md)。

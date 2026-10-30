# 本次交付验证状态

2026-10-30，版本0.2.0。源码候选，不等于工程师可用验收通过。

独立Mac arm64机器根从固定公共hash归档完成CPython3.12.13/uv0.11.14/原版0.1.28依赖准备；不使用旧工具环境。本次适用结果：

| 验证 | 实际结果 |
| --- | --- |
| 新独立机器根固定hash依赖安装 | PASS，Mac arm64 |
| 无.git ZIP中文空格路径第二独立根bootstrap/configure/注册 | PASS，无Git或开发环境依赖 |
| CLI0.163.0隔离CODEX_HOME实际cache hash与app-server发现 | PASS，7skills/18工具，未绑定bridge connected，零CAD调用 |
| 14项管理/桥接回归 | PASS；含旧连接拒绝、消费marker、固定上游operations实际async文本和列表、未知任务阻止切换、图片/structuredContent、真实合成stdio子进程通知/ID、固定operation捕获RPC reset仍保留未知任务 |
| 固定上游schema | PASS，仅离线对象反射逐项比较17schema，不运行transport/lifespan |
| 初次CLI插件发现失败 | 已修复：mcp.schema必需$schema、command仅bare或contained ./；失败保留，不计最终通过 |
| lifecycle切换前pending/嵌套data/共享marketplace保护 | PASS mock；真实跨版本/GUI回退待验 |

已明确证明隔离CLI宿主未绑定无红错发现；**没有证明桌面首次prepare/start/connect及切项目新连接可用**。这是源码候选，不是工程师完整可用验收。

一次验证偏差：直接初始化原版MCP时误判其无RPC副作用，实际server_lifespan向既有9875发ping/get_rpc_status。未调用CAD业务工具或文档查询；已关闭该stdio子进程。此测试无效，不计上游17工具实链路通过。前后只读hash显示原源码/安装缓存各40文件、配置/instance/owned-files一致，进程身份一致；不能据此证明文档内存无影响。后续增加回归：未绑定/未知实例时bridge绝不构造上游。

所有真实GUI/首次握手、headless执行/cwd、图片展示、桌面新聊天是否新建连接、跨版本GUI回退均待验。当前9875已有实例，未为验收关闭/换端口/启动第二实例。Windows x64由用户后续实机验证；PowerShell、FreeCAD CLI/profile隔离和中文空格CreateProcess均未通过声明。

证据在交付源码以外的delivery目录，不能把机器日志放进源码ZIP；最终测试摘要仅记合成/隔离结果。不复用历史FreeCAD或SolidCraft通过结论。

# 协作说明

默认中文。仅维护 FreeCAD Codex 插件首版：原版 17 个 MCP 工具接入，以及 SE 项目身份初始化。仅保留 seagent-project-init 技能；操作经验待工程师实际使用后再沉淀。

安装运行入口见 src/aitools/freecad_plugin/README.md。当前验证范围为 macOS arm64；不声称 Windows 安装支持。不得恢复历史 0.2.0 的桥接工具或操作技能，除非用户明确要求。

SE-SOUL.md 是身份原则维护源；与插件内 skills/seagent-project-init/assets/SE-SOUL.md 分发模板保持逐字节一致。项目初始化后以 AGENTS.md 全文或软链接加载原则，不逐工具检查。

不得提交内部模型、运行数据、凭据、机器配置或缓存。delivery-files.json 是逐文件交付清单，修改文件范围后同步维护。保留上游许可和固定版本锁，不修改上游 MCP。未知端口不接管，不关闭用户 CAD 实例。测试不创建用户可见聊天，不将文件读取测试表述为模型会话行为验收。

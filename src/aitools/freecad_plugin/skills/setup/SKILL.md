---
name: setup
description: 安装与首次连接
---

# 安装与首次连接

安装不选择工作区。找到本技能实际安装插件根，读取machine-locator.json和../../docs/installation-windows.md；不要猜开发机路径。依赖缺失按文档恢复，不覆盖现安装。
首次使用：用当前聊天宿主exec查询真实cwd，与聊天工作区核对。用machine-locator指定机器根的runtime Python执行 `<实际插件根>/scripts/manage.py prepare --project <真实绝对cwd>`；脚本从locator定位自定义data，不能从插件目录猜业务目录。成功返回generation和marker，标记仅本机关联不是认证凭据。取不到可信cwd则停止。
用户明确开始CAD后执行同脚本start。受管窗口存在但未就绪则doctor检查，保留窗口不重复启动。未知9875不ping不接管。就绪后调用seagent_connect(marker=<本次prepare标记>)；只初始化已核实实例的原版MCP，不创建修改文档。成功后get_rpc_status/list_documents，再执行业务。未绑定也能发现18工具，不必重新注册。
切项目前任务到终态，用户保存并自行退出旧GUI；目标聊天从真实cwd执行prepare。旧MCP连接拒绝新generation，按宿主支持方式新建连接/聊天；不能可靠建立则停止报告待验，不重复重装。

## 共同边界
固定上游0.1.28：17个业务工具与seagent_connect管理工具，总计18个，7个skills。单聊天顺序控制一个受管实例。Name是内部标识，Label可重复。截图不是精确几何分析，Solid数不是业务零件数。单位、坐标和父级变换需记录。图文/代码/路径可能进入模型服务，真实资料须授权；技能不是沙箱。超时不等于完成，不重试结果未知写操作。源数据保留，另存明确路径和覆盖意图。

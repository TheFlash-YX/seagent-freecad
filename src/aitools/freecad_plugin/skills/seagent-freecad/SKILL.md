---
name: seagent-freecad
description: 任务路由
---

# 任务路由

先读setup，从实际聊天cwd完成prepare/start/seagent_connect，再get_rpc_status/list_documents。导入读open-inspect；高亮截图读view-highlight；修改读edit；保存读save-export；错误读diagnose。参数见../../references/tools.md，不新增业务复合接口。

## 共同边界
固定上游0.1.28：17个业务工具与seagent_connect管理工具，总计18个，7个skills。单聊天顺序控制一个受管实例。Name是内部标识，Label可重复。截图不是精确几何分析，Solid数不是业务零件数。单位、坐标和父级变换需记录。图文/代码/路径可能进入模型服务，真实资料须授权；技能不是沙箱。超时不等于完成，不重试结果未知写操作。源数据保留，另存明确路径和覆盖意图。

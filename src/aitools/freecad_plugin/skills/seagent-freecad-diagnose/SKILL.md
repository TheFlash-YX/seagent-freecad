---
name: seagent-freecad-diagnose
description: 诊断与恢复
---

# 诊断与恢复

先doctor只读检查；未知9875不RPC、不接管、不kill、不换端口。旧generation拒绝是保护，不在旧聊天重绑。async文本返回job_id，用get_async_status到done/failed；同步无job_id不得凭造。账本未知/inflight阻止写入和切换，先查询真实状态。离线恢复须用户保存退出GUI并确认所有FreeCADCmd结束，再用manage.py resolve-offline --request <记录ID> --reason <人工核查依据>；保留审计不强清锁。见../../docs/troubleshooting.md。

## 共同边界
固定上游0.1.28：17个业务工具与seagent_connect管理工具，总计18个，7个skills。单聊天顺序控制一个受管实例。Name是内部标识，Label可重复。截图不是精确几何分析，Solid数不是业务零件数。单位、坐标和父级变换需记录。图文/代码/路径可能进入模型服务，真实资料须授权；技能不是沙箱。超时不等于完成，不重试结果未知写操作。源数据保留，另存明确路径和覆盖意图。

---
name: seagent-freecad-edit
description: 修改与事务
---

# 修改与事务

先查询属性可写性、单位和父级变换。Label可改，定位用Name。Placement区分绝对与增量、局部与全局。GUI修改顺序执行，事务异常abortTransaction；undo/redo重算复验。不自动保存覆盖源文件。

## 共同边界
固定上游0.1.28：17个业务工具与seagent_connect管理工具，总计18个，7个skills。单聊天顺序控制一个受管实例。Name是内部标识，Label可重复。截图不是精确几何分析，Solid数不是业务零件数。单位、坐标和父级变换需记录。图文/代码/路径可能进入模型服务，真实资料须授权；技能不是沙箱。超时不等于完成，不重试结果未知写操作。源数据保留，另存明确路径和覆盖意图。

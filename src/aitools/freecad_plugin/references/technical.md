# 固定上游技术注意

适用freecad-mcp0.1.28固定commit，参数见[tools.md](tools.md)，本次状态见[validation.md](../docs/validation.md)。这里不是业务或平台验收证明。

文档Name不同于Label/文件名，Label可重复。Solid/compound不是业务零件。FreeCAD长度通常mm；输入单位、坐标系、父App::Part/Link变换需分别核实，Placement局部与全局不同。

execute_code可能在GUI线程执行；同步超时不代表取消。execute_code_async仅后台独立计算，GUI写入用上游commit；返回TextContent中的job_id（通常job-前缀），get_async_status返回文本或job列表，到终态后才依赖结果。桥接账本按固定上游实际文本解析，未知保留。

execute_code_headless是独立FreeCADCmd进程，不共享GUI文档。原始Python内部结果有success/returncode/timed_out等，但实际MCP返回TextContent和isError，不承诺这些原始字段以JSON暴露。上游subprocess.run超时会结束它启动的headless子进程；这不等于终止GUI，也不能据任意宿主超时报文断言子进程已结束。管理桥不强杀GUI，未知状态须人工核验后恢复。

headless脚本落在用户`~/.cache/freecad-mcp/headless`，可能包含业务代码/路径；机器logs/profile也可能含数据，不能打包上传，不自动整理删除。cwd不是访问沙箱。

get_view不接受doc_name，先确认活动文档；focus_object可能清除选择，截图不替代数值测量。undo/redo依赖事务；导出STEP需明确keepPlacement并重读。上述业务行为在本次独立交付的真实GUI链路均待验证，不复用历史验收。

Parts Library/FEM需要独立资源、材料/约束/求解器配置，工具可发现不代表工程分析已验证。原版MCP初始化的server_lifespan会ping并查询Addon版本，不能当作无RPC的本地tools/list；桥接仅可信实例握手后才启动原版。

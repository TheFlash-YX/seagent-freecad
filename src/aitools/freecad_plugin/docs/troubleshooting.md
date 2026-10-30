# 诊断与恢复

优先实际安装副本scripts/manage.py doctor（机器locator定位data），只检查本地路径和TCP占用，不RPC。不输出token/完整环境/业务日志给模型。9875未知或身份缺失拒绝，不接管不杀进程不换端口；受管GUI未就绪保留窗口检查本地日志，不重复start。监听检查权限失败停止而不视为空闲。

未连接时bridge正常initialize/tools/list，CAD返回“尚未连接当前项目”；按setup真实cwd prepare/start/握手。旧generation拒绝时用当前项目新连接，不在旧聊天重绑。安装成功不能替代桌面技能发现、首连、切换验收。

pending.json保留在途、job或未知记录。查询get_rpc_status/get_async_status/list_documents允许，结果未知的写请求不重试；状态列表或返回文本必须核对真实job_id。上游headless超时内部可能结束自身helper，宿主超时不代表结束；不强杀GUI。桥意外退出在途记录保留，不自动清除。

离线解除未知记录：用户先保存退出所有FreeCAD/FreeCADCmd，人工通过系统进程核查和日志确认无任务；manage.py resolve-offline --request <记录ID> --reason '核查方式和结论'。脚本再次确认无受管GUI、无9875及无FreeCAD/FreeCADCmd进程，然后写recovery-audit.json保留原记录。状态仍未知不可解除，不能把超时当核查依据。不得自动删lifecycle.lock；中断锁owner.json保留后人工确认其进程身份退出，再处理锁，避免活请求清锁。

机器logs/profile、headless用户缓存`~/.cache/freecad-mcp/headless`可能含业务代码/路径；不打包、不上传、不自动整理删除。缺可选Parts Library/FEM不等于MCP故障，不宣称工程校核完成。

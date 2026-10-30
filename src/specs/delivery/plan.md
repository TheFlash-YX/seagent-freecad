# 实现方案

独立Python/uv与原版Addon；stdlib JSON-lines管理bridge只作身份/就绪/生命周期门控，业务参数结果透明转发。固定9875；本地进程/回执与每连接generation核验。未绑定正常initialize/tools/list；原版初始化有RPC，只在可信实例后启动。临时机器根/CODEX_HOME执行隔离宿主验证，真实GUI待验。

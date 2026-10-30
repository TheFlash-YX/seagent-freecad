# 更新、回退和卸载

源码ZIP更新解压到新版本目录，不覆盖旧源码/机器配置/profile/runtime。新版本用新的机器data根bootstrap/configure/deploy check（不install），不迁移binding或模型。所有在途/异步/headless必须到终态，用户保存退出旧GUI；未知9875或任务拒绝，绝不kill。

新版本Python运行**新版本源码**scripts/lifecycle.py update --data <旧机器根> --to-data <新机器根>，默认只计划；检查结果后显式--apply。核对归属/hash、共享marketplace用途后走官方remove/add；保留全部旧文件。更新失败不会自动恢复注册，可能暂时不可用；错误与upgrade-failure.json明确保留现场。无共享冲突时，用旧版本源码deploy.py install --data <旧机器根>恢复旧注册；若新marketplace已注册，先按实际list核验再用其对应lifecycle卸载/处理，不自动覆盖。

回退相同原则：使用**目标旧版本源码**的lifecycle.py rollback --data <当前新机器根> --to-data <保留旧机器根>，先计划再--apply；这样generate使用目标旧源码，不把当前源码写到旧包。两个data根必须互不包含。跨版本真实宿主/GUI回退尚待验，模拟测试不能冒充实机通过。

卸载：scripts/lifecycle.py uninstall --data <机器根>先计划，--apply显式移除已核对归属的插件注册。共享marketplace不自动删除，全部runtime/配置/profile/日志/模型均保留；删除源码不等于卸载缓存。本候选不提供自动清理运行时，避免误删被改文件。恢复需明确重新deploy install，不自动重启客户端。

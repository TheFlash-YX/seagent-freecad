# 安装、运行与生命周期

适用本包0.1.0/macOS arm64/FreeCAD1.1.4，2026-10-27。固定来源见upstream.lock.json；官方宿主机制见 https://developers.openai.com/plugins/build/plugins 。根portable command只接受裸命令或包内`./`路径，本包使用`./scripts/launch.sh`；不用绝对`/bin/sh`，不依赖未验证`${PLUGIN_ROOT}`替换。

## 目录与隔离

默认 `$HOME/Library/Application Support/SEAgentFreeCAD/` 包含：
- runtime/{uv,python,upstream,.venv,READY}：受管依赖，源码hash清单upstream-files.json逐文件核对；上游不改。
- downloads/：固定hash公共归档与新建uv缓存，升级不依赖开发机私有环境。
- config.json：明确FreeCAD应用、GUI/freecadcmd argv、Addon路径、固定SHA，不存凭据。
- freecad-profile/：专用配置及原版Addon设置；通过实际FreeCAD CLI `FREECAD_USER_HOME`/`FREECAD_USER_DATA`（目录须先存在）隔离。`-M`加载上游Addon，不写用户全局Mod目录。
- instance.json：PID、ps启动时间及完整命令、应用、启动argv；仅进程归属，不是聊天所有权。
- logs/与工作派生数据：保留用户数据；模型输出由任务明确路径，绝不默认写插件缓存。

FreeCAD1.1.4内置Python3.11与MCP Python3.12.13分开。freecadcmd配置是argv数组，经shlex.join交给原版CLI，避免空格/中文拆词。尚未完成第二台干净电脑完整流程，不能把隔离目录等同完整无开发环境验收。

## 连接与端口

doctor只TCP探测/本地文件，不向未知RPC发ping。start端口未知占用拒绝；已记录受管进程存在但无监听则报未就绪，不重复启动。MCP启动前lsof监听PID必须与instance及ps身份一致。原版tools/list不执行模型操作；需要GUI的工具须有正确实例。

这是启动前保护，不是全时强制隔离。原版长连接活跃期间若端口后来被替换，上游可能重新连接；本包不修改/代理上游，发现异常应停止调用并人工诊断。不宣称阻止别的聊天访问同端口。重复服务初始化不启动CAD、导入或保存。

## 认证和权限

仅loopback。可用原版FREECAD_MCP_TOKEN环境配置并在专用Addon配套设置，凭据不进入命令参数、版本资料、模型上下文或日志。不要假设宿主继承任意环境变量；当前默认未配置token的本地合成测试不能外推认证验收。使用非空token时应实际验证匹配/拒绝，不关闭宿主原有审批设置。

## 中断、升级与卸载

下载写`.part`，hash通过后才rename，不执行未校验产物；失败非零、有界重试。解压使用固定hash归档、路径检查；上游进一步用Python data过滤防路径/软链逃逸。`*.partial`保留中断状态，不自动删用户文件；检查来源和内容后显式移出/删除该partial目录再重跑。已有不同/被改动源或配置不覆盖；保留旧安装。安装READY最后落盘，launcher缺READY清晰失败。

运行与构建依赖分别由原版uv.lock及build-requirements.lock锁定。上游PEP517动态构建依赖原本没有冻结，本包预装hash固定构建依赖，再frozen/inexact/no-build-isolation安装原版；不改上游pyproject。保留build依赖便于复现，不能只统计上游运行依赖数作为全部安装包数。

升级通过官方插件安装入口更新副本，重新核对固定源hash、17原工具Schema、安装与身份初始化，不直接修改Codex缓存。卸载注册不停止CAD，先按用户意图保存。可选清理仅删除清单一致自有文件，修改/未知文件和全部用户资料保留；不删除共享Addon、手动MCP和其他插件。详见README命令。

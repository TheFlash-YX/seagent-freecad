# 源码内置验证记录 — 2026-11-05

源码内置改动已由父代理审查并应用到本地目标仓库；父代理已独立完成安装、回归、真实stdio与GUI截图验收，见末节。宿主安装副本与GitHub远端未更新；全进程网络隔离、Windows等范围仍未验证。下文保留子代理候选阶段的事实与阻塞记录。

## 基线与输入

- 只读目标：TheFlash-YX/seagent-freecad，origin `https://github.com/TheFlash-YX/seagent-freecad.git`，main，HEAD `017e13b2d51b5f26c9bd2a0f4709e7ce11e946a1`；开始和结束只读检查均干净。由 `git archive HEAD` 导出全部跟踪文件与 mode，未携带 .git、模型、运行数据或凭据。
- 候选插件0.1.1，上游0.1.28 / `8babe9927ce8e6e8fe7dd6ae2ffa2c93776e845a`；uv0.11.14、独立CPython3.12.13，两个插件依赖锁未改。模型由父平台确认gpt-6.1-sol。
- macOS arm64；本机只读确认FreeCAD app BundleVersion 1.1.4，GUI/freecadcmd文件存在。未用其历史结果证明本次GUI通过。
- 固定归档由开发维护操作实际下载，SHA256正确；另取得Git API完整树，逐一核对81 blobs、8,223,860字节、Git blob IDs与mode，无链接/gitlink。固定树包含examples/adk/.env，仅为上游GOOGLE_API_KEY=xxxx示例配置，非本机凭据；根.gitignore显式保留完整vendor。LICENSE与既有版权副本一致。
- 所有DATA在任务专用隔离工作目录，位于目标revised仓库之外。没有使用现有FreeCAD MCP源码或旧venv。仅复制并校验已下载uv/Python发行包，两个成功安装的uv包缓存初始均为空；没有upstream.tar.gz源码缓存。

## 实际执行与结果

以交付目录为 `$TASK`、插件为 `$TASK/revised/src/aitools/freecad_plugin`。运行时与下载属于临时 `work/`，完成后清理；简明脱敏证据在交付的 `evidence/`，不是分发文件。

| 项目 | 实际命令/输入 | 结果 |
|---|---|---|
| V01 固定来源 | tests/vendor_snapshot.py --archive 固定归档 --git-tree 固定树 --output 新目录；完整manifest比较 | 0；81文件字节/mode、归档hash、LICENSE一致 |
| V02 Git候选与导出 | 临时git init/add、全部Git blob比对；git archive候选tree后运行check_package.py | 0；无忽略、换行或mode丢失 |
| V03/V04 独立安装复用 | acceptance.py --data 新DATA --output 新证据 --artifact-cache 锁定发行包目录 --freecad-app /Applications/FreeCAD.app | 0；download-only、bootstrap及reuse-bootstrap均0，本地项目构建安装 |
| V05–V10/V13 来源与失败 | DATA venv Python运行tests/test_vendor_install.py | 0；21项、无跳过。覆盖缺失/修改/新增vendor，manifest hash/commit/重复键/穿越，依赖锁，旧自洽异源，缺清单、partial、复制失败、源码发布后清单失败恢复、清单后中断、依赖失败READY、重叠/链接/FIFO/mode，正常pyc与未知源码/Addon拒绝 |
| V11 生命周期 | DATA venv Python运行tests/test_management.py | 0；6项、无跳过。原端口/卸载/doctor/shlex行为，0.1.0旧owner、修改/未知用户文件保留，真实跨进程活动MCP租约阻止卸载 |
| V12 download-only | acceptance驱动实际执行 | 0；仅uv/Python发行包，未创建源码或READY，不是离线包 |
| M01/M02/M03 | DATA venv Python运行tests/probe_mcp.py，经实际launch.sh | 0；17工具，inputSchema与仓库固定快照及安装原定义均一致，schema-differences.json为空；模块/CLI/direct_url均属于本次DATA |
| 活动MCP保护 | 同一真实stdio连接存续时实际调用environment-run及uninstall --remove-runtime | 两次预期非零，明确活动MCP租约拒绝；READY与CLI保留。探针本身退出0 |
| M04 | configure、doctor、无GUI的stdio探针 | 0；没有调用start；本次9875初查无监听，端口保护测试只使用自建临时监听、无RPC payload |
| M06 | DATA venv Python运行tests/test_project_init.py；SOUL文件比对 | 0；11项，无跳过；两份SOUL、mcp.json、固定工具Schema和Skill逐字节保持基线 |
| 补丁 | git diff --no-index --binary baseline revised；另一baseline副本git apply --check -p2及实际apply | diff预期1；check/apply均0，结果全文件字节和可执行位与revised一致 |

活动FreeCAD身份保护通过受控进程身份边界回归验证；实际GUI活动实例拒绝验证包含于probe_gui.py，child尚未执行。没有将模拟身份测试写成真实FreeCAD进程验收。

## 网络证据与明确失败

安装代码静态审计未发现执行中的上游clone/fetch/archive、Git依赖或在线源码回退；溯源URL仅元数据/维护文档。acceptance.py通过PATH curl包装器实际向固定源码URL自检，返回预期97并记录BLOCKED；与安装请求日志分开保存。

尝试不预置uv发行包的download-only：真实curl向锁定uv GitHub发布URL发请求，三次连接超时，最终28；验收驱动返回1并保留失败记录。这是发行物网络限制，未改机器网络、不换来源。随后预置校验正确的uv/Python发行包，在同一拒绝上游URL的包装器下使用另一全新DATA安装成功；uv包缓存初始为空，PyPI锁定包实际安装成功。成功场景安装curl请求为0，未下载上游归档；不能把它说成首次uv联网下载成功。

结论限定为“curl边界自检、静态审计、空源码缓存独立安装通过”。未具备覆盖所有子进程的完整网络隔离审计，不能宣称全链路网络阻断已验收或完全离线。

## 阻塞与父验收

M05：child sandbox执行 `/bin/ps` 返回 `Operation not permitted`。probe_gui.py在启动前核对进程身份能力失败，退出1；未启动GUI、未生成截图。这是child权限边界，不是FreeCAD源码功能失败。父代理在独立DATA重新执行：

```sh
python3 src/aitools/freecad_plugin/tests/acceptance.py \
  --data /绝对路径/全新验收/data --output /绝对路径/全新验收/evidence \
  --artifact-cache '/Users/ninebot/Library/Application Support/SEAgentFreeCAD/downloads' \
  --freecad-app /Applications/FreeCAD.app --gui
```

编排Python须在被测DATA之外。先核对真实app和9875；未知占用即非零退出，不接管。脚本请求来自真实工具Schema，创建唯一合成文档、10×20×30mm长方体、查询并断言体积6000mm³、取1000×800等轴截图；需实际查看图像。只关闭本次合成文档和身份核验匹配的专用实例。不导入公司模型，不向未知RPC发请求。详细请求已写入tests/probe_gui.py。

M07：官方宿主installedPath/vendor发现未执行，当前安装副本未修改；不得声称已分发到DC或所有宿主。未建立新用户可见聊天。

数据路径保护明确覆盖目标仓库重叠、DATA根项目marker和运行子路径逃逸；不通用识别任意第三方项目祖先，应显式选择项目源码之外的独立DATA。旧自定义进程启动不能可靠识别；切换前人工停用旧MCP并保存退出CAD，优先新DATA。未测Windows、第二台机器、17项工具全部业务操作、非空token认证和完整工程分析。

## 父代理独立验收与本地合入 — 2026-11-05

父平台任务记录确认子代理模型为`gpt-6.1-sol`。实现由子代理完成；父代理负责范围规划、只读代码审查、退回修复、补丁合入及下列实际验收，没有代写实现代码。

合入前重新确认真实目标`/Users/ninebot/yx/seagent-freecad`处于上述干净基线；实际执行`git apply --check -p2`和`git apply -p2`均退出0。合入后逐文件比较123个交付文件的字节与可执行位，全部与审查候选一致；随后仅同步README、CHANGELOG、runtime及开发记录中的验收状态，不改实现代码。固定81文件vendor另经父代理与SHA-256正确的原归档全量比对，无遗漏、额外文件或mode差异。

父验收使用原运行时之外的全新被测DATA；编排仅借用既有CPython3.12发行解释器，不复用旧MCP模块、venv或源码。实际命令：

```sh
env PYTHONDONTWRITEBYTECODE=1 \
  '/Users/ninebot/Library/Application Support/SEAgentFreeCAD/runtime/python/bin/python3.12' \
  /Users/ninebot/yx/seagent-freecad/src/aitools/freecad_plugin/tests/acceptance.py \
  --data /Users/ninebot/yx/SEAgent/data/derived/freecad-mcp-vendoring-parent-20261105-01/data \
  --output /Users/ninebot/yx/SEAgent/data/derived/freecad-mcp-vendoring-parent-20261105-01/evidence \
  --artifact-cache '/Users/ninebot/Library/Application Support/SEAgentFreeCAD/downloads' \
  --freecad-app /Applications/FreeCAD.app --gui
```

总退出码0。证据根为上述`--output`目录，原始日志、图像、运行时均未加入分发清单。

| 验证 | 父代理实际结果 |
|---|---|
| 上游源码URL包装器自检 | 返回预期97；实际安装无上游源码归档，保留全进程网络审计未覆盖的限制 |
| download-only、新安装、重复安装 | 均0；仅预置校验一致的uv/CPython发行包，uv包缓存初始为空 |
| 来源/安装回归 | 21项通过，无跳过 |
| 管理回归 | 6项通过，无跳过；含旧owner/用户文件和活动MCP卸载保护 |
| 项目初始化回归 | 11项通过，无跳过 |
| 包检查、configure、verify-upstream、doctor | 均0 |
| 真实stdio | 17工具，与固定仓库inputSchema一致；活动MCP期间安装及卸载均被拒绝 |
| 真实GUI合成样例 | 创建唯一文档`VendoringBox_67efc1066db3`与Part::Box；尺寸10×20×30 mm，体积6000 mm³断言通过 |
| 实际活动GUI安装拒绝 | 专用FreeCAD运行时安装被拒绝，READY保留，见`gui/active-install-refusal.txt` |
| 截图与人工查看 | `gui/box.png`为1000×800真实viewport图；父代理实际查看，长方体可见，无空图或错误画面 |
| 资源清理 | 仅关闭本次合成文档和身份匹配的专用实例；随后只读核验9875无监听 |

`results.json`记录每条实际argv、退出码和预期码；`mcp/summary.json`、`gui/summary.json`及工具返回记录可复现协议/几何证据。截图属于显示验证，精确尺寸/体积来自显式数值断言，不从图片估计。

父工作区不存在可被平台项目执行器识别的根Python环境声明：prepare返回`environment:null`，status返回`DESIGN_AGENT_PROJECT_ENVIRONMENT_UNAVAILABLE`。因此以上结论来自明确命令执行及日志/图像复验，不冒称平台声明式项目检查已通过。

交付状态：本地目标仓库工作树已更新，未创建Git提交、未推送或合并远端、未更新官方宿主安装副本。现有生产DATA和其他CAD实例未改。源码集成、独立运行时与GUI最小闭环验收通过；M07、全进程网络隔离、无缓存uv联网获取、Windows与完整工程分析仍保持前述限制。

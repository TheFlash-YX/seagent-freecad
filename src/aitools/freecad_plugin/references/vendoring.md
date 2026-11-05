# 固定上游源码的分发与维护

插件 0.1.1 内置 `neka-nat/freecad-mcp` 0.1.28，commit `8babe9927ce8e6e8fe7dd6ae2ffa2c93776e845a`。普通 Git 文件快照为 81 blobs、8,223,860 字节；包括隐藏文件、资源、测试和 MIT LICENSE。业务源码逐字节不变，不启用嵌套 .github 工作流。插件发布版本与上游版本独立。

归档来源：<https://codeload.github.com/neka-nat/freecad-mcp/tar.gz/8babe9927ce8e6e8fe7dd6ae2ffa2c93776e845a>；SHA-256 `f2d623d0d1dec086a46e156d2d169c0456b52a81db5593134b641e7baa08870f`。完整树可从 GitHub Git Trees API 对该 commit 获取，必须 `recursive=1`、`truncated=false`。锁文件中 URL 仅作溯源，用户安装不下载该归档，不 clone/fetch，不提供源码在线回退。

## 维护者重现导入

在仓库外的任务临时目录下载上述固定归档和 Git tree JSON。使用兼容 Python 执行（输出目录必须不存在）：

```sh
python3 src/aitools/freecad_plugin/tests/vendor_snapshot.py \
  --archive /任务目录/upstream.tar.gz \
  --git-tree /任务目录/upstream-tree.json \
  --output /任务目录/verified-snapshot
```

脚本先核对归档 SHA-256，拒绝绝对路径、非规范路径、`..`、链接、设备文件、未知/重复条目；对每个文件校验 Git blob ID、size 和 mode 后才写输出。去掉归档容器，不执行上游脚本。输出清单使用 UTF-8、按路径排序、JSON indent=2、尾换行，含 size、SHA-256 和 Git mode；清单不包含自身。随后人工比较输出与 vendor 及 vendor-files.json，并核对锁文件的 manifest_sha256。根 .gitattributes 的 `* -text` 保证字节不转换。

`source_integrity.expected()` 在安装和管理入口核对锁文件、清单、完整 vendor 文件集合、mode、内容、隐藏文件以及两个 uv.lock 和构建依赖锁。清单不是外部签名；可共同修改的仓库文件不能提供独立信任证明。运行时清单仍采用路径→SHA-256，并须与当前 vendor 期待值完全一致；不能给未知旧目录重算清单以登记信任。

运行时只额外允许：受管 `.py` 同目录下 `__pycache__/<模块>.cpython-<版本>[.opt-1|.opt-2].pyc`。未知源码、sourceless `.pyc`、未知 Addon、额外目录和链接均拒绝。vendor 本身不允许任何生成缓存。

## 升级

未来升级由维护者选择新的固定提交，独立审查许可证、业务源码、依赖锁和工具 Schema 差异，调整导入脚本固定值、完整清单、来源锁及版本，并重跑验收。不跟随 HEAD，不实现用户运行时自动升级。首次集成保持 uv、Python、uv.lock、build-requirements.lock 和 17 工具 Schema 原值。

## 复验

在仓库外选择全新 DATA 与证据目录，用 DATA 之外的编排 Python 运行：

```sh
python3 src/aitools/freecad_plugin/tests/acceptance.py \
  --data /绝对路径/新验收/data --output /绝对路径/新验收/evidence \
  --artifact-cache /可选的只读发行包目录 \
  --freecad-app /已确认路径/FreeCAD.app
```

省略 artifact-cache 将正常下载 uv/Python；指定时仅复制并核验 uv.tar.gz/python.tar.gz，不复制旧 upstream、venv 或 uv 包缓存。新 uv 缓存起初为空。驱动实际执行 download-only、安装、重复安装、源码损坏/中断回归、管理/身份回归、configure、doctor、真实 stdio 和固定 Schema 对比，逐命令记录 argv/退出码。任一步失败退出非零。curl 包装器自检先证明上游 URL 被拒绝，安装阶段另记 curl 请求；静态检查覆盖实际安装脚本。此方法不提供所有子进程的完整网络隔离证明，不修改全机网络设置。

明确具备专用 GUI 条件且 9875 空闲后，增加 `--gui`。它先核对进程身份能力，再显式 start，使用真实发现且与固定基线一致的 Schema 新建 10×20×30 mm `Part::Box`，查询尺寸/6000 mm³ 体积并取真实截图；结束关闭本次文档和已登记的专用 GUI。截图需人工查看，不能视为完整工程分析验收。未知监听或无法核对 PID 时非零退出；不接管、不换端口。GUI 脚本也可独立运行 `tests/probe_gui.py --package /插件根 --output /新证据/gui --start --close-owned`，使用该 DATA venv Python，且已 configure。

宿主官方安装及 installedPath 的 vendor 发现是单独验收项，本脚本不修改当前安装副本，不创建用户可见测试聊天。当前开发实际结果和未验收项见仓库 `src/specs/freecad-mcp-vendoring/validation.md`。

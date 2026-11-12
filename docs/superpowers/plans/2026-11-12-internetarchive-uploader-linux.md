# InternetArchiveUploader Linux Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在用户 Fork 中实现 Linux GUI、自定义认证配置、多文件拖拽队列、可配置并发、类型预填及自动构建。

**Architecture:** 保留 PySide6 与 internetarchive 库。将 item 级配置与文件任务分离，使用独立认证会话的后台任务和主线程事件调度，避免全局日志重定向。GUI 扩展写在手工维护的组件中，不直接覆盖 Designer 生成文件。

**Tech Stack:** Python 3.11（先验证上游依赖兼容性）、PySide6、internetarchive、pytest、pytest-qt、PyInstaller、GitHub Actions。

**Spec:** `docs/superpowers/specs/2026-11-12-internetarchive-uploader-linux-design.md`；实施时将本文与 spec 一起放入 Fork。

## Global Constraints

- 用户已确认：一文件一任务，默认共用指定 identifier，允许逐任务修改。
- 并发默认 2，范围 1～8；属于文件级并发，不是分片上传。
- 配置优先级：--config > GUI 保存路径 > `${XDG_CONFIG_HOME:-~/.config}/internetarchive-uploader/ia.ini`。
- 目标 Linux x86_64，Ubuntu 22.04、24.04；保留 Windows 兼容，不承诺 ARM64。
- 不静默覆盖远端同名文件，不自动修改已有 item metadata，不擅自小写化 identifier。
- 不在代码、日志、CI 或产物中保存凭据；真实上传必须明确授权。
- 用户负责所有需要图形交互的实际测试；代理负责非交互自动化、无头冒烟测试和构建验证，不宣称完成实际桌面测试。
- 不包含队列持久化、分片续传、目录递归拖拽、完整已有 metadata 编辑器。
- 当前工作区不是 Git 仓库；执行前确认 Fork 所有者，使用隔离分支/工作区，不能在公共工作区初始化无关仓库。

## Review Focus

1. 中文/空格路径和无写权限配置：正确选中配置，不静默切账号（任务 2）。
2. 相同 item 的远程文件名冲突及查询超时：不得当成可安全覆盖或不存在（任务 4）。
3. 文件导入后被替换、重试前请求结果不明：不得盲目重复提交（任务 4、5）。
4. 并发调低、初始化失败、停止后恢复：不得超额派发、永久阻塞或丢任务（任务 5）。
5. 无桌面门户/防休眠支持及从其他目录启动产物：降级正常，资源和认证路径正确（任务 7、8）。

## 文件布局

新增 `uploader/` 包：
- `models.py`：ItemConfig、UploadTask、枚举和结果类型。
- `config.py`：配置优先级、文件权限及配置绑定。
- `detection.py`：扩展名/MIME/文件头判断。
- `archive_client.py`：internetarchive 适配和错误分类。
- `item_service.py`：item 准备、文件冲突、结果核实。
- `queue.py`：纯逻辑调度状态机。
- `workers.py`：后台任务及 Qt 信号桥接。
- `resources.py`：资源路径与可选防休眠封装。
- `widgets/task_table.py`：拖拽和任务表；`widgets/settings_dialog.py`：配置路径设置。
- `controller.py`：GUI 事件与业务协调。

修改 `main.py`、`LoginDialog/login_dialog.py`、`.gitignore`、`requirements.txt`、`README.md`。保留现有 `UI/main_window.py` 布局，手工组合新增组件；不改动不相关的 preset 功能。

新增 `tests/`、`requirements-dev.txt`、`pytest.ini`、`packaging/linux.spec`、`scripts/smoke_gui.py`、`scripts/check_dist.py`、`.github/workflows/build-linux.yml`、`docs/manual-linux-test.md`。

## Task 1: Fork、隔离工作区与依赖契约验证

**Files:** 创建 `tests/test_dependency_contract.py`、`requirements-dev.txt`、`pytest.ini`；修改 `requirements.txt`、`.gitignore`。

**Interfaces:** 产出可安装的固定依赖集和记录在 `docs/dependency-contract.md` 中的库调用约定；不提前写上传实现。

- [ ] 确认用户的 Fork 账号/组织和执行方式；只读检查 gh 登录身份，不打印 token；按 git-worktrees 技能创建隔离工作区。
- [ ] Fork/clone 上游，核对 origin/upstream；复制批准的 spec 与计划，记录上游 commit SHA。
- [ ] 创建虚拟环境验证 Python 3.11 与固定依赖；如依赖不可用，记录错误及兼容版本证据，不直接无上限升级。
- [ ] 编写契约测试：检查显式 config_file 会话创建、上传方法参数、identifier 校验规则；请求发送用 mock，不访问真实账号。首次运行确认缺少测试环境或约定未建立的失败。
- [ ] 建立测试依赖与配置，检查 IA 源码确认查询异常、重试、进度接入、配置 fallback、认证写入行为；把确切调用签名和进度能力记录到依赖契约。若 Python 3.11 不支持，先更新计划并报告，不能悄悄变更构建基线。
- [ ] `python -m pytest tests/test_dependency_contract.py -v` 应全部通过；安装/编译失败不算通过。
- [ ] 提交 `build: establish tested dependencies and upstream baseline`。

## Task 2: 配置路径与安全认证

**Files:** 创建 `uploader/__init__.py`、`uploader/config.py`、`tests/test_config.py`；修改 `LoginDialog/login_dialog.py`、`main.py`。

**Interfaces:** `resolve_config_path(cli: str | None, saved: str | None, env: Mapping[str, str]) -> Path`；`ConfigManager(path: Path)` 提供 `validate() -> None`、`new_session() -> ArchiveSession`、`configure(username: str, password: str) -> None`；无默认账号 fallback。

- [ ] 编写失败测试：`test_cli_overrides_saved`、`test_xdg_default`、`test_unicode_space_path`、`test_invalid_config_never_falls_back`、`test_created_file_mode_0600`、`test_unwritable_destination`，断言路径精确匹配、损坏配置报错及 POSIX 权限。
- [ ] `python -m pytest tests/test_config.py -v` 确认失败。
- [ ] 实现解析、显式校验和认证；创建目标目录前由 GUI 确认，写凭据时安全创建/替换，避免先宽权限写入再收紧；认证成功重新创建会话，密码不 strip、不缓存、不日志输出。
- [ ] 登录框接收 ConfigManager，认证放后台执行，通过信号更新结果；删除吞掉异常的空 except，输出脱敏分类错误。
- [ ] 运行上述测试及依赖契约，确认全部通过；提交 `feat: support explicit secure IA configuration`。

## Task 3: Item/文件模型和类型识别

**Files:** 创建 `uploader/models.py`、`uploader/detection.py`、`tests/test_models.py`、`tests/test_detection.py`。

**Interfaces:** `ItemConfig(identifier: str, metadata: dict[str, str | list[str]], confirmed: bool)`；`UploadTask(id: str, local_path: Path, item_key: str, remote_name: str, config_path: Path, size: int, mtime_ns: int, state: TaskState)`；`Detection(mediatype: str | None, reason: str, needs_confirmation: bool)`；`detect_file(path: Path) -> Detection`。TaskState 为 DRAFT/QUEUED/RUNNING/SUCCEEDED/FAILED，自动重试记录在额外 attempt/retry_at 字段。Item 初始化状态独立保存。

- [ ] 编写失败测试：常见格式映射、ZIP/7Z/RAR 不确定、扩展名与文件头矛盾需确认、未知格式、混合文件共享 item 冲突、人工值不覆盖；同 item 共享同一 metadata 配置。
- [ ] `python -m pytest tests/test_models.py tests/test_detection.py -v` 确认失败。
- [ ] 实现数据类型及有限长度文件头读取，不执行文件/解压；title 建议与手动确认分离；不使用未经验证的集合权限推断。
- [ ] 运行上述测试全部通过，提交 `feat: model item uploads and detect media types`。

## Task 4: IA 适配、条目准备与冲突检查

**Files:** 创建 `uploader/archive_client.py`、`uploader/item_service.py`、`tests/test_archive_client.py`、`tests/test_item_service.py`。

**Interfaces:** `ItemSnapshot(exists: bool, metadata: dict, files: dict)`；`UploadResult(remote_name: str, verified: bool)`；`ArchiveClient(config: ConfigManager).inspect(identifier: str) -> ItemSnapshot`、`.upload_file(task: UploadTask, metadata: dict | None) -> UploadResult`；`ItemService.prepare(item: ItemConfig, tasks: list[UploadTask], snapshot: ItemSnapshot) -> Preparation`，Preparation 包含 existing、initializer_task_id 和 conflicts。规范化错误：AuthenticationFailure、PermissionFailure、RetryableFailure(retry_after)、RemoteStateUnknown、ConflictFailure。

- [ ] 编写失败测试：查询超时不返回 exists=False；已有 item 上传 metadata=None；新 item 只有初始化任务带 metadata；同名远端和本地任务均报冲突；无权限不重试；identifier 大小写保持；文件 size/mtime 改变时拒绝执行。
- [ ] `python -m pytest tests/test_archive_client.py tests/test_item_service.py -v` 确认失败。
- [ ] 按任务 1 契约实现适配。使用文件映射明确远端文件名，检查返回的每个响应；默认跳过冲突，需用户另行选择新名字，不实现无提示覆盖。
- [ ] 添加 `reconcile(task: UploadTask) -> str`，仅返回 confirmed/absent/unknown；测试超时后同名文件仅凭存在不能确认本次成功，需可信大小和校验信息。无法确认则停止并要求核实，不自动再传。
- [ ] 运行测试全通过；提交 `feat: safely prepare items and append uploads`。

## Task 5: 调度、重试与独立后台工作

**Files:** 创建 `uploader/queue.py`、`uploader/workers.py`、`tests/test_queue.py`、`tests/test_workers.py`。

**Interfaces:** `TaskQueue(limit: int = 2)` 提供 `add(task: UploadTask) -> None`、`set_limit(n: int) -> None`、`start() -> None`、`stop_dispatch() -> None`、`next_ready(now: float) -> list[UploadTask]`、`complete(task_id: str, result: UploadResult) -> None`、`fail(task_id: str, error: Exception, now: float) -> None`；`retry_failed(task_id: str) -> None`。`UploadWorker(task, client, metadata)` 通过 task_id 关联的 result/error/log 信号通知主线程；所有队列状态只在主线程修改。

- [ ] 用 fake clock/client 编写失败测试：默认 2、边界 1/8、超界报错；同新 item 只派初始化文件；初始化失败阻止后续且可人工重试恢复；降低额度不取消运行任务；停止/恢复不丢任务；单任务失败不影响其他 item。
- [ ] `python -m pytest tests/test_queue.py tests/test_workers.py -v` 确认失败。
- [ ] 实现可注入时钟的调度与独立会话工作池。自动重试最多 3 次（总尝试最多 4 次），指数退避基数 2 秒、上限 60 秒；服务端 Retry-After 大于上限时仍尊重该值，不提前重试。延迟重试不占上传工作槽。
- [ ] 增加测试：401/403 不重试、429 尊重 Retry-After、网络结果不明先 reconcile、相同远程目标互斥、日志只包含对应 task_id、不泄露凭据。
- [ ] 默认新 item 初始化后允许同 item 并发；仅在用户授权测试证明其不可靠时启用按 item 串行的兼容策略，并记录原因。无真实验证时明确标记未实测。
- [ ] 运行本任务及此前全部非 GUI 测试，全部通过后提交 `feat: schedule bounded concurrent upload tasks`。

## Task 6: 拖拽任务界面与配置交互

**Files:** 创建 `uploader/widgets/__init__.py`、`uploader/widgets/task_table.py`、`uploader/widgets/settings_dialog.py`、`uploader/controller.py`、`tests/test_gui_queue.py`；修改 `main.py`。

**Interfaces:** `TaskTable.files_dropped(list[str])`、`SettingsDialog.config_selected(str)`；`UploadController.import_files(paths: list[Path], default_item: ItemConfig) -> None`、`.start_queue() -> None`、`.stop_dispatch() -> None`。控制器消费任务 2～5 接口；GUI settings 只保存非敏感路径与并发设置。

- [ ] 编写 pytest-qt 失败测试：本地 URI 多文件拖拽、一文件一行、默认共同 identifier、单项/批量修改、忽略非本地 URL/目录并显示提示、运行行不可编辑、重复文件处理、远端冲突不能启动。
- [ ] `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_gui_queue.py -v` 确认失败。
- [ ] 组合任务表、item 表单、当前配置路径、并发 spinbox、启动/停止派发/重试按钮与独立日志；保留额外 metadata 对话框。移除旧单线程 uploader 连接和 stdout/stderr 全局重定向。
- [ ] 实现类型建议确认、混合类型提示、用户修改锁定、已有 item metadata 只读。切换配置时活动任务禁止，排队任务须显式重新绑定并清除旧账号的 item 查询缓存。
- [ ] 添加无头测试：导入不自动上传、停止不声称取消活动请求、成功文案不声称派生完成、点击条目链接调用正确 URL、登录成功使用新 session。
- [ ] 运行全部测试通过后提交 `feat: add drag-and-drop upload queue interface`。实际拖拽体验交用户验收，不由代理操作桌面。

## Task 7: Linux 资源、降级与关闭生命周期

**Files:** 创建 `uploader/resources.py`、`tests/test_runtime.py`、`scripts/smoke_gui.py`；修改 `main.py`、`LoginDialog/login_dialog.py`。

**Interfaces:** `resource_path(relative: str) -> Path`；`optional_keep_awake()` 上下文管理器；GUI 关闭控制由 controller 统一处理，等待模式保持事件循环运行。

- [ ] 编写失败测试：切换 cwd 后图标仍存在、认证不写安装目录、防休眠异常仍执行上传、无桌面门户不导致启动失败、活动任务时关闭提示且不会直接销毁线程。
- [ ] `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_runtime.py -v` 确认失败。
- [ ] 实现基于模块/打包资源目录定位，替换所有固定 cwd 资源路径；不强制覆盖用户设置的 Qt 平台主题；修正登录框引用不存在图片的问题。
- [ ] 实现退出选项：取消退出；停止派发并等待活动任务结束后退出。首期不提供强制杀死线程按钮，保证关闭期间 UI 可响应。
- [ ] 新增非交互 `--smoke-test`，不登录、不联网、创建界面后自动退出；测试正常退出码与图片资源加载。
- [ ] 运行测试全部通过；提交 `fix: make Linux startup and shutdown portable`。

## Task 8: Linux 构建和安全产物

**Files:** 创建 `packaging/linux.spec`、`scripts/check_dist.py`、`.github/workflows/build-linux.yml`、`tests/test_packaging_contract.py`；修改 `requirements-dev.txt`。

**Interfaces:** `python scripts/check_dist.py <dist-dir>` 非零表示缺文件/含凭据；打包程序支持任务 7 的 `--smoke-test`。

- [ ] 编写失败测试：产物必须包含资源、LICENSE、README；拒绝 ia.ini、会话日志、测试密钥样本。配置模板如需要必须使用明确不同名称且无秘密。
- [ ] `python -m pytest tests/test_packaging_contract.py -v` 确认失败。
- [ ] 编写 PyInstaller onedir spec，包含 PySide6 插件、assets、README、LICENSE；只纳入列明资源，不整目录收集工作区。
- [ ] 创建 Workflow：Ubuntu 22.04 x86_64 构建；Python 3.11；固定经过验证的依赖；安装必要 X11/Qt 运行库、Xvfb；运行 pytest 和源码 smoke，再打包/产物 smoke/安全检查。22.04、24.04 分别下载产物进行兼容性 smoke。
- [ ] 配置 pull_request、默认分支 push、v* tags、workflow_dispatch；基础 contents:read；单独 tag release job contents:write；不用 pull_request_target 执行外部代码。
- [ ] 生成版本化 tar.gz 和 SHA256SUMS；分支/手动任务仅 Artifact，版本标签发布 Release；测试不使用 IA secrets。
- [ ] 运行 `python -m PyInstaller packaging/linux.spec --noconfirm`，再执行产物 `--smoke-test` 与 check_dist。仅在成功后记录构建通过；本机缺系统依赖时明确报告，不用代码检查冒充产物执行。
- [ ] 提交 `ci: build and release Linux desktop artifacts`。

## Task 9: 用户验收清单、文档与最终验证

**Files:** 修改 `README.md`；创建 `docs/manual-linux-test.md`、`docs/verification-results.md`。

**Interfaces:** 手工验收每项记录环境、步骤、期望、实际结果和通过/失败/未测试；用户执行图形交互。

- [ ] 编写用户清单：Ubuntu/X11/Wayland启动；非默认 ia.ini；多文件拖拽；统一与不同 item；metadata 人工覆盖；同名冲突；并发调节；停止派发；失败重试；关闭等待；解压产物在无 Python 环境启动。真实上传须先取得授权并使用合法测试文件。
- [ ] README 说明安装、--config、配置优先级、并发含义、metadata/item 区别、追加行为、安全限制、产物和上游许可。
- [ ] 运行 `python -m pytest -v`（无显示时设置 offscreen）、构建和 smoke，并将命令、退出结果和未完成验证写入 verification-results；不将用户尚未执行的测试标为通过。
- [ ] 按 requesting-code-review 技能进行最终审查，检查 spec 覆盖、凭据泄露、线程退出、远端误覆盖与发布权限；如无独立审查工具/会话，说明限制。
- [ ] 提交文档，向用户提供构建产物位置和逐项验收清单，等待用户反馈后修复；没有明确授权不自动合并、推送标签或发布正式 Release。

## 自检与执行门禁

覆盖：FR-01→任务1/9；FR-02→7/8/9；FR-03→2/6；FR-04→3/4/6；FR-05→4/5；FR-06→3/6；FR-07→8/9。Review Focus 五项均已分配测试。

首先需用户审阅本计划、选择执行方式并指定 Fork 所有者。实施过程每个任务完成后提交与验证，不把创建计划视为执行授权。真正需要图形交互的验证一律交用户。

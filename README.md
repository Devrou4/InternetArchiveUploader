# Internet Archive Uploader (Linux 增强版)

基于 [Devrou4/InternetArchiveUploader](https://github.com/Devrou4/InternetArchiveUploader) 的 Fork，
上游代码与设计保持不变，新增 Linux 桌面支持、批量拖拽上传队列、文件级并发、类型识别和自动构建。

上游许可证与版权声明见 `LICENSE`。

## 功能

- **Linux 图形界面**：Ubuntu 22.04 / 24.04（x86_64），X11 与 Wayland 下的可用 Qt 后端。
- **Windows 产物**：Windows Server 2022 / 2025 构建的 `.exe`（onedir，解压即用）。
- **批量拖拽**：一次拖入多个文件，一文件一任务；默认全部上传到同一个 item，也可逐条修改。
- **多文件共用 item**：不会为每个文件创建重复条目，也不会覆盖已有条目的 metadata。
- **可配置并发**：1～8，默认 2。这是“同时上传的文件数”，不是单个文件分片。
- **类型识别**：按扩展名 + 文件头推荐 `mediatype`；压缩包和未知格式要求人工确认。
- **自定义认证配置**：`--config` 或图形设置，支持中文与空格路径。
- **代理支持**：`--proxy` 或图形设置；登录、查询、上传全部走该代理。
- **手动确认后才上传**：导入文件不会立即上传。
- **只在 CI 构建**：GitHub Actions 产出 Linux 产物，不在本地打包。

## 安装

### 使用 CI 产物（推荐）

从 GitHub Actions 的 Artifact 或 Release 下载对应平台：

```
InternetArchiveUploader-<version>-linux-x86_64.tar.gz     # Linux
InternetArchiveUploader-<version>-windows-x86_64.zip      # Windows
SHA256SUMS-linux-<runner> / SHA256SUMS-windows-<runner>
```

Windows 解压后运行 `InternetArchiveUploader\InternetArchiveUploader.exe`，无需安装 Python。

Flatpak 从 `Build Flatpak` workflow 的 Artifact 获取（`v*` 标签或手动触发时可发布到 Release）：

```bash
flatpak install --user --bundle io.github.jcleng.InternetArchiveUploader.flatpak
flatpak run io.github.jcleng.InternetArchiveUploader
```

沙箱内的数据目录在 `~/.var/app/io.github.jcleng.InternetArchiveUploader/`；
`ia.ini`、`settings.json`（记住的代理）都落在那里。

```bash
sha256sum -c SHA256SUMS
tar -xzf InternetArchiveUploader-*.tar.gz
./InternetArchiveUploader/InternetArchiveUploader
```

系统需要 Qt 运行库（CI 安装的同一组）：

```bash
sudo apt-get install -y libegl1 libgl1 libglvnd0 libxkbcommon-x11-0 \
  libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 \
  libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 \
  libdbus-1-3 libfontconfig1 libfreetype6
```

### 从源码运行

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## 配置与认证

配置文件优先级：

1. 命令行 `--config /path/to/ia.ini`
2. 图形设置中上次选择的路径
3. 默认 `${XDG_CONFIG_HOME:-~/.config}/internetarchive-uploader/ia.ini`

```bash
./InternetArchiveUploader/InternetArchiveUploader --config "/home/me/我的 配置/ia.ini"
```

- 文件不存在时，首次登录会自动创建（权限 0600）。
- 配置文件不存在、损坏或无读取权限时明确报错，不会悄悄切换到其他账号。
- 有上传任务进行中时不能切换配置或退出登录。
- 凭据文件不会被日志、README、CI 或产物包含。

## 代理设置

图形：**登录窗口底部的 `proxy` 输入框**（未登录时即可填写，否则需要代理才能连通的网络将无法完成登录）；
登录后也可在 Settings → HTTP proxy 修改。
命令行：

```bash
./InternetArchiveUploader/InternetArchiveUploader --proxy http://192.168.195.18:20171
```

- 留空表示直连；空白字符会被忽略。
- 登录窗口填写后，同一代理会带到主窗口，用于登录、条目查询和文件上传（含 S3 端点）。
- 登录框与 Settings 共用同一份代理状态，不会出现"登录走了代理、上传没走"的情况。
- 必须包含协议和端口：`http://host:port` 或 `https://host:port`。
- 支持 `http`、`https`、`socks5`、`socks5h`；SOCKS 需额外安装 `PySocks`。
- 用户名密码可以写在 URL 中（`http://user:pass@host:port`），界面和日志只显示 `***:***`。
- 有上传任务进行中时不能更换代理。
- 代理不可用不代表 archive.org 不可用；请先用 `curl -x <proxy> https://archive.org` 自查。
- **代理会被记住**：登录成功或保存设置后写入用户配置目录的 `settings.json`
  （Linux `${XDG_CONFIG_HOME:-~/.config}/internetarchive-uploader/`，Windows `%APPDATA%\internetarchive-uploader\`），
  下次启动自动带出；清空输入框即清除记忆。优先级：`--proxy` > 记住的值 > 直连。
- `settings.json` 与 `ia.ini` 分开存放：前者只有非敏感偏好，后者才含凭据。

## 使用流程

1. 登录 Internet Archive 账号（凭据只用于换取 API key）。
2. 填写 **Identifier**（条目 ID，例如 `NintendoSwitchGame_TotK`）、标题、描述等 metadata。
3. 拖入一个或多个文件，或在“Select file”中多选。
4. 检查表格中的远程文件名、识别类型与冲突提示。
5. 需要时修改并发数（Settings）。
6. 点击 Upload，队列按并发上限派发。
7. “Stop dispatching”只停止派发新文件，正在传输的文件会继续。
8. 失败的条目可在修正后使用“Retry failed”。

### 重要区分

- **Identifier** 决定文件进入哪个条目，**Title** 只是展示标题。
- **`mediatype` 是条目级属性**：多个文件共用一个 item 时只有一份 metadata。
- **同名远程文件不会被覆盖**：会被标记为冲突，需要手动改名或移除。
- **成功提示表示上传请求完成**，不代表 archive.org 后台派生任务已结束。
- 新条目由“第一个文件 + 统一 metadata”创建，其余文件随后并发追加。

## 已知限制

- 不支持目录递归拖拽（只能拖文件）。
- 不持久化队列，退出应用后不续传。
- 不做单文件分片并行或跨进程断点续传。
- 不提供已有条目的完整 metadata 批处理编辑器（请用官网 `Edit → change the information`）。
- 结果不明的上传不会被自动重传，需要你在 archive.org 上核实。
- 同一 item 内并发行为尚未用真实账号验证；如遇服务端限制，请把并发降到 1。

## 构建与测试

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
xvfb-run -a python scripts/smoke_gui.py
```

CI：`.github/workflows/build-linux.yml`（名称仍沿用，实际构建两个平台）：

| 平台 | 构建矩阵 | 产物 |
| --- | --- | --- |
| Linux | ubuntu-22.04 / 24.04 | `*.tar.gz` |
| Windows | windows-2022 / 2025 | `*.zip`（内含 `InternetArchiveUploader.exe`） |
| Flatpak | freedesktop-24.08 容器 | `*.flatpak` |

每个平台都执行：跑测试 → 源码冒烟 → PyInstaller 打包 → 产物内容校验 →
产物冒烟 → 压缩 + SHA256 → Artifact。另有 `verify-*` 任务在**没有 Python** 的
对应系统上下载产物、校验和、解压并启动。`v*` 标签时才发布 Release。

Flatpak 由独立的 `.github/workflows/build-flatpak.yml` 构建：下载最近一次成功的 Linux
产物 → 重打包为确定性 tar.gz（去属主、固定 mtime）→ 改写 manifest 的 URL/sha256 →
`flatpak-builder` 出包 → 安装并运行 `--smoke-test` → 生成 SHA256SUM。
手动触发时填写 `release_tag` 即可发布到 Release。

## 手工验收

图形交互验收由用户执行，清单见 [`docs/manual-linux-test.md`](docs/manual-linux-test.md)。
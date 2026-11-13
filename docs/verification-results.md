# Verification results

日期：2026-11-12
上游基线：`5aaea69`
分支：`master`（Fork: `jcleng/InternetArchiveUploader`）

## 已由自动化验证

| 项目 | 命令 | 结果 |
| --- | --- | --- |
| 全量测试 | `QT_QPA_PLATFORM=offscreen python -m pytest -q` | 125 passed |
| 源码冒烟 | `xvfb-run -a python scripts/smoke_gui.py`（CI） | exit 0 |
| CI 构建 Linux+Windows | GitHub Actions run 43198270648 (@bbb9add) | success（4 个构建 + 4 个产物校验 job 全绿） |
| 产物内容检查 | `python -m uploader.packaging_contract dist/InternetArchiveUploader` | ok |
| 产物启动 | `xvfb-run -a python scripts/smoke_dist.py dist/InternetArchiveUploader` | exit 0 |
| 下载后校验 | `sha256sum -c SHA256SUMS` + 解压启动（CI package-smoke job） | success |
| 代理连通性（本地实测） | `session.get('https://archive.org/services/check_identifier.php')` | HTTP 200，session.proxies 同时含 http/https |
| 产物清单 | Actions Artifacts | Linux `-ubuntu-22.04`/`-ubuntu-24.04`（各 76 MB）、Windows `-windows-2022`/`-windows-2025`（各 50 MB） |
| Flatpak runtime 升级 | run 43220573031 (25.08) / run 43221956869 (26.08 @644fea9) | success；`org.freedesktop.Platform/x86_64/26.08` 实际安装，无 EOL 警告，`smoke-test: ok` |
| Flatpak 产物 | `Build Flatpak` run 43198270648 → 改后 run @abf8f04 | success；安装 + `smoke-test: ok`，47 MB |
| Windows 产物 | zip 内 `InternetArchiveUploader.exe`，无 Python 环境启动 | success（verify-windows job） |

说明：

- 本地容器缺少 `libEGL`、无 sudo；Qt 运行库临时解包到 `/tmp/qtlibs` 并通过
  `LD_LIBRARY_PATH` 注入，仅用于本地测试，未写入仓库或 CI。
- 按用户要求，**未在本地执行 PyInstaller 打包**，打包与产物验证全部在 CI 完成。

## 尚未验证（需用户执行）

- 代理在真实上传（含 IAS3 大文件）路径上的表现：本地只验证了普通 GET。
- Windows 真实桌面交互与真实上传（CI 只验证了启动冒烟）。
- 真实桌面交互：拖拽、编辑、并发调节、关闭流程（见 `docs/manual-linux-test.md`）。
- 真实账号上传，包括新建条目、追加文件、同名冲突、权限失败。
- 同一 item 内并发上传在 archive.org 侧的实际行为。
- 真实网络条件与长期运行稳定性。

以上项目在完成前不得标记为通过。

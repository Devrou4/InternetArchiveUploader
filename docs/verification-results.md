# Verification results

日期：2026-11-12
上游基线：`5aaea69`
分支：`master`（Fork: `jcleng/InternetArchiveUploader`）

## 已由自动化验证

| 项目 | 命令 | 结果 |
| --- | --- | --- |
| 全量测试 | `QT_QPA_PLATFORM=offscreen python -m pytest -q` | 125 passed |
| 源码冒烟 | `xvfb-run -a python scripts/smoke_gui.py`（CI） | exit 0 |
| CI 构建 22.04/24.04 | GitHub Actions run 43193710126 (@2d79e97) | success |
| 产物内容检查 | `python -m uploader.packaging_contract dist/InternetArchiveUploader` | ok |
| 产物启动 | `xvfb-run -a python scripts/smoke_dist.py dist/InternetArchiveUploader` | exit 0 |
| 下载后校验 | `sha256sum -c SHA256SUMS` + 解压启动（CI package-smoke job） | success |
| 产物清单 | Actions Artifacts | `InternetArchiveUploader-master-linux-x86_64-ubuntu-22.04`、`-ubuntu-24.04` |

说明：

- 本地容器缺少 `libEGL`、无 sudo；Qt 运行库临时解包到 `/tmp/qtlibs` 并通过
  `LD_LIBRARY_PATH` 注入，仅用于本地测试，未写入仓库或 CI。
- 按用户要求，**未在本地执行 PyInstaller 打包**，打包与产物验证全部在 CI 完成。

## 尚未验证（需用户执行）

- 真实桌面交互：拖拽、编辑、并发调节、关闭流程（见 `docs/manual-linux-test.md`）。
- 真实账号上传，包括新建条目、追加文件、同名冲突、权限失败。
- 同一 item 内并发上传在 archive.org 侧的实际行为。
- 真实网络条件与长期运行稳定性。

以上项目在完成前不得标记为通过。

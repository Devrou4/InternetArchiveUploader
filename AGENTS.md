# AGENTS.md

Guidance for agents and contributors working in this repository.

This is a **fork** of [Devrou4/InternetArchiveUploader](https://github.com/Devrou4/InternetArchiveUploader)
(`upstream` remote). The fork adds a Linux/Windows desktop build, a drag-and-drop
upload queue, proxy support and Flatpak packaging. Upstream code and the MIT
license are preserved.

## Quick reference

```bash
# Setup
python3 -m venv .venv && . .venv/bin/activate      # or: uv venv
pip install -r requirements.txt -r requirements-dev.txt

# Test (headless; no display needed)
QT_QPA_PLATFORM=offscreen python -m pytest -q

# Single test
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_queue.py -q

# Run the app / headless smoke (use the venv interpreter, not system python3)
python main.py
python main.py --smoke-test          # resource check only, exits 0, no network
python scripts/smoke_gui.py          # same, via subprocess

# Packaging (CI does this; see "Do not build locally")
python -m PyInstaller packaging/linux.spec --noconfirm
python -m uploader.packaging_contract dist/InternetArchiveUploader
python scripts/smoke_dist.py dist/InternetArchiveUploader
```

Run everything from an activated virtualenv. The system `python3` usually
lacks `requests`/`PySide6`, and mixing the two produces confusing import and
Qt crashes that look like test failures.

On a minimal container Qt may need system libs (`libEGL.so.1`, `libxkbcommon`,
`libdbus-1.so.3`). CI installs them via apt; there is no apt/sudo in some
sandboxes, so do not "fix" a missing library by vendoring it into the repo.

## Constraints that matter

- **The user tests all GUI interactions.** Do not claim a drag/drop, dialog or
  desktop behaviour is verified because a unit test passed. Automated tests use
  `QT_QPA_PLATFORM=offscreen`; anything needing a real display/file chooser goes
  to `docs/manual-linux-test.md` for the user.
- **Never build release artifacts locally.** PyInstaller and Flatpak builds run
  on GitHub Actions only. Local work is: tests, `--smoke-test`, contract checks.
- **Never put credentials in the repo or logs.** `ia.ini` holds secrets and is
  git-ignored; `settings.json` holds only non-sensitive preferences. Proxy
  credentials must be printed through `redact_proxy()`.
- **Only `--proxy`, the remembered proxy, and XDG paths may be resolved
  implicitly.** No hardcoded proxy addresses, no hardcoded home paths, no silent
  fallback to a different account when a config fails to load.
- **Identifier case is preserved.** Do not lowercase user input; any server-side
  restriction surfaces as an error.
- **`mediatype` is item-level, not per-file.** Multiple files sharing one
  identifier share one metadata payload.
- **Never overwrite a remote file silently.** Same-name uploads are conflicts
  that the user must resolve by renaming (edit the Remote name cell).
- **Retry is per file.** `UploadController.retry(task_id)` requeues exactly one
  task and resets its attempt count and progress; double-clicking a failed row
  is the UI shortcut.

## Architecture

```
main.py                     MainWindow: wiring, layout, CLI (--config, --proxy, --smoke-test)
LoginDialog/login_dialog.py Credentials + proxy entry; authenticates on a QThread
UI/, AdditionalMetadataDialog/, assets_rc.py, assets/
                            Upstream Qt Designer files — generated, do not hand-edit;
                            keep custom widgets in uploader/widgets/ instead

uploader/
  models.py         ItemConfig, UploadTask, TaskState
  config_paths.py   resolve_config_path(), resolve_proxy() (CLI > saved > platform default)
  config.py         ConfigManager: ia.ini validation, session creation, auth with 0600 write
  proxy.py          normalize_proxy(), redact_proxy()
  settings.py       AppSettings: remembered proxy in settings.json
  detection.py      detect_file() -> Detection(mediatype|None, needs_confirmation)
  archive_client.py ArchiveClient + typed failures (Retryable/Auth/Permission/Conflict/Unknown)
  item_service.py   ItemService.prepare(): who initialises the item, which names collide
  progress.py       CountingFile: reports (bytes_read, total) while the library reads
  queue.py          TaskQueue: dispatch limit, retry backoff, initializer gating (pure, no Qt)
  workers.py        UploadWorker: emits results only, never mutates shared state
  controller.py     UploadController: glue; owns queue, threads and the pump timer
  resources.py      resource_path(), user_config_dir(), user_state_dir(), optional_keep_awake()
  packaging_contract.py  check_dist(): bundle content/credential checks
  widgets/task_table.py   Drop target + task grid (editable Remote name / Item columns)
  widgets/settings_dialog.py  Config path, proxy, concurrency
```

### Data flow

1. Files dropped → `TaskTable.add_paths()` creates one `UploadTask` per file,
   attaches `detect_file()` advice, renders rows. **No upload starts here.**
2. User reviews identifier/metadata → `MainWindow.start_upload()` builds `ItemConfig`.
3. `UploadController.register_tasks()` inspects the item, enqueues tasks,
   computes conflicts and marks the initializer file.
4. `_pump()` dispatches up to `limit` files; the initializer carries the
   metadata, later files append. Workers run on their own `QThread` with their
   own session.
5. Results arrive as signals; **only the controller mutates queue state**.

### Threading rules

- Queue state lives on the main thread. Workers emit signals; they never touch
  `UploadTask` fields.
- `UploadController.shutdown()` stops dispatching and joins threads. Paths that
  destroy a controller (window close, tests) must call it — leaving a live
  `QThread` behind crashes Qt with no Python traceback.
- Each worker gets an isolated session; do not share one `ArchiveSession`
  across threads without evidence it is safe.

### Progress reporting

`upload_file` has no progress callback, so `ArchiveClient` hands it a
`CountingFile` instead of a path; every read is counted. Consequences:

- Progress is the offset of the current read window, not cumulative — the
  library rewinds the body before sending, so a cumulative counter would
  exceed the file size.
- A failing UI callback must never break the transfer (`CountingFile` swallows
  it); the same applies to the Qt signal.
- `UploadController` throttles redraws (200 ms) but **flushes on completion**;
  a throttled final update would leave the row stuck at 99%.
- A row at 100% is not success. `failed at N%` is deliberate: the bytes may
  have left the machine without the server accepting the file.
- Redraws go through `TaskTable.update_row()`, not a full `refresh()`, so the
  selection survives.

### Retry policy

Retryable failures (429/502/503/504, network) retry up to 4 total attempts with
exponential backoff (2s base, 60s cap), honouring a larger `Retry-After`.
Authentication, permission, conflict and local-file-changed failures are
terminal. A result of unknown remote state is **not** retried: the user must
verify on archive.org.

## Testing conventions

- `pytest` + `pytest-qt`; tests live in `tests/`, one file per module.
- **Write the failing test first.** Every fix in this repo's history that
  skipped that step turned out to hide a second bug.
- Never construct `QDropEvent` by hand — it segfaults under offscreen. Call
  `drop_paths()` / `note_skipped_urls()`, which `dropEvent()` delegates to.
- Tests must be platform-neutral: no `/tmp` assumptions, no POSIX-only
  permission checks without `skipif`, no `bash` assumptions on Windows.
- `TestMainWindow`'s `window` fixture stubs `show()`; use `visible_window` when
  the test depends on real geometry or visibility.
- Contract tests (`test_*_contract.py`) pin facts that CI would otherwise
  discover first: dependency signatures, bundle layout, workflow YAML, Flatpak
  manifest invariants. A stray quote in a `run:` block is caught by
  `test_workflow_run_blocks_have_balanced_quotes`.
- `requirements-dev.txt` pins `PyYAML`; without it the contract tests **skip**
  instead of checking.

## Packaging

| Target | Spec / manifest | Workflow | Output |
| --- | --- | --- | --- |
| Linux | `packaging/linux.spec` | `.github/workflows/build-linux.yml` (`build-linux`) | `*.tar.gz` |
| Windows | `packaging/windows.spec` | same file (`build-windows`) | `*.zip` with `.exe` |
| Flatpak | `packaging/flatpak/*.yaml` | `.github/workflows/build-flatpak.yml` | `*.flatpak` |

`build-linux.yml` keeps its historical name but builds both desktop platforms.
Each platform has a `verify-*` job that downloads the artifact on a **Python-free**
runner, checks the checksum, extracts and launches with `--smoke-test`.

### Flatpak invariants (learned the hard way)

- The bundle source is `type: file`, not `archive` — flatpak-builder
  auto-extracts archives, which breaks the explicit `tar` step.
- Extract into `${FLATPAK_DEST}`, not `${FLATPAK_DEST}/InternetArchiveUploader`;
  the archive already has that top-level directory.
- Repack the bundle owner-agnostically (`--owner=0 --group=0 --numeric-owner`,
  fixed `--mtime`) and extract with `--no-same-owner`; CI files are uid 1001.
- The metainfo needs **both** `project_license` and `metadata_license`, plus a
  file under `share/licenses/<id>/`, or `appstreamcli compose` fails.
- The workflow patches the manifest's placeholder URL + 64-zero sha256 in place;
  appending a second `sha256:` key is invalid YAML.

## Commit and review expectations

- Conventional prefixes: `feat:`, `fix:`, `test:`, `docs:`, `ci:`, `build:`.
- Keep commits scoped; do not mix a refactor with a behaviour change.
- Do not commit `.venv/`, `dist/`, `ia.ini`, `settings.json`, or artifacts.
- Pushing to `master` on the fork triggers the full CI matrix; confirm tests are
  green locally first. Never tag or publish a Release without explicit approval.

## Known gaps (do not assume they are done)

- Real GUI interaction, real uploads and the Flatpak sandbox on a desktop are
  verified by the user only — see `docs/manual-linux-test.md`.
- Concurrent uploads **within one item** are enabled but unverified against the
  live service; if the server throttles, drop concurrency or serialize per item.
- No queue persistence, no resumable transfers, no directory-recursive drops,
  no full existing-item metadata editor.
- The Flatpak runtime is pinned to `24.08`, which upstream marks end-of-life.
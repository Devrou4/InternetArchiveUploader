# Internet Archive Uploader

A graphical tool for uploading media to the [Internet Archive](https://archive.org/) using the
Internet Archive Python library, built with PySide6. Pick files or folders, fill in the metadata,
and let the upload queue handle the rest.

This is a fork of [Devrou4/InternetArchiveUploader](https://github.com/Devrou4/InternetArchiveUploader)
that keeps the original workflow and adds Linux support, a real upload queue, HTTP proxy support
and packaged builds for Linux, Windows and Flatpak.

## Features

Everything the upstream project does, plus:

- **Upload files or folders.** Dropping a folder expands it recursively; files from subfolders keep
  their relative path (for example `cd1/track.mp3`) so duplicate filenames cannot collide.
- **A real queue instead of one batch.** Every file is its own task with its own row in the table.
- **Per-file progress.** Each row shows its own byte-level percentage while it uploads.
- **Per-file retry.** A failed row shows `failed at N%` plus the reason; double-click it (or use the
  context menu) to retry just that file.
- **Per-file cancel.** Select a running row and press *Cancel selected*, or right-click →
  *Cancel this upload*. The transfer stops at the next chunk boundary.
- **Per-row remove.** Each row has its own *Remove* button; running rows cannot be removed.
- **Configurable concurrency.** 1–8 files at a time (default 2).
- **Automatic media-type detection.** File extension plus magic bytes suggest `mediatype`; archives
  and unknown formats are flagged for manual confirmation. Your manual choice always wins.
- **Choose your credentials file.** `--config`, or the Settings dialog; supports non-ASCII paths.
- **HTTP proxy support.** Set it on the login screen (so it is usable before you can reach
  archive.org), in Settings, or with `--proxy`. It is remembered between launches.
- Built with Python, the Internet Archive Python library, and PySide6.
- Monitors upload activity through a log pane.

## Requirements

Prebuilt bundles need no Python installation:

- **Windows** — extract the `.zip` and run `InternetArchiveUploader\InternetArchiveUploader.exe`.
- **Linux** — extract the `.tar.gz` and run `InternetArchiveUploader/InternetArchiveUploader`.
  The Qt runtime libraries listed under [Installation](#installation) must be present.
- **Flatpak** — install the `.flatpak` bundle on any distribution with Flatpak.

Running from source requires Python 3.11 and the packages in `requirements.txt`.

## Installation

### Prebuilt downloads

Grab the asset for your platform from the
[releases page](https://github.com/jcleng/InternetArchiveUploader/releases).
Each release publishes a Linux archive, a Windows archive and a Flatpak bundle, with
`SHA256SUMS-*` files for verification:

```bash
sha256sum -c SHA256SUMS-linux-ubuntu-24.04
```

**Windows**

1. Download `InternetArchiveUploader-<version>-windows-x86_64.zip`.
2. Extract it.
3. Double-click `InternetArchiveUploader\InternetArchiveUploader.exe`.

**Linux**

1. Download `InternetArchiveUploader-<version>-linux-x86_64.tar.gz`.
2. Extract it.
3. Install the Qt runtime libraries if they are missing:

   ```bash
   sudo apt-get install -y libegl1 libgl1 libglvnd0 libxkbcommon-x11-0 \
     libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 \
     libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 \
     libdbus-1-3 libfontconfig1 libfreetype6
   ```

4. Run `./InternetArchiveUploader/InternetArchiveUploader`.

**Flatpak**

```bash
flatpak install --user --bundle io.github.jcleng.InternetArchiveUploader.flatpak
flatpak run io.github.jcleng.InternetArchiveUploader
```

Inside the sandbox, settings and credentials live in
`~/.var/app/io.github.jcleng.InternetArchiveUploader/`.

### From source

```bash
git clone https://github.com/jcleng/InternetArchiveUploader.git
cd InternetArchiveUploader
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Visible folders are exposed read-only to the Flatpak sandbox, so files can be picked from anywhere
under your home directory.

## Usage

1. **Authenticate first.**

   The application asks for your Internet Archive account on first launch. Make sure you have a
   registered account at [archive.org](https://archive.org/).

   **Important security note.** Your password is **not stored** by the application. It is used only
   to obtain the **access** and **private keys** required for uploads, through
   `internetarchive.configure`. The keys are written to `ia.ini` (mode `0600` on Linux); the password
   itself is never saved or logged.

   If you are behind a firewall, fill in the **proxy** field on this screen before logging in —
   without it the login request cannot reach archive.org.

2. **Choose where credentials live (optional).**

   `ia.ini` defaults to a per-user location:

   | Platform | Default path |
   | --- | --- |
   | Linux | `${XDG_CONFIG_HOME:-~/.config}/internetarchive-uploader/ia.ini` |
   | Windows | `%APPDATA%\internetarchive-uploader\ia.ini` |

   Override it with `--config /path/to/ia.ini` or via *Settings*. Resolution order is
   command line → last choice saved in Settings → platform default. A missing or corrupt file is
   reported as an error; the application never silently falls back to a different account.

3. **Fill in the item metadata.**

   `identifier` decides which item the files belong to; `title` is only the display title. Note that
   `mediatype` is a property of the *item*, not of each file — every file uploaded to the same
   identifier shares one metadata payload.

4. **Add files.**

   - *Select file* opens a multi-select dialog.
   - *Folder* adds every file inside a folder, recursively. Hidden files and OS junk such as
     `.DS_Store` are skipped.
   - Dragging files or folders onto the window works too.

   Adding files never starts an upload; review the table first.

5. **Review the queue.**

   Each row shows the remote name, target item, detected type, status, progress and any error.
   Two columns are editable:

   - *Remote name* — rename the file inside the item.
   - *Item* — send this particular row to a different identifier.

   Files whose remote name already exists in the item are flagged as conflicts and will not start;
   rename them instead of overwriting.

6. **Set concurrency (optional).**

   *Concurrent uploads* controls how many files transfer at the same time (1–8, default 2). This is
   the number of files in flight, not the number of chunks per file. Higher values can trigger
   server-side throttling; the uploader retries temporary failures a limited number of times with
   backoff.

7. **Upload.**

   *Upload* starts the queue. For a new item, the first file creates the item with the metadata you
   entered and the remaining files are appended. For an existing item, files are appended and its
   metadata is left untouched.

8. **Monitor, retry, cancel.**

   - Progress advances per row; the final value is never lost to redraw throttling.
   - *Cancel selected* stops the selected transfers; a cancelled row shows `cancelled at N%`.
   - *Stop dispatching* stops starting new files but lets running uploads finish.
   - *Retry failed* requeues every failed or cancelled row. To retry a single file, double-click it
     or use its context menu.

9. **Verify.**

   A successful upload means the request completed; archive.org still runs its derive step
   afterwards. Open the item page (the log pane links to it) to confirm the files and metadata.

### Folder uploads and remote names

Dropping `album/` containing `a.mp3`, `cd1/b.mp3` and `notes.txt` produces three rows with the
remote names `a.mp3`, `cd1/b.mp3` and `notes.txt`. Keeping the relative path means two files called
`track.mp3` in different subfolders stay distinct.

### Proxy

- Login screen, *Settings*, or `--proxy http://host:port`.
- Applies to authentication, item lookups and uploads alike.
- Must include a scheme and a port; `host:port` alone is rejected rather than silently ignored.
- Supports `http`, `https`, `socks5` and `socks5h` (SOCKS needs `PySocks`).
- Credentials in the URL are shown as `***:***` in the UI and logs.
- The last value is remembered in `settings.json` (a non-sensitive file, separate from `ia.ini`).
  Clear the field to forget it. Precedence: `--proxy` → remembered value → direct connection.
- To troubleshoot, compare with `curl -x <proxy> https://archive.org`.

## Metadata Explanation

When uploading files to the Internet Archive, you need to provide metadata. This helps describe and
categorize the content, making it more discoverable by others. The metadata fields include:

- **`identifier`**: A unique identifier for the item you are uploading. This will be used to track the item in the Internet Archive system. The identifier should be unique to avoid conflicts with other uploads (e.g., "future_of_sustainability_2025"). Length must be 5–80 characters and must not contain spaces.
- **`title`**: The title of the item. This is the name or label given to your uploaded media (e.g., "The Future of Sustainability").
- **`creator`**: The person or entity responsible for creating the content (e.g., "John Doe Productions").
- **`description`**: A brief summary or description of the content being uploaded. This helps users understand what the file is about (e.g., "An insightful documentary about sustainability practices in modern society").
- **`collection`**: The Internet Archive collection to upload your item to. This could be one of the predefined collections such as `"movies"`, `"audio"`, `"texts"`, or others.
- **`subject`**: Keywords or topics related to the content. These are separated by commas to describe the main themes or subjects of the media (e.g., "documentary, sustainability, environment").
- **`mediatype`**: The item-level media type (`audio`, `movies`, `image`, `texts`, `software`, …). Suggested automatically from the dropped files; a mixed selection is flagged and requires your choice.

Each field helps improve the organization and searchability of your content within the Internet Archive, allowing other users to find it more easily.

## Limitations

- The queue is not persisted; quitting the application does not resume unfinished work.
- Uploads are not resumable across restarts and files are not split into parallel chunks.
- Concurrent uploads **within one item** are enabled but not verified against the live service. If
  archive.org throttles, lower the concurrency.
- When an upload's outcome is unknown (for example a timeout after the last chunk), the file is
  **not** retried automatically. Check the item on archive.org first.
- This is not a metadata editor for existing items; use archive.org's *Edit → change the
  information* for that.
- The Linux build targets x86_64 and is tested on Ubuntu 22.04 and 24.04.

## Development

```bash
pip install -r requirements.txt -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen python -m pytest -q     # headless, no display needed
python main.py --smoke-test                        # resource check, exits 0, no network
```

Packaging is done in CI, never locally:

| Target | Spec / manifest | Workflow | Output |
| --- | --- | --- | --- |
| Linux | `packaging/linux.spec` | `.github/workflows/build-linux.yml` | `*.tar.gz` |
| Windows | `packaging/windows.spec` | `.github/workflows/build-linux.yml` | `*.zip` |
| Flatpak | `packaging/flatpak/*.yaml` | `.github/workflows/build-flatpak.yml` | `*.flatpak` |

Each platform has a verification job that downloads the artifact on a machine without Python,
checks the checksum, extracts it and launches it with `--smoke-test`. A `v*` tag publishes all three
to a GitHub release.

See [`AGENTS.md`](AGENTS.md) for the architecture, the threading rules and the packaging invariants.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. It is
a fork of [Devrou4/InternetArchiveUploader](https://github.com/Devrou4/InternetArchiveUploader) and
keeps the original copyright notice.
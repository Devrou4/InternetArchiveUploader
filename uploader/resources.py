import contextlib
import os
import sys
from pathlib import Path

ASSETS_DIR_NAME = "assets"
APP_DIR_NAME = "internetarchive-uploader"

try:
    from wakepy import keep as _wakepy_keep

    def _keep_running():
        return _wakepy_keep.running()
except Exception:  # pragma: no cover - depends on platform
    def _keep_running():
        raise RuntimeError("wakepy unavailable")


def application_root() -> Path:
    """Return the directory that holds bundled resources."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def resource_path(relative: str) -> Path:
    """Resolve a bundled resource regardless of the current working directory."""
    return application_root() / ASSETS_DIR_NAME / relative


def user_config_dir() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    directory = base / APP_DIR_NAME
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def user_state_dir() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    directory = base / APP_DIR_NAME
    directory.mkdir(parents=True, exist_ok=True)
    return directory


@contextlib.contextmanager
def optional_keep_awake():
    """Best-effort sleep inhibition; a desktop without a portal must not block uploads."""
    try:
        manager = _keep_running()
    except Exception:
        yield
        return

    try:
        manager.__enter__()
    except Exception:
        yield
        return

    try:
        yield
    finally:
        try:
            manager.__exit__(None, None, None)
        except Exception:
            pass
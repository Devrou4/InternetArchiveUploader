import os
from pathlib import Path
from typing import Mapping

APP_DIR_NAME = "internetarchive-uploader"
CONFIG_FILE_NAME = "ia.ini"


def default_config_path(env: Mapping[str, str]) -> Path:
    """Return the per-user default config path, honouring XDG_CONFIG_HOME."""
    xdg = env.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(xdg) / APP_DIR_NAME / CONFIG_FILE_NAME


def resolve_config_path(
    cli: str | None,
    saved: str | None,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Resolve config priority: CLI > saved GUI choice > XDG default."""
    env = os.environ if env is None else env
    if cli:
        return Path(cli).expanduser()
    if saved:
        return Path(saved).expanduser()
    return default_config_path(env)
import os
from pathlib import Path
from typing import Mapping

APP_DIR_NAME = "internetarchive-uploader"
CONFIG_FILE_NAME = "ia.ini"


def default_config_path(env: Mapping[str, str], platform: str | None = None) -> Path:
    """Return the per-user default config path.

    Windows uses %APPDATA%; Linux/BSD use XDG_CONFIG_HOME with a ~/.config
    fallback. Nothing is hardcoded to one platform's layout.
    """
    platform = os.name if platform is None else platform
    if platform.startswith("win"):
        base = env.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    else:
        base = env.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / APP_DIR_NAME / CONFIG_FILE_NAME


def resolve_config_path(
    cli: str | None,
    saved: str | None,
    env: Mapping[str, str] | None = None,
    platform: str | None = None,
) -> Path:
    """Resolve config priority: CLI > saved GUI choice > platform default."""
    env = os.environ if env is None else env
    if cli:
        return Path(cli).expanduser()
    if saved:
        return Path(saved).expanduser()
    return default_config_path(env, platform)

def resolve_proxy(cli: str | None, saved: str | None) -> str | None:
    """Proxy priority: command line > remembered setting > direct connection.

    Kept separate from the config path so a stale remembered proxy can never
    silently replace an explicit --proxy.
    """
    return (cli or "").strip() or (saved or "").strip() or None

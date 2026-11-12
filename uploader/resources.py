import sys
from pathlib import Path

ASSETS_DIR_NAME = "assets"


def application_root() -> Path:
    """Return the directory that holds bundled resources."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def resource_path(relative: str) -> Path:
    """Resolve a bundled resource regardless of the current working directory."""
    return application_root() / ASSETS_DIR_NAME / relative
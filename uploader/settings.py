"""Non-sensitive user preferences.

Deliberately separate from `ia.ini`: that file holds credentials, while this
one only remembers convenience values such as the last proxy address. Keeping
them apart means the settings file can never be mistaken for a secret, and a
lost settings file never breaks authentication.
"""

import json
import os
from pathlib import Path

from uploader.proxy import ProxyError, normalize_proxy
from uploader.resources import user_config_dir

SETTINGS_FILE_NAME = "settings.json"
PROXY_KEY = "proxy"


def default_settings_path() -> Path:
    return user_config_dir() / SETTINGS_FILE_NAME


class AppSettings:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else default_settings_path()

    def _read(self) -> dict:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError:
            return {}
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, sort_keys=True)
        except Exception:
            try:
                os.unlink(temp)
            except OSError:
                pass
            raise
        os.replace(temp, self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def load_proxy(self) -> str | None:
        value = self._read().get(PROXY_KEY)
        if not value:
            return None
        try:
            return normalize_proxy(value)
        except ProxyError:
            return None

    def save_proxy(self, proxy: str | None) -> None:
        data = self._read()
        if proxy:
            data[PROXY_KEY] = proxy
        else:
            data.pop(PROXY_KEY, None)
        self._write(data)
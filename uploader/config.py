import os
import tempfile
from pathlib import Path

import internetarchive as ia

from uploader.proxy import ProxyError, normalize_proxy


class ConfigError(Exception):
    """Raised when the IA configuration cannot be used."""


class ConfigManager:
    """Owns one explicit IA config file for the whole application session."""

    def __init__(self, path: Path, proxy: str | None = None):
        self.path = Path(path)
        try:
            self.proxy = normalize_proxy(proxy)
        except ProxyError as exc:
            raise ConfigError(str(exc)) from None

    def with_proxy(self, proxy: str | None) -> "ConfigManager":
        return ConfigManager(self.path, proxy)

    def proxy_mapping(self) -> dict[str, str]:
        if not self.proxy:
            return {}
        return {"http": self.proxy, "https": self.proxy}

    def validate(self) -> None:
        if not self.path.is_file():
            raise ConfigError(f"Configuration file not found: {self.path}")
        if not os.access(self.path, os.R_OK):
            raise ConfigError(f"Configuration file is not readable: {self.path}")

    def new_session(self) -> ia.ArchiveSession:
        self.validate()
        try:
            session = ia.get_session(config_file=str(self.path))
        except Exception as exc:  # library raises broad types on bad config
            raise ConfigError(f"Cannot load configuration {self.path}: {type(exc).__name__}") from None
        proxies = self.proxy_mapping()
        if proxies:
            session.proxies.update(proxies)
        return session

    def configure(self, username: str, password: str) -> None:
        """Authenticate and write credentials to the managed path with 0600."""
        if not username or not password:
            raise ConfigError("Username and password are required")
        parent = self.path.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ConfigError(f"Cannot create directory {parent}: {exc.strerror}") from None
        if not os.access(parent, os.W_OK):
            raise ConfigError(f"Directory is not writable: {parent}")

        handle, temp_name = tempfile.mkstemp(prefix=".ia-", suffix=".ini", dir=parent)
        os.close(handle)
        os.chmod(temp_name, 0o600)
        saved_env = _push_proxy_env(self.proxy)
        try:
            ia.configure(
                username=username,
                password=password,
                config_file=temp_name,
            )
            if not os.path.isfile(temp_name):
                raise ConfigError("Authentication failed: no configuration was written")
            os.replace(temp_name, self.path)
            os.chmod(self.path, 0o600)
        except ConfigError:
            _unlink(temp_name)
            raise
        except Exception as exc:
            _unlink(temp_name)
            raise ConfigError(
                f"Authentication failed ({type(exc).__name__}); configuration unchanged"
            ) from None
        finally:
            _restore_proxy_env(saved_env)


def _unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def _push_proxy_env(proxy: str | None) -> dict[str, str | None]:
    """ia.configure() builds its own session, which reads proxies from the environment."""
    saved = {name: os.environ.get(name) for name in ("HTTP_PROXY", "HTTPS_PROXY")}
    if proxy:
        os.environ["HTTP_PROXY"] = proxy
        os.environ["HTTPS_PROXY"] = proxy
    return saved


def _restore_proxy_env(saved: dict[str, str | None]) -> None:
    for name, value in saved.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
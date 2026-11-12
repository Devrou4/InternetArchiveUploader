import os
import tempfile
from pathlib import Path

import internetarchive as ia


class ConfigError(Exception):
    """Raised when the IA configuration cannot be used."""


class ConfigManager:
    """Owns one explicit IA config file for the whole application session."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def validate(self) -> None:
        if not self.path.is_file():
            raise ConfigError(f"Configuration file not found: {self.path}")
        if not os.access(self.path, os.R_OK):
            raise ConfigError(f"Configuration file is not readable: {self.path}")

    def new_session(self) -> ia.ArchiveSession:
        self.validate()
        try:
            return ia.get_session(config_file=str(self.path))
        except Exception as exc:  # library raises broad types on bad config
            raise ConfigError(f"Cannot load configuration {self.path}: {type(exc).__name__}") from None

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


def _unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass
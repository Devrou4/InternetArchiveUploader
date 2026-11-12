import os
import stat
from pathlib import Path

import pytest

from uploader import config


def _fake_configure_factory(monkeypatch):
    calls = []

    def fake_configure(username, password, config_file, host="archive.org"):
        calls.append({"username": username, "password": password, "config_file": config_file})
        Path(config_file).write_text("[s3]\naccess = a\n", encoding="utf-8")
        return str(config_file)

    monkeypatch.setattr(config.ia, "configure", fake_configure)
    return calls


def test_invalid_config_never_falls_back(tmp_path: Path, monkeypatch):
    missing = tmp_path / "missing" / "ia.ini"
    get_session_calls = []
    monkeypatch.setattr(
        config.ia,
        "get_session",
        lambda *a, **kw: get_session_calls.append((a, kw)),
    )
    manager = config.ConfigManager(missing)

    with pytest.raises(config.ConfigError):
        manager.validate()
    with pytest.raises(config.ConfigError):
        manager.new_session()

    assert get_session_calls == []


def test_new_session_uses_explicit_path(tmp_path: Path, monkeypatch):
    target = tmp_path / "custom.ini"
    target.write_text("[s3]\naccess = a\n", encoding="utf-8")
    seen = []
    monkeypatch.setattr(
        config.ia,
        "get_session",
        lambda *a, **kw: seen.append(kw.get("config_file")),
    )
    manager = config.ConfigManager(target)

    manager.validate()
    manager.new_session()

    assert seen == [str(target)]


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")
def test_created_file_mode_0600(tmp_path: Path, monkeypatch):
    _fake_configure_factory(monkeypatch)
    target = tmp_path / "sub" / "ia.ini"
    manager = config.ConfigManager(target)

    manager.configure("user@example.com", "  secret with spaces  ")

    mode = stat.S_IMODE(target.stat().st_mode)
    assert mode == 0o600


def test_password_is_not_stripped(tmp_path: Path, monkeypatch):
    calls = _fake_configure_factory(monkeypatch)
    manager = config.ConfigManager(tmp_path / "ia.ini")

    manager.configure("user@example.com", "  pad  ")

    assert calls[0]["password"] == "  pad  "
    assert (tmp_path / "ia.ini").is_file()


def test_unwritable_destination(tmp_path: Path, monkeypatch):
    _fake_configure_factory(monkeypatch)
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("file", encoding="utf-8")
    manager = config.ConfigManager(blocker / "ia.ini")

    with pytest.raises(config.ConfigError):
        manager.configure("user@example.com", "pw")


def test_error_messages_do_not_leak_credentials(tmp_path: Path, monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("payload with secret-token-123")

    monkeypatch.setattr(config.ia, "configure", boom)
    manager = config.ConfigManager(tmp_path / "ia.ini")

    with pytest.raises(config.ConfigError) as excinfo:
        manager.configure("user@example.com", "secret-token-123")

    assert "secret-token-123" not in str(excinfo.value)

PROXY = "http://192.168.195.18:20171"


def test_session_applies_proxy_to_both_schemes(tmp_path: Path, monkeypatch):
    target = tmp_path / "ia.ini"
    target.write_text("[s3]\naccess = a\n", encoding="utf-8")
    sessions = []

    class FakeSession(dict):
        pass

    def fake_get_session(config_file=None, **kw):
        session = FakeSession()
        session.proxies = {}
        sessions.append(session)
        return session

    monkeypatch.setattr(config.ia, "get_session", fake_get_session)
    manager = config.ConfigManager(target, proxy=PROXY)

    session = manager.new_session()

    assert session.proxies["http"] == PROXY
    assert session.proxies["https"] == PROXY


def test_configure_authenticates_through_proxy(tmp_path: Path, monkeypatch):
    seen = {}

    def fake_configure(username, password, config_file, host="archive.org"):
        seen["proxies"] = os.environ.get("HTTP_PROXY"), os.environ.get("HTTPS_PROXY")
        Path(config_file).write_text("[s3]\naccess = a\n", encoding="utf-8")
        return str(config_file)

    monkeypatch.setattr(config.ia, "configure", fake_configure)
    manager = config.ConfigManager(tmp_path / "ia.ini", proxy=PROXY)

    manager.configure("user@example.com", "pw")

    assert seen["proxies"] == (PROXY, PROXY)


def test_configure_restores_environment(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.setattr(
        config.ia,
        "configure",
        lambda **kw: Path(kw["config_file"]).write_text("[s3]\n", encoding="utf-8") or kw["config_file"],
    )
    manager = config.ConfigManager(tmp_path / "ia.ini", proxy=PROXY)

    manager.configure("u@e.com", "pw")

    assert "HTTP_PROXY" not in os.environ
    assert "HTTPS_PROXY" not in os.environ

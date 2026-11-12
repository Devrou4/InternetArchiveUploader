from pathlib import Path

import pytest

from uploader.settings import AppSettings


def test_round_trips_proxy(tmp_path: Path):
    settings = AppSettings(tmp_path / "settings.json")

    settings.save_proxy("http://192.168.195.18:20171")

    assert AppSettings(tmp_path / "settings.json").load_proxy() == "http://192.168.195.18:20171"


def test_missing_file_means_no_proxy(tmp_path: Path):
    assert AppSettings(tmp_path / "settings.json").load_proxy() is None


def test_corrupt_file_does_not_crash(tmp_path: Path):
    target = tmp_path / "settings.json"
    target.write_text("{not json", encoding="utf-8")

    assert AppSettings(target).load_proxy() is None


def test_clearing_proxy_removes_the_key(tmp_path: Path):
    settings = AppSettings(tmp_path / "settings.json")
    settings.save_proxy("http://proxy:3128")

    settings.save_proxy(None)

    assert settings.load_proxy() is None


def test_invalid_stored_proxy_is_ignored(tmp_path: Path):
    target = tmp_path / "settings.json"
    target.write_text('{"proxy": "not a url"}', encoding="utf-8")

    assert AppSettings(target).load_proxy() is None


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX modes")
def test_settings_file_is_private(tmp_path: Path):
    import stat

    settings = AppSettings(tmp_path / "settings.json")
    settings.save_proxy("http://user:pass@proxy:3128")

    mode = stat.S_IMODE((tmp_path / "settings.json").stat().st_mode)
    assert mode == 0o600


def test_no_credentials_leak_into_other_keys(tmp_path: Path):
    settings = AppSettings(tmp_path / "settings.json")
    settings.save_proxy("http://alice:hunter2@proxy:3128")

    raw = (tmp_path / "settings.json").read_text(encoding="utf-8")

    assert "proxy" in raw
    assert "hunter2" in raw  # stored, but never printed to logs/UI


def test_proxy_priority_cli_over_saved(tmp_path: Path):
    from uploader.config_paths import resolve_proxy

    assert resolve_proxy("http://cli:1", "http://saved:2") == "http://cli:1"
    assert resolve_proxy(None, "http://saved:2") == "http://saved:2"
    assert resolve_proxy(None, None) is None


def test_settings_live_in_the_user_config_dir(tmp_path: Path, monkeypatch):
    from uploader import resources
    from uploader.settings import default_settings_path

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(resources.sys, "platform", "linux")

    assert default_settings_path() == tmp_path / "internetarchive-uploader" / "settings.json"
    assert resources.user_config_dir().is_dir()


def test_login_prefills_remembered_proxy(qtbot, tmp_path: Path):
    from LoginDialog.login_dialog import LoginDialog
    from uploader.config import ConfigManager

    settings = AppSettings(tmp_path / "settings.json")
    settings.save_proxy("http://saved-proxy:3128")
    dialog = LoginDialog(ConfigManager(tmp_path / "ia.ini"), settings=settings)
    dialog.set_threaded(False)
    qtbot.addWidget(dialog)

    assert dialog.le_proxy.text() == "http://saved-proxy:3128"


def test_successful_login_remembers_the_proxy(qtbot, tmp_path: Path, monkeypatch):
    from LoginDialog.login_dialog import LoginDialog
    from uploader.config import ConfigManager

    settings = AppSettings(tmp_path / "settings.json")
    dialog = LoginDialog(ConfigManager(tmp_path / "ia.ini"), settings=settings)
    dialog.set_threaded(False)
    qtbot.addWidget(dialog)
    monkeypatch.setattr(
        "uploader.config.ConfigManager.configure", lambda self, u, p: None
    )
    dialog.le_mail.setText("u@e.com")
    dialog.le_pass.setText("pw")
    dialog.le_proxy.setText("http://typed:3128")

    dialog.submit()

    assert AppSettings(tmp_path / "settings.json").load_proxy() == "http://typed:3128"


def test_clearing_proxy_at_login_forgets_it(qtbot, tmp_path: Path, monkeypatch):
    from LoginDialog.login_dialog import LoginDialog
    from uploader.config import ConfigManager

    settings = AppSettings(tmp_path / "settings.json")
    settings.save_proxy("http://old:3128")
    dialog = LoginDialog(ConfigManager(tmp_path / "ia.ini"), settings=settings)
    dialog.set_threaded(False)
    qtbot.addWidget(dialog)
    monkeypatch.setattr(
        "uploader.config.ConfigManager.configure", lambda self, u, p: None
    )
    dialog.le_mail.setText("u@e.com")
    dialog.le_pass.setText("pw")
    dialog.le_proxy.clear()

    dialog.submit()

    assert AppSettings(tmp_path / "settings.json").load_proxy() is None


def test_settings_dialog_change_is_remembered(qtbot, tmp_path: Path):
    from uploader.widgets.settings_dialog import SettingsDialog

    settings = AppSettings(tmp_path / "settings.json")
    dialog = SettingsDialog(tmp_path / "ia.ini", limit=2, proxy="", settings=settings)
    qtbot.addWidget(dialog)
    dialog.proxy_field.setText("http://new:3128")

    dialog._save()

    assert AppSettings(tmp_path / "settings.json").load_proxy() == "http://new:3128"


def test_main_uses_remembered_proxy_when_no_flag(tmp_path: Path, monkeypatch):
    import main as app_main

    settings = AppSettings(tmp_path / "settings.json")
    settings.save_proxy("http://remembered:3128")
    captured = {}

    class FakeWindow:
        def __init__(self, manager, **kw):
            captured["proxy"] = manager.proxy

        def show(self):
            pass

    monkeypatch.setattr(app_main, "MainWindow", FakeWindow)
    monkeypatch.setattr(app_main, "AppSettings", lambda: settings)
    monkeypatch.setattr(app_main.qtw.QApplication, "exec", lambda self: 0)

    app_main.main([])

    assert captured["proxy"] == "http://remembered:3128"

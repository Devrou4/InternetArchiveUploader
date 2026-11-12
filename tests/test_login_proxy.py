from pathlib import Path

import pytest
from PySide6 import QtGui as qtg

from LoginDialog.login_dialog import LoginDialog
from uploader.config import ConfigManager
from uploader.proxy import redact_proxy


@pytest.fixture
def manager(tmp_path: Path):
    return ConfigManager(tmp_path / "ia.ini")


def make_dialog(qtbot, manager):
    dialog = LoginDialog(manager)
    dialog.set_threaded(False)
    qtbot.addWidget(dialog)
    return dialog


def test_login_dialog_has_proxy_field(qtbot, manager):
    dialog = make_dialog(qtbot, manager)

    assert dialog.le_proxy is not None
    assert dialog.le_proxy.text() == ""


def test_login_dialog_prefills_existing_proxy(qtbot, tmp_path: Path):
    dialog = make_dialog(qtbot, ConfigManager(tmp_path / "a.ini", proxy="http://proxy:3128"))

    assert dialog.le_proxy.text() == "http://proxy:3128"


def patch_configure(monkeypatch, recorder):
    """submit() rebuilds the manager via with_proxy, so patch the class."""
    from uploader.config import ConfigManager as _CM

    monkeypatch.setattr(_CM, "configure", lambda self, u, p: recorder(self))


def test_login_uses_typed_proxy(qtbot, manager, monkeypatch):
    dialog = make_dialog(qtbot, manager)
    used = []
    patch_configure(monkeypatch, lambda mgr: used.append((dialog.le_mail.text(), mgr.proxy)))
    dialog.le_mail.setText("u@e.com")
    dialog.le_pass.setText("pw")
    dialog.le_proxy.setText("http://192.168.195.18:20171")

    dialog.submit()

    assert used == [("u@e.com", "http://192.168.195.18:20171")]


def test_login_rejects_malformed_proxy_without_attempting(qtbot, manager, monkeypatch):
    dialog = make_dialog(qtbot, manager)
    called = []
    patch_configure(monkeypatch, lambda mgr: called.append(True))
    dialog.le_mail.setText("u@e.com")
    dialog.le_pass.setText("pw")
    dialog.le_proxy.setText("192.168.195.18:20171")

    dialog.submit()

    assert called == []
    assert "scheme" in dialog.lb_status.text()


def test_blank_proxy_means_direct_connection(qtbot, tmp_path: Path, monkeypatch):
    dialog = make_dialog(qtbot, ConfigManager(tmp_path / "b.ini", proxy="http://proxy:3128"))
    used = []
    patch_configure(monkeypatch, lambda mgr: used.append(mgr.proxy))
    dialog.le_mail.setText("u@e.com")
    dialog.le_pass.setText("pw")
    dialog.le_proxy.clear()

    dialog.submit()

    assert used == [None]


def test_successful_login_emits_proxy_so_uploads_reuse_it(qtbot, manager, monkeypatch):
    dialog = make_dialog(qtbot, manager)
    patch_configure(monkeypatch, lambda mgr: None)
    dialog.le_mail.setText("u@e.com")
    dialog.le_pass.setText("pw")
    dialog.le_proxy.setText("http://proxy:3128")
    emitted = []
    dialog.logged.connect(lambda: emitted.append(dialog.manager.proxy))

    dialog.submit()

    assert emitted == ["http://proxy:3128"]


def test_status_never_shows_proxy_credentials(qtbot, manager, monkeypatch):
    dialog = make_dialog(qtbot, manager)
    patch_configure(monkeypatch, lambda mgr: None)
    dialog.le_mail.setText("u@e.com")
    dialog.le_pass.setText("pw")
    dialog.le_proxy.setText("http://alice:hunter2@proxy:3128")

    dialog.submit()

    assert "hunter2" not in dialog.lb_status.text()
    assert "hunter2" not in dialog.windowTitle()


def test_main_window_adopts_proxy_from_login_dialog(qtbot, tmp_path, monkeypatch):
    """A proxy typed at login must also drive uploads in the main window."""
    import main as app_main
    from PySide6 import QtWidgets as qtw

    config = tmp_path / "ia.ini"
    config.write_text("[s3]\naccess = a\nsecret = b\n", encoding="utf-8")
    monkeypatch.setattr(app_main.MainWindow, "show", lambda self: None)
    window = app_main.MainWindow(ConfigManager(config))
    qtbot.addWidget(window)
    dialog = LoginDialog(window.manager)
    dialog.set_threaded(False)
    qtbot.addWidget(dialog)
    dialog.le_proxy.setText("http://192.168.195.18:20171")

    window._after_login_from(dialog)

    assert window.manager.proxy == "http://192.168.195.18:20171"
    assert "192.168.195.18" in window.config_label.text()
    assert window.controller._manager.proxy == "http://192.168.195.18:20171"


def test_main_window_proxy_from_dialog_is_used_by_new_sessions(qtbot, tmp_path, monkeypatch):
    import main as app_main

    config = tmp_path / "ia.ini"
    config.write_text("[s3]\naccess = a\nsecret = b\n", encoding="utf-8")
    monkeypatch.setattr(app_main.MainWindow, "show", lambda self: None)
    window = app_main.MainWindow(ConfigManager(config))
    qtbot.addWidget(window)
    dialog = LoginDialog(window.manager)
    dialog.set_threaded(False)
    qtbot.addWidget(dialog)
    dialog.le_proxy.setText("http://proxy.local:3128")

    window._after_login_from(dialog)

    assert window.manager.proxy_mapping() == {
        "http": "http://proxy.local:3128",
        "https": "http://proxy.local:3128",
    }


def test_apply_proxy_updates_manager_without_authenticating(qtbot, manager, monkeypatch):
    dialog = make_dialog(qtbot, manager)
    dialog.le_proxy.setText("http://proxy:3128")
    called = []
    patch_configure(monkeypatch, lambda mgr: called.append(True))

    ok = dialog.apply_proxy()

    assert ok is True
    assert dialog.manager.proxy == "http://proxy:3128"
    assert called == []


def test_apply_proxy_reports_bad_value(qtbot, manager):
    dialog = make_dialog(qtbot, manager)
    dialog.le_proxy.setText("proxy:3128")

    assert dialog.apply_proxy() is False
    assert "scheme" in dialog.lb_status.text()


def test_login_logo_uses_existing_asset(qtbot, manager):
    from uploader.resources import resource_path

    dialog = make_dialog(qtbot, manager)

    assert not dialog.lb_logo.pixmap().isNull()
    palette = dialog.palette()
    expected = (
        "Internet_Acrhive_Logo_Black.png"
        if palette.color(qtg.QPalette.Window).value() >= 128
        else "Internet_Acrhive_Logo_White.png"
    )
    assert resource_path(expected).is_file()


def test_login_proxy_row_is_above_the_login_button(qtbot, manager):
    dialog = make_dialog(qtbot, manager)
    dialog.show()
    qtbot.waitExposed(dialog)

    proxy_y = dialog.le_proxy.mapTo(dialog, dialog.le_proxy.rect().topLeft()).y()
    button_y = dialog.pb_login.mapTo(dialog, dialog.pb_login.rect().topLeft()).y()

    assert proxy_y < button_y

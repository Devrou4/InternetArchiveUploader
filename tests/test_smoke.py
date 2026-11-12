from pathlib import Path

import pytest
from PySide6 import QtGui as qtg
from PySide6 import QtWidgets as qtw

import main as app_main
from uploader.config import ConfigManager
from uploader.models import TaskState


def test_smoke_test_returns_zero_without_network(capsys):
    assert app_main.main(["--smoke-test"]) == 0
    assert "smoke-test: ok" in capsys.readouterr().out


def test_parse_args_accepts_config_and_smoke():
    args = app_main.parse_args(["--config", "/tmp/x/ia.ini", "--smoke-test"])

    assert args.config == "/tmp/x/ia.ini"
    assert args.smoke_test is True


def test_close_with_active_uploads_can_be_cancelled(qtbot, tmp_path: Path, monkeypatch):
    config = tmp_path / "ia.ini"
    config.write_text("[s3]\naccess = a\nsecret = b\n", encoding="utf-8")
    monkeypatch.setattr(app_main.MainWindow, "show", lambda self: None)
    window = app_main.MainWindow(ConfigManager(config))
    qtbot.addWidget(window)
    window.controller.has_active_tasks = lambda: True

    asked = []
    monkeypatch.setattr(
        qtw.QMessageBox,
        "question",
        lambda *a, **kw: asked.append(True) or qtw.QMessageBox.StandardButton.Cancel,
    )

    closed = window.close()

    assert asked == [True]
    assert closed is False


def test_close_waits_instead_of_killing_threads(qtbot, tmp_path: Path, monkeypatch):
    config = tmp_path / "ia.ini"
    config.write_text("[s3]\naccess = a\nsecret = b\n", encoding="utf-8")
    monkeypatch.setattr(app_main.MainWindow, "show", lambda self: None)
    window = app_main.MainWindow(ConfigManager(config))
    qtbot.addWidget(window)
    window.controller.has_active_tasks = lambda: True
    waits = []

    monkeypatch.setattr(
        qtw.QMessageBox,
        "question",
        lambda *a, **kw: qtw.QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(window.controller, "stop_dispatch", lambda: waits.append("stop"))
    monkeypatch.setattr(window.controller, "wait_for_active", lambda: waits.append("wait") or True)

    assert window.close() is True
    assert waits == ["stop", "wait"]


def test_close_with_unfinished_uploads_is_refused(qtbot, tmp_path: Path, monkeypatch):
    config = tmp_path / "ia.ini"
    config.write_text("[s3]\naccess = a\nsecret = b\n", encoding="utf-8")
    monkeypatch.setattr(app_main.MainWindow, "show", lambda self: None)
    window = app_main.MainWindow(ConfigManager(config))
    qtbot.addWidget(window)
    window.controller.has_active_tasks = lambda: True
    monkeypatch.setattr(
        qtw.QMessageBox,
        "question",
        lambda *a, **kw: qtw.QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(window.controller, "wait_for_active", lambda: False)
    monkeypatch.setattr(qtw.QMessageBox, "warning", lambda *a, **kw: None)

    assert window.close() is False
from pathlib import Path

import pytest
from PySide6 import QtWidgets as qtw

import main as app_main
from uploader.config import ConfigManager
from uploader.models import TaskState


@pytest.fixture
def window(qtbot, tmp_path: Path, monkeypatch):
    config = tmp_path / "ia.ini"
    config.write_text("[s3]\naccess = a\nsecret = b\n", encoding="utf-8")
    monkeypatch.setattr(app_main.MainWindow, "show", lambda self: None)
    monkeypatch.setattr(app_main.LoginDialog, "show", lambda self: None)
    window = app_main.MainWindow(ConfigManager(config, proxy="http://proxy.example:3128"))
    qtbot.addWidget(window)
    return window


def test_import_does_not_auto_upload(window, tmp_path: Path):
    file_path = tmp_path / "a.mp3"
    file_path.write_bytes(b"ID3\x04" + b"\x00" * 28)
    started = []
    window.controller.start = lambda: started.append(1)

    window.add_paths([str(file_path)])

    assert window.tasks.rowCount() == 1
    assert started == []
    assert window.tasks.tasks()[0].state is TaskState.DRAFT


def test_detected_mediatype_is_preselected(window, tmp_path: Path):
    file_path = tmp_path / "clip.mp4"
    file_path.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 24)

    window.add_paths([str(file_path)])

    assert window.cb_mediatype.currentText() == "movies"


def test_mixed_types_warn_instead_of_guessing(window, tmp_path: Path):
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"ID3\x04" + b"\x00" * 28)
    movie = tmp_path / "b.mp4"
    movie.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 24)

    window.add_paths([str(audio), str(movie)])

    assert "Mixed media types" in window.tb_console.toPlainText()


def test_identifier_case_is_not_lowercased(window):
    assert window.validate_identifier("NintendoSwitchGame_TotK") is True


def test_identifier_with_space_is_rejected(window):
    assert window.validate_identifier("My Item") is False


def test_stop_dispatch_does_not_claim_cancellation(window):
    window.start_upload()

    window.stop_dispatch()

    assert "continue" in window.statusBar().currentMessage()


def test_folder_button_explains_limit(window):
    window.pick_folder_notice()

    assert "not supported" in window.tb_console.toPlainText()


def test_config_switch_updates_bound_config(window, tmp_path: Path):
    other = tmp_path / "other.ini"
    other.write_text("[s3]\naccess = c\nsecret = d\n", encoding="utf-8")

    window.on_config_selected(str(other))

    assert window.current_config == other
    assert str(other) in window.config_label.text()


def test_media_type_manual_choice_wins(window, tmp_path: Path):
    file_path = tmp_path / "a.mp3"
    file_path.write_bytes(b"ID3\x04" + b"\x00" * 28)
    window.add_paths([str(file_path)])

    window.cb_mediatype.setCurrentText("software")
    window.add_paths([str(file_path)])

    assert window.cb_mediatype.currentText() == "software"

def test_main_window_shows_proxy_in_status(window):
    assert window.manager.proxy == "http://proxy.example:3128"
    assert "proxy.example:3128" in window.config_label.text()


def test_window_proxy_change_rebuilds_manager(window, tmp_path: Path):
    window._on_proxy_selected("")

    assert window.manager.proxy is None


def test_parse_args_accepts_proxy():
    args = app_main.parse_args(["--proxy", "http://192.168.195.18:20171"])

    assert args.proxy == "http://192.168.195.18:20171"


def test_main_rejects_malformed_proxy_before_network(capsys):
    assert app_main.main(["--smoke-test", "--proxy", "192.168.195.18:20171"]) == 2
    assert "scheme" in capsys.readouterr().err


@pytest.fixture
def visible_window(qtbot, tmp_path: Path):
    """Real show() — the `window` fixture stubs it out to keep tests quiet."""
    config = tmp_path / "ia.ini"
    config.write_text("[s3]\naccess = a\nsecret = b\n", encoding="utf-8")
    window = app_main.MainWindow(ConfigManager(config))
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    qtbot.wait(100)
    return window


def test_file_buttons_are_not_covered_by_task_table(visible_window, qtbot):
    window = visible_window

    tasks_rect = window.tasks.geometry()
    tasks_rect.moveTopLeft(window.tasks.mapTo(window, window.tasks.rect().topLeft()))

    for name in ("tb_file", "tb_folder", "tb_remove"):
        button = getattr(window, name)
        assert button.isVisible(), f"{name} is not visible"
        rect = button.rect()
        rect.moveTopLeft(button.mapTo(window, button.rect().topLeft()))
        assert rect.width() > 0 and rect.height() > 0, f"{name} has no size"
        assert not tasks_rect.intersects(rect), f"{name} is covered by the task table"


def test_file_buttons_are_clickable(visible_window, qtbot, monkeypatch):
    window = visible_window
    opened = []
    monkeypatch.setattr(
        app_main.qtw.QFileDialog,
        "getOpenFileNames",
        lambda *a, **kw: (opened.append(True) or ([], "")),
    )

    qtbot.mouseClick(window.tb_file, app_main.qtc.Qt.MouseButton.LeftButton)

    assert opened == [True]


def test_import_buttons_are_labelled(visible_window):
    """Icon-only buttons rendered blank on Linux; each must show readable text."""
    for name, expected in (
        ("tb_file", "Select file"),
        ("tb_folder", "Folder"),
        ("tb_remove", "Remove"),
    ):
        button = getattr(visible_window, name)
        assert button.text() == expected
        assert button.toolTip()


def test_toolbar_icons_do_not_leave_blank_buttons(visible_window):
    for name in ("tb_file", "tb_folder", "tb_remove"):
        button = getattr(visible_window, name)
        assert not button.icon().isNull() or button.text()

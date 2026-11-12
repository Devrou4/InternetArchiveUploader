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
    window = app_main.MainWindow(ConfigManager(config))
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
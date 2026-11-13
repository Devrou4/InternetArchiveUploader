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


def test_folder_button_never_reports_unsupported(window, monkeypatch):
    """Regression: the button used to print 'not supported' instead of picking."""
    monkeypatch.setattr(
        app_main.qtw.QFileDialog, "getExistingDirectory", lambda *a, **kw: ""
    )

    window.tb_folder.click()

    assert "not supported" not in window.tb_console.toPlainText().lower()


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

    # tb_remove is retired: Remove now lives on each row.
    for name in ("tb_file", "tb_folder"):
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
    ):
        button = getattr(visible_window, name)
        assert button.text() == expected
        assert button.toolTip()


def test_toolbar_icons_do_not_leave_blank_buttons(visible_window):
    for name in ("tb_file", "tb_folder"):
        button = getattr(visible_window, name)
        assert not button.icon().isNull() or button.text()


def test_close_uses_controller_shutdown(visible_window, monkeypatch):
    """The real shutdown path must join workers, not just stop dispatching."""
    calls = []
    visible_window.controller.has_active_tasks = lambda: True
    monkeypatch.setattr(app_main.qtw.QMessageBox, "question",
                        lambda *a, **kw: app_main.qtw.QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(visible_window.controller, "shutdown",
                        lambda: calls.append("shutdown") or True)

    assert visible_window.close() is True
    assert calls == ["shutdown"]


def test_progress_signal_updates_the_row(window, tmp_path: Path):
    from uploader.models import TaskState

    path = tmp_path / "a.mp3"
    path.write_bytes(b"ID3\x04" + b"\x00" * 28)
    window.add_paths([str(path)])
    task = window.tasks.tasks()[0]
    task.size = 100
    task.state = TaskState.RUNNING

    window.controller._queue.add(task)
    window.controller._on_progress(task.id, 42, 100)

    assert "42" in window.tasks.progress_text(0)


def test_retry_button_requeues_only_failed_rows(window, tmp_path: Path, monkeypatch):
    from uploader.models import TaskState

    ok = tmp_path / "a.mp3"
    ok.write_bytes(b"ID3\x04" + b"\x00" * 28)
    bad = tmp_path / "b.mp3"
    bad.write_bytes(b"ID3\x04" + b"\x00" * 28)
    window.add_paths([str(ok), str(bad)])
    tasks = window.tasks.tasks()
    for task in tasks:
        window.controller._queue.add(task)
    tasks[0].state = TaskState.SUCCEEDED
    tasks[1].state = TaskState.FAILED
    tasks[1].error = "boom"
    started = []
    monkeypatch.setattr(window.controller, "start", lambda: started.append(True))

    window.retry_failed()

    assert tasks[0].state is TaskState.SUCCEEDED
    assert tasks[1].state is TaskState.QUEUED
    assert started == [True]


def test_double_clicking_a_failed_row_retries_that_file(window, tmp_path: Path, monkeypatch):
    from uploader.models import TaskState

    path = tmp_path / "a.mp3"
    path.write_bytes(b"ID3\x04" + b"\x00" * 28)
    window.add_paths([str(path)])
    task = window.tasks.tasks()[0]
    window.controller._queue.add(task)
    task.state = TaskState.FAILED
    task.error = "boom"
    window.tasks.refresh()
    started = []
    monkeypatch.setattr(window.controller, "start", lambda: started.append(True))

    window.tasks.table.cellDoubleClicked.emit(0, 0)

    assert task.state is TaskState.QUEUED
    assert started == [True]


def test_default_window_is_wide_enough_for_the_progress_column(visible_window):
    """A 640px window hides Progress/Detail behind a scrollbar; widen by default."""
    viewport = visible_window.tasks.table.viewport().width()
    shown_columns = sum(
        visible_window.tasks.table.columnWidth(c) for c in range(6)  # through Progress
    )

    assert shown_columns <= viewport, (
        f"progress column needs {shown_columns}px but only {viewport}px is visible"
    )


def test_cancel_button_cancels_only_selected_running_rows(window, tmp_path: Path, monkeypatch):
    from uploader.models import TaskState

    paths = []
    for name in ("a.mp3", "b.mp3"):
        p = tmp_path / name
        p.write_bytes(b"ID3\x04" + b"\x00" * 28)
        paths.append(str(p))
    window.add_paths(paths)
    tasks = window.tasks.tasks()
    for t in tasks:
        window.controller._queue.add(t)
    tasks[0].state = TaskState.RUNNING
    tasks[1].state = TaskState.RUNNING
    window.tasks.refresh()
    cancelled = []
    monkeypatch.setattr(window.controller, "cancel", lambda tid: cancelled.append(tid))
    window.tasks.table.selectRow(0)

    window.cancel_selected()

    assert cancelled == [tasks[0].id]


def test_cancel_selected_with_nothing_selected_is_a_no_op(window, monkeypatch):
    called = []
    monkeypatch.setattr(window.controller, "cancel", lambda tid: called.append(tid))

    window.cancel_selected()

    assert called == []


def test_double_clicking_a_cancelled_row_requeues_it(window, tmp_path: Path, monkeypatch):
    from uploader.models import TaskState

    p = tmp_path / "a.mp3"
    p.write_bytes(b"ID3\x04" + b"\x00" * 28)
    window.add_paths([str(p)])
    task = window.tasks.tasks()[0]
    window.controller._queue.add(task)
    task.state = TaskState.CANCELLED
    window.tasks.refresh()
    started = []
    monkeypatch.setattr(window.controller, "start", lambda: started.append(True))

    window.tasks.table.cellDoubleClicked.emit(0, 0)

    assert task.state is TaskState.QUEUED
    assert started == [True]


def test_folder_button_opens_a_directory_dialog_and_adds_files(window, tmp_path: Path, monkeypatch):
    folder = tmp_path / "set"
    (folder / "sub").mkdir(parents=True)
    (folder / "a.mp3").write_bytes(b"ID3\x04" + b"\x00" * 28)
    (folder / "sub" / "b.mp3").write_bytes(b"ID3\x04" + b"\x00" * 28)
    monkeypatch.setattr(
        app_main.qtw.QFileDialog,
        "getExistingDirectory",
        lambda *a, **kw: str(folder),
    )

    window.tb_folder.click()

    assert window.tasks.rowCount() == 2


def test_cancelled_directory_selection_adds_nothing(window, monkeypatch):
    monkeypatch.setattr(
        app_main.qtw.QFileDialog, "getExistingDirectory", lambda *a, **kw: ""
    )

    window.tb_folder.click()

    assert window.tasks.rowCount() == 0


def test_global_remove_button_is_gone(window):
    """Remove now lives on each row; a global one would be ambiguous."""
    assert not window.tb_remove.isVisible()
    assert window.tb_remove.text() == "" or window.tb_remove.isHidden()


def test_additional_metadata_widgets_are_removed(window):
    """The feature was removed at the user's request; no state may linger."""
    assert not window.tb_add_metadata.isVisible()
    assert not hasattr(window, "additional_metadata")
    assert not hasattr(window, "fetch_additional_metadata")


def test_metadata_has_no_additional_fields_in_payload(window, tmp_path: Path):
    path = tmp_path / "a.mp3"
    path.write_bytes(b"ID3\x04" + b"\x00" * 28)
    window.add_paths([str(path)])
    window.le_identifier.setText("some-item")
    window.le_title.setText("T")

    item = window.build_item_config()

    assert set(item.metadata) == {
        "title", "description", "creator", "subject", "collection", "mediatype"
    }

from pathlib import Path

import pytest
from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg

from uploader.models import ItemConfig, TaskState, UploadTask
from uploader.widgets.task_table import TaskTable


def make_window(qtbot):
    table = TaskTable()
    qtbot.addWidget(table)
    return table


def local_uri(tmp_path: Path, name: str) -> qtc.QUrl:
    path = tmp_path / name
    path.write_bytes(b"data")
    return qtc.QUrl.fromLocalFile(str(path))


def drop_event(table, urls):
    """Hand a drop to the widget without constructing a Qt-owned event by hand."""
    mime = qtc.QMimeData()
    mime.setUrls(urls)
    table.drop_paths([url.toLocalFile() for url in urls if url.isLocalFile()])
    table.note_skipped_urls([url for url in urls if not url.isLocalFile()])


def test_multiple_local_files_become_separate_rows(qtbot, tmp_path: Path):
    table = make_window(qtbot)

    drop_event(table, [local_uri(tmp_path, "a.bin"), local_uri(tmp_path, "b.bin")])

    assert table.rowCount() == 2
    assert table.remote_name(0) == "a.bin"


def test_non_local_url_is_ignored(qtbot, tmp_path: Path):
    table = make_window(qtbot)
    drop_event(table, [qtc.QUrl("https://example.com/x.mp4")])

    assert table.rowCount() == 0
    assert "local file" in table.last_warning.lower()


def test_directory_is_ignored_with_warning(qtbot, tmp_path: Path):
    table = make_window(qtbot)
    folder = tmp_path / "folder"
    folder.mkdir()

    drop_event(table, [qtc.QUrl.fromLocalFile(str(folder))])

    assert table.rowCount() == 0
    assert "folder" in table.last_warning.lower()


def test_duplicate_drop_is_ignored(qtbot, tmp_path: Path):
    table = make_window(qtbot)
    url = local_uri(tmp_path, "a.bin")
    drop_event(table, [url])
    drop_event(table, [url])

    assert table.rowCount() == 1


def test_rows_share_one_item_by_default(qtbot, tmp_path: Path):
    table = make_window(qtbot)
    table.set_item(ItemConfig("item-1", {"title": "T"}))
    drop_event(table, [local_uri(tmp_path, "a.bin"), local_uri(tmp_path, "b.bin")])

    tasks = table.tasks()
    assert {t.item_key for t in tasks} == {"item-1"}
    assert tasks[0].state is TaskState.DRAFT


def test_bulk_item_change_updates_selected_rows(qtbot, tmp_path: Path):
    table = make_window(qtbot)
    drop_event(table, [local_uri(tmp_path, "a.bin"), local_uri(tmp_path, "b.bin")])

    table.set_item_key_for_rows([0, 1], "other-item")

    assert {t.item_key for t in table.tasks()} == {"other-item"}


def test_running_row_cannot_be_edited(qtbot, tmp_path: Path):
    table = make_window(qtbot)
    drop_event(table, [local_uri(tmp_path, "a.bin")])
    task = table.tasks()[0]
    task.state = TaskState.RUNNING
    table.refresh()

    table.set_item_key_for_rows([0], "blocked")

    assert task.item_key != "blocked"


def test_conflict_rows_cannot_start(qtbot, tmp_path: Path):
    table = make_window(qtbot)
    drop_event(table, [local_uri(tmp_path, "a.bin")])
    task = table.tasks()[0]
    task.error = "Remote name already in use: a.bin"

    assert table.startable_tasks() == []


def test_remove_selected_rows(qtbot, tmp_path: Path):
    table = make_window(qtbot)
    drop_event(table, [local_uri(tmp_path, "a.bin"), local_uri(tmp_path, "b.bin")])

    table.remove_rows([0])

    assert [t.remote_name for t in table.tasks()] == ["b.bin"]

def test_editing_the_remote_name_column_updates_the_task(qtbot, tmp_path: Path):
    """The column is editable; without a handler the edit is silently dropped
    and a conflict cannot be resolved from the UI."""
    table = make_window(qtbot)
    drop_event(table, [local_uri(tmp_path, "a.bin")])
    task = table.tasks()[0]

    item = table.table.item(0, 1)
    item.setText("renamed.bin")
    table.table.itemChanged.emit(item)

    assert task.remote_name == "renamed.bin"


def test_editing_remote_name_to_a_duplicate_is_rejected(qtbot, tmp_path: Path):
    table = make_window(qtbot)
    drop_event(table, [local_uri(tmp_path, "a.bin"), local_uri(tmp_path, "b.bin")])

    item = table.table.item(0, 1)
    item.setText("b.bin")
    table.table.itemChanged.emit(item)

    assert table.tasks()[0].remote_name == "a.bin"
    assert "same remote name" in table.last_warning


def test_progress_column_shows_percent_per_task(qtbot, tmp_path: Path):
    table = make_window(qtbot)
    drop_event(table, [local_uri(tmp_path, "a.bin"), local_uri(tmp_path, "b.bin")])
    a, b = table.tasks()

    from uploader.models import TaskState

    a.size = 100
    a.progress = (50, 100)
    a.state = TaskState.RUNNING
    b.size = 100
    b.state = TaskState.DRAFT
    table.refresh()

    assert table.progress_text(0) == "50%"
    assert table.progress_text(1) == "—"


def test_failed_row_offers_a_retry(qtbot, tmp_path: Path):
    from uploader.models import TaskState

    table = make_window(qtbot)
    drop_event(table, [local_uri(tmp_path, "a.bin")])
    task = table.tasks()[0]
    task.state = TaskState.FAILED
    task.error = "boom"
    table.refresh()

    assert table.retryable_task_ids() == [task.id]


def test_succeeded_row_is_not_retryable(qtbot, tmp_path: Path):
    from uploader.models import TaskState

    table = make_window(qtbot)
    drop_event(table, [local_uri(tmp_path, "a.bin")])
    task = table.tasks()[0]
    task.state = TaskState.SUCCEEDED
    table.refresh()

    assert table.retryable_task_ids() == []


def test_failed_row_shows_the_partial_amount_not_a_full_bar(qtbot, tmp_path: Path):
    """A failed upload that got to 100% of the bytes must not look finished."""
    from uploader.models import TaskState

    table = make_window(qtbot)
    drop_event(table, [local_uri(tmp_path, "a.bin")])
    task = table.tasks()[0]
    task.size = 100
    task.bytes_done = 100
    task.state = TaskState.FAILED
    task.error = "server said no"
    table.refresh()

    label = table.progress_text(0)

    assert "failed" in label.lower()
    assert label != "100%"


def test_detail_column_is_wide_enough_to_read_the_error(qtbot, tmp_path: Path):
    """Detail carries the reason a file failed; it must not be a sliver.

    The window is narrow, so the table scrolls horizontally instead of
    squeezing every column — but Detail must stay readable.
    """
    from uploader.models import TaskState

    table = make_window(qtbot)
    table.resize(620, 200)
    table.show()
    qtbot.waitExposed(table)
    drop_event(table, [local_uri(tmp_path, "a.bin")])
    task = table.tasks()[0]
    task.state = TaskState.FAILED
    task.error = "HTTP 403 not permitted for this collection"
    table.refresh()

    assert table.table.columnWidth(6) >= 200
    assert "403" in table.detail_text(0)


def test_cancelled_row_shows_cancelled_and_offers_requeue(qtbot, tmp_path: Path):
    from uploader.models import TaskState

    table = make_window(qtbot)
    drop_event(table, [local_uri(tmp_path, "a.bin")])
    task = table.tasks()[0]
    task.state = TaskState.CANCELLED
    table.refresh()

    assert "cancelled" in table.progress_text(0).lower() or "取消" in table.progress_text(0)
    assert task.id in table.retryable_task_ids()


def test_active_task_ids_lists_only_running_rows(qtbot, tmp_path: Path):
    from uploader.models import TaskState

    table = make_window(qtbot)
    drop_event(table, [local_uri(tmp_path, "a.bin"), local_uri(tmp_path, "b.bin")])
    a, b = table.tasks()
    a.state = TaskState.RUNNING
    b.state = TaskState.SUCCEEDED
    table.refresh()

    assert table.active_task_ids() == [a.id]

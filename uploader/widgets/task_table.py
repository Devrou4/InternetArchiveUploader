"""Drag-and-drop upload task table.

Owns presentation only. Editing rules (running rows are frozen, conflicted
rows cannot start) are enforced here so the controller cannot bypass them.
"""

import uuid
from pathlib import Path

from PySide6 import QtCore as qtc
from PySide6 import QtWidgets as qtw

from uploader.detection import detect_file
from uploader.models import ItemConfig, TaskState, UploadTask

COLUMNS = ["File", "Remote name", "Item", "Type", "Status", "Detail"]


class TaskTable(qtw.QWidget):
    files_added = qtc.Signal(list)

    def __init__(self, config_path: Path | None = None, parent=None):
        super().__init__(parent)
        self._config_path = Path(config_path) if config_path else Path("ia.ini")
        self._tasks: list[UploadTask] = []
        self._item = ItemConfig("", {})
        self._seen_paths: set[str] = set()
        self.last_warning = ""

        self.setAcceptDrops(True)
        layout = qtw.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.hint = qtw.QLabel("Drop files here, or use “Select file”.")
        self.hint.setObjectName("drop_hint")
        layout.addWidget(self.hint)

        self.table = qtw.QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSelectionBehavior(qtw.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        # Editable columns: Remote name (1) and Item (2). Everything else is
        # derived from the file or the queue state.
        self.table.itemChanged.connect(self._on_item_changed)
        self._refreshing = False
        layout.addWidget(self.table)

    # ---- item binding --------------------------------------------------
    def set_item(self, item: ItemConfig) -> None:
        self._item = item

    def set_config_path(self, path: Path) -> None:
        self._config_path = Path(path)

    # ---- drag and drop -------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        self.drop_paths([url.toLocalFile() for url in urls if url.isLocalFile()])
        self.note_skipped_urls([url for url in urls if not url.isLocalFile()])
        event.acceptProposedAction()

    def drop_paths(self, paths: list[str]) -> list[UploadTask]:
        added = self.add_paths(paths)
        if added:
            self.files_added.emit([task.local_path for task in added])
        return added

    def note_skipped_urls(self, urls: list[qtc.QUrl]) -> None:
        if urls:
            self._warn("Only local files can be dropped; browser links are ignored.")

    def rowCount(self) -> int:
        return len(self._tasks)

    def _warn(self, message: str) -> None:
        self.last_warning = message
        self.hint.setText(message)

    def add_paths(self, paths: list[str]) -> list[UploadTask]:
        added: list[UploadTask] = []
        for raw in paths:
            path = Path(raw)
            if not path.is_file():
                self._warn(f"Not a regular file (folders are not supported yet): {path.name}")
                continue
            key = str(path.resolve())
            if key in self._seen_paths:
                continue
            self._seen_paths.add(key)
            stat = path.stat()
            detection = detect_file(path)
            task = UploadTask(
                id=str(uuid.uuid4()),
                local_path=path,
                item_key=self._item.identifier,
                remote_name=path.name,
                config_path=self._config_path,
                size=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
            )
            task.detected_mediatype = detection.mediatype
            task.needs_confirmation = detection.needs_confirmation
            self._tasks.append(task)
            added.append(task)
        if added:
            self.hint.setText(f"{len(self._tasks)} file(s) ready. Review metadata, then start.")
        self.refresh()
        return added

    # ---- queries -------------------------------------------------------
    def tasks(self) -> list[UploadTask]:
        return list(self._tasks)

    def row_for(self, task_id: str) -> int | None:
        for row, task in enumerate(self._tasks):
            if task.id == task_id:
                return row
        return None

    def remote_name(self, row: int) -> str:
        return self._tasks[row].remote_name

    def startable_tasks(self) -> list[UploadTask]:
        return [
            task
            for task in self._tasks
            if task.state in (TaskState.DRAFT, TaskState.QUEUED) and not task.error
        ]

    # ---- editing -------------------------------------------------------
    def set_item_key_for_rows(self, rows: list[int], item_key: str) -> None:
        for row in rows:
            if not 0 <= row < len(self._tasks):
                continue
            task = self._tasks[row]
            if task.state in (TaskState.RUNNING, TaskState.SUCCEEDED):
                continue
            task.item_key = item_key
        self.refresh()

    def set_remote_name(self, row: int, name: str) -> None:
        task = self._tasks[row]
        if task.state in (TaskState.RUNNING, TaskState.SUCCEEDED):
            return
        if any(other is not task and other.remote_name == name for other in self._tasks):
            self._warn(f"Two tasks would upload the same remote name: {name}")
            return
        task.remote_name = name
        task.error = ""
        self.refresh()

    def remove_rows(self, rows: list[int]) -> None:
        for row in sorted(rows, reverse=True):
            if not 0 <= row < len(self._tasks):
                continue
            task = self._tasks.pop(row)
            self._seen_paths.discard(str(task.local_path.resolve()))
        self.refresh()

    # ---- rendering -----------------------------------------------------
    def _on_item_changed(self, item) -> None:
        if self._refreshing or item is None:
            return
        row, column = item.row(), item.column()
        if not 0 <= row < len(self._tasks):
            return
        if column == 1:
            self.set_remote_name(row, item.text().strip())
        elif column == 2:
            self.set_item_key_for_rows([row], item.text().strip())

    def refresh(self) -> None:
        self._refreshing = True
        try:
            self._render()
        finally:
            self._refreshing = False

    def _render(self) -> None:
        self.table.setRowCount(len(self._tasks))
        for row, task in enumerate(self._tasks):
            mediatype = getattr(task, "detected_mediatype", None)
            if getattr(task, "needs_confirmation", False):
                type_text = "confirm manually"
            else:
                type_text = mediatype or "—"
            cells = [
                task.local_path.name,
                task.remote_name,
                task.item_key,
                type_text,
                task.state.value,
                task.error,
            ]
            for column, value in enumerate(cells):
                item = self.table.item(row, column)
                if item is None:
                    item = qtw.QTableWidgetItem()
                    self.table.setItem(row, column, item)
                item.setText(str(value))
                if task.state in (TaskState.RUNNING, TaskState.SUCCEEDED):
                    item.setFlags(item.flags() & ~qtc.Qt.ItemFlag.ItemIsEditable)
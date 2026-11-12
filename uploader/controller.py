"""Glue between the GUI and upload business logic.

All queue state changes happen here, on the main thread. Workers only emit
signals, which Qt delivers back to this object.
"""

from pathlib import Path

from PySide6 import QtCore as qtc

from uploader.archive_client import ArchiveClient, RemoteStateUnknown
from uploader.config import ConfigError, ConfigManager
from uploader.item_service import ItemSnapshot
from uploader.models import ItemConfig, TaskState, UploadTask
from uploader.queue import TaskQueue
from uploader.workers import UploadWorker


class UploadController(qtc.QObject):
    log = qtc.Signal(str)
    status = qtc.Signal(str)
    state_changed = qtc.Signal()
    item_lookup_failed = qtc.Signal(str)

    def __init__(self, manager: ConfigManager, queue: TaskQueue | None = None, parent=None):
        super().__init__(parent)
        self._manager = manager
        self._queue = queue or TaskQueue()
        self._client: ArchiveClient | None = None
        self._items: dict[str, ItemConfig] = {}
        self._threads: dict[str, qtc.QThread] = {}
        self._workers: dict[str, UploadWorker] = {}
        self._snapshot_cache: dict[str, ItemSnapshot] = {}
        self._timer = qtc.QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._pump)
        self._dispatch_enabled = False

    # ---- configuration -------------------------------------------------
    @property
    def queue(self) -> TaskQueue:
        return self._queue

    def client(self) -> ArchiveClient:
        if self._client is None:
            self._client = ArchiveClient(self._manager.new_session())
        return self._client

    def reset_session(self) -> None:
        """Called after the auth config changes; forget all cached identity."""
        self._client = None
        self._snapshot_cache.clear()

    def has_active_tasks(self) -> bool:
        return bool(self._threads) or self._queue.running_count > 0

    def set_limit(self, limit: int) -> None:
        self._queue.set_limit(limit)
        self.state_changed.emit()

    # ---- item registration --------------------------------------------
    def ensure_item(self, item: ItemConfig) -> ItemSnapshot | None:
        try:
            snapshot = self.client().inspect(item.identifier)
        except (RemoteStateUnknown, ConfigError) as exc:
            self.item_lookup_failed.emit(str(exc))
            return None
        self._snapshot_cache[item.identifier] = snapshot
        self._items[item.identifier] = item
        return snapshot

    def register_tasks(self, item: ItemConfig, tasks: list[UploadTask]) -> bool:
        snapshot = self.ensure_item(item)
        if snapshot is None:
            return False
        tasks = [task for task in tasks if task.item_key == item.identifier]
        known = {existing.id for existing in self._queue.tasks()}
        for task in tasks:
            if task.id not in known:
                self._queue.add(task)
        self._queue.register_item(item, tasks, snapshot)
        self.state_changed.emit()
        return True

    # ---- lifecycle -----------------------------------------------------
    def start(self) -> None:
        self._dispatch_enabled = True
        self._queue.start()
        self._timer.start()
        self._pump()

    def stop_dispatch(self) -> None:
        self._dispatch_enabled = False
        self._queue.stop_dispatch()
        self.status.emit("Stopped dispatching new files; running uploads continue.")

    def shutdown(self, timeout_ms: int = 30000) -> bool:
        """Stop dispatching and join every worker.

        Must be called before the controller (and its QThreads) is destroyed;
        letting Qt own a half-finished thread is what produces crashes with no
        Python frames.
        """
        self.stop_dispatch()
        self._timer.stop()
        if not self.wait_for_active(timeout_ms):
            return False
        # Deliver queued signals (success/failure) before returning.
        qtc.QCoreApplication.processEvents()
        return True

    def wait_for_active(self, timeout_ms: int = 30000) -> bool:
        deadline = qtc.QDateTime.currentMSecsSinceEpoch() + timeout_ms
        for thread in list(self._threads.values()):
            thread.quit()
            if not thread.wait(max(1, deadline - qtc.QDateTime.currentMSecsSinceEpoch())):
                return False
        return True

    def retry(self, task_id: str) -> None:
        self._queue.retry_failed(task_id, now=self._now())
        self.state_changed.emit()

    # ---- pump ----------------------------------------------------------
    def _now(self) -> float:
        return qtc.QDateTime.currentMSecsSinceEpoch() / 1000.0

    def _pump(self) -> None:
        for task in self._queue.next_ready(now=self._now()):
            self._launch(task)

    def _launch(self, task: UploadTask) -> None:
        metadata = self._queue.metadata_for_task(task)
        thread = qtc.QThread(self)
        worker = UploadWorker(task, self.client(), metadata)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)

        worker.succeeded.connect(lambda result, tid=task.id: self._on_success(tid, result))
        worker.failed.connect(lambda error, tid=task.id: self._on_failure(tid, error))
        worker.unknown.connect(lambda message, tid=task.id: self._on_unknown(tid, message))
        worker.log.connect(self.log)

        self._threads[task.id] = thread
        self._workers[task.id] = worker
        thread.start()
        self.state_changed.emit()

    def _finish(self, task_id: str) -> None:
        """Retire a finished worker without blocking the GUI thread.

        This runs from a slot invoked by the worker's own signal, so calling
        wait() here would wait on ourselves. quit() lets the loop end and the
        thread deletes itself once it is really finished.
        """
        thread = self._threads.pop(task_id, None)
        self._workers.pop(task_id, None)
        if thread is not None:
            thread.quit()
            thread.finished.connect(thread.deleteLater)

    def _on_success(self, task_id: str, result) -> None:
        self._queue.complete(task_id, result)
        self._finish(task_id)
        task = self._queue.task(task_id)
        self.log.emit(f"{task.remote_name}: done")
        self.state_changed.emit()

    def _on_failure(self, task_id: str, error: Exception) -> None:
        message = f"{type(error).__name__}: {error}"
        self._queue.fail(task_id, error, now=self._now())
        self._finish(task_id)
        self.log.emit(f"{self._queue.task(task_id).remote_name}: {message}")
        self.state_changed.emit()

    def _on_unknown(self, task_id: str, message: str) -> None:
        self._queue.needs_attention(task_id, message, now=self._now())
        self._finish(task_id)
        self.log.emit(message)
        self.state_changed.emit()


def build_task_from_rows(rows, config_path: Path) -> list[UploadTask]:
    return [task for task in rows]
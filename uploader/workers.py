"""Background upload worker.

The worker emits results only. It never mutates shared task state; the GUI
thread owns that through TaskQueue.
"""

from PySide6 import QtCore as qtc

from uploader.archive_client import RemoteStateUnknown
from uploader.progress import UploadCancelled
from uploader.resources import optional_keep_awake


class UploadWorker(qtc.QObject):
    succeeded = qtc.Signal(object)
    # task_id, bytes_done, bytes_total — keeps concurrent workers distinguishable.
    progress = qtc.Signal(str, int, int)
    failed = qtc.Signal(object)
    cancelled = qtc.Signal(str)
    unknown = qtc.Signal(str)
    log = qtc.Signal(str)

    def __init__(self, task, client, metadata=None, cancel=None):
        super().__init__()
        self._task = task
        self._client = client
        self._metadata = metadata
        self._cancel = cancel

    def _emit_progress(self, done: int, total: int) -> None:
        self.progress.emit(self._task.id, int(done), int(total))

    @qtc.Slot()
    def run(self):
        self.log.emit(f"{self._task.remote_name}: uploading")
        try:
            with optional_keep_awake():
                result = self._client.upload_file(
                    self._task,
                    self._metadata,
                    on_progress=self._emit_progress,
                    cancel=self._cancel,
                )
        except UploadCancelled:
            self.log.emit(f"{self._task.remote_name}: cancelled")
            self.cancelled.emit(self._task.id)
        except RemoteStateUnknown as exc:
            state = self._client.reconcile(self._task)
            if state == "confirmed":
                self.succeeded.emit(None)
            else:
                self.unknown.emit(
                    f"{self._task.remote_name}: upload result unknown, verify on archive.org ({exc})"
                )
        except Exception as exc:
            self.failed.emit(exc)
        else:
            self.log.emit(f"{self._task.remote_name}: uploaded")
            self.succeeded.emit(result)
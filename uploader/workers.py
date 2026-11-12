"""Background upload worker.

The worker emits results only. It never mutates shared task state; the GUI
thread owns that through TaskQueue.
"""

from PySide6 import QtCore as qtc

from uploader.archive_client import RemoteStateUnknown


class UploadWorker(qtc.QObject):
    succeeded = qtc.Signal(object)
    failed = qtc.Signal(str)
    unknown = qtc.Signal(str)
    log = qtc.Signal(str)

    def __init__(self, task, client, metadata=None):
        super().__init__()
        self._task = task
        self._client = client
        self._metadata = metadata

    @qtc.Slot()
    def run(self):
        self.log.emit(f"{self._task.remote_name}: uploading")
        try:
            result = self._client.upload_file(self._task, self._metadata)
        except RemoteStateUnknown as exc:
            state = self._client.reconcile(self._task)
            if state == "confirmed":
                self.succeeded.emit(None)
            else:
                self.unknown.emit(
                    f"{self._task.remote_name}: upload result unknown, verify on archive.org ({exc})"
                )
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.log.emit(f"{self._task.remote_name}: uploaded")
            self.succeeded.emit(result)
"""Per-file upload progress.

The pinned `internetarchive` release has no progress callback: it prepares the
request internally and only prints a `tqdm` bar when `verbose=True`. Rather than
scraping that output, the uploader feeds a counting file object instead of a
plain path, so every byte the library reads is observed.

Progress reports the offset of the current read window, which is what a user
expects to see advance. It is deliberately not cumulative across rewinds: the
library rewinds the body before sending, so a cumulative counter would exceed
the file size.
"""

import os
import threading
from pathlib import Path


class UploadCancelled(Exception):
    """Raised inside the upload loop when the user cancels a transfer."""


class CancelToken:
    """Thread-safe cancellation flag shared between the UI and a worker.

    Cancellation cannot interrupt a socket write in progress; it aborts at the
    next chunk boundary, so at most one chunk is thrown away.
    """

    def __init__(self):
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()


class CountingFile:
    """File wrapper reporting `(bytes_read, total)` while the library reads it."""

    def __init__(self, path, on_progress=None, cancel=None):
        self._handle = open(Path(path), "rb")
        self._cancel = cancel
        self._total = os.fstat(self._handle.fileno()).st_size
        self._done = 0
        self._last_reported = -1
        self._on_progress = on_progress
        self.name = str(path)

    # ---- reporting -----------------------------------------------------
    def _report(self) -> None:
        if self._on_progress is None or self._done == self._last_reported:
            return
        self._last_reported = self._done
        try:
            self._on_progress(self._done, self._total)
        except Exception:
            # A failing UI callback must never break a transfer in flight.
            pass

    # ---- file protocol -------------------------------------------------
    def read(self, size: int = -1) -> bytes:
        if self._cancel is not None and self._cancel.cancelled:
            raise UploadCancelled("Upload cancelled by the user")
        data = self._handle.read(size)
        self._done = self._handle.tell()
        self._report()
        return data

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        result = self._handle.seek(offset, whence)
        self._done = result
        self._last_reported = -1
        return result

    def tell(self) -> int:
        return self._handle.tell()

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def close(self) -> None:
        self._handle.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()
        return False
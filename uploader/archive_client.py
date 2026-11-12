"""Internet Archive adapter.

Every failure mode is classified here so callers never have to guess whether
"no metadata" means "item absent" or "the request failed".
"""

from dataclasses import dataclass, field
from pathlib import Path

from uploader.models import UploadTask


class ArchiveError(Exception):
    """Base class for classified archive failures."""


class AuthenticationFailure(ArchiveError):
    pass


class PermissionFailure(ArchiveError):
    pass


class ConflictFailure(ArchiveError):
    pass


class RemoteStateUnknown(ArchiveError):
    pass


class LocalFileChanged(ArchiveError):
    pass


class RetryableFailure(ArchiveError):
    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


@dataclass(frozen=True)
class ItemSnapshot:
    exists: bool
    metadata: dict
    files: dict[str, dict] = field(default_factory=dict)


@dataclass(frozen=True)
class UploadResult:
    remote_name: str
    verified: bool


class ArchiveClient:
    """Thin, testable wrapper around one ArchiveSession."""

    def __init__(self, session):
        self._session = session

    def inspect(self, identifier: str) -> ItemSnapshot:
        try:
            raw = self._session.get_metadata(identifier)
        except Exception as exc:
            raise RemoteStateUnknown(f"Cannot query {identifier}: {type(exc).__name__}") from None

        if not raw:
            return ItemSnapshot(exists=False, metadata={}, files={})

        metadata = raw.get("metadata", {}) or {}
        files = {entry.get("name"): entry for entry in raw.get("files", []) if entry.get("name")}
        return ItemSnapshot(exists=True, metadata=metadata, files=files)

    def upload_file(self, task: UploadTask, metadata: dict | None) -> UploadResult:
        self._assert_unchanged(task)

        snapshot = self.inspect(task.item_key)
        if task.remote_name in snapshot.files:
            raise ConflictFailure(
                f"Remote file already exists in {task.item_key}: {task.remote_name}"
            )

        item = self._session.get_item(task.item_key)
        try:
            response = item.upload_file(
                str(task.local_path),
                key=task.remote_name,
                metadata=metadata,
            )
        except Exception as exc:
            raise self._classify(exc) from None

        status = getattr(response, "status_code", None)
        if status in (401, 407):
            raise AuthenticationFailure("Authentication rejected (HTTP 401)")
        if status == 403:
            raise PermissionFailure("Upload not permitted (HTTP 403)")
        if status == 409:
            raise ConflictFailure("Remote file already exists")
        if status in (429, 502, 503, 504):
            retry_after = _retry_after(response)
            raise RetryableFailure(f"Temporarily unavailable (HTTP {status})", retry_after)
        if status != 200:
            raise ArchiveError(f"Upload failed (HTTP {status})")

        return UploadResult(remote_name=task.remote_name, verified=False)

    @staticmethod
    def _assert_unchanged(task: UploadTask) -> None:
        path = Path(task.local_path)
        try:
            stat = path.stat()
        except OSError:
            raise LocalFileChanged(f"Local file is no longer available: {path.name}") from None
        if stat.st_size != task.size or stat.st_mtime_ns != task.mtime_ns:
            raise LocalFileChanged(f"Local file changed after import: {path.name}")

    @staticmethod
    def _classify(exc: Exception) -> ArchiveError:
        name = type(exc).__name__
        if "Authentication" in name:
            return AuthenticationFailure("Authentication failed")
        if "Checksum" in name:
            return RetryableFailure("Checksum mismatch reported by the archive")
        return RetryableFailure(f"Network or archive error: {name}")

    def reconcile(self, task: UploadTask) -> str:
        """Return 'confirmed', 'absent' or 'unknown' for an interrupted upload."""
        try:
            snapshot = self.inspect(task.item_key)
        except RemoteStateUnknown:
            return "unknown"
        if not snapshot.exists:
            return "absent"
        return "unknown"


def _retry_after(response) -> float | None:
    try:
        value = response.headers.get("Retry-After")
    except AttributeError:
        return None
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
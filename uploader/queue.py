"""Upload scheduling state machine.

Pure Python, single-threaded: the GUI calls these methods on the main thread.
Workers never mutate task state directly.
"""

from uploader.archive_client import (
    AuthenticationFailure,
    ConflictFailure,
    LocalFileChanged,
    PermissionFailure,
    RemoteStateUnknown,
    RetryableFailure,
)
from uploader.item_service import ItemService, Preparation
from uploader.models import ItemConfig, TaskState, UploadTask

MIN_LIMIT = 1
MAX_LIMIT = 8
MAX_ATTEMPTS = 4
BACKOFF_BASE = 2.0
BACKOFF_CAP = 60.0


class TaskQueue:
    def __init__(self, limit: int = 2):
        self._validate_limit(limit)
        self._limit = limit
        self._tasks: dict[str, UploadTask] = {}
        self._order: list[str] = []
        self._items: dict[str, ItemConfig] = {}
        self._prepared: dict[str, Preparation] = {}
        self._dispatched_initializer: set[str] = set()
        self._dispatch_enabled = False
        self._active: set[str] = set()
        self._service = ItemService()

    # ---- configuration -------------------------------------------------
    @property
    def limit(self) -> int:
        return self._limit

    def set_limit(self, limit: int) -> None:
        self._validate_limit(limit)
        self._limit = limit

    @staticmethod
    def _validate_limit(limit: int) -> None:
        if not isinstance(limit, int) or not MIN_LIMIT <= limit <= MAX_LIMIT:
            raise ValueError(f"Concurrency must be between {MIN_LIMIT} and {MAX_LIMIT}")

    # ---- task registration ---------------------------------------------
    def add(self, task: UploadTask) -> None:
        self._tasks[task.id] = task
        self._order.append(task.id)
        if task.state is TaskState.DRAFT and not task.error:
            task.state = TaskState.QUEUED

    def register_item(
        self,
        item: ItemConfig,
        tasks: list[UploadTask],
        snapshot,
    ) -> Preparation:
        prep = self._service.prepare(item, tasks, snapshot)
        self._items[item.identifier] = item
        self._prepared[item.identifier] = prep
        for task in tasks:
            if task.id in prep.conflicts:
                task.state = TaskState.DRAFT
                task.error = f"Remote name already in use: {prep.conflicts[task.id]}"
        return prep

    def conflicts(self, item_key: str) -> dict[str, str]:
        prep = self._prepared.get(item_key)
        return dict(prep.conflicts) if prep else {}

    # ---- control -------------------------------------------------------
    def start(self) -> None:
        self._dispatch_enabled = True

    def stop_dispatch(self) -> None:
        self._dispatch_enabled = False

    @property
    def running_count(self) -> int:
        return len(self._active)

    def task(self, task_id: str) -> UploadTask:
        return self._tasks[task_id]

    def tasks(self) -> list[UploadTask]:
        return [self._tasks[tid] for tid in self._order]

    def metadata_for(self, item_key: str) -> dict | None:
        item = self._items.get(item_key)
        return dict(item.metadata) if item else None

    # ---- dispatch ------------------------------------------------------
    def next_ready(self, now: float) -> list[UploadTask]:
        ready = self.ready_after_retry(now)
        if not self._dispatch_enabled:
            return []

        result: list[UploadTask] = []
        for task in ready:
            if len(self._active) >= self._limit:
                break
            if not self._may_dispatch(task):
                continue
            task.state = TaskState.RUNNING
            task.attempts += 1
            task.retry_at = None
            self._active.add(task.id)
            result.append(task)
        return result

    def ready_after_retry(self, now: float) -> list[UploadTask]:
        ready: list[UploadTask] = []
        for tid in self._order:
            task = self._tasks[tid]
            if task.state is not TaskState.QUEUED:
                continue
            if task.retry_at is not None and task.retry_at > now:
                continue
            ready.append(task)
        return ready

    def _may_dispatch(self, task: UploadTask) -> bool:
        prep = self._prepared.get(task.item_key)
        if prep is None:
            return True
        if prep.initializer_task_id is None:
            return task.id not in prep.conflicts
        if task.id in prep.conflicts:
            return False
        if prep.initializer_task_id in self._dispatched_initializer:
            return True
        if task.id == prep.initializer_task_id:
            return True
        return False

    def metadata_for_task(self, task: UploadTask) -> dict | None:
        prep = self._prepared.get(task.item_key)
        if prep is None or prep.existing:
            return None
        if task.id != prep.initializer_task_id:
            return None
        return self.metadata_for(task.item_key)

    # ---- outcomes ------------------------------------------------------
    def complete(self, task_id: str, result) -> None:
        task = self._tasks[task_id]
        task.state = TaskState.SUCCEEDED
        task.error = ""
        self._active.discard(task_id)
        prep = self._prepared.get(task.item_key)
        if prep and prep.initializer_task_id == task_id:
            self._dispatched_initializer.add(task_id)

    def fail(self, task_id: str, error: Exception, now: float) -> None:
        task = self._tasks[task_id]
        self._active.discard(task_id)
        task.error = str(error)

        if isinstance(error, RetryableFailure) and task.attempts < MAX_ATTEMPTS - 1:
            delay = error.retry_after if error.retry_after else min(
                BACKOFF_BASE ** task.attempts, BACKOFF_CAP
            )
            task.state = TaskState.QUEUED
            task.retry_at = now + delay
            return

        task.state = TaskState.FAILED
        prep = self._prepared.get(task.item_key)
        if prep and prep.initializer_task_id == task_id:
            for other in self.tasks():
                if other.item_key == task.item_key and other.state is TaskState.QUEUED:
                    other.state = TaskState.FAILED
                    other.error = "Item initialisation failed"

    def needs_attention(self, task_id: str, message: str, now: float) -> None:
        task = self._tasks[task_id]
        self._active.discard(task_id)
        task.state = TaskState.FAILED
        task.error = message

    def cancel(self, task_id: str) -> None:
        """Mark a task cancelled and free its slot.

        For a running task this only removes it from the active set; the worker
        notices its CancelToken and aborts at the next chunk boundary.
        """
        task = self._tasks.get(task_id)
        if task is None or task.state is TaskState.SUCCEEDED:
            return
        task.state = TaskState.CANCELLED
        task.error = "Cancelled by the user"
        self._active.discard(task_id)
        prep = self._prepared.get(task.item_key)
        if prep and prep.initializer_task_id == task_id:
            self._dispatched_initializer.discard(task_id)

    def retry_failed(self, task_id: str, now: float) -> None:
        task = self._tasks[task_id]
        if task.state not in (TaskState.FAILED, TaskState.CANCELLED):
            return
        task.state = TaskState.QUEUED
        task.attempts = 0
        task.retry_at = None
        task.error = ""
        task.reset_progress()
        prep = self._prepared.get(task.item_key)
        if prep and prep.initializer_task_id == task_id:
            self._dispatched_initializer.discard(task_id)
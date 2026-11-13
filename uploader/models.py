from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class TaskState(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ItemConfig:
    identifier: str
    metadata: dict = field(default_factory=dict)
    confirmed: bool = False


@dataclass
class UploadTask:
    id: str
    local_path: Path
    item_key: str
    remote_name: str
    config_path: Path
    size: int
    mtime_ns: int
    state: TaskState = TaskState.DRAFT
    attempts: int = 0
    retry_at: float | None = None
    error: str = ""
    bytes_done: int = 0

    def __post_init__(self) -> None:
        self.local_path = Path(self.local_path)
        self.config_path = Path(self.config_path)
        self.state = TaskState(self.state)

    @property
    def progress(self) -> tuple[int, int]:
        return self.bytes_done, self.size

    @progress.setter
    def progress(self, value: tuple[int, int]) -> None:
        self.bytes_done = max(0, int(value[0]))

    @property
    def percent(self) -> int:
        if self.size <= 0:
            return 100 if self.state is TaskState.SUCCEEDED else 0
        return min(100, int(self.bytes_done * 100 / self.size))

    def reset_progress(self) -> None:
        self.bytes_done = 0
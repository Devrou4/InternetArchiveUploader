from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class TaskState(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


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

    def __post_init__(self) -> None:
        self.local_path = Path(self.local_path)
        self.config_path = Path(self.config_path)
        self.state = TaskState(self.state)
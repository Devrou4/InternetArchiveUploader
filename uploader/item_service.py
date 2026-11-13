from dataclasses import dataclass, field

from uploader.archive_client import ItemSnapshot
from uploader.models import ItemConfig, UploadTask


@dataclass
class Preparation:
    existing: bool = False
    initializer_task_id: str | None = None
    conflicts: dict[str, str] = field(default_factory=dict)


class ItemService:
    """Decides which task initialises an item and which names collide."""

    def prepare(
        self,
        item: ItemConfig,
        tasks: list[UploadTask],
        snapshot: ItemSnapshot,
    ) -> Preparation:
        if not item.identifier.strip():
            raise ValueError("Item identifier is required")

        prep = Preparation(existing=snapshot.exists)

        seen: dict[str, str] = {}
        for task in tasks:
            name = task.remote_name
            if name in snapshot.files:
                prep.conflicts[task.id] = name
            elif name in seen:
                prep.conflicts[task.id] = name
                prep.conflicts[seen[name]] = name
            else:
                seen[name] = task.id

        if not snapshot.exists and tasks:
            prep.initializer_task_id = tasks[0].id

        return prep


__all__ = ["ItemService", "Preparation", "ItemSnapshot"]
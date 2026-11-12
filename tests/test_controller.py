from pathlib import Path

import pytest

from uploader.archive_client import RetryableFailure, UploadResult
from uploader.controller import UploadController
from uploader.item_service import ItemSnapshot
from uploader.models import ItemConfig, TaskState, UploadTask
from uploader.queue import TaskQueue


class FakeManager:
    def __init__(self):
        self.calls = 0

    def new_session(self):
        self.calls += 1
        return object()


class FakeClient:
    def __init__(self, snapshot=None, result=None):
        self.snapshot = snapshot or ItemSnapshot(False, {}, {})
        self.result = result or UploadResult("a.bin", True)
        self.inspections = []

    def inspect(self, identifier):
        self.inspections.append(identifier)
        return self.snapshot

    def upload_file(self, task, metadata):
        return self.result


def make_task(tmp_path: Path, tid="t1", item="item-1") -> UploadTask:
    local = tmp_path / f"{tid}.bin"
    local.write_bytes(b"x")
    return UploadTask(
        id=tid,
        local_path=local,
        item_key=item,
        remote_name=f"{tid}.bin",
        config_path=tmp_path / "ia.ini",
        size=1,
        mtime_ns=local.stat().st_mtime_ns,
    )


def test_register_requires_successful_lookup(tmp_path: Path):
    from uploader.archive_client import RemoteStateUnknown

    class FailingClient(FakeClient):
        def inspect(self, identifier):
            raise RemoteStateUnknown("network down")

    controller = UploadController(FakeManager())
    controller._client = FailingClient()
    item = ItemConfig("item-1", {"title": "T"})
    failures = []
    controller.item_lookup_failed.connect(failures.append)

    assert controller.register_tasks(item, [make_task(tmp_path)]) is False
    assert failures


def test_register_stores_snapshot_for_initializer(tmp_path: Path):
    controller = UploadController(FakeManager())
    controller._client = FakeClient(ItemSnapshot(False, {}, {}))
    item = ItemConfig("item-1", {"title": "New"})
    task = make_task(tmp_path)

    assert controller.register_tasks(item, [task]) is True
    assert controller.queue.metadata_for_task(task) == {"title": "New"}


def test_existing_item_sends_no_metadata(tmp_path: Path):
    controller = UploadController(FakeManager())
    controller._client = FakeClient(ItemSnapshot(True, {"title": "old"}, {}))
    item = ItemConfig("item-1", {"title": "new"})
    task = make_task(tmp_path)

    controller.register_tasks(item, [task])

    assert controller.queue.metadata_for_task(task) is None


def test_reset_session_drops_cached_client():
    manager = FakeManager()
    controller = UploadController(manager)
    controller.client()

    controller.reset_session()

    assert controller._client is None


def test_active_tasks_block_reported():
    controller = UploadController(FakeManager())

    assert controller.has_active_tasks() is False
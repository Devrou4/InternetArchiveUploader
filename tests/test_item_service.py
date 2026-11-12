from pathlib import Path

import pytest

from uploader.item_service import ItemService, ItemSnapshot, Preparation
from uploader.models import ItemConfig, UploadTask


def task(tmp_path: Path, tid: str, remote: str, item_key: str = "item-1") -> UploadTask:
    local = tmp_path / f"{tid}.bin"
    local.write_bytes(b"x")
    return UploadTask(
        id=tid,
        local_path=local,
        item_key=item_key,
        remote_name=remote,
        config_path=tmp_path / "ia.ini",
        size=1,
        mtime_ns=local.stat().st_mtime_ns,
    )


def test_new_item_assigns_single_initializer(tmp_path: Path):
    service = ItemService()
    tasks = [task(tmp_path, "a", "a.bin"), task(tmp_path, "b", "b.bin")]

    prep = service.prepare(ItemConfig("item-1", {"title": "T"}), tasks, ItemSnapshot(False, {}, {}))

    assert prep.initializer_task_id == "a"
    assert prep.conflicts == {}


def test_existing_item_has_no_initializer(tmp_path: Path):
    service = ItemService()
    tasks = [task(tmp_path, "a", "a.bin")]

    prep = service.prepare(
        ItemConfig("item-1", {}),
        tasks,
        ItemSnapshot(True, {"title": "old"}, {}),
    )

    assert prep.initializer_task_id is None
    assert prep.existing is True


def test_remote_name_conflict_is_reported(tmp_path: Path):
    service = ItemService()
    tasks = [task(tmp_path, "a", "a.bin")]

    prep = service.prepare(
        ItemConfig("item-1", {}),
        tasks,
        ItemSnapshot(True, {}, {"a.bin": {"name": "a.bin"}}),
    )

    assert prep.conflicts["a"] == "a.bin"


def test_duplicate_local_remote_names_are_reported(tmp_path: Path):
    service = ItemService()
    tasks = [task(tmp_path, "a", "same.bin"), task(tmp_path, "b", "same.bin")]

    prep = service.prepare(ItemConfig("item-1", {}), tasks, ItemSnapshot(False, {}, {}))

    assert set(prep.conflicts) == {"a", "b"}


def test_empty_identifier_is_rejected(tmp_path: Path):
    service = ItemService()

    with pytest.raises(ValueError):
        service.prepare(ItemConfig("  ", {}), [task(tmp_path, "a", "a.bin")], ItemSnapshot(False, {}, {}))
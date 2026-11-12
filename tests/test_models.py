from pathlib import Path

import pytest

from uploader.models import ItemConfig, TaskState, UploadTask


def test_task_state_values():
    assert TaskState.DRAFT.value == "draft"
    assert TaskState.QUEUED.value == "queued"
    assert TaskState.RUNNING.value == "running"
    assert TaskState.SUCCEEDED.value == "succeeded"
    assert TaskState.FAILED.value == "failed"


def test_item_config_keeps_metadata_as_given():
    metadata = {"title": "My item", "subject": ["a", "b"]}

    item = ItemConfig(identifier="MyItem_2024", metadata=metadata)

    assert item.identifier == "MyItem_2024"
    assert item.metadata["title"] == "My item"
    assert item.metadata["subject"] == ["a", "b"]
    assert item.confirmed is False


def test_upload_task_records_config_binding(tmp_path: Path):
    task = UploadTask(
        id="t1",
        local_path=tmp_path / "a.txt",
        item_key="MyItem_2024",
        remote_name="a.txt",
        config_path=tmp_path / "ia.ini",
        size=10,
        mtime_ns=123,
    )

    assert task.state is TaskState.DRAFT
    assert task.item_key == "MyItem_2024"
    assert task.attempts == 0
    assert UploadTask("t9", tmp_path / "a", "same", "a", tmp_path / "i", 1, 1, state="queued").state is TaskState.QUEUED


def test_item_configs_share_one_metadata_object(tmp_path: Path):
    task_a = UploadTask("t1", tmp_path / "a", "same", "a", tmp_path / "i", 1, 1)
    task_b = UploadTask("t2", tmp_path / "b", "same", "b", tmp_path / "i", 1, 1)

    assert task_a.item_key == task_b.item_key

def test_task_tracks_progress_and_clears_on_retry(tmp_path: Path):
    task = UploadTask("t1", tmp_path / "a", "item", "a", tmp_path / "i", 100, 1)

    task.progress = (40, 100)
    assert task.progress == (40, 100)

    task.reset_progress()
    assert task.progress == (0, 100)


def test_progress_total_defaults_to_the_file_size(tmp_path: Path):
    task = UploadTask("t1", tmp_path / "a", "item", "a", tmp_path / "i", 4096, 1)

    assert task.progress == (0, 4096)

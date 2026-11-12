from pathlib import Path

import pytest

from uploader.archive_client import AuthenticationFailure, RemoteStateUnknown, RetryableFailure
from uploader.item_service import ItemSnapshot
from uploader.models import ItemConfig, TaskState, UploadTask
from uploader.queue import TaskQueue


def task(tmp_path: Path, tid: str, item_key: str = "item-1") -> UploadTask:
    local = tmp_path / f"{tid}.bin"
    local.write_bytes(b"x")
    return UploadTask(
        id=tid,
        local_path=local,
        item_key=item_key,
        remote_name=f"{tid}.bin",
        config_path=tmp_path / "ia.ini",
        size=1,
        mtime_ns=local.stat().st_mtime_ns,
    )


def test_default_limit_is_two(tmp_path: Path):
    assert TaskQueue().limit == 2


@pytest.mark.parametrize("limit", [1, 8])
def test_limit_boundaries_accepted(limit):
    assert TaskQueue(limit=limit).limit == limit


@pytest.mark.parametrize("limit", [0, 9, -3])
def test_limit_out_of_range_rejected(limit):
    with pytest.raises(ValueError):
        TaskQueue(limit=limit)


def test_dispatch_respects_limit(tmp_path: Path):
    queue = TaskQueue(limit=2)
    for tid in ("a", "b", "c"):
        queue.add(task(tmp_path, tid, item_key=tid))

    queue.start()
    ready = queue.next_ready(now=0.0)

    assert len(ready) == 2
    assert queue.running_count == 2


def test_reducing_limit_does_not_cancel_running(tmp_path: Path):
    queue = TaskQueue(limit=2)
    for tid in ("a", "b", "c"):
        queue.add(task(tmp_path, tid, item_key=tid))
    queue.start()
    queue.next_ready(now=0.0)

    queue.set_limit(1)

    assert queue.running_count == 2
    assert queue.next_ready(now=0.0) == []


def test_new_item_initializer_runs_first(tmp_path: Path):
    queue = TaskQueue(limit=4)
    first = task(tmp_path, "a")
    second = task(tmp_path, "b")
    queue.add(first)
    queue.add(second)
    queue.register_item(ItemConfig("item-1", {"title": "T"}), [first, second], ItemSnapshot(False, {}, {}))
    queue.start()

    ready = queue.next_ready(now=0.0)

    assert [t.id for t in ready] == ["a"]


def test_initializer_failure_blocks_followers(tmp_path: Path):
    queue = TaskQueue(limit=4)
    first = task(tmp_path, "a")
    second = task(tmp_path, "b")
    queue.add(first)
    queue.add(second)
    queue.register_item(ItemConfig("item-1", {"title": "T"}), [first, second], ItemSnapshot(False, {}, {}))
    queue.start()
    queue.next_ready(now=0.0)

    queue.fail("a", AuthenticationFailure("bad key"), now=0.0)

    assert queue.next_ready(now=10.0) == []
    assert second.state is TaskState.FAILED


def test_stop_dispatch_keeps_pending_tasks(tmp_path: Path):
    queue = TaskQueue(limit=1)
    for tid in ("a", "b"):
        queue.add(task(tmp_path, tid, item_key=tid))
    queue.start()
    queue.next_ready(now=0.0)

    queue.stop_dispatch()
    queue.complete("a", result=None)
    queue.start()

    assert [t.id for t in queue.next_ready(now=0.0)] == ["b"]


def test_retry_failed_task_reenters_queue(tmp_path: Path):
    queue = TaskQueue(limit=1)
    t = task(tmp_path, "a", item_key="x")
    queue.add(t)
    queue.start()
    queue.next_ready(now=0.0)
    queue.fail("a", AuthenticationFailure("nope"), now=0.0)

    queue.retry_failed("a", now=5.0)

    assert t.state is TaskState.QUEUED
    assert queue.next_ready(now=5.0)


def test_retryable_failure_backs_off(tmp_path: Path):
    queue = TaskQueue(limit=1)
    t = task(tmp_path, "a", item_key="x")
    queue.add(t)
    queue.start()
    queue.next_ready(now=0.0)

    queue.fail("a", RetryableFailure("slow down", retry_after=30), now=0.0)

    assert t.state is TaskState.QUEUED
    assert t.retry_at == 30
    assert queue.next_ready(now=10.0) == []
    assert [x.id for x in queue.next_ready(now=30.0)] == ["a"]


def test_retryable_failure_gives_up_after_four_attempts(tmp_path: Path):
    queue = TaskQueue(limit=1)
    t = task(tmp_path, "a", item_key="x")
    queue.add(t)
    queue.start()

    now = 0.0
    for _ in range(4):
        queue.next_ready(now=now)
        queue.fail("a", RetryableFailure("slow"), now=now)
        now = t.retry_at or now

    assert t.state is TaskState.FAILED


def test_auth_failure_is_not_retried(tmp_path: Path):
    queue = TaskQueue(limit=1)
    t = task(tmp_path, "a", item_key="x")
    queue.add(t)
    queue.start()
    queue.next_ready(now=0.0)

    queue.fail("a", AuthenticationFailure("bad"), now=0.0)

    assert t.state is TaskState.FAILED
    assert queue.ready_after_retry(now=100.0) == []


def test_unknown_remote_state_requires_attention(tmp_path: Path):
    queue = TaskQueue(limit=4)
    t = task(tmp_path, "a", item_key="x")
    queue.add(t)
    queue.start()
    queue.next_ready(now=0.0)

    queue.needs_attention("a", "upload result unknown", now=0.0)

    assert t.state is TaskState.FAILED
    assert "unknown" in t.error


def test_failure_in_one_item_does_not_block_another(tmp_path: Path):
    queue = TaskQueue(limit=2)
    a = task(tmp_path, "a", item_key="x")
    b = task(tmp_path, "b", item_key="y")
    queue.add(a)
    queue.add(b)
    queue.start()
    queue.next_ready(now=0.0)

    queue.fail("a", AuthenticationFailure("bad"), now=0.0)
    queue.complete("b", result=None)

    assert a.state is TaskState.FAILED
    assert b.state is TaskState.SUCCEEDED

def test_single_failed_task_can_be_retried_without_touching_others(tmp_path: Path):
    queue = TaskQueue(limit=2)
    a = task(tmp_path, "a", item_key="x")
    b = task(tmp_path, "b", item_key="y")
    queue.add(a)
    queue.add(b)
    queue.start()
    queue.next_ready(now=0.0)
    queue.fail("a", AuthenticationFailure("bad"), now=0.0)
    queue.complete("b", result=None)

    queue.retry_failed("a", now=1.0)

    assert a.state is TaskState.QUEUED
    assert b.state is TaskState.SUCCEEDED


def test_retrying_a_succeeded_task_is_a_no_op(tmp_path: Path):
    queue = TaskQueue(limit=1)
    t = task(tmp_path, "a", item_key="x")
    queue.add(t)
    queue.start()
    queue.next_ready(now=0.0)
    queue.complete("a", result=None)

    queue.retry_failed("a", now=1.0)

    assert t.state is TaskState.SUCCEEDED


def test_retry_resets_attempts_and_progress(tmp_path: Path):
    queue = TaskQueue(limit=1)
    t = task(tmp_path, "a", item_key="x")
    t.progress = (50, 100)
    queue.add(t)
    queue.start()
    queue.next_ready(now=0.0)
    queue.fail("a", AuthenticationFailure("bad"), now=0.0)

    queue.retry_failed("a", now=1.0)

    assert t.attempts == 0
    assert t.progress[0] == 0

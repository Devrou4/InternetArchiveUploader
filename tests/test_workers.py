from pathlib import Path

import pytest

from uploader import workers
from uploader.archive_client import (
    AuthenticationFailure,
    ConflictFailure,
    RetryableFailure,
    UploadResult,
    RemoteStateUnknown,
)
from uploader.models import UploadTask


def make_task(tmp_path: Path) -> UploadTask:
    local = tmp_path / "a.bin"
    local.write_bytes(b"x")
    return UploadTask(
        id="t1",
        local_path=local,
        item_key="item-1",
        remote_name="a.bin",
        config_path=tmp_path / "ia.ini",
        size=1,
        mtime_ns=local.stat().st_mtime_ns,
    )


class FakeClient:
    def __init__(self, error=None, result=None, reconcile_state="confirmed"):
        self.error = error
        self.result = result or UploadResult("a.bin", True)
        self.reconcile_state = reconcile_state
        self.uploads = []

    def upload_file(self, task, metadata):
        self.uploads.append((task.id, metadata))
        if self.error:
            raise self.error
        return self.result

    def reconcile(self, task):
        return self.reconcile_state


def run_worker(task, client, metadata=None):
    events = []
    worker = workers.UploadWorker(task, client, metadata)
    worker.succeeded.connect(lambda result: events.append(("ok", result)))
    worker.failed.connect(lambda message: events.append(("fail", message)))
    worker.unknown.connect(lambda message: events.append(("unknown", message)))
    worker.log.connect(lambda message: events.append(("log", message)))
    worker.run()
    return [event for event in events if event[0] != "log"]


def test_success_emits_result(tmp_path: Path):
    events = run_worker(make_task(tmp_path), FakeClient(), metadata={"title": "x"})

    assert events[0][0] == "ok"
    assert events[0][1].remote_name == "a.bin"
    assert all("secret" not in str(e) for e in events)


def test_retryable_failure_is_reported_as_failure(tmp_path: Path):
    events = run_worker(make_task(tmp_path), FakeClient(error=RetryableFailure("503")))

    assert events[0][0] == "fail"


def test_unknown_remote_state_emits_unknown(tmp_path: Path):
    client = FakeClient(error=RemoteStateUnknown("timeout"), reconcile_state="unknown")

    events = run_worker(make_task(tmp_path), client)

    assert events[0][0] == "unknown"


def test_conflict_failure_is_reported(tmp_path: Path):
    events = run_worker(make_task(tmp_path), FakeClient(error=ConflictFailure("exists")))

    assert events[0][0] == "fail"
    assert "exists" in events[0][1]


def test_worker_never_touches_thread_unsafe_state(tmp_path: Path):
    task = make_task(tmp_path)
    run_worker(task, FakeClient())

    assert task.state.value == "draft"
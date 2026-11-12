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

    def upload_file(self, task, metadata, on_progress=None, cancel=None):
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
    worker.failed.connect(lambda error: events.append(("fail", error)))
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
    assert isinstance(events[0][1], RetryableFailure)


def test_unknown_remote_state_emits_unknown(tmp_path: Path):
    client = FakeClient(error=RemoteStateUnknown("timeout"), reconcile_state="unknown")

    events = run_worker(make_task(tmp_path), client)

    assert events[0][0] == "unknown"


def test_conflict_failure_is_reported(tmp_path: Path):
    events = run_worker(make_task(tmp_path), FakeClient(error=ConflictFailure("exists")))

    assert events[0][0] == "fail"
    assert "exists" in str(events[0][1])


def test_worker_never_touches_thread_unsafe_state(tmp_path: Path):
    task = make_task(tmp_path)
    run_worker(task, FakeClient())

    assert task.state.value == "draft"

def test_worker_emits_progress_for_its_own_task(tmp_path: Path):
    task = make_task(tmp_path)
    events = []

    class ProgressClient(FakeClient):
        def upload_file(self, task_arg, metadata, on_progress=None, cancel=None):
            if on_progress:
                on_progress(1, 2)
                on_progress(2, 2)
            return UploadResult(task_arg.remote_name, True)

    worker = workers.UploadWorker(task, ProgressClient(), None)
    worker.progress.connect(lambda tid, done, total: events.append((tid, done, total)))
    worker.run()

    assert events == [("t1", 1, 2), ("t1", 2, 2)]


def test_worker_progress_is_scoped_to_its_task_id(tmp_path: Path):
    """Two concurrent workers must not mix their progress."""
    task_a = make_task(tmp_path)
    task_b = make_task(tmp_path)
    task_b.id = "t2"
    got = []

    class Client(FakeClient):
        def upload_file(self, task_arg, metadata, on_progress=None, cancel=None):
            on_progress(5, 5)
            return UploadResult(task_arg.remote_name, True)

    for t in (task_a, task_b):
        w = workers.UploadWorker(t, Client(), None)
        w.progress.connect(lambda tid, d, total: got.append(tid))
        w.run()

    assert got == ["t1", "t2"]


def test_worker_emits_cancelled_separately_from_failure(tmp_path: Path):
    from uploader.progress import UploadCancelled

    task = make_task(tmp_path)
    events = []

    class CancellingClient(FakeClient):
        def upload_file(self, task_arg, metadata, on_progress=None, cancel=None):
            raise UploadCancelled("user cancelled")

    worker = workers.UploadWorker(task, CancellingClient(), None)
    worker.cancelled.connect(lambda tid: events.append(("cancelled", tid)))
    worker.failed.connect(lambda err: events.append(("failed", err)))
    worker.run()

    assert events == [("cancelled", "t1")]


def test_worker_passes_the_cancel_token_to_the_client(tmp_path: Path):
    from uploader.progress import CancelToken

    task = make_task(tmp_path)
    token = CancelToken()
    seen = []

    class Client(FakeClient):
        def upload_file(self, task_arg, metadata, on_progress=None, cancel=None):
            seen.append(cancel is token)
            return UploadResult(task_arg.remote_name, True)

    workers.UploadWorker(task, Client(), None, cancel=token).run()

    assert seen == [True]

from dataclasses import dataclass
from pathlib import Path

import pytest

from uploader.archive_client import (
    ArchiveClient,
    AuthenticationFailure,
    ConflictFailure,
    PermissionFailure,
    RemoteStateUnknown,
    RetryableFailure,
)
from uploader.models import UploadTask


class FakeSession:
    def __init__(self, metadata=None, error=None, upload_status=200):
        self.metadata = metadata
        self.error = error
        self.upload_status = upload_status
        self.upload_calls = []
        self.metadata_calls = []

    def get_metadata(self, identifier):
        self.metadata_calls.append(identifier)
        if self.error:
            raise self.error
        return self.metadata

    def get_item(self, identifier):
        session = self

        class FakeItem:
            def load(self_inner):
                pass

            def upload_file(self_inner, body, key=None, metadata=None, **kwargs):
                session.upload_calls.append({"body": body, "key": key, "metadata": metadata})

                class FakeResponse:
                    status_code = session.upload_status
                    text = ""

                return FakeResponse()

        return FakeItem()


def make_task(tmp_path: Path, remote_name="f.bin") -> UploadTask:
    local = tmp_path / "f.bin"
    local.write_bytes(b"data")
    return UploadTask(
        id="t1",
        local_path=local,
        item_key="item-1",
        remote_name=remote_name,
        config_path=tmp_path / "ia.ini",
        size=local.stat().st_size,
        mtime_ns=local.stat().st_mtime_ns,
    )


def test_inspect_maps_metadata_to_snapshot(tmp_path: Path):
    session = FakeSession(metadata={"metadata": {"title": "T"}, "files": [{"name": "a.txt"}]})
    client = ArchiveClient(session)

    snapshot = client.inspect("item-1")

    assert snapshot.exists is True
    assert snapshot.metadata["title"] == "T"
    assert "a.txt" in snapshot.files


def test_inspect_query_error_is_not_treated_as_absent():
    session = FakeSession(error=RuntimeError("boom"))
    client = ArchiveClient(session)

    with pytest.raises(RemoteStateUnknown):
        client.inspect("item-1")


def test_upload_existing_item_sends_no_metadata(tmp_path: Path):
    session = FakeSession(metadata={"metadata": {"title": "T"}, "files": []})
    client = ArchiveClient(session)
    task = make_task(tmp_path)

    client.upload_file(task, metadata=None)

    assert session.upload_calls[0]["metadata"] is None
    assert session.upload_calls[0]["key"] == "f.bin"


def test_upload_new_item_sends_metadata(tmp_path: Path):
    session = FakeSession(metadata=None)
    client = ArchiveClient(session)
    task = make_task(tmp_path)

    client.upload_file(task, metadata={"title": "New"})

    assert session.upload_calls[0]["metadata"] == {"title": "New"}


def test_identifier_case_is_preserved(tmp_path: Path):
    session = FakeSession(metadata=None)
    client = ArchiveClient(session)
    task = make_task(tmp_path)
    task.item_key = "NintendoSwitchGame_TotK"

    client.inspect("NintendoSwitchGame_TotK")

    assert session.metadata_calls == ["NintendoSwitchGame_TotK"]


@pytest.mark.parametrize(
    ("status", "error_type"),
    [(401, AuthenticationFailure), (403, PermissionFailure), (503, RetryableFailure)],
)
def test_upload_errors_are_classified(tmp_path: Path, status, error_type):
    session = FakeSession(metadata=None, upload_status=status)
    client = ArchiveClient(session)

    with pytest.raises(error_type):
        client.upload_file(make_task(tmp_path), metadata={"title": "x"})


def test_conflict_when_remote_name_exists(tmp_path: Path):
    session = FakeSession(metadata={"metadata": {}, "files": [{"name": "f.bin"}]})
    client = ArchiveClient(session)

    with pytest.raises(ConflictFailure):
        client.upload_file(make_task(tmp_path), metadata=None)


def test_local_file_changed_since_import_is_rejected(tmp_path: Path):
    session = FakeSession(metadata=None)
    client = ArchiveClient(session)
    task = make_task(tmp_path)
    task.mtime_ns = task.mtime_ns - 1

    with pytest.raises(Exception):
        client.upload_file(task, metadata={"title": "x"})

    assert session.upload_calls == []

def test_upload_file_accepts_a_progress_callback(tmp_path: Path):
    session = FakeSession(metadata=None)
    client = ArchiveClient(session)
    seen = []

    client.upload_file(make_task(tmp_path), metadata={"title": "x"}, on_progress=lambda d, t: seen.append((d, t)))

    assert session.upload_calls, "upload was attempted"


def test_progress_callback_received_bytes_reach_the_caller(tmp_path: Path):
    """The client must hand a counting file to the library, not a bare path."""
    seen = []

    class CountingAwareSession(FakeSession):
        def get_item(self, identifier):
            session = self

            class FakeItem:
                def load(self_inner):
                    pass

                def upload_file(self_inner, body, key=None, metadata=None, **kwargs):
                    if hasattr(body, "read"):
                        body.read()
                    session.upload_calls.append({"body": body, "key": key})

                    class R:
                        status_code = 200
                        text = ""

                    return R()

            return FakeItem()

    client = ArchiveClient(CountingAwareSession(metadata=None))
    client.upload_file(make_task(tmp_path), metadata=None, on_progress=lambda d, t: seen.append(d))

    assert seen and seen[-1] > 0


def test_cancelled_upload_raises_upload_cancelled(tmp_path: Path):
    from uploader.progress import CancelToken, UploadCancelled

    class SlowSession(FakeSession):
        def get_item(self, identifier):
            class FakeItem:
                def load(self_inner):
                    pass

                def upload_file(self_inner, body, key=None, metadata=None, **kw):
                    body.read()          # token is already cancelled
                    return None

            return FakeItem()

    client = ArchiveClient(SlowSession(metadata=None))
    token = CancelToken()
    token.cancel()

    with pytest.raises(UploadCancelled):
        client.upload_file(make_task(tmp_path), metadata=None, cancel=token)

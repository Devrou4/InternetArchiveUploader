"""Per-file byte progress.

The library exposes no progress callback, so the adapter feeds the upload a
counting file object. These tests pin the counting itself, because a wrong
counter shows a plausible but false progress bar.
"""

from pathlib import Path

import pytest

from uploader.progress import CountingFile


def test_reports_bytes_as_they_are_read(tmp_path: Path):
    payload = b"x" * 3000
    path = tmp_path / "a.bin"
    path.write_bytes(payload)
    seen = []

    with CountingFile(path, on_progress=lambda done, total: seen.append((done, total))) as handle:
        assert handle.read(1000) == b"x" * 1000
        assert seen[-1] == (1000, 3000)
        handle.read(500)
        assert seen[-1] == (1500, 3000)

    assert seen[-1] == (1500, 3000)


def test_total_is_the_original_size_even_after_seek_zero(tmp_path: Path):
    """upload_file() rewinds the body before sending; the total must survive."""
    path = tmp_path / "a.bin"
    path.write_bytes(b"y" * 2048)
    seen = []

    with CountingFile(path, on_progress=lambda d, t: seen.append((d, t))) as handle:
        handle.read(2048)
        handle.seek(0)
        handle.read(10)

    assert seen[-1] == (10, 2048)


def test_progress_is_monotonic_without_duplicate_at_the_end(tmp_path: Path):
    path = tmp_path / "a.bin"
    path.write_bytes(b"z" * 100)
    seen = []

    with CountingFile(path, on_progress=lambda d, t: seen.append(d)) as handle:
        while handle.read(30):
            pass

    assert seen == sorted(seen)
    assert seen[-1] == 100
    assert seen.count(100) == 1


def test_empty_file_reports_a_finished_zero_total(tmp_path: Path):
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")
    seen = []

    with CountingFile(path, on_progress=lambda d, t: seen.append((d, t))) as handle:
        assert handle.read(10) == b""

    assert seen == [(0, 0)]


def test_callback_failure_does_not_break_the_upload(tmp_path: Path):
    """A broken UI callback must never abort a transfer in flight."""
    path = tmp_path / "a.bin"
    path.write_bytes(b"q" * 500)

    def boom(done, total):
        raise RuntimeError("ui gone")

    with CountingFile(path, on_progress=boom) as handle:
        assert handle.read(500) == b"q" * 500


def test_exposes_the_attributes_requests_relies_on(tmp_path: Path):
    path = tmp_path / "a.bin"
    path.write_bytes(b"a" * 42)

    with CountingFile(path, on_progress=lambda d, t: None) as handle:
        assert handle.name == str(path)
        assert handle.seekable()
        assert handle.tell() == 0
        assert len(handle.read()) == 42


def test_cancel_token_aborts_the_read_loop(tmp_path: Path):
    """Cancellation aborts at the next chunk boundary, not mid-write."""
    from uploader.progress import CancelToken, UploadCancelled

    path = tmp_path / "big.bin"
    path.write_bytes(b"x" * 5000)
    token = CancelToken()
    reads = []

    with CountingFile(path, on_progress=lambda d, t: reads.append(d), cancel=token) as handle:
        handle.read(1000)
        token.cancel()
        with pytest.raises(UploadCancelled):
            handle.read(1000)

    assert reads == [1000]


def test_cancel_before_first_read_aborts_immediately(tmp_path: Path):
    from uploader.progress import CancelToken, UploadCancelled

    path = tmp_path / "a.bin"
    path.write_bytes(b"x" * 100)
    token = CancelToken()
    token.cancel()

    with CountingFile(path, cancel=token) as handle:
        with pytest.raises(UploadCancelled):
            handle.read(10)


def test_uncancelled_token_never_interferes(tmp_path: Path):
    from uploader.progress import CancelToken

    path = tmp_path / "a.bin"
    path.write_bytes(b"x" * 100)
    token = CancelToken()

    with CountingFile(path, cancel=token) as handle:
        assert handle.read(100) == b"x" * 100

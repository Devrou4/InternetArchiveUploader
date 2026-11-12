from pathlib import Path

import pytest

from uploader.detection import detect_file

MP4_HEADER = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 24
PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24
PDF_HEADER = b"%PDF-1.7\n" + b"\x00" * 24
ZIP_HEADER = b"PK\x03\x04" + b"\x00" * 24


def write(tmp_path: Path, name: str, data: bytes = b"x" * 32) -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


@pytest.mark.parametrize(
    ("name", "header", "expected"),
    [
        ("song.mp3", b"ID3\x04" + b"\x00" * 28, "audio"),
        ("album.flac", b"fLaC" + b"\x00" * 28, "audio"),
        ("clip.mp4", MP4_HEADER, "movies"),
        ("movie.mkv", b"\x1aE\xdf\xa3" + b"\x00" * 28, "movies"),
        ("photo.png", PNG_HEADER, "image"),
        ("book.pdf", PDF_HEADER, "texts"),
        ("book.epub", ZIP_HEADER, "texts"),
        ("readme.txt", b"hello world", "texts"),
        ("game.nsp", b"NSP" + b"\x00" * 29, "software"),
        ("game.xci", b"XCI" + b"\x00" * 29, "software"),
    ],
)
def test_common_formats(tmp_path: Path, name, header, expected):
    detection = detect_file(write(tmp_path, name, header))

    assert detection.mediatype == expected
    assert detection.needs_confirmation is False


@pytest.mark.parametrize("name", ["bundle.zip", "bundle.7z", "bundle.rar"])
def test_archives_are_uncertain(tmp_path: Path, name):
    detection = detect_file(write(tmp_path, name, ZIP_HEADER if name.endswith("zip") else b"7z\xbc\xaf" + b"\x00" * 28))

    assert detection.mediatype is None
    assert detection.needs_confirmation is True


def test_unknown_extension_is_uncertain(tmp_path: Path):
    detection = detect_file(write(tmp_path, "mystery.bin", b"\x00\x01\x02" + b"\x00" * 28))

    assert detection.mediatype is None
    assert detection.needs_confirmation is True
    assert detection.reason


def test_extension_and_header_conflict_needs_confirmation(tmp_path: Path):
    detection = detect_file(write(tmp_path, "fake.mp4", PNG_HEADER))

    assert detection.needs_confirmation is True
    assert detection.mediatype is None


def test_missing_file_is_uncertain(tmp_path: Path):
    detection = detect_file(tmp_path / "gone.mp3")

    assert detection.needs_confirmation is True
    assert detection.mediatype is None


def test_directory_is_uncertain(tmp_path: Path):
    directory = tmp_path / "folder.mp3"
    directory.mkdir()

    detection = detect_file(directory)

    assert detection.needs_confirmation is True


def test_empty_file_uses_extension(tmp_path: Path):
    detection = detect_file(write(tmp_path, "empty.mp3", b""))

    assert detection.mediatype == "audio"
    assert detection.needs_confirmation is False
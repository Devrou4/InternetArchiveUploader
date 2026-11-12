from pathlib import Path

import pytest

from uploader.packaging_contract import (
    REQUIRED_FILES,
    FORBIDDEN_NAMES,
    check_dist,
)


def make_dist(root: Path) -> Path:
    """Mirror the onedir layout: assets live next to the binary."""
    (root / "InternetArchiveUploader").write_text("binary", encoding="utf-8")
    for relative in REQUIRED_FILES:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x", encoding="utf-8")
    return root


def test_complete_dist_passes(tmp_path: Path):
    dist = make_dist(tmp_path)

    assert check_dist(dist) == []


def test_missing_resource_is_reported(tmp_path: Path):
    dist = make_dist(tmp_path)
    (dist / "assets" / "Internet_Acrhive_Logo_White.png").unlink()

    problems = check_dist(dist)

    assert any("Logo_White" in p for p in problems)


@pytest.mark.parametrize("name", sorted(FORBIDDEN_NAMES))
def test_credentials_are_rejected(tmp_path: Path, name):
    dist = make_dist(tmp_path)
    (dist / name).write_text("secret", encoding="utf-8")

    problems = check_dist(dist)

    assert any(name in p for p in problems)


def test_nested_credentials_are_rejected(tmp_path: Path):
    dist = make_dist(tmp_path)
    nested = dist / "sub" / "ia.ini"
    nested.parent.mkdir()
    nested.write_text("[s3]\naccess = x\n", encoding="utf-8")

    problems = check_dist(dist)

    assert any("ia.ini" in p for p in problems)

def test_internal_data_layout_is_accepted(tmp_path: Path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "InternetArchiveUploader").write_text("binary", encoding="utf-8")
    internal = dist / "_internal"
    for relative in REQUIRED_FILES:
        target = internal / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x", encoding="utf-8")

    assert check_dist(dist) == []

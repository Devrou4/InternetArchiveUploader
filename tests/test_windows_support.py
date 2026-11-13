"""Windows packaging and path expectations.

These run on Linux but assert the Windows branch explicitly, so CI on
windows-latest exercises the same contract instead of discovering it late.
"""

from pathlib import Path

import pytest

from uploader import config_paths, resources
from uploader.packaging_contract import EXPECTED_BINARY, check_dist


def test_binary_name_gets_exe_suffix_on_windows():
    assert EXPECTED_BINARY("win32") == "InternetArchiveUploader.exe"
    assert EXPECTED_BINARY("linux") == "InternetArchiveUploader"


def test_windows_bundle_requires_the_exe(tmp_path: Path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "InternetArchiveUploader.exe").write_text("binary", encoding="utf-8")
    for relative in (
        "LICENSE",
        "README.md",
        "assets/Internet_Acrhive_Logo_White.png",
        "assets/Internet_Acrhive_Logo_Black.png",
        "assets/Internet_Archive_Icon.jpg",
    ):
        target = dist / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x", encoding="utf-8")

    assert check_dist(dist, platform="win32") == []


def test_windows_bundle_without_exe_is_rejected(tmp_path: Path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "InternetArchiveUploader").write_text("linux binary", encoding="utf-8")

    problems = check_dist(dist, platform="win32")

    assert any("InternetArchiveUploader.exe" in p for p in problems)


def test_linux_bundle_still_expects_extensionless_binary(tmp_path: Path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "InternetArchiveUploader.exe").write_text("windows binary", encoding="utf-8")

    problems = check_dist(dist, platform="linux")

    assert any("Missing executable" in p for p in problems)


def test_default_config_uses_appdata_on_windows():
    env = {"APPDATA": r"C:\Users\me\AppData\Roaming"}

    path = config_paths.default_config_path(env, platform="win32")

    assert str(path).replace("\\", "/").endswith(
        "AppData/Roaming/internetarchive-uploader/ia.ini"
    )


def test_default_config_keeps_xdg_on_linux():
    env = {"XDG_CONFIG_HOME": "/home/me/.config"}

    path = config_paths.default_config_path(env, platform="linux")

    assert path == Path("/home/me/.config/internetarchive-uploader/ia.ini")


def test_user_config_dir_uses_appdata_on_windows(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    monkeypatch.setattr(resources.sys, "platform", "win32")

    directory = resources.user_config_dir()

    assert directory == tmp_path / "Roaming" / "internetarchive-uploader"
    assert directory.is_dir()


def test_windows_state_dir_uses_localappdata(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    monkeypatch.setattr(resources.sys, "platform", "win32")

    directory = resources.user_state_dir()

    assert directory == tmp_path / "Local" / "internetarchive-uploader"
    assert directory.is_dir()


def test_smoke_dist_finds_the_exe_on_windows(tmp_path: Path, monkeypatch):
    from scripts import smoke_dist

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "InternetArchiveUploader.exe").write_text("x", encoding="utf-8")
    monkeypatch.setattr(smoke_dist.sys, "platform", "win32")

    assert smoke_dist.binary_path(dist).name == "InternetArchiveUploader.exe"


def test_smoke_dist_reports_missing_binary(tmp_path: Path):
    from scripts import smoke_dist

    assert smoke_dist.binary_path(tmp_path).name in {
        "InternetArchiveUploader",
        "InternetArchiveUploader.exe",
    }
    assert smoke_dist.main([str(tmp_path)]) == 1


def test_windows_spec_exists_and_targets_main():
    spec = Path(__file__).resolve().parent.parent / "packaging" / "windows.spec"

    text = spec.read_text(encoding="utf-8")

    assert "main.py" in text
    assert "COLLECT" in text
    assert "windows" in text.lower()


def test_windows_spec_uses_the_ico_not_the_png():
    spec = Path(__file__).resolve().parent.parent / "packaging" / "windows.spec"
    text = spec.read_text(encoding="utf-8")

    assert "icon.ico" in text

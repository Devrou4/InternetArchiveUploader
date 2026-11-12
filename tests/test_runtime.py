import os
from pathlib import Path

import pytest

from uploader import resources
from uploader.resources import optional_keep_awake, resource_path


def test_resource_does_not_depend_on_cwd(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    path = resource_path("Internet_Acrhive_Logo_White.png")

    assert path.is_file()


def test_frozen_app_uses_bundle_root(tmp_path: Path, monkeypatch):
    bundle = tmp_path / "bundle"
    (bundle / "assets").mkdir(parents=True)
    (bundle / "assets" / "icon.png").write_bytes(b"x")
    monkeypatch.setattr(resources.sys, "frozen", True, raising=False)
    monkeypatch.setattr(resources.sys, "_MEIPASS", str(bundle), raising=False)

    assert resource_path("icon.png") == bundle / "assets" / "icon.png"


def test_wakepy_failure_does_not_block_upload(monkeypatch):
    def boom():
        raise RuntimeError("no desktop portal")

    monkeypatch.setattr(resources, "_keep_running", boom)
    ran = []

    with optional_keep_awake():
        ran.append(True)

    assert ran == [True]


def test_optional_keep_awake_is_a_context_manager():
    with optional_keep_awake():
        pass


def test_default_dirs_are_user_writable(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))

    config_dir = resources.user_config_dir()
    log_dir = resources.user_state_dir()

    assert config_dir.is_dir()
    assert log_dir.is_dir()
    assert os.access(config_dir, os.W_OK)
    assert os.access(log_dir, os.W_OK)
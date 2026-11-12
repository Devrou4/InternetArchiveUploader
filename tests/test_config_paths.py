import os
from pathlib import Path

import pytest

from uploader.config_paths import default_config_path, resolve_config_path


def test_cli_overrides_saved(tmp_path: Path):
    result = resolve_config_path(
        cli=str(tmp_path / "cli.ini"),
        saved=str(tmp_path / "saved.ini"),
        env={},
    )

    assert result == tmp_path / "cli.ini"


def test_saved_overrides_xdg_default(tmp_path: Path):
    result = resolve_config_path(
        cli=None,
        saved=str(tmp_path / "saved.ini"),
        env={"XDG_CONFIG_HOME": str(tmp_path / "xdg")},
    )

    assert result == tmp_path / "saved.ini"


def test_xdg_default(tmp_path: Path):
    result = resolve_config_path(
        cli=None,
        saved=None,
        env={"XDG_CONFIG_HOME": str(tmp_path / "xdg")},
    )

    assert result == tmp_path / "xdg" / "internetarchive-uploader" / "ia.ini"


def test_xdg_default_falls_back_to_home_config(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    result = default_config_path({})

    assert result == tmp_path / ".config" / "internetarchive-uploader" / "ia.ini"


def test_unicode_space_path(tmp_path: Path):
    target = tmp_path / "我的 配置" / "ia.ini"

    result = resolve_config_path(cli=str(target), saved=None, env={})

    assert result == target


def test_tilde_is_expanded(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    result = resolve_config_path(cli="~/custom/ia.ini", saved=None, env={})

    assert result == tmp_path / "custom" / "ia.ini"
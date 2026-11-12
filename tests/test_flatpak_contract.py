"""Flatpak packaging contract.

The manifest is only exercised on CI, so these tests pin the pieces that would
otherwise fail there for the first time.
"""

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parent.parent
FLATPAK = ROOT / "packaging" / "flatpak"
MANIFEST = FLATPAK / "io.github.jcleng.InternetArchiveUploader.yaml"
APP_ID = "io.github.jcleng.InternetArchiveUploader"


@pytest.fixture(scope="module")
def manifest():
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_exists_with_expected_app_id(manifest):
    assert MANIFEST.is_file()
    assert manifest["id"] == APP_ID


def test_runtime_matches_the_workflow_container(manifest):
    workflow = (ROOT / ".github" / "workflows" / "build-flatpak.yml").read_text(encoding="utf-8")
    runtime_version = str(manifest["runtime-version"])

    assert workflow.count(runtime_version) >= 1
    assert manifest["runtime"] == "org.freedesktop.Platform"
    assert manifest["sdk"] == "org.freedesktop.Sdk"


def test_command_points_at_the_wrapper(manifest):
    wrapper = FLATPAK / "internetarchive-uploader-wrapper"

    assert manifest["command"] == "internetarchive-uploader-wrapper"
    assert wrapper.is_file()


def test_wrapper_is_executable_and_runs_the_app(manifest):
    wrapper = FLATPAK / "internetarchive-uploader-wrapper"
    text = wrapper.read_text(encoding="utf-8")

    assert text.startswith("#!")
    assert "exec" in text
    assert "InternetArchiveUploader" in text


def test_required_files_are_listed_as_sources(manifest):
    module = [m for m in manifest["modules"] if "sources" in m][-1]
    names = {Path(s.get("path", s.get("dest-filename", ""))).name for s in module["sources"]}

    assert "InternetArchiveUploader.desktop" in names
    assert "InternetArchiveUploader.metainfo.xml" in names
    assert "internetarchive-uploader-wrapper" in names


def test_appimage_source_has_a_checksum(manifest):
    uploader = [m for m in manifest["modules"] if m.get("name") == "internetarchive-uploader"][0]
    file_sources = [s for s in uploader["sources"] if s.get("type") in {"file", "archive"}]
    remote = [s for s in file_sources if s.get("url")]

    for source in remote:
        assert "sha256" in source, f"{source.get('url')} has no sha256"


def test_finish_args_allow_network_and_show_the_gui(manifest):
    args = manifest["finish-args"]

    assert "--share=network" in args
    assert any(a.startswith("--socket=x11") for a in args)
    assert any(a.startswith("--socket=wayland") for a in args)


def test_desktop_entry_is_valid():
    desktop = (FLATPAK / "InternetArchiveUploader.desktop").read_text(encoding="utf-8")

    assert "[Desktop Entry]" in desktop
    assert "Exec=internetarchive-uploader-wrapper" in desktop
    assert f"Icon={APP_ID}" in desktop
    assert "Terminal=false" in desktop


def test_metainfo_matches_app_id_and_desktop_name():
    import xml.etree.ElementTree as ET

    root = ET.parse(FLATPAK / "InternetArchiveUploader.metainfo.xml").getroot()

    assert root.findtext("id") == APP_ID
    assert root.find("name") is not None
    assert root.findtext("summary")
    launchable = root.find("launchable")
    assert launchable is not None and launchable.text == f"{APP_ID}.desktop"


def test_app_icon_is_at_least_128px():
    """Flatpak/hicolor expects a real icon; the upstream 40px asset is too small."""
    from PySide6 import QtGui

    icon = FLATPAK / "icons" / f"{APP_ID}.png"
    assert icon.is_file()
    image = QtGui.QImage(str(icon))
    assert image.width() >= 128 and image.height() >= 128


def test_workflow_builds_and_publishes_the_bundle():
    workflow = (ROOT / ".github" / "workflows" / "build-flatpak.yml").read_text(encoding="utf-8")

    assert "flatpak-builder" in workflow
    assert "flatpak install --user" in workflow
    assert "sha256sum" in workflow
    assert "*.flatpak" in workflow


def test_workflow_does_not_need_secrets():
    workflow = (ROOT / ".github" / "workflows" / "build-flatpak.yml").read_text(encoding="utf-8")

    assert "secrets." not in workflow


def test_bundle_source_is_a_file_not_an_archive(manifest):
    """flatpak-builder auto-extracts `archive` sources, which breaks our tar step."""
    uploader = [m for m in manifest["modules"] if m.get("name") == "internetarchive-uploader"][0]
    bundle = [
        s for s in uploader["sources"]
        if s.get("dest-filename") == "uploader-bundle.tar.gz"
    ][0]

    assert bundle["type"] == "file"


def test_build_commands_extract_without_chown(manifest):
    """CI tarballs carry uid 1001; the sandbox cannot chown, so drop ownership."""
    uploader = [m for m in manifest["modules"] if m.get("name") == "internetarchive-uploader"][0]
    commands = " ".join(uploader["build-commands"])

    assert "--no-same-owner" in commands
    assert "InternetArchiveUploader" in commands


def test_workflow_run_blocks_have_balanced_quotes():
    """A stray quote breaks the whole step with 'unexpected EOF'."""
    import re
    import subprocess
    import tempfile

    text = (ROOT / ".github" / "workflows" / "build-flatpak.yml").read_text(encoding="utf-8")
    blocks = re.findall(r"run: \|\n((?:\s{10}.*\n)+)", text)
    assert blocks, "no run: | blocks found"

    for block in blocks:
        script = "\n".join(line[10:] for line in block.splitlines() if line.strip())
        handle = tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False)
        handle.write(script)
        handle.close()
        result = subprocess.run(["bash", "-n", handle.name], capture_output=True, text=True)
        assert result.returncode == 0, f"{result.stderr}\n---\n{script}"

from pathlib import Path

import pytest

from uploader.proxy import ProxyError, normalize_proxy, redact_proxy


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("http://192.168.195.18:20171", "http://192.168.195.18:20171"),
        ("  http://192.168.195.18:20171  ", "http://192.168.195.18:20171"),
        ("https://proxy.example.com:8443", "https://proxy.example.com:8443"),
        ("http://127.0.0.1:7890", "http://127.0.0.1:7890"),
        ("http://user:pass@proxy.example.com:3128", "http://user:pass@proxy.example.com:3128"),
    ],
)
def test_valid_proxy_is_kept(raw, expected):
    assert normalize_proxy(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_blank_means_no_proxy(raw):
    assert normalize_proxy(raw) is None


@pytest.mark.parametrize(
    "raw",
    [
        "192.168.195.18:20171",
        "proxy.example.com",
        "ftp://proxy.example.com:21",
        "http://",
        "http://host:notaport",
        "http://host:99999",
    ],
)
def test_malformed_proxy_is_rejected(raw):
    with pytest.raises(ProxyError):
        normalize_proxy(raw)


def test_socks_requires_extra_dependency():
    with pytest.raises(ProxyError) as excinfo:
        normalize_proxy("socks5://127.0.0.1:1080")

    assert "PySocks" in str(excinfo.value)


def test_credentials_are_redacted_for_display():
    assert redact_proxy("http://user:secret@proxy:3128") == "http://***:***@proxy:3128"
    assert redact_proxy("http://proxy:3128") == "http://proxy:3128"
    assert redact_proxy(None) == "none"


def test_redaction_never_leaks_password():
    redacted = redact_proxy("http://alice:hunter2@proxy:3128")

    assert "hunter2" not in redacted
    assert "alice" not in redacted

def test_settings_dialog_exposes_proxy_field(qtbot, tmp_path: Path):
    from uploader.widgets.settings_dialog import SettingsDialog

    dialog = SettingsDialog(tmp_path / "ia.ini", limit=2, proxy="http://proxy:3128")
    qtbot.addWidget(dialog)

    assert dialog.proxy_field.text() == "http://proxy:3128"


def test_settings_dialog_emits_normalized_proxy(qtbot, tmp_path: Path):
    from uploader.widgets.settings_dialog import SettingsDialog

    dialog = SettingsDialog(tmp_path / "ia.ini", limit=2, proxy="")
    qtbot.addWidget(dialog)
    emitted = []
    dialog.proxy_selected.connect(emitted.append)
    dialog.proxy_field.setText("  http://192.168.195.18:20171  ")

    dialog._save()

    assert emitted == ["http://192.168.195.18:20171"]


def test_settings_dialog_rejects_bad_proxy_without_closing(qtbot, tmp_path: Path):
    from uploader.widgets.settings_dialog import SettingsDialog

    dialog = SettingsDialog(tmp_path / "ia.ini", limit=2, proxy="")
    qtbot.addWidget(dialog)
    dialog.proxy_field.setText("192.168.195.18:20171")

    dialog._save()

    assert dialog.isVisible() is False or dialog.result() == 0
    assert "scheme" in dialog.error_label.text()


def test_blank_proxy_field_means_direct_connection(qtbot, tmp_path: Path):
    from uploader.widgets.settings_dialog import SettingsDialog

    dialog = SettingsDialog(tmp_path / "ia.ini", limit=2, proxy="http://proxy:3128")
    qtbot.addWidget(dialog)
    emitted = []
    dialog.proxy_selected.connect(emitted.append)
    dialog.proxy_field.clear()

    dialog._save()

    assert emitted == [""]

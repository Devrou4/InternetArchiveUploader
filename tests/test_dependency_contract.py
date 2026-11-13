"""Non-network contract checks against the pinned internetarchive release.

These pin the exact library behaviour the rest of the application relies on,
so an accidental dependency bump fails here rather than inside the GUI.
"""

import inspect

import internetarchive as ia
import pytest
from requests import Response


def test_get_session_accepts_explicit_config_file(tmp_path):
    config_file = tmp_path / "ia.ini"
    config_file.write_text("", encoding="utf-8")

    session = ia.get_session(config_file=str(config_file))

    assert str(session.config_file) == str(config_file)


def test_item_load_exposes_exists_and_metadata():
    source = inspect.getsource(ia.Item.load)

    assert "self.exists = bool(self.item_metadata)" in source
    assert "self.item_metadata" in source


def test_upload_file_accepts_remote_key_and_metadata():
    params = inspect.signature(ia.Item.upload_file).parameters

    assert "key" in params
    assert "metadata" in params
    assert "validate_identifier" in params


def test_upload_returns_requests_responses():
    annotation = inspect.signature(ia.upload).return_annotation

    assert "Response" in str(annotation)


def test_expected_exception_types_are_public():
    for name in ("AuthenticationError", "AccountAPIError"):
        assert hasattr(ia.exceptions, name)


def test_response_status_code_is_the_upload_result_signal():
    response = Response()
    response.status_code = 200

    assert response.ok is True
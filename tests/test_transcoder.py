import pytest
from app.transcoder import sanitize_filename, _build_vf_filter


def test_sanitize_filename_accent():
    assert sanitize_filename("Éléphant") == "elephant"


def test_sanitize_filename_spaces():
    assert sanitize_filename("hello world") == "hello_world"


def test_sanitize_filename_hyphen():
    assert sanitize_filename("foo-bar") == "foo_bar"


def test_sanitize_filename_mixed():
    assert sanitize_filename("Münchner Straße!") == "munchner_strae"


def test_sanitize_filename_none():
    assert sanitize_filename(None) == ""


def test_sanitize_filename_empty():
    assert sanitize_filename("") == ""


def test_sanitize_filename_whitespace_only():
    assert sanitize_filename("   ") == ""


def test_sanitize_filename_special_only():
    assert sanitize_filename("!!!@@@###") == ""


def test_sanitize_filename_truncate():
    long = "a" * 100
    assert len(sanitize_filename(long)) == 64


def test_sanitize_filename_leading_trailing_underscores():
    assert sanitize_filename("__hello__") == "hello"


def test_sanitize_filename_multiple_underscores():
    assert sanitize_filename("a   b___c") == "a_b_c"


def test_sanitize_filename_lowercase():
    assert sanitize_filename("HELLO World") == "hello_world"


class TestBuildVfFilter:
    def test_crop_filter(self):
        result = _build_vf_filter("crop")
        assert result == "scale=320:240:force_original_aspect_ratio=increase,crop=320:240"

    def test_original_filter(self):
        result = _build_vf_filter("original")
        assert result == "scale=320:240:force_original_aspect_ratio=decrease,pad=320:240:(ow-iw)/2:(oh-ih)/2:color=black"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="format_mode invalide"):
            _build_vf_filter("invalid")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="format_mode invalide"):
            _build_vf_filter("")

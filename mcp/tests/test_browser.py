import pytest

from jarvis_mcp.browser import _normalize_url


def test_normalize_adds_https() -> None:
    assert _normalize_url("example.com") == "https://example.com"


def test_normalize_rejects_empty() -> None:
    with pytest.raises(ValueError):
        _normalize_url("")

from types import SimpleNamespace

import pytest

from jarvis_mcp.browser import _normalize_url, goto


def test_normalize_adds_https() -> None:
    assert _normalize_url("example.com") == "https://example.com"


def test_normalize_rejects_empty() -> None:
    with pytest.raises(ValueError):
        _normalize_url("")


def test_goto_uses_macos_open(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_run(cmd: list[str], **kwargs: object) -> SimpleNamespace:
        seen["cmd"] = cmd
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("jarvis_mcp.browser.subprocess.run", fake_run)
    out = goto("https://www.youtube.com")
    assert seen["cmd"] == ["open", "https://www.youtube.com"]
    assert out["ok"] is True
    assert out["via"] == "open"

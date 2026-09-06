from jarvis_mcp.server import TOOL_NAMES, JarvisMcp
from memory.store import Store


class FakeHost:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def call(self, op: str, **fields: object) -> dict:
        self.calls.append((op, fields))
        return {"ok": True, "op": op, **fields}


def test_exactly_four_tool_names() -> None:
    assert TOOL_NAMES == ("memory", "desktop", "browser", "calendar")


def test_desktop_open_hits_host() -> None:
    host = FakeHost()
    mcp = JarvisMcp(store=Store(), host=host)  # type: ignore[arg-type]
    out = mcp.call("desktop", {"action": "open", "name": "Safari"})
    assert out["ok"] is True
    assert host.calls[0][0] == "app.open"


def test_quit_and_calendar_create_need_confirm() -> None:
    host = FakeHost()
    mcp = JarvisMcp(store=Store(), host=host)  # type: ignore[arg-type]
    quit_gate = mcp.call("desktop", {"action": "quit", "bundle_id": "com.apple.Notes"})
    assert quit_gate["needs_confirm"] is True
    assert host.calls == []
    created = mcp.call("calendar", {"action": "create", "title": "dentist", "confirmed": True})
    assert created["ok"] is True
    assert host.calls[-1][0] == "calendar.create"


def test_memory_remember_and_search() -> None:
    mcp = JarvisMcp(store=Store(), host=FakeHost())  # type: ignore[arg-type]
    mcp.call("memory", {"action": "remember", "fact": "dentist tuesday 4pm", "subject": "dentist"})
    hits = mcp.call("memory", {"action": "search", "query": "dentist"})
    assert hits["ok"] is True
    assert any("dentist" in f for f in hits["facts"])


def test_unknown_tool_rejected() -> None:
    mcp = JarvisMcp(store=Store(), host=FakeHost())  # type: ignore[arg-type]
    try:
        mcp.call("whatsapp", {"action": "send"})
    except ValueError as exc:
        assert "unknown tool" in str(exc)
    else:
        raise AssertionError("expected reject")

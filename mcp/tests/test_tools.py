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


def test_desktop_open_accepts_target_alias() -> None:
    host = FakeHost()
    mcp = JarvisMcp(store=Store(), host=host)  # type: ignore[arg-type]
    out = mcp.call("desktop", {"action": "open", "target": "Safari"})
    assert out["ok"] is True
    assert host.calls[0] == ("app.open", {"name": "Safari"})


def test_desktop_open_hits_host() -> None:
    host = FakeHost()
    mcp = JarvisMcp(store=Store(), host=host)  # type: ignore[arg-type]
    out = mcp.call("desktop", {"action": "open", "name": "Safari"})
    assert out["ok"] is True
    assert host.calls[0][0] == "app.open"


def test_close_all_except_quits_running_keep_named() -> None:
    class ListingHost(FakeHost):
        def call(self, op: str, **fields: object) -> dict:
            self.calls.append((op, fields))
            if op == "app.list":
                return {"ok": True, "apps": ["Safari", "Notes", "Cursor", "Music", "Finder"]}
            return {"ok": True, "op": op, **fields}

    host = ListingHost()
    mcp = JarvisMcp(store=Store(), host=host)  # type: ignore[arg-type]
    out = mcp.call(
        "desktop",
        {"action": "close", "except": ["Safari", "Cursor"], "confirmed": True},
    )
    assert out["ok"] is True
    quit_names = [f.get("name") for op, f in host.calls if op == "app.quit"]
    assert quit_names == ["Notes", "Music"]


def test_quit_all_except_in_name() -> None:
    class ListingHost(FakeHost):
        def call(self, op: str, **fields: object) -> dict:
            self.calls.append((op, fields))
            if op == "app.list":
                return {"ok": True, "apps": ["Safari", "Notes", "Cursor"]}
            return {"ok": True, "op": op, **fields}

    host = ListingHost()
    mcp = JarvisMcp(store=Store(), host=host)  # type: ignore[arg-type]
    mcp.call(
        "desktop",
        {"action": "quit", "name": "all apps except safari and cursor", "confirmed": True},
    )
    quit_names = [f.get("name") for op, f in host.calls if op == "app.quit"]
    assert quit_names == ["Notes"]


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


def test_act_uses_last_opened_app(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_act(text: str, app: str | None = None) -> dict:
        seen["text"] = text
        seen["app"] = app
        return {"ok": True, "text": text, "app": app}

    monkeypatch.setattr("jarvis_mcp.ax.act", fake_act)
    host = FakeHost()
    mcp = JarvisMcp(store=Store(), host=host)  # type: ignore[arg-type]
    mcp.call("desktop", {"action": "open", "name": "WhatsApp"})
    out = mcp.call("desktop", {"action": "act", "text": "Sunny", "irreversible": False})
    assert out["ok"] is True
    assert seen == {"text": "Sunny", "app": "WhatsApp"}


def test_unknown_tool_rejected() -> None:
    mcp = JarvisMcp(store=Store(), host=FakeHost())  # type: ignore[arg-type]
    try:
        mcp.call("whatsapp", {"action": "send"})
    except ValueError as exc:
        assert "unknown tool" in str(exc)
    else:
        raise AssertionError("expected reject")

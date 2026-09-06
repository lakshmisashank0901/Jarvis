from pathlib import Path

from brain.turn import run_user_turn
from jarvis_mcp.server import JarvisMcp
from memory.store import Store


class FakeHost:
    def __init__(self) -> None:
        self.ops: list[str] = []

    def call(self, op: str, **fields: object) -> dict:
        self.ops.append(op)
        return {"ok": True, "op": op}


def test_remember_then_search(tmp_path: Path) -> None:
    mcp = JarvisMcp(store=Store(tmp_path / "m.sqlite"), host=FakeHost())  # type: ignore[arg-type]
    remembered = run_user_turn("Remember my dentist is Tuesday 4pm", mcp)
    assert remembered["spoken"] == "Remembered."
    found = run_user_turn("When is my dentist?", mcp)
    assert "dentist" in found["spoken"].lower() or "tuesday" in found["spoken"].lower()


def test_lock_needs_confirm_until_flag(tmp_path: Path) -> None:
    host = FakeHost()
    mcp = JarvisMcp(store=Store(tmp_path / "m.sqlite"), host=host)  # type: ignore[arg-type]
    gated = run_user_turn("Lock the screen", mcp)
    assert gated["confirm"] is not None
    assert host.ops == []
    done = run_user_turn("Lock the screen", mcp, confirmed=True)
    assert done["confirm"] is None
    assert "system.lock" in host.ops


def test_what_is_the_time_speaks_local_clock(tmp_path: Path) -> None:
    host = FakeHost()
    mcp = JarvisMcp(store=Store(tmp_path / "m.sqlite"), host=host)  # type: ignore[arg-type]
    done = run_user_turn("what is the time", mcp)
    assert done["call"]["arguments"]["action"] == "clock"
    assert host.ops == []
    assert "missing value" not in done["spoken"]
    assert any(ch.isdigit() for ch in done["spoken"])


def test_open_and_volume_runs_both(tmp_path: Path) -> None:
    host = FakeHost()
    mcp = JarvisMcp(store=Store(tmp_path / "m.sqlite"), host=host)  # type: ignore[arg-type]
    done = run_user_turn("open safari and set volume to 100", mcp)
    assert host.ops == ["app.open", "system.volume"]
    assert "Opened" in done["spoken"]
    assert "Volume set to 100" in done["spoken"]


def test_open_and_click_runs_both(tmp_path: Path, monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_act(text: str, app: str | None = None) -> dict:
        seen["text"] = text
        seen["app"] = app
        return {"ok": True, "text": text}

    monkeypatch.setattr("jarvis_mcp.ax.act", fake_act)
    host = FakeHost()
    mcp = JarvisMcp(store=Store(tmp_path / "m.sqlite"), host=host)  # type: ignore[arg-type]
    done = run_user_turn("open Safari and click Compose", mcp)
    assert host.ops == ["app.open"]
    assert seen == {"text": "Compose", "app": "Safari"}
    assert "Opened Safari" in done["spoken"]
    assert "Clicked Compose" in done["spoken"]


def test_confirmed_quit_sends_app_name(tmp_path: Path) -> None:
    host = FakeHost()
    mcp = JarvisMcp(store=Store(tmp_path / "m.sqlite"), host=host)  # type: ignore[arg-type]
    done = run_user_turn("Quit Notes", mcp, confirmed=True)
    assert done["confirm"] is None
    assert host.ops == ["app.quit"]
    assert "Notes" in done["spoken"]

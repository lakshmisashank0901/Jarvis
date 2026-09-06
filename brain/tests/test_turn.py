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

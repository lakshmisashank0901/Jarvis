from pathlib import Path

from brain.converse import parse_plan, run_converse
from jarvis_mcp.server import JarvisMcp
from memory.store import Store


class FakeHost:
    def __init__(self) -> None:
        self.ops: list[str] = []

    def call(self, op: str, **fields: object) -> dict:
        self.ops.append(op)
        return {"ok": True, "op": op, **fields}


def test_parse_plan_broken_json_uses_speak_not_blob() -> None:
    raw = (
        '{"speak":"I will close all applications except Safari and Cursor.",'
        '"ask":false,"calls":[{"name":"desktop","arguments":{"action":"close","apps":["dropbox"'
    )
    plan = parse_plan(raw)
    assert not plan["speak"].lstrip().startswith("{")
    assert "Safari" in plan["speak"] or "sure" in plan["speak"].lower()


def test_converse_rewrites_close_except(tmp_path: Path) -> None:
    class ListingHost:
        def __init__(self) -> None:
            self.ops: list[tuple[str, dict]] = []

        def call(self, op: str, **fields: object) -> dict:
            self.ops.append((op, dict(fields)))
            if op == "app.list":
                return {"ok": True, "apps": ["Safari", "Notes", "Cursor"]}
            return {"ok": True, "op": op, **fields}

    host = ListingHost()
    mcp = JarvisMcp(store=Store(tmp_path / "m.sqlite"), host=host)  # type: ignore[arg-type]
    turn = run_converse(
        "close all apps except safari and cursor",
        mcp,
        confirmed=True,
        complete=lambda _p: (
            '{"speak":"I will close the others.","ask":false,'
            '"calls":[{"name":"desktop","arguments":{"action":"close","apps":["dropbox"]}}]}'
            if "tool result" not in _p
            else '{"speak":"Closed the other apps.","ask":false,"calls":[]}'
        ),
    )
    assert not turn["spoken"].lstrip().startswith("{")
    assert ("app.quit", {"name": "Notes"}) in [(op, f) for op, f in host.ops]


def test_converse_opens_each_listed_site(tmp_path: Path, monkeypatch) -> None:
    import brain.converse as converse

    seen: list[str] = []
    monkeypatch.setattr(
        "jarvis_mcp.browser.goto",
        lambda url: seen.append(url) or {"ok": True, "url": url},
    )
    converse._history.clear()
    mcp = JarvisMcp(store=Store(tmp_path / "m.sqlite"), host=FakeHost())  # type: ignore[arg-type]
    turn = run_converse(
        "open youtube discord instagram linkedin",
        mcp,
        complete=lambda _p: '{"speak":"Which website?","ask":true,"calls":[]}',
    )
    assert turn["confirm"] is None
    assert seen == [
        "https://www.youtube.com",
        "https://discord.com",
        "https://www.instagram.com",
        "https://www.linkedin.com",
    ]
    assert "youtubediscord" not in turn["spoken"]


def test_converse_open_youtube_goes_to_browser(tmp_path: Path, monkeypatch) -> None:
    import brain.converse as converse

    seen: dict[str, str] = {}

    def fake_goto(url: str) -> dict:
        seen["url"] = url
        return {"ok": True, "url": url}

    monkeypatch.setattr("jarvis_mcp.browser.goto", fake_goto)
    converse._history.clear()
    mcp = JarvisMcp(store=Store(tmp_path / "m.sqlite"), host=FakeHost())  # type: ignore[arg-type]
    turn = run_converse(
        "open youtube",
        mcp,
        complete=lambda _p: '{"speak":"Is that a website or an app?","ask":true,"calls":[]}',
    )
    assert turn["confirm"] is None
    assert "youtube.com" in seen.get("url", "")
    assert "website or an app" not in turn["spoken"].lower()


def test_converse_followup_opens_prior_site(tmp_path: Path, monkeypatch) -> None:
    import brain.converse as converse

    seen: dict[str, str] = {}
    monkeypatch.setattr(
        "jarvis_mcp.browser.goto",
        lambda url: seen.update(url=url) or {"ok": True, "url": url},
    )
    converse._history.clear()
    converse._history.extend(
        [
            {"role": "user", "content": "open youtube"},
            {"role": "assistant", "content": "Browser or a local app?"},
        ]
    )
    mcp = JarvisMcp(store=Store(tmp_path / "m.sqlite"), host=FakeHost())  # type: ignore[arg-type]
    turn = run_converse(
        "web browser",
        mcp,
        complete=lambda _p: '{"speak":"Which website?","ask":true,"calls":[]}',
    )
    assert "youtube.com" in seen.get("url", "")
    assert turn["confirm"] is None


def test_converse_asks_when_unsure(tmp_path: Path) -> None:
    mcp = JarvisMcp(store=Store(tmp_path / "m.sqlite"), host=FakeHost())  # type: ignore[arg-type]
    turn = run_converse(
        "do the thing",
        mcp,
        complete=lambda _p: '{"speak":"Do you want me to lock the Mac?","ask":true,"calls":[]}',
    )
    assert turn["confirm"] is not None
    assert "lock" in turn["spoken"].lower()
    assert turn["call"]["name"] == ""


def test_converse_rewrites_speak_from_tool_result(tmp_path: Path) -> None:
    replies = iter(
        [
            '{"speak":"Checking.","ask":false,"calls":[{"name":"desktop","arguments":{"action":"clock"}}]}',
            '{"speak":"It is noon.","ask":false,"calls":[]}',
        ]
    )
    mcp = JarvisMcp(store=Store(tmp_path / "m.sqlite"), host=FakeHost())  # type: ignore[arg-type]
    turn = run_converse("time", mcp, complete=lambda _p: next(replies))
    assert turn["spoken"] == "It is noon."


def test_converse_executes_model_tool(tmp_path: Path) -> None:
    host = FakeHost()
    mcp = JarvisMcp(store=Store(tmp_path / "m.sqlite"), host=host)  # type: ignore[arg-type]
    turn = run_converse(
        "safari please",
        mcp,
        complete=lambda _p: (
            '{"speak":"I will open Safari.","ask":false,'
            '"calls":[{"name":"desktop","arguments":{"action":"open","name":"Safari"}}]}'
        ),
    )
    assert host.ops == ["app.open"]
    assert "Safari" in turn["spoken"]
    assert turn["confirm"] is None

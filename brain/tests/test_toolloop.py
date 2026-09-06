import json

from brain.grammar import Tool
from brain.toolloop import Message, run_tool_turn


async def test_tool_turn_rejects_unknown_name() -> None:
    tools = [Tool(name="memory", schema={}), Tool(name="desktop", schema={})]

    async def decode(_prompt: str, _gbnf: str) -> str:
        return json.dumps({"name": "browser", "arguments": {}})

    async def execute(_name: str, _args: dict) -> dict:
        return {"ok": True}

    try:
        await run_tool_turn(
            [Message(role="user", content="go to the web")],
            tools,
            decode=decode,
            execute=execute,
        )
    except ValueError as exc:
        assert "hallucinated" in str(exc)
    else:
        raise AssertionError("expected hallucinated tool to fail")


async def test_tool_turn_caps_at_three_calls() -> None:
    tools = [Tool(name="memory", schema={})]
    calls = {"n": 0}

    async def decode(_prompt: str, _gbnf: str) -> str:
        calls["n"] += 1
        return json.dumps({"name": "memory", "arguments": {"continue": True}})

    async def execute(_name: str, _args: dict) -> dict:
        return {"ok": True}

    out = await run_tool_turn(
        [Message(role="user", content="remember x")],
        tools,
        decode=decode,
        execute=execute,
    )
    assert calls["n"] == 3
    assert sum(1 for m in out if m.role == "tool") == 3

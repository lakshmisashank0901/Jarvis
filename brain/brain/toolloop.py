from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from brain.grammar import Tool, schema_to_gbnf

MAX_TOOL_CALLS = 3

DecodeFn = Callable[[str, str], Awaitable[str]]
ExecFn = Callable[[str, dict[str, Any]], Awaitable[Any]]


@dataclass
class Message:
    role: str
    content: str


async def run_tool_turn(
    messages: list[Message],
    tools: list[Tool],
    *,
    decode: DecodeFn,
    execute: ExecFn,
    max_calls: int = MAX_TOOL_CALLS,
) -> list[Message]:
    """llama.cpp --jinja path: grammar-constrained tool JSON, then speak."""
    gbnf = schema_to_gbnf(tools)
    allowed = {t.name for t in tools}
    out = list(messages)
    for _ in range(max_calls):
        raw = await decode(json.dumps([{"role": m.role, "content": m.content} for m in out]), gbnf)
        call = json.loads(raw)
        name = call["name"]
        if name not in allowed:
            raise ValueError(f"hallucinated tool: {name}")
        result = await execute(name, call.get("arguments") or {})
        out.append(Message(role="assistant", content=raw))
        out.append(Message(role="tool", content=json.dumps(result)))
        if not call.get("arguments", {}).get("continue"):
            break
    return out

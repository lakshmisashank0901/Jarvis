from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brain.router import ToolCall, route
from jarvis_mcp.server import JarvisMcp
from memory.store import Store

DEFAULT_STORE = Path.home() / ".jarvis" / "memory.sqlite"


def default_mcp() -> JarvisMcp:
    DEFAULT_STORE.parent.mkdir(parents=True, exist_ok=True)
    return JarvisMcp(store=Store(DEFAULT_STORE))


def speak(call: ToolCall, result: dict[str, Any]) -> str:
    if result.get("needs_confirm"):
        return f"I need a three second confirm: {result.get('text')}."
    if result.get("ok") is False:
        return str(result.get("error") or "That failed.")
    action = call.arguments.get("action")
    if call.name == "memory" and action == "search":
        facts = result.get("facts") or []
        return str(facts[0]) if facts else "I do not have that yet."
    if call.name == "memory":
        return "Remembered."
    if call.name == "desktop" and action == "open":
        return f"Opened {call.arguments.get('name')}."
    if call.name == "desktop" and action == "volume":
        return f"Volume set to {call.arguments.get('level')}."
    if call.name == "desktop" and action == "inspect":
        tree = result.get("tree") or "the front app"
        return f"On screen: {tree}"[:240]
    if call.name == "browser" and action == "goto":
        return f"Opened {result.get('url') or 'the page'}."
    if call.name == "calendar" and action == "list":
        return str(result.get("events") or "No events.")[:240]
    if call.name == "calendar" and action == "create":
        return f"Added {call.arguments.get('title')} to the calendar."
    return "Done."


def run_user_turn(
    text: str,
    mcp: JarvisMcp,
    *,
    confirmed: bool = False,
) -> dict[str, Any]:
    call = route(text)
    args = dict(call.arguments)
    if confirmed:
        args["confirmed"] = True
    result = mcp.call(call.name, args)
    spoken = speak(call, result)
    confirm = None
    if result.get("needs_confirm"):
        confirm = {
            "id": "pending",
            "text": result.get("text") or spoken,
            "deadline_ms": 3000,
            "utterance": text,
        }
    return {
        "call": {"name": call.name, "arguments": args},
        "result": result,
        "spoken": spoken,
        "confirm": confirm,
    }


def dump_turn(payload: dict[str, Any]) -> str:
    return json.dumps(payload)

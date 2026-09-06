from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from brain.understand import resolve_destinations
from jarvis_mcp.server import TOOL_NAMES, JarvisMcp

CompleteFn = Callable[[str], str]

DEFAULT_MODEL = Path.home() / ".jarvis" / "models" / "Qwen3.5-9B-4bit"
SYSTEM = """You are Jarvis, a local assistant on this Mac. No cloud. Thinking off.
You may use only these tools: memory, desktop, browser, calendar.
desktop actions: open, quit, focus, inspect, act, files_open, files_reveal, volume, mute, lock, sleep, clock
close means quit. To leave apps open: {"name":"desktop","arguments":{"action":"quit","except":["Safari","Cursor"]}}. Do not invent an apps list.
browser actions: goto, snapshot, click, type
calendar actions: list, create, update
memory actions: search, remember
Reply with one JSON object and nothing else:
{"speak":"what you say to the user","ask":false,"calls":[]}
Known sites (youtube, hotstar, gmail, netflix, …) are browser.goto with a full https URL. Do not ask if it is an app. Do not ask which website when they already named it.
If the request is unclear, set ask true, keep calls empty, and speak one confirmation question.
If you will act, put tool calls in calls and explain briefly in speak.
Never invent a tool name outside the four."""

_JSON = re.compile(r"\{.*\}", re.S)
_SPEAK = re.compile(r'"speak"\s*:\s*"((?:\\.|[^"\\])*)"')
_EXCEPT = re.compile(r"\bexcept\s+(.+)", re.I)
_DANGER = {"quit", "close", "lock", "sleep"}
_history: list[dict[str, str]] = []
_loaded: tuple[Any, Any] | None = None


def model_path() -> Path | None:
    raw = os.environ.get("JARVIS_MLX_MODEL", str(DEFAULT_MODEL))
    path = Path(raw)
    weights = path / "model.safetensors"
    if path.is_dir() and (path / "config.json").exists() and weights.exists() and weights.stat().st_size > 1_000_000_000:
        return path
    return None


def available() -> bool:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    return os.environ.get("JARVIS_LLM", "echo") == "mlx" and model_path() is not None


def _except_from_text(text: str) -> list[str]:
    match = _EXCEPT.search(text.strip().rstrip(".!?"))
    if not match:
        return []
    return [
        part.strip()
        for part in re.split(r"\s+and\s+|,\s*", match.group(1))
        if part.strip() and part.strip().lower() not in {"the", "app", "apps"}
    ]


def parse_plan(raw: str) -> dict[str, Any]:
    match = _JSON.search(raw.strip())
    data: dict[str, Any] | None = None
    if match:
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            data = None
    if data is None:
        spoken = _SPEAK.search(raw)
        if spoken:
            speak = bytes(spoken.group(1), "utf-8").decode("unicode_escape")
            return {"speak": speak, "ask": True, "calls": []}
        return {"speak": "I am not sure I understood. Can you say that another way?", "ask": True, "calls": []}
    speak = str(data.get("speak") or "").strip()
    calls = data.get("calls") if isinstance(data.get("calls"), list) else []
    ask = bool(data.get("ask"))
    if not speak:
        speak = "Should I go ahead with that?"
        ask = True
    return {"speak": speak, "ask": ask, "calls": calls}


def _complete_mlx(prompt: str) -> str:
    global _loaded
    path = model_path()
    if path is None:
        return '{"speak":"The local model is not on disk yet.","ask":true,"calls":[]}'
    from mlx_lm import generate, load

    if _loaded is None:
        _loaded = load(str(path))
    model, tokenizer = _loaded
    kwargs: dict[str, Any] = {}
    try:
        chat = tokenizer.apply_chat_template(
            [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
    except TypeError:
        chat = tokenizer.apply_chat_template(
            [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
        )
    return generate(model, tokenizer, prompt=chat, max_tokens=256, **kwargs)


def run_converse(
    text: str,
    mcp: JarvisMcp,
    *,
    confirmed: bool = False,
    complete: CompleteFn | None = None,
) -> dict[str, Any]:
    prior = "\n".join(f"{m['role']}: {m['content']}" for m in _history[-6:])
    prompt = f"{prior}\nuser: {text}".strip()
    complete_fn = complete or _complete_mlx
    dests = resolve_destinations(text, [m["content"] for m in _history if m["role"] == "user"])
    if dests:
        labels = [str(d["arguments"].get("url") or d["arguments"].get("name") or "") for d in dests]
        raw = json.dumps(
            {"speak": f"Opening {', '.join(labels)}.", "ask": False, "calls": dests}
        )
    else:
        raw = complete_fn(prompt)
    plan = parse_plan(raw)
    spoken = plan["speak"]
    if spoken.lstrip().startswith("{"):
        spoken = parse_plan(spoken)["speak"]
    confirm = None
    call: dict[str, Any] = {"name": "", "arguments": {}}
    result: dict[str, Any] = {"ok": True}
    if plan["ask"] and not confirmed:
        confirm = {"id": "pending", "text": spoken, "deadline_ms": 8000, "utterance": text}
    else:
        for item in plan["calls"][:4]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "")
            if name not in TOOL_NAMES:
                continue
            args = dict(item.get("arguments") if isinstance(item.get("arguments"), dict) else {})
            keep = _except_from_text(text)
            if name == "desktop" and str(args.get("action") or "") in {"close", "quit"} and keep:
                args["action"] = "quit"
                args["except"] = keep
                args.pop("apps", None)
                args.pop("name", None)
                args.pop("target", None)
            if confirmed:
                args["confirmed"] = True
            elif not plan["ask"] and str(args.get("action") or "") not in _DANGER:
                args["confirmed"] = True
            try:
                result = mcp.call(name, args)
            except Exception as exc:
                result = {"ok": False, "error": str(exc)}
            call = {"name": name, "arguments": args}
            if result.get("needs_confirm"):
                confirm = {
                    "id": "pending",
                    "text": result.get("text") or spoken,
                    "deadline_ms": 3000,
                    "utterance": text,
                }
                break
            if result.get("ok") is False:
                spoken = f"{spoken} {result.get('error') or 'That failed.'}".strip()
                break
        if call.get("name") and not dests:
            follow = complete_fn(
                f"{prompt}\ntool result: {json.dumps(result)}\n"
                "Update speak from the tool result. JSON only. No extra calls."
            )
            spoken = parse_plan(follow)["speak"] or spoken
    _history.append({"role": "user", "content": text})
    _history.append({"role": "assistant", "content": spoken})
    return {"call": call, "result": result, "spoken": spoken, "confirm": confirm}

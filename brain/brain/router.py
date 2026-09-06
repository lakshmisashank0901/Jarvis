from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]


_URL = re.compile(r"https?://\S+", re.I)


def route(text: str) -> ToolCall:
    raw = text.strip()
    low = raw.lower()

    if _is_browser(low):
        return _browser(raw, low)
    if low.startswith("focus ") or low.startswith("quit ") or low.startswith("open "):
        return _desktop(raw, low)
    if _is_calendar(low):
        return _calendar(raw, low)
    if _is_memory(low):
        return _memory(raw, low)
    return _desktop(raw, low)


def _is_browser(low: str) -> bool:
    if "on this page" in low:
        return True
    if "browser" in low and ("go to" in low or "open" in low):
        return True
    if low.startswith("go to ") or "http://" in low or "https://" in low:
        return True
    return False


def _is_calendar(low: str) -> bool:
    keys = (
        "calendar",
        "book 30",
        "book thirty",
        "meeting",
        "standup",
        "event friday",
        "event saturday",
        "event sunday",
        "event monday",
        "event tuesday",
        "event wednesday",
        "event thursday",
    )
    return any(k in low for k in keys)


def _is_memory(low: str) -> bool:
    if low.startswith("remember "):
        return True
    if "search my memory" in low or "in my memory" in low:
        return True
    if low.startswith("when is ") or low.startswith("what's my ") or low.startswith("what is my "):
        return True
    return False


def _browser(raw: str, low: str) -> ToolCall:
    url_m = _URL.search(raw)
    if url_m:
        return ToolCall("browser", {"action": "goto", "url": url_m.group(0)})
    if "go to " in low:
        rest = raw[low.index("go to ") + 6 :].strip()
        url = rest if rest.startswith("http") else f"https://{rest.split()[0]}"
        return ToolCall("browser", {"action": "goto", "url": url})
    if "click" in low:
        return ToolCall("browser", {"action": "click", "text": _after(low, "click")})
    if "type" in low:
        return ToolCall("browser", {"action": "type", "text": _after(low, "type")})
    return ToolCall("browser", {"action": "snapshot"})


def _calendar(raw: str, low: str) -> ToolCall:
    if any(k in low for k in ("create", "book ", "add ")):
        return ToolCall(
            "calendar",
            {"action": "create", "title": _event_title(raw), "confirm_text": raw},
        )
    if any(k in low for k in ("change", "update", "move ", "reschedule")):
        return ToolCall(
            "calendar",
            {"action": "update", "title": _event_title(raw), "confirm_text": raw},
        )
    return ToolCall("calendar", {"action": "list"})


def _memory(raw: str, low: str) -> ToolCall:
    if low.startswith("remember "):
        fact = raw[9:].strip()
        return ToolCall("memory", {"action": "remember", "fact": fact})
    query = raw
    for prefix in ("search my memory for ", "when is ", "what's ", "what is "):
        if low.startswith(prefix):
            query = raw[len(prefix) :].strip(" ?")
            break
    return ToolCall("memory", {"action": "search", "query": query})


def _desktop(raw: str, low: str) -> ToolCall:
    if low.startswith("open the file") or low.startswith("open file") or "open the file" in low:
        path = _path(raw)
        return ToolCall("desktop", {"action": "files_open", "path": path})
    if "reveal" in low:
        return ToolCall("desktop", {"action": "files_reveal", "path": _path(raw)})
    if "volume" in low:
        nums = re.findall(r"\d+", raw)
        level = int(nums[0]) if nums else 50
        return ToolCall("desktop", {"action": "volume", "level": level})
    if low.startswith("mute") or "mute the" in low:
        return ToolCall("desktop", {"action": "mute", "on": True})
    if low.startswith("lock"):
        return ToolCall("desktop", {"action": "lock", "confirm_text": "Lock the Mac"})
    if low.startswith("sleep"):
        return ToolCall("desktop", {"action": "sleep", "confirm_text": "Sleep the Mac"})
    if low.startswith("quit "):
        return ToolCall("desktop", {"action": "quit", "name": raw[5:].strip(), "confirm_text": raw})
    if low.startswith("focus "):
        return ToolCall("desktop", {"action": "focus", "name": raw[6:].strip()})
    if "on this screen" in low or "what's on" in low and "calendar" not in low:
        return ToolCall("desktop", {"action": "inspect"})
    if low.startswith("click "):
        return ToolCall("desktop", {"action": "act", "text": raw[6:].strip(), "irreversible": False})
    if low.startswith("open "):
        name = raw[5:].strip()
        if name.lower().startswith("the "):
            name = name[4:]
        return ToolCall("desktop", {"action": "open", "name": name})
    return ToolCall("desktop", {"action": "inspect"})


def _after(low: str, word: str) -> str:
    i = low.find(word)
    return low[i + len(word) :].strip(" .")


def _path(raw: str) -> str:
    m = re.search(r"((?:~|/)\S+)", raw)
    return m.group(1) if m else raw.split()[-1]


def _event_title(raw: str) -> str:
    return re.sub(r"(?i)(create a calendar event|book 30 minutes|book|change|update)", "", raw).strip()


def looks_like_url(text: str) -> bool:
    try:
        return urlparse(text).scheme in {"http", "https"}
    except ValueError:
        return False

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

STAGE_NAMES = ("vad", "eot", "asr", "llm_ttft", "first_clause", "tts_ttfa", "outbuf")
WS_URL = "ws://127.0.0.1:8741/v1"


class HudState(StrEnum):
    idle = "idle"
    listening = "listening"
    thinking = "thinking"
    speaking = "speaking"
    confirm = "confirm"


@dataclass
class Confirm:
    id: str
    text: str
    deadline_ms: int = 3000


@dataclass
class HudEvent:
    state: HudState
    partial: str | None = None
    confirm: Confirm | None = None

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "t": "hud",
            "state": self.state.value,
            "partial": self.partial,
            "confirm": None,
        }
        if self.confirm:
            payload["confirm"] = {
                "id": self.confirm.id,
                "text": self.confirm.text,
                "deadline_ms": self.confirm.deadline_ms,
            }
        return payload


@dataclass
class StageEvent:
    name: str
    ms: float

    def to_json(self) -> dict[str, Any]:
        if self.name not in STAGE_NAMES:
            raise ValueError(f"unknown stage {self.name}")
        return {"t": "stage", "name": self.name, "ms": self.ms}


def make_hud(state: HudState, partial: str | None = None, confirm: Confirm | None = None) -> HudEvent:
    return HudEvent(state=state, partial=partial, confirm=confirm)


def make_stage(name: str, ms: float) -> StageEvent:
    return StageEvent(name=name, ms=ms)


def parse_app_message(raw: str) -> dict[str, Any]:
    data = json.loads(raw)
    if data.get("t") not in {"hotkey", "confirm"}:
        raise ValueError("unknown app message")
    return data

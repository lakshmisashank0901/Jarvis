from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from jarvisd.brain_client import BrainClient
from jarvisd.tts_clause import ClauseTts
from jarvisd.ws import STAGE_NAMES, HudState, make_hud, make_stage

EOT_SILENCE_MS = 200


@dataclass
class StageTimer:
    marks: dict[str, float] = field(default_factory=dict)

    def mark(self, name: str, started: float) -> float:
        if name not in STAGE_NAMES:
            raise ValueError(f"unknown stage {name}")
        ms = (time.perf_counter() - started) * 1000
        self.marks[name] = ms
        return ms


def should_fire_eot(silence_ms: float) -> bool:
    return silence_ms >= EOT_SILENCE_MS


async def run_text_turn(
    text: str,
    brain: BrainClient,
    tts: ClauseTts,
    emit: Callable[[dict[str, Any]], None],
) -> dict[str, float]:
    timer = StageTimer()
    t0 = time.perf_counter()
    timer.mark("vad", t0)
    eot_t = time.perf_counter()
    if not should_fire_eot(EOT_SILENCE_MS):
        raise RuntimeError("EOT window misconfigured")
    timer.mark("eot", eot_t)
    asr_t = time.perf_counter()
    transcript = text
    timer.mark("asr", asr_t)
    emit(make_hud(HudState.thinking, partial=transcript).to_json())
    emit(make_stage("asr", timer.marks["asr"]).to_json())

    reply_parts: list[str] = []
    first_clause = True
    async for kind, payload in brain.stream_chat(transcript):
        if kind == "ttft":
            timer.marks["llm_ttft"] = float(payload)
            emit(make_stage("llm_ttft", timer.marks["llm_ttft"]).to_json())
        elif kind == "clause":
            if first_clause:
                c0 = time.perf_counter()
                tts.start(str(payload))
                timer.mark("first_clause", c0)
                t1 = time.perf_counter()
                timer.mark("tts_ttfa", t1)
                emit(make_hud(HudState.speaking, partial=str(payload)).to_json())
                emit(make_stage("first_clause", timer.marks["first_clause"]).to_json())
                emit(make_stage("tts_ttfa", timer.marks["tts_ttfa"]).to_json())
                first_clause = False
            else:
                tts.start(str(payload))
        elif kind == "token":
            reply_parts.append(str(payload))
    out_t = time.perf_counter()
    timer.mark("outbuf", out_t)
    emit(make_stage("outbuf", timer.marks["outbuf"]).to_json())
    emit(make_hud(HudState.idle).to_json())
    return timer.marks


def load_pipecat_graph() -> str:
    """Pipecat 1.8.x graph is constructed here when the extra is installed."""
    try:
        import pipecat  # noqa: F401
    except ImportError:
        return "text-fallback"
    return "pipecat"

from __future__ import annotations

import os
from collections.abc import Callable


class ClauseTts:
    """Start Kokoro at the first clause. Never wait for EOS."""

    def __init__(self, on_audio: Callable[[bytes], None] | None = None) -> None:
        self.on_audio = on_audio
        self.started: list[str] = []

    def start(self, clause: str) -> None:
        self.started.append(clause)
        if os.environ.get("JARVIS_TTS") == "kokoro":
            try:
                from mlx_audio import tts  # type: ignore

                audio = tts.generate(clause, model="kokoro")
                if self.on_audio:
                    self.on_audio(bytes(audio))
            except Exception:
                if self.on_audio:
                    self.on_audio(clause.encode())
            return
        if self.on_audio:
            self.on_audio(clause.encode())

    def cancel(self) -> None:
        self.started.clear()

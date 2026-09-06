from __future__ import annotations

import os
from collections.abc import AsyncIterator
from dataclasses import dataclass

DEFAULT_MODEL = "Qwen3.5-9B-4bit"
DRAFT_MODEL = "Qwen3.5-2B"
VISION_MODEL = "Qwen3-VL-4B-4bit"
THINKING = False


@dataclass
class LlmSettings:
    conversation_model: str = DEFAULT_MODEL
    draft_model: str = DRAFT_MODEL
    vision_model: str = VISION_MODEL
    thinking: bool = THINKING
    backend: str = "echo"


def settings_from_env() -> LlmSettings:
    backend = os.environ.get("JARVIS_LLM", "echo")
    return LlmSettings(backend=backend, thinking=False)


class EchoBackend:
    """Deterministic stand-in until MLX weights are on disk."""

    name = "echo"

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        reply = prompt.strip() or "Ready."
        if not reply.endswith((".", "?", "!")):
            reply = f"{reply}."
        for word in reply.split(" "):
            yield word if word.endswith((".", "?", "!", ";")) else f"{word} "


class MlxBackend:
    name = "mlx"

    def __init__(self, settings: LlmSettings) -> None:
        self.settings = settings
        self._loaded = False

    def load(self) -> None:
        if self.settings.thinking:
            raise RuntimeError("thinking mode must stay off")
        try:
            import mlx_lm  # noqa: F401
        except ImportError as exc:
            raise RuntimeError("mlx-lm is not installed; keep JARVIS_LLM=echo") from exc
        self._loaded = True

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        if not self._loaded:
            self.load()
        # Weights are machine-local. Echo shape until a path is configured.
        path = os.environ.get("JARVIS_MLX_MODEL")
        if not path:
            echo = EchoBackend()
            async for tok in echo.stream(prompt):
                yield tok
            return
        from mlx_lm import load, stream_generate

        model, tokenizer = load(path)
        for out in stream_generate(model, tokenizer, prompt=prompt, max_tokens=256):
            yield out.text


def make_backend(settings: LlmSettings | None = None) -> EchoBackend | MlxBackend:
    cfg = settings or settings_from_env()
    if cfg.backend == "mlx":
        return MlxBackend(cfg)
    return EchoBackend()

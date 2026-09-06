from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from brain.clause import split_clauses
from brain.kv import MAX_KV_TOKENS, KvStore
from brain.prefix import PrefixCache
from brain.tiers import make_backend, settings_from_env


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    stream: bool = True
    model: str | None = None


def _count_tokens(text: str) -> int:
    return max(1, len(text.split()))


def create_app(kv: KvStore | None = None, prefix: PrefixCache | None = None) -> FastAPI:
    store = kv or KvStore(cap=MAX_KV_TOKENS)
    cache = prefix or PrefixCache()
    settings = settings_from_env()
    backend = make_backend(settings)
    app = FastAPI(title="jarvis-brain")

    @app.get("/v1/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "kv_tokens": store.tokens,
            "kv_cap": store.cap,
            "model": getattr(backend, "name", settings.conversation_model),
        }

    async def _stream(req: ChatRequest) -> AsyncIterator[bytes]:
        user = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
        store.append_turn("user", user, _count_tokens(user))
        system = next((m.content for m in req.messages if m.role == "system"), "")
        tools_json = json.dumps([m.model_dump() for m in req.messages if m.role == "tool"])
        if not cache.hit(system, tools_json):
            cache.warm(system, tools_json)

        t0 = time.perf_counter()
        first = True
        buf = ""
        emitted = 0
        async for tok in backend.stream(user):
            if first:
                ttft_ms = (time.perf_counter() - t0) * 1000
                yield f": llm_ttft {ttft_ms:.1f}\n\n".encode()
                first = False
            buf += tok
            clauses = split_clauses(buf)
            if len(clauses) > emitted + 1:
                for clause in clauses[emitted:-1]:
                    yield f": x-clause {json.dumps(clause)}\n\n".encode()
                    emitted += 1
            chunk = {
                "id": "jarvis",
                "object": "chat.completion.chunk",
                "choices": [{"index": 0, "delta": {"content": tok}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(chunk)}\n\n".encode()
        for clause in split_clauses(buf)[emitted:]:
            if clause.strip():
                yield f": x-clause {json.dumps(clause)}\n\n".encode()
        store.append_turn("assistant", buf, _count_tokens(buf))
        done = {
            "id": "jarvis",
            "object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(done)}\n\n".encode()
        yield b"data: [DONE]\n\n"

    @app.post("/v1/chat/completions", response_model=None)
    async def chat(req: ChatRequest) -> StreamingResponse | JSONResponse:
        if req.stream:
            return StreamingResponse(_stream(req), media_type="text/event-stream")
        user = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
        store.append_turn("user", user, _count_tokens(user))
        parts: list[str] = []
        async for tok in backend.stream(user):
            parts.append(tok)
        text = "".join(parts)
        store.append_turn("assistant", text, _count_tokens(text))
        return JSONResponse(
            {
                "id": "jarvis",
                "object": "chat.completion",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": text}}],
            }
        )

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("brain.server:app", host="127.0.0.1", port=8742, reload=False)


if __name__ == "__main__":
    main()

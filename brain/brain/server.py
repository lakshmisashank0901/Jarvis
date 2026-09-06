from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from brain.clause import split_clauses
from brain.kv import MAX_KV_TOKENS, KvStore
from brain.prefix import PrefixCache
from brain.tiers import make_backend, settings_from_env
from brain.turn import default_mcp, run_user_turn
from jarvis_mcp.server import JarvisMcp


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    stream: bool = True
    model: str | None = None
    confirmed: bool = False


def _count_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _sse_text(text: str, extra_comments: list[str]) -> AsyncIterator[bytes]:
    async def gen() -> AsyncIterator[bytes]:
        t0 = time.perf_counter()
        yield f": llm_ttft {(time.perf_counter() - t0) * 1000:.1f}\n\n".encode()
        for comment in extra_comments:
            yield f"{comment}\n\n".encode()
        buf = ""
        emitted = 0
        for word in text.split(" "):
            tok = word if word.endswith((".", "?", "!", ";")) else f"{word} "
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
        done = {
            "id": "jarvis",
            "object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(done)}\n\n".encode()
        yield b"data: [DONE]\n\n"

    return gen()


def create_app(
    kv: KvStore | None = None,
    prefix: PrefixCache | None = None,
    mcp: JarvisMcp | None = None,
) -> FastAPI:
    store = kv or KvStore(cap=MAX_KV_TOKENS)
    cache = prefix or PrefixCache()
    settings = settings_from_env()
    backend = make_backend(settings)
    tools = mcp or default_mcp()
    app = FastAPI(title="jarvis-brain")

    @app.get("/v1/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "kv_tokens": store.tokens,
            "kv_cap": store.cap,
            "model": getattr(backend, "name", settings.conversation_model),
            "tools": tools.tools(),
        }

    def _handle(req: ChatRequest) -> dict[str, Any]:
        user = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
        store.append_turn("user", user, _count_tokens(user))
        system = next((m.content for m in req.messages if m.role == "system"), "")
        tools_json = json.dumps(tools.tools())
        if not cache.hit(system, tools_json):
            cache.warm(system, tools_json)
        turn = run_user_turn(user, tools, confirmed=req.confirmed)
        store.append_turn("assistant", turn["spoken"], _count_tokens(turn["spoken"]))
        return turn

    @app.post("/v1/chat/completions", response_model=None)
    async def chat(req: ChatRequest) -> StreamingResponse | JSONResponse:
        turn = _handle(req)
        spoken = str(turn["spoken"])
        comments = [f": tool {json.dumps(turn['call'])}"]
        if turn["confirm"]:
            comments.append(f": confirm {json.dumps(turn['confirm'])}")
        if req.stream:
            return StreamingResponse(_sse_text(spoken, comments), media_type="text/event-stream")
        return JSONResponse(
            {
                "id": "jarvis",
                "object": "chat.completion",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": spoken}}],
                "jarvis": turn,
            }
        )

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("brain.server:app", host="127.0.0.1", port=8742, reload=False)


if __name__ == "__main__":
    main()

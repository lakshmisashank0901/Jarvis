from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, Literal

import httpx

BRAIN_URL = "http://127.0.0.1:8742"

Kind = Literal["ttft", "clause", "token", "confirm"]


class BrainClient:
    def __init__(self, base_url: str = BRAIN_URL) -> None:
        self.base_url = base_url.rstrip("/")

    async def health(self) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{self.base_url}/v1/health")
            res.raise_for_status()
            return res.json()

    async def stream_chat(
        self, user_text: str, *, confirmed: bool = False
    ) -> AsyncIterator[tuple[Kind, str]]:
        payload = {
            "messages": [{"role": "user", "content": user_text}],
            "stream": True,
            "confirmed": confirmed,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                json=payload,
            ) as res:
                res.raise_for_status()
                async for line in res.aiter_lines():
                    if not line:
                        continue
                    if line.startswith(": llm_ttft "):
                        yield "ttft", line.split(" ", 2)[2]
                        continue
                    if line.startswith(": x-clause "):
                        yield "clause", json.loads(line[len(": x-clause ") :])
                        continue
                    if line.startswith(": confirm "):
                        yield "confirm", line[len(": confirm ") :]
                        continue
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    tok = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                    if tok:
                        yield "token", tok

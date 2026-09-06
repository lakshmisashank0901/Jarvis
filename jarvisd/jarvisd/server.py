from __future__ import annotations

import asyncio
import json
from typing import Any

from websockets.asyncio.server import ServerConnection, serve

from jarvisd.brain_client import BrainClient
from jarvisd.pipeline import run_text_turn
from jarvisd.tts_clause import ClauseTts
from jarvisd.ws import HudState, WS_URL, make_hud, parse_app_message

HOST = "127.0.0.1"
PORT = 8741


class Session:
    def __init__(self, ws: ServerConnection) -> None:
        self.ws = ws
        self.brain = BrainClient()
        self.tts = ClauseTts()
        self.pending_confirm: dict[str, Any] | None = None

    async def send(self, payload: dict[str, Any]) -> None:
        await self.ws.send(json.dumps(payload))

    async def handle(self, raw: str) -> None:
        msg = parse_app_message(raw)
        if msg["t"] == "hotkey" and msg.get("name") == "cancel":
            self.tts.cancel()
            await self.send(make_hud(HudState.idle).to_json())
            return
        if msg["t"] == "hotkey" and msg.get("name") == "ptt_down":
            await self.send(make_hud(HudState.listening).to_json())
            return
        if msg["t"] == "confirm":
            self.pending_confirm = msg
            return


async def handler(ws: ServerConnection) -> None:
    session = Session(ws)
    await session.send(make_hud(HudState.idle).to_json())
    async for raw in ws:
        text = raw if isinstance(raw, str) else raw.decode()
        data = json.loads(text)
        if data.get("t") == "dev_text":
            events: list[dict[str, Any]] = []

            def emit(payload: dict[str, Any], bucket: list[dict[str, Any]] = events) -> None:
                bucket.append(payload)

            await run_text_turn(data["text"], session.brain, session.tts, emit)
            for ev in events:
                await session.send(ev)
            continue
        await session.handle(text)


async def main() -> None:
    async with serve(handler, HOST, PORT):
        await asyncio.Future()


if __name__ == "__main__":
    print(f"jarvisd ws {WS_URL}", flush=True)
    asyncio.run(main())

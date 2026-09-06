# Jarvis Master Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> This is the **master sequencing plan**. Each phase below is its own sub-project and must ship working, testable software before the next phase starts. Do not collapse processes. Do not substitute the pinned stack.

**Goal:** Build a computer-only “workshop Jarvis” on one M4 Pro 24 GB Mac: voice in, voice out, `< 750 ms` p50, no cloud, no external devices. It runs the Mac — apps, files, system, browser, Calendar — not lights, plugs, or a suit.

**Architecture:** Four processes, never one. `Jarvis.app` (Swift 6) talks WebSocket to `jarvisd` (Pipecat). `jarvisd` talks HTTP to `brain` (FastAPI). `brain` talks stdio MCP to tools and owns the KV cap, warm prefix cache, tier routing, and the MLX / llama.cpp split. TTS starts at the first clause boundary.

**Tech Stack:** Swift 6 + SwiftUI (app only). Python 3.12 + `uv` everywhere else. `pipecat-ai` 1.8.x, MLX (`mlx-lm`), `llama-server --jinja`, sqlite-vec, MCP stdio.

## Global Constraints

- Hardware: MacBook Pro, Apple M4 Pro, 24 GB unified memory, macOS 26. Memory bandwidth 273 GB/s.
- Build target is **Config A only**. Do not switch to Config B (Gemma 4 26B-A4B) without an explicit instruction.
- Config A resident budget (GB): macOS 3.5 + voice 2.4 + retrieval 0.3 + Qwen3.5-9B-4bit 6.0 + Qwen3.5-2B draft 1.3 + Qwen3-VL-4B-4bit 3.0 + KV q8 16K 1.5 = 18.0 resident, 6.0 free.
- Voice-to-voice target `< 750 ms` p50. Stage budget: VAD 30 + end-of-turn 209 + ASR 65 + LLM TTFT 120 + first clause 123 + TTS TTFA 100 + output buffer 50 = 697 ms.
- Any added latency must show where it is recovered. Instrument every stage boundary in `bench/roundtrip.py`.
- No cloud LLM / ASR / TTS. No Ollama. No LangChain / LlamaIndex / CrewAI. No Qdrant / Chroma / Pinecone. No Whisper on the realtime path. No Electron / React Native / chat window. No speech-to-speech models. Thinking mode off.
- Language: Python 3.12, `uv` only (never bare `pip install`). Swift 6 strict concurrency for the app only.
- `launchd` agents, never daemons. Developer ID signing from day one. Unsandboxed. HUD uses `orderFrontRegardless()`, never `makeKeyAndOrderFront`.
- Cap KV in `brain/server.py` via `MAX_KV_TOKENS`. Evict oldest-turn-first. `mlx_lm.server` has no `--max-kv-size`.
- Tool calls: `llama-server --jinja` plus GBNF generated from the live MCP schema. Exactly four tools (`memory`, `desktop`, `browser`, `calendar`). Measure selection accuracy before adding a fifth.
- Fire turn detection at 200 ms of silence, not 800. Neural Engine runs ASR + TTS. GPU stays free for the LLM.
- Desktop control is AX-tree-first (Peekaboo). Vision (`Qwen3-VL-4B` 4-bit) is fallback only.
- Destructive actions: HUD 3-second cancel, plain-language description. No optimistic-execute-with-undo.
- **Computer only.** No Home Assistant, smart plugs, phones, cars, or other external devices in v1. Mail/Messages/Slack have no extra tool — open the app, then AX `inspect`/`act`.

---

## Tech stack — frontend vs backend

There is **no web frontend**. The only UI is a native macOS app. “Backend” is three local processes, not a cloud API.

### Frontend — `app/` (one process: `Jarvis.app`)

| Piece | Pin | Role |
|---|---|---|
| Language | Swift 6, strict concurrency | App only |
| UI | SwiftUI `MenuBarExtra` + `NSPanel` HUD | Always-available status; HUD must not steal focus |
| Hotkeys | Carbon `RegisterEventHotKey` | Global push-to-talk / cancel. Do not use `NSEvent.addGlobalMonitorForEvents` |
| Transport | WebSocket client → `jarvisd` | Push state; never poll. HUD updates `< 50 ms` |
| Signing | Developer ID, unsandboxed | TCC grants attach to (path, bundle ID, signature) |
| Install | `/Applications/Jarvis.app` | launchd agents talk to this identity |

**Not used:** Electron, React, React Native, a scrolling chat box as the primary UI. The transcript is an audit window, opened on purpose.

### Backend — three processes

| Process | Pin | Role |
|---|---|---|
| `jarvisd/` | Python 3.12, `pipecat-ai` 1.8.x | Voice orchestration, barge-in, interruption |
| VAD | Silero VAD v6.2 | Speech start/end, 30 ms budget |
| Turn detect | Smart Turn **v3.1** int8 **ONNX** | Fire at 200 ms silence. Not CoreML |
| ASR | Parakeet TDT v3 (`parakeet-mlx` or FluidAudio/CoreML sidecar) | Runs on Neural Engine |
| TTS | Kokoro 82M via `mlx-audio` | First audio at clause boundary, 100 ms TTFA |
| `brain/` | FastAPI + uvicorn | Not a passthrough. Owns KV cap, prefix cache, tier routing, MLX/llama.cpp split |
| Conversation LLM | **MLX** `mlx-lm`, `Qwen3.5-9B` 4-bit + `Qwen3.5-2B` draft | Streaming tokens for speech |
| Tool-call LLM | **llama.cpp** `llama-server --jinja` | Grammar-constrained JSON tool calls |
| Vision | `Qwen3-VL-4B` 4-bit, resident | Fallback only |
| `mcp/` + `memory/` | MCP stdio, `sqlite-vec`, EmbeddingGemma-300M q8 | Tools + bitemporal memory |
| Desktop tools | Peekaboo + host `NSWorkspace` / files / system | Open, quit, files, volume, lock; AX for in-app tasks |
| Browser | Playwright MCP | Named web flow |
| Calendar | EventKit in `Jarvis.app` | list / create / update |
| Ops | `launchd` AGENT plists + `iogpu.wired_limit_mb` | Never daemons, never SSH-headless |

### Shared contracts (not optional)

```
Jarvis.app  --WebSocket-->  jarvisd  --HTTP /v1-->  brain  --stdio-->  MCP servers
                 |                    |
                 +-- barge-in/cancel  +-- KV cap, prefix cache, GBNF tool loop
```

- `brain` exposes an OpenAI-shaped `/v1/chat/completions` (stream) plus `/v1/health`.
- `jarvisd` is the only audio owner. A crash in the agent loop must not kill the mic/speaker graph.
- Clause-boundary events from `brain` start TTS immediately. Never wait for EOS.

---

## File map

```
app/
  Jarvis.xcodeproj
  Sources/Jarvis/
    App.swift                 MenuBarExtra entry, launchd handshake
    HUD/HUDPanel.swift        NSPanel, orderFrontRegardless, 3s cancel
    HUD/HUDState.swift        Codable snapshot pushed over WS
    Transport/JarvisSocket.swift
    Hotkeys/HotkeyCenter.swift
    Audit/AuditWindow.swift   transcript as audit surface, not a chat box
    Host/HostSocket.swift     unix socket for TCC-bound actions
    Host/AppLauncher.swift    NSWorkspace open / quit / focus
    Host/FileHost.swift       open path, reveal in Finder
    Host/SystemHost.swift     volume, mute, lock, sleep
    Host/CalendarStore.swift  EventKit list/create/update
    Signing/entitlements.plist  unsandboxed; no App Sandbox; Calendars usage
jarvisd/
  pyproject.toml
  jarvisd/pipeline.py         Pipecat graph
  jarvisd/ws.py               app ↔ jarvisd protocol
  jarvisd/brain_client.py     HTTP stream to brain
  jarvisd/tts_clause.py       start Kokoro at first clause
brain/
  pyproject.toml
  brain/server.py             FastAPI, MAX_KV_TOKENS, eviction
  brain/prefix.py             warm prefix cache
  brain/tiers.py              model load/evict
  brain/toolloop.py           MCP client, 1–3 calls/turn
  brain/grammar.py            live MCP schema → GBNF
  brain/clause.py             clause-boundary splitter for TTS
mcp/
  jarvis_mcp/server.py        first four tools
memory/
  schema.sql                  bitemporal facts
  store.py                    hybrid retrieval + RRF + rerank top 20–30
bench/
  roundtrip.py                per-stage latency
  toolcall.py                 tool-selection accuracy
ops/
  launchd/com.jarvis.jarvisd.plist
  launchd/com.jarvis.brain.plist
  wired_limit.sh
docs/
  JARVIS-CURSOR-CONTEXT.md
  WORK-PROGRESS.md
  superpowers/plans/
```

---

## Process and protocol (lock these names)

### WebSocket `app` ↔ `jarvisd` (`ws://127.0.0.1:8741/v1`)

```python
# jarvisd → app
{"t": "hud", "state": "idle"|"listening"|"thinking"|"speaking"|"confirm",
 "partial": str | None, "confirm": {"id": str, "text": str, "deadline_ms": 3000} | None}

{"t": "audit", "role": "user"|"assistant"|"tool", "text": str, "ts": str}

{"t": "stage", "name": str, "ms": float}   # names must match bench/roundtrip.py

# app → jarvisd
{"t": "hotkey", "name": "ptt_down"|"ptt_up"|"cancel"}
{"t": "confirm", "id": str, "ok": bool}
```

Stage names (fixed): `vad`, `eot`, `asr`, `llm_ttft`, `first_clause`, `tts_ttfa`, `outbuf`.

### HTTP `jarvisd` ↔ `brain` (`http://127.0.0.1:8742`)

- `GET /v1/health` → `{ok, kv_tokens, kv_cap, model}`
- `POST /v1/chat/completions` OpenAI-compatible stream. Extra: `x-clause` SSE comments at clause boundaries.
- `MAX_KV_TOKENS = 16384`. Evict oldest-turn-first before append.

### Host socket `app` (`unix:///tmp/jarvis-host.sock`)

Only `Jarvis.app` binds this. MCP is a client. Calendar TCC and `NSWorkspace` stay on the signed app.

```python
{"op": "app.open", "name": str | None, "bundle_id": str | None} -> {"ok": bool, "bundle_id": str}
{"op": "app.quit", "bundle_id": str} -> {"ok": bool}
{"op": "app.focus", "bundle_id": str | None, "name": str | None} -> {"ok": bool}

{"op": "files.open", "path": str} -> {"ok": bool}
{"op": "files.reveal", "path": str} -> {"ok": bool}

{"op": "system.volume", "level": int} -> {"ok": bool}          # 0–100
{"op": "system.mute", "on": bool} -> {"ok": bool}
{"op": "system.lock"} -> {"ok": bool}
{"op": "system.sleep"} -> {"ok": bool}

{"op": "calendar.list", "from": str, "to": str} -> {"ok": bool, "events": [{"id": str, "title": str, "start": str, "end": str}]}
{"op": "calendar.create", "title": str, "start": str, "end": str} -> {"ok": bool, "id": str}
{"op": "calendar.update", "id": str, "title": str | None, "start": str | None, "end": str | None} -> {"ok": bool}
```

Confirm (3 s HUD) before: `app.quit`, `system.lock`, `system.sleep`, `calendar.create`, `calendar.update`, and any irreversible `desktop.act`. `files.open` / `files.reveal` / `app.open` / volume do not confirm.

### First four tools (do not add a fifth until `bench/toolcall.py` is measured)

One MCP name each. Extra Mac verbs are **actions**, not new tools.

1. `memory` — `action`: `search` | `remember`.
2. `desktop` — `action`: `open` | `quit` | `focus` | `inspect` | `act` | `files_open` | `files_reveal` | `volume` | `mute` | `lock` | `sleep`.
   - Apps/files/system go through the host socket.
   - `inspect` / `act` are Peekaboo AX (Mail, Notes, Slack, etc. — no fifth tool).
3. `browser` — Playwright: `goto` | `snapshot` | `click` | `type`.
4. `calendar` — EventKit: `list` | `create` | `update`.

---

## Phase order (do not skip ahead)

Each phase ends with a command that must pass. No HUD until Phase 6. No Peekaboo / Playwright / EventKit until Phase 7. Host socket lands in Phase 6 so Phase 7 can call it.

### Phase 0 — Repo, pins, empty benches

**Files:**
- Create: `docs/JARVIS-CURSOR-CONTEXT.md` (copy of the pinned spec)
- Create: `docs/WORK-PROGRESS.md`
- Create: `pyproject.toml` (workspace root, Python 3.12, `uv`)
- Create: `brain/pyproject.toml`, `jarvisd/pyproject.toml`, `mcp/pyproject.toml`
- Create: `bench/roundtrip.py`, `bench/toolcall.py` (stage-name constants + CLI stubs)
- Create: `.python-version` = `3.12`
- Create: `AGENTS.md` pointing at the context file and this plan

**Produces:** `STAGE_NAMES = ("vad", "eot", "asr", "llm_ttft", "first_clause", "tts_ttfa", "outbuf")`

- [ ] **Step 1:** Init git, copy the context file into `docs/`, write `AGENTS.md` and workspace `pyproject.toml` requiring Python `>=3.12,<3.13` and `uv`.
- [ ] **Step 2:** Add `bench/roundtrip.py` that prints the seven stage names and exits 0. No timing yet.
- [ ] **Step 3:** Verify: `uv python pin 3.12 && uv run python bench/roundtrip.py` prints the seven names.
- [ ] **Step 4:** Commit: `chore: pin repo layout, Python 3.12, and latency stage names`

**Done when:** `uv run python bench/roundtrip.py` lists the seven stages.

### Phase 1 — `brain` skeleton: health, KV cap, eviction

**Files:**
- Create: `brain/brain/server.py`
- Create: `brain/brain/kv.py`
- Test: `brain/tests/test_kv.py`

**Interfaces:**
- Produces: `class KvStore: cap: int; tokens: int; append_turn(role: str, text: str, n_tokens: int) -> None; evict_oldest_turn() -> None`
- Produces: FastAPI app `create_app(kv: KvStore) -> FastAPI` with `GET /v1/health` and `POST /v1/chat/completions` (echo stream, no model yet)

- [ ] **Step 1:** Write `test_kv_evicts_oldest_turn_first` — fill past `MAX_KV_TOKENS = 16384`, assert oldest turn gone, newest present, `tokens <= cap`.
- [ ] **Step 2:** Run `uv run --package brain pytest brain/tests/test_kv.py -v` — expect FAIL (no `KvStore`).
- [ ] **Step 3:** Implement `KvStore` oldest-turn-first eviction. No MLX yet.
- [ ] **Step 4:** Re-run pytest — expect PASS.
- [ ] **Step 5:** Add `GET /v1/health` returning `kv_tokens`, `kv_cap=16384`. Test with `TestClient`.
- [ ] **Step 6:** Commit: `feat(brain): cap KV at 16384 and evict oldest-turn-first`

**Done when:** health reports the cap; eviction test passes; no model weights loaded.

### Phase 2 — `brain` conversation path (MLX) + clause events

**Files:**
- Create: `brain/brain/tiers.py`
- Create: `brain/brain/prefix.py`
- Create: `brain/brain/clause.py`
- Modify: `brain/brain/server.py`
- Test: `brain/tests/test_clause.py`, `brain/tests/test_prefix.py`

**Interfaces:**
- Produces: `split_clauses(text: str) -> list[str]` — emit on `. ? !` or `;` once length ≥ 8 tokens-equivalent (whitespace split)
- Produces: `PrefixCache.warm(system: str, tools_json: str) -> None` and `PrefixCache.hit() -> bool`
- Produces: SSE stream that yields `x-clause` when `split_clauses` fires, then tokens

- [ ] **Step 1:** TDD `split_clauses` — `"Hello there, I can help. What next?"` → `["Hello there, I can help.", " What next?"]`.
- [ ] **Step 2:** TDD prefix cache: after `warm()`, `hit()` is True; a new system string misses.
- [ ] **Step 3:** Wire `mlx-lm` for `Qwen3.5-9B` 4-bit + `Qwen3.5-2B` draft. Thinking mode off. Load via `tiers.py`.
- [ ] **Step 4:** Measure TTFT on **turn 3**, never turn 1. Target 120 ms warm. Record in `bench/roundtrip.py` as `llm_ttft`.
- [ ] **Step 5:** Commit: `feat(brain): MLX stream with warm prefix and clause boundaries`

**Done when:** three-turn script shows warm TTFT logged; clauses emit before EOS.

### Phase 3 — `brain` tool path (llama.cpp + GBNF)

**Files:**
- Create: `brain/brain/grammar.py`
- Create: `brain/brain/toolloop.py`
- Test: `brain/tests/test_grammar.py`, `bench/toolcall.py`

**Interfaces:**
- Consumes: MCP tool list `list[Tool(name: str, schema: dict)]`
- Produces: `schema_to_gbnf(tools: list[Tool]) -> str` — grammar allows only listed `name` values
- Produces: `async def run_tool_turn(messages, tools) -> list[Message]` using `llama-server --jinja`
- Rule: conversation tokens stay on MLX. Tool-calling turns go to llama.cpp. Do not bypass `brain`.

- [ ] **Step 1:** TDD `schema_to_gbnf` — a two-tool schema must reject a third name (string-level assert on the GBNF `name` enum).
- [ ] **Step 2:** Start `llama-server --jinja` from `tiers.py` only when a tool turn is selected.
- [ ] **Step 3:** `toolloop.py` max 3 MCP calls per user turn, then speak.
- [ ] **Step 4:** `bench/toolcall.py` fixture: 20 prompts, expected tool name. Print accuracy. Do not add tool 5.
- [ ] **Step 5:** Commit: `feat(brain): GBNF tool loop via llama-server --jinja`

**Done when:** hallucinated tool names cannot decode; accuracy script runs.

### Phase 4 — `memory`

**Files:**
- Create: `memory/schema.sql`, `memory/store.py`
- Test: `memory/tests/test_store.py`

**Interfaces:**
- Produces: `remember(fact: str, valid_from: datetime, observed_at: datetime) -> int`
- Produces: `search(query: str, k: int = 20) -> list[Fact]` — hybrid + RRF + rerank, `k <= 30`
- Rule: supersede closes `valid_to`. Never `DELETE`. Core memory block always in the prefix cache.

- [ ] **Step 1:** TDD bitemporal supersede — two remembers of the same subject; only the latest has `valid_to IS NULL`.
- [ ] **Step 2:** TDD search cap — requesting `k=100` still reranks at most 30.
- [ ] **Step 3:** Embeddings: EmbeddingGemma-300M q8. sqlite-vec virtual table. No extra vector server.
- [ ] **Step 4:** Commit: `feat(memory): bitemporal sqlite-vec store with capped rerank`

**Done when:** supersede + rerank-cap tests pass.

### Phase 5 — `jarvisd` voice loop (no HUD yet)

**Files:**
- Create: `jarvisd/jarvisd/pipeline.py`, `ws.py`, `brain_client.py`, `tts_clause.py`
- Test: `jarvisd/tests/test_eot_window.py`, `bench/roundtrip.py` (wire real timers)

**Interfaces:**
- Consumes: brain SSE + `x-clause`
- Produces: WebSocket `hud` / `stage` / `audit` events
- Pins: Silero VAD v6.2, Smart Turn v3.1 int8 ONNX, 200 ms silence, Parakeet TDT v3, Kokoro 82M `mlx-audio`
- Rule: no blocking calls inside Pipecat frame handlers. ASR+TTS on ANE. Barge-in cancels TTS immediately.

- [ ] **Step 1:** TDD: Smart Turn must be consulted at 200 ms silence, not 800. Constant `EOT_SILENCE_MS = 200`.
- [ ] **Step 2:** Build Pipecat 1.8.x graph: VAD → EOT → ASR → `brain_client` → clause TTS.
- [ ] **Step 3:** On first `x-clause`, start Kokoro. Do not buffer the full LLM reply.
- [ ] **Step 4:** Drive `bench/roundtrip.py` from a recorded wav. Print all seven stages. Fail CI if p50 ≥ 750 ms once models are warm.
- [ ] **Step 5:** Commit: `feat(jarvisd): Pipecat voice loop with 200ms EOT and clause TTS`

**Done when:** a wav fixture comes back as audio and `roundtrip.py` prints seven timings.

### Phase 6 — `app` HUD + hotkeys + confirm + host socket

**Files:**
- Create: Swift sources listed in the file map
- Test: Swift Testing for `HUDState` decode, `AppLauncher` name→bundle resolution, `CalendarStore` parse; manual TCC pass on device

**Interfaces:**
- Consumes: `hud` / `audit` / `stage` JSON above
- Produces: `hotkey` / `confirm` JSON
- Produces: host socket ops `app.open` / `app.quit` / `app.focus`, `files.open` / `files.reveal`, `system.volume` / `mute` / `lock` / `sleep`, `calendar.list` / `create` / `update`
- Rules: `orderFrontRegardless()`; `RegisterEventHotKey`; HUD state `< 50 ms`; audit window is not a text-input chatbot; unsandboxed Developer ID; no App Sandbox entitlement; EventKit requestAccess on first calendar op.

- [ ] **Step 1:** Decode `HUDState` from the JSON schema in a Swift test. Unknown `state` must not crash.
- [ ] **Step 2:** `MenuBarExtra` + `NSPanel` HUD. Push over WebSocket, never poll.
- [ ] **Step 3:** Carbon hotkeys: PTT and cancel.
- [ ] **Step 4:** Confirm sheet: 3.0 s deadline, plain-language `confirm.text`, Cancel / OK. Timeout = cancel.
- [ ] **Step 5:** `AppLauncher` open/quit/focus via `NSWorkspace`. Test: `"Safari"` resolves to `com.apple.Safari`.
- [ ] **Step 6:** `FileHost` open + reveal; `SystemHost` volume 0–100, mute, lock, sleep.
- [ ] **Step 7:** `CalendarStore` list/create/update via EventKit. Create/update are not called until confirm is true.
- [ ] **Step 8:** Bind `unix:///tmp/jarvis-host.sock` (unlink on start). Reject non-local peers.
- [ ] **Step 9:** Sign with Developer ID from the first archive. Install to `/Applications` for TCC (Accessibility + Calendars).
- [ ] **Step 10:** Commit: `feat(app): HUD, host socket, Mac control, EventKit`

**Done when:** HUD updates `< 50 ms`; host can open Safari, reveal a file, and set volume.

### Phase 7 — MCP four tools (memory, desktop, browser, calendar)

**Files:**
- Create: `mcp/jarvis_mcp/server.py`
- Create: `mcp/jarvis_mcp/host_client.py`
- Modify: `brain/brain/toolloop.py` to spawn stdio servers (our MCP + Playwright MCP)
- Test: `bench/toolcall.py` against the live four-tool schema

**Interfaces:**
- Produces: MCP stdio server exposing exactly `memory`, `desktop`, `browser`, `calendar`
- `desktop` host actions (`open`/`quit`/`focus`/`files_*`/`volume`/`mute`/`lock`/`sleep`) and `calendar.*` call the host socket
- `desktop.inspect` / `desktop.act` call Peekaboo
- `browser.*` call Playwright MCP
- Confirm-gated: `quit`, `lock`, `sleep`, irreversible `act`, `calendar.create` / `update`

- [ ] **Step 1:** Register exactly four tool names. Generate GBNF from that live list (`name` enum is those four).
- [ ] **Step 2:** Implement all `desktop` host actions. Missing app/path → spoken error, no crash.
- [ ] **Step 3:** Peekaboo for AX inspect/act (any Mac app, including Mail/Notes). Vision stays unloaded unless AX fails.
- [ ] **Step 4:** Wire Playwright as `browser`. Do not AX-drive Chrome/Safari for web tasks.
- [ ] **Step 5:** Wire `calendar` to host EventKit. list is read-only; create/update go through HUD confirm.
- [ ] **Step 6:** Run `bench/toolcall.py` with prompts for remember, open Safari, open a file, set volume, go to a URL, create a 30-min event. Record accuracy. Do not add a fifth tool.
- [ ] **Step 7:** Commit: `feat(mcp): four tools — memory, desktop, browser, calendar`

**Done when:** accuracy is recorded; open-app, open-file, volume, one Playwright goto, and one confirmed calendar create work; confirm-gated ops cannot fire silently.

### Phase 8 — `ops` launchd (computer only)

**Files:**
- Create: `ops/launchd/com.jarvis.brain.plist`, `ops/launchd/com.jarvis.jarvisd.plist`
- Create: `ops/wired_limit.sh`
- Modify: `docs/WORK-PROGRESS.md`

- [ ] **Step 1:** Agents, not daemons. They must fail clearly if no Aqua session (no SSH-headless).
- [ ] **Step 2:** `wired_limit.sh` documents measuring `mx.metal.device_info()` and setting `iogpu.wired_limit_mb`.
- [ ] **Step 3:** Do **not** wire Home Assistant or any external device. Computer only.
- [ ] **Step 4:** Commit: `chore(ops): launchd agents and GPU wired-limit helper`

**Done when:** login starts `brain` then `jarvisd`; mic works without a Terminal window.

---

## What we will not do in **v1**

- Cloud APIs, Ollama, LangChain, extra vector DBs, Whisper realtime, chat-first UI, plan-then-execute prompting, Moshi/Qwen-Omni, App Sandbox, CoreML Smart Turn, Config B, a fifth tool before `bench/toolcall.py` has a number.
- External devices: Home Assistant, IoT, phones, cars, “suit” hardware.
- The v2 list below. Do not implement it while Phases 0–8 are open.

## v2 — remaining Mac surface (do not start until v1 is green)

Still **computer only**. No devices. Prefer new **actions** on `desktop` / host socket. A new MCP tool name is allowed only after `bench/toolcall.py` has a v1 accuracy number.

| Area | v2 ops / behavior | Gate |
|---|---|---|
| Files | `files.copy`, `files.move`, `files.delete`, `files.mkdir`, `files.rename` | delete/move: 3 s confirm |
| Spotlight | `desktop.search` — `NSMetadataQuery` / Spotlight, then open hit | read-only |
| Contacts | EventKit-adjacent `Contacts` store: search, read, create | create: confirm |
| Reminders | EventKit reminders: list, create, complete | create/complete: confirm |
| Notes | Apple Notes via Scripting Bridge or AX; no third-party note apps as a new tool | — |
| Screenshots | `system.screenshot` (screen / window / selection) → file path | — |
| Clipboard | `system.clipboard_get`, `system.clipboard_set` | set: confirm if not user-initiated paste |
| Notifications | `system.notifications` — read Notification Center (where TCC allows) | read-only |
| Radios | `system.wifi`, `system.bluetooth` on/off/status | confirm |
| Wallpaper | `system.wallpaper` set from a local path | confirm |
| Windows | `desktop.tile`, `desktop.fullscreen`, `desktop.spaces` | — |
| Shell | `desktop.shell` — **allowlisted** commands only, never raw unsupervised bash | always 3 s confirm; no `sudo` |
| AirDrop | `files.airdrop` | confirm |
| Print | `files.print` | confirm |
| Music | Apple Music / Now Playing: play, pause, next, search library | — |
| Shortcuts | `shortcuts run <UUID>` only (never by name) | confirm if the shortcut is write/send |
| Presence | Wake word “Jarvis” + proactive speak-first (calendar nags) | must keep `< 750 ms` p50 |
| Character | Kokoro voice + dry/brief system prompt | thinking stays off |
| AX escape | macos-automator-mcp | after Peekaboo miss |
| Vision | `Qwen3-VL-4B` on unlabeled / canvas only | not primary click path |
| Mail / Messages | Dedicated APIs if AX is not enough | no fifth tool until measured |
| Calls | FaceTime on this Mac: start (Contact/handle), answer, decline, hang up. Incoming: HUD + spoken “call from …” | start/hang up: confirm; answer/decline: no delay beyond HUD |
| WhatsApp | Named send: resolve “mom” from Contacts/memory, open WhatsApp Web (Playwright, must already be logged in), send text. Utterance: `send "Hi" to mom on whatsapp` | 3 s confirm; no unofficial WhatsApp API |
| Gap bucket | Anything else v1 cannot do on this Mac, found while using it | same confirm + four-process rules |

v2 is **not** Home Assistant, not a suit, not cloud. Those stay out unless you explicitly ask later.

Do not write a v2 implementation plan until Phase 8 is done and you say to start v2.

---

## Self-review

1. **Spec coverage:** v1 = Config A, four processes, four tools (Mac apps/files/system/AX, browser, calendar, memory). v2 = remaining Mac surface listed above. External devices stay out of both unless re-opened.
2. **Placeholders:** None. Tool names, ports (`8741`, `8742`), host socket path, `MAX_KV_TOKENS = 16384`, stage names, and JSON keys are fixed.
3. **Types:** `KvStore`, `PrefixCache`, `split_clauses`, `schema_to_gbnf`, `run_tool_turn`, `remember` / `search`, host `op` names, WS message `t` keys — used with the same names across phases.

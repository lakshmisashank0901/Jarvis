# JARVIS — Project Context for Cursor

> Fully local voice-first assistant. This file tells Cursor how the project is built,
> what is pinned, and what it must never suggest. Read before writing any code.

Fully local, voice-first personal assistant. Runs entirely on one MacBook Pro.
**No cloud inference. Ever.** If a task seems to need a cloud model, say so and stop — do not add one.

## Hardware contract

| | |
|---|---|
| Machine | MacBook Pro, Apple **M4 Pro**, **24 GB** unified memory, macOS 26 |
| Memory bandwidth | **273 GB/s** — decode is memory-bound; this is the ceiling |
| GPU wired limit | ~15.8–18.0 GB (measure with `mx.metal.device_info()`; raise via `iogpu.wired_limit_mb`) |
| Neural Engine | Runs ASR + TTS. Keep the GPU free for the LLM. |

Decode ceiling: `tok/s ≈ 273 × 0.75 / active_weight_GB`. Use this before proposing any model.

## Memory budget — Config A (the one we build)

Total 24.0 GB. Do not propose anything that breaks this.

```
macOS + apps        3.5
voice pipeline      2.4   (ANE)
retrieval           0.3
Qwen3.5-9B 4-bit    6.0
Qwen3.5-2B draft    1.3
Qwen3-VL-4B 4-bit   3.0   (resident, vision fallback)
KV cache q8 16K     1.5   (HARD CAPPED)
────────────────────────
resident           18.0
free                6.0
```

Config B (Gemma 4 26B-A4B, 15.0 GB, no vision/draft, 1.3 GB free) exists but is not the build target. Do not switch to it without an explicit instruction.

## Latency budget — this is a contract, not an aspiration

Voice-to-voice target **< 750 ms p50**. Current allocation:

```
 30 ms  VAD + buffering
209 ms  end-of-turn  (200 ms silence window + Smart Turn inference)
 65 ms  ASR finalization
120 ms  LLM TTFT (warm prefix cache)
123 ms  first clause (~8 tok @ ~65 tok/s)
100 ms  TTS time-to-first-audio
 50 ms  output buffer
───────
697 ms
```

Any change that adds latency to a stage must show where it is recovered. Instrument every stage boundary in `bench/roundtrip.py`.

## Pinned stack — do not substitute

| Layer | Use |
|---|---|
| Language | Python **3.12**, `uv` for envs. Swift 6 for the app only. |
| Voice orchestration | `pipecat-ai` 1.8.x |
| VAD | Silero VAD v6.2 |
| Turn detection | Smart Turn **v3.1** int8 (ONNX, not CoreML — the CoreML analyzer is deprecated) |
| ASR | Parakeet TDT v3 (`parakeet-mlx`, or FluidAudio/CoreML in the sidecar) |
| TTS | Kokoro 82M via `mlx-audio` |
| LLM runtime | **MLX** (`mlx-lm`) for conversation; **llama.cpp** (`llama-server --jinja`) for tool-calling turns |
| Reasoner | `Qwen3.5-9B` 4-bit + `Qwen3.5-2B` draft |
| Vision | `Qwen3-VL-4B` 4-bit — fallback only |
| Embeddings | EmbeddingGemma-300M q8 |
| Vector store | `sqlite-vec` |
| Tool protocol | **MCP** over stdio |
| Desktop control | Peekaboo (MCP) → macos-automator-mcp (escape hatch) → Playwright MCP (web) |
| Home | Home Assistant, `llama.cpp` integration pointed at our `/v1` |
| App shell | SwiftUI `MenuBarExtra` + `NSPanel` HUD |

## Architecture invariants

1. **Four processes, never one.** `Jarvis.app` (Swift) ↔ WebSocket ↔ `jarvisd` (Pipecat) ↔ HTTP ↔ `brain` (FastAPI) ↔ stdio ↔ MCP servers. A crash in the agent loop must not kill audio.
2. **Desktop control is AX-tree-first.** Use the Accessibility API for reading and acting. Vision is a fallback for canvas apps and unlabeled controls only. Never propose screenshot→VLM→click as the primary path.
3. **`brain` is not a passthrough.** It owns: the KV cap, the warm prefix cache, tier routing, and the MLX/llama.cpp split. Do not bypass it.
4. **TTS starts at the first clause boundary.** Never wait for a complete LLM response.
5. **The app owns TCC.** Grants attach to (path, bundle ID, signature). Everything that needs Accessibility runs under the signed app's identity.

## Non-negotiables

- **Cap the KV cache.** `mlx_lm.server` has no `--max-kv-size`; unbounded growth kernel-panics the machine. Enforce `MAX_KV_TOKENS` in `brain/server.py` and evict oldest-turn-first.
- **`--jinja` on `llama-server`** for every tool-calling turn. Without it you get prose, not JSON.
- **Grammar-constrained decoding for all tool calls.** Generate GBNF from the live MCP schema. Hallucinated tool names are the dominant local-model failure and this is the fix.
- **Warm prefix cache** for system prompt + tool schemas. Cold prefill is ~4 s. Verify TTFT on turn 3, never turn 1.
- **Fire turn detection at 200 ms of silence.** Not 800. This is 30% of the latency budget.
- **launchd agents, never daemons.** Nothing here works headless or over SSH.
- **Developer ID signing from day one.** Ad-hoc signatures destroy TCC grants on every rebuild.
- **Unsandboxed.** A sandboxed app cannot hold Accessibility control of other apps. Do not add App Sandbox entitlements.
- **Thinking mode off.** Reasoning models are the wrong shape for a voice loop.

## Do not suggest

- ❌ Any cloud LLM/ASR/TTS API — OpenAI, Anthropic, Deepgram, ElevenLabs, Cartesia
- ❌ **Ollama** — its MLX backend needs >32 GB; at 24 GB we fall to the slow path
- ❌ **LangChain / LlamaIndex / CrewAI** — latency and abstraction we don't want. The tool loop is ~150 lines and we own it.
- ❌ **Qdrant, Chroma, Pinecone, or any vector store with a server process**
- ❌ **Mem0 / Graphiti / Letta / Cognee** — multi-tenant problems we don't have
- ❌ **Whisper** on the realtime path — encoder-decoder makes TTFT scale with utterance length
- ❌ **A chat window.** This is voice-first. A scrolling transcript with a text box turns it into a chatbot. The transcript is an audit surface, opened deliberately.
- ❌ **Plan-then-execute prompting** — measured to hurt every open-weight model by 5–33 points
- ❌ **Speech-to-speech models** (Moshi, Qwen-Omni) — they can't call tools reliably
- ❌ `localStorage`/browser storage, Electron, React Native
- ❌ Speculative "future-proofing" abstractions. Write the concrete thing.

## Repo map

```
app/          Swift 6 — Jarvis.app. MenuBarExtra, NSPanel HUD, hotkeys, audit window.
              Unsandboxed. Developer ID signed. Installs to /Applications.
jarvisd/      Pipecat pipeline. Owns barge-in and interruption.
brain/        FastAPI shim. server.py (KV cap, prefix cache) · tiers.py (model
              load/evict) · toolloop.py (MCP client) · grammar.py (schema → GBNF)
mcp/          Our own MCP server.
memory/       schema.sql (bitemporal) · store.py (hybrid retrieval + RRF + rerank)
bench/        roundtrip.py (per-stage latency) · toolcall.py (tool-selection accuracy)
ops/          launchd AGENT plists, wired-limit script
```

## Conventions

**Python** — 3.12, full type hints, `async` throughout the audio and serving paths. No blocking calls inside Pipecat frame handlers. `uv` only; never `pip install` bare. Structured logging with stage names matching `bench/roundtrip.py`.

**Swift** — Swift 6 strict concurrency. HUD state updates must land in <50 ms; push over WebSocket, never poll. `orderFrontRegardless()`, never `makeKeyAndOrderFront` — the HUD must not steal focus. Use `RegisterEventHotKey` (Carbon) for global hotkeys, not `NSEvent.addGlobalMonitorForEvents`, which would require Input Monitoring permission we otherwise don't need.

**Tools** — start with four, measure selection accuracy before adding a fifth. Accuracy degrades as the schema list grows and every schema costs prefill tokens. Design for 1–3 tool calls per turn with a human in the loop; long-horizon autonomy is unsolved (best open-weight 16%, frontier 10%).

**Memory schema** — bitemporal. Every fact carries `valid_from`/`valid_to` (when it was true) and `observed_at` (when we learned it). Superseding closes `valid_to`; never delete. Core memory block is always in context and agent-editable; archival is retrieved on demand. Rerank top 20–30, never 100.

**Destructive actions** — anything irreversible surfaces in the HUD with a 3-second cancel and a plain-language description. No optimistic-execute-with-undo; most desktop actions have no undo.

## Known traps

- Qwen 2026 chat templates have open llama.cpp bugs — tool calls landing in `reasoning_content` instead of `delta.tool_calls`. Test the exact model+quant+runtime triple end to end. Pin versions.
- Electron/Chromium tears down its AX tree when occluded. Prefer Playwright MCP for anything browser-shaped.
- Background control uses private SkyLight APIs (`SLEventPostToPid`). Keep a foreground fallback.
- `shortcuts run` blocks forever on a permission prompt. Pre-clear interactively.
- App Intents cannot be invoked directly by third parties. `shortcuts run <UUID>` is the only bridge — use UUIDs, not names.

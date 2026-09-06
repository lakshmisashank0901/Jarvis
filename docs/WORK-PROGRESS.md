# Work progress

## 2026-09-06

- Ingested spec; wrote master plan; locked v1 (computer only) and v2 backlog.
- **Implemented v1** on branch `v1`:
  - Phase 0: Python 3.12, uv workspace, benches, `AGENTS.md`
  - Phase 1: `KvStore` cap 16384, oldest-turn eviction, `/v1/health`
  - Phase 2: clause split, prefix cache, SSE `x-clause` + echo LLM (`JARVIS_LLM=mlx` hook)
  - Phase 3: GBNF + tool loop (max 3, reject unknown names)
  - Phase 4: bitemporal memory, rerank cap 30
  - Phase 5: jarvisd WS/protocol, 200 ms EOT, clause TTS starter (Kokoro when `JARVIS_TTS=kokoro`)
  - Phase 6: Swift HUD/host sources (open in Xcode; Developer ID not applied here)
  - Phase 7: four tools `memory` `desktop` `browser` `calendar` + confirm gates
  - Phase 8: launchd agent plists + `wired_limit.sh` (no Home Assistant)
- Tests: `uv run pytest -q` — 20 passed.
- Not on this machine yet: Qwen weights, Parakeet/Kokoro/Pipecat extras, Peekaboo AX, Playwright browser, Developer ID signature.

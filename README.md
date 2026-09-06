# Jarvis v1

Local workshop assistant. Voice-first, computer only. See `AGENTS.md` and `docs/superpowers/plans/2026-09-06-jarvis-implementation.md`.

```
uv sync --all-packages
uv run pytest -q
uv run python bench/roundtrip.py
./ops/run-v1.sh
```

`JARVIS_LLM=echo` until MLX weights are on disk. Set `JARVIS_LLM=mlx` and `JARVIS_MLX_MODEL=` to a local 4-bit Qwen path.

App: `app/README.md`. launchd: `ops/README.md`. v2 is not this branch.

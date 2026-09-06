# Jarvis v1

Local workshop assistant. Computer only. Four tools: `memory`, `desktop`, `browser`, `calendar`.

## Run the servers

```bash
cd ~/Desktop/Jarvis
uv sync --all-packages
uv run pytest -q
./ops/run-v1.sh
```

Brain: http://127.0.0.1:8742 · jarvisd: ws://127.0.0.1:8741/v1

## Talk (text)

In another terminal:

```bash
uv run python -m brain.ask "Remember my dentist is Tuesday 4pm"
uv run python -m brain.ask "When is my dentist?"
uv run python -m brain.ask "Open Safari"
uv run python -m brain.ask "Go to https://example.com"
uv run python -m brain.ask "What's on my calendar tomorrow?"
```

Lock / quit / sleep / calendar create wait for `--confirmed`:

```bash
uv run python -m brain.ask --confirmed "Lock the screen"
```

Or curl:

```bash
curl -s http://127.0.0.1:8742/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"Open Safari"}],"stream":false}'
```

## Menu-bar HUD

```bash
cd app && swift run Jarvis
```

Hotkeys: ⌥⌘Space (PTT) · ⌥⌘Esc (cancel). Sign with Developer ID before putting it in `/Applications`.

## Models

Default `JARVIS_LLM=echo` plus a rule router (20/20 fixture accuracy). For real Qwen:

`JARVIS_LLM=mlx JARVIS_MLX_MODEL=/path/to/qwen-4bit`

v2 (WhatsApp, wake word, FaceTime, …) is not this branch.

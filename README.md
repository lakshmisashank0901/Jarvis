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

## App window

```bash
# keep ./ops/run-v1.sh running, then:
cd ~/Desktop/Jarvis/app && swift run Jarvis
```

Type in the Jarvis window. Green = brain connected. No microphone yet.

## Models

If `~/.jarvis/models/Qwen3.5-9B-4bit` is present, `./ops/run-v1.sh` sets `JARVIS_LLM=mlx` and the model replies in natural language, calls tools, or asks when unsure.

Otherwise: `JARVIS_LLM=echo` plus the rule router (20/20 fixture accuracy).

v2 (WhatsApp, wake word, FaceTime, …) is not this branch.

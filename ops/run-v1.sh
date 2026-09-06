#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."
export JARVIS_LLM="${JARVIS_LLM:-echo}"
export PYTHONPATH="$PWD/brain:$PWD/jarvisd:$PWD/mcp:$PWD/memory${PYTHONPATH:+:$PYTHONPATH}"
if [[ ! -x .venv/bin/python ]]; then
  echo "run: uv sync --all-packages" >&2
  exit 1
fi
.venv/bin/python -m brain.server &
brain_pid=$!
sleep 0.4
.venv/bin/python -m jarvisd.server &
jarvisd_pid=$!
trap 'kill $brain_pid $jarvisd_pid 2>/dev/null || true' INT TERM
echo "brain  http://127.0.0.1:8742/v1/health"
echo "jarvisd ws://127.0.0.1:8741/v1"
wait

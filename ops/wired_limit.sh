#!/bin/zsh
# Measure Metal wired memory, then optionally raise iogpu.wired_limit_mb.
# Agents only — this does nothing over SSH/headless.

set -euo pipefail
if [[ -z "${SSH_CONNECTION:-}" ]]; then
  echo "Aqua session ok"
else
  echo "refuse: launchd agents must not run over SSH" >&2
  exit 2
fi

python3 - <<'PY'
try:
    import mlx.core as mx
    print(mx.metal.device_info())
except Exception as exc:
    print("mx.metal.device_info() unavailable:", exc)
PY

echo "To raise the GPU wired limit (example 18432 MB):"
echo "  sudo sysctl iogpu.wired_limit_mb=18432"

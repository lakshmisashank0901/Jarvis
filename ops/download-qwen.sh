#!/usr/bin/env bash
set -euo pipefail
DEST="${JARVIS_MLX_MODEL:-$HOME/.jarvis/models/Qwen3.5-9B-4bit}"
mkdir -p "$DEST"
export HF_XET_HIGH_PERFORMANCE=1
uv run python - <<PY
from pathlib import Path
from huggingface_hub import snapshot_download
dest = Path("$DEST")
snapshot_download(repo_id="Micklavin/Qwen3.5-9B-4bit", local_dir=str(dest))
print("ready", dest)
PY

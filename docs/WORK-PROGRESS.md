# Work progress

## 2026-09-06

- v1 complete enough to use:
  - Tool router (20/20 bench accuracy) wired into `/v1/chat/completions`
  - Real macOS host fallback (`open`, osascript volume/calendar) when the app socket is down
  - AX inspect/act via System Events (Peekaboo if installed)
  - Browser `goto` via `open` or Playwright
  - `uv run python -m brain.ask "…"`
  - Swift package builds (`swift build --product Jarvis`)
  - Confirm gate for lock/quit/sleep/calendar write
- Tests: 26 passed. `bench/toolcall.py` accuracy=1.000
- Still yours to supply: Qwen weights, Developer ID, Peekaboo CLI, Playwright browsers
- GitHub: https://github.com/lakshmisashank0901/Jarvis

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
- Dedicated SwiftUI window (`DashboardView`): type commands, see replies, brain online/offline. Floating IDLE box no longer shows on launch. Still no mic.
- Window is forced to front on launch; menu bar → “Show Jarvis window”. HUD panel stays hidden.
- UI health/ask used a URLSession that waited for “network”; localhost timed out while brain was up. Fixed with ephemeral session + 2s health poll.
- Chat 500: Swift host socket was dropped (empty JSON). Retain unix server; HostClient falls back to `open`/osascript; tool errors no longer 500.
- Quit after checkbox: Swift `app.quit` ignored `name` and returned ok. Resolve by name; empty target falls back to osascript.
- Dashboard restyled as a dark holographic console: animated core, tool rail, chips, ARM toggle. Same brain/commands.
- “What is the time” was falling through to AX inspect (`missing value`). Now `desktop.clock` speaks local time.
- Click was targeting a button on Jarvis (frontmost). Now uses last opened app, strips “on/contact”, matches any labeled control, then Cmd+F search.
- Click `-10006`: System Events cannot `set frontmost` on process `safari`. Activate via `tell application` instead.
- `click compose` on Gmail was Cmd+F find-in-page, then lied “Clicked”. Page JS click for Safari/Chrome; no search fallback.
- Safari JS-from-Apple-Events is optional. Click walks AX; Gmail Compose falls back to the `c` shortcut.
- Compound “open Safari and click Compose” was only `open`. Now `route_steps` runs open, then click.
- Hybrids only split on click, so “open safari and set volume to 100” was volume only. Split any command chain (`and` / `then`).
- Hybrid chains now cover every v1 verb, plus `,` `;` `.` `also` `plus`. Facts with “and” stay one step.
- Intent layer: polite/synonym normalize; `open X` is an app if installed, otherwise a site (Hotstar → browser).
- “What are my events today” was inspect. Calendar list now matches events/agenda.
- Conversation path: `mlx-lm` + Qwen3.5-9B 4-bit under `~/.jarvis/models`. Model speaks / calls tools / asks; router is echo fallback only.
- Qwen3.5-9B 4-bit (~4.7 GB) is on disk. Restart `./ops/run-v1.sh` so `JARVIS_LLM=mlx`.
- Open failed: model sent `target` not `name`. Desktop maps target/app/application → name.
- Close-all dumped truncated JSON (`close` + invented apps). Parse speak from broken JSON; `close`/`except` quits running apps and keeps named + Finder.
- “open youtube” asked forever. Converse now resolves known sites (and follow-ups like “web browser”) to `browser.goto` before the model can ask.
- “open youtube, discord, instagram, linkedin” was glued into one fake domain. Known-site lists now split into separate `browser.goto` calls.
- Space-separated “open youtube discord instagram linkedin” was still one fake domain. Consecutive known sites now each get `open` in the default browser.
- Fixed `run-v1.sh`: `jarvisd` was not on PYTHONPATH (`No module named jarvisd.server`).

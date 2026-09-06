from __future__ import annotations

import shutil
import subprocess
from typing import Any


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, check=False, capture_output=True, text=True)


def _osa(script: str) -> subprocess.CompletedProcess[str]:
    return _run(["osascript", "-e", script])


def dispatch(op: str, **fields: Any) -> dict[str, Any]:
    if op == "app.open":
        name = fields.get("name") or fields.get("bundle_id")
        if not name:
            return {"ok": False, "error": "name required"}
        proc = _run(["open", "-a", str(name)])
        if proc.returncode != 0:
            return {"ok": False, "error": proc.stderr.strip() or "open failed"}
        return {"ok": True, "name": str(name)}
    if op == "app.quit":
        target = fields.get("name") or fields.get("bundle_id")
        proc = _osa(f'tell application "{target}" to quit')
        return {"ok": proc.returncode == 0, "error": proc.stderr.strip() or None}
    if op == "app.focus":
        target = fields.get("name") or fields.get("bundle_id")
        proc = _osa(f'tell application "{target}" to activate')
        return {"ok": proc.returncode == 0}
    if op == "files.open":
        path = str(fields.get("path", ""))
        proc = _run(["open", path])
        return {"ok": proc.returncode == 0, "path": path, "error": proc.stderr.strip() or None}
    if op == "files.reveal":
        path = str(fields.get("path", ""))
        proc = _run(["open", "-R", path])
        return {"ok": proc.returncode == 0, "path": path}
    if op == "system.volume":
        level = int(fields.get("level", 50))
        level = min(100, max(0, level))
        proc = _osa(f"set volume output volume {level}")
        return {"ok": proc.returncode == 0, "level": level}
    if op == "system.mute":
        on = bool(fields.get("on", True))
        script = "set volume with output muted" if on else "set volume without output muted"
        proc = _osa(script)
        return {"ok": proc.returncode == 0, "on": on}
    if op == "system.lock":
        proc = _run(
            [
                "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession",
                "-suspend",
            ]
        )
        if proc.returncode != 0:
            _osa('tell application "System Events" to keystroke "q" using {command down, control down}')
        return {"ok": True}
    if op == "system.sleep":
        proc = _run(["pmset", "sleepnow"])
        return {"ok": proc.returncode == 0}
    if op == "calendar.list":
        proc = _osa(
            'tell application "Calendar" to get summary of every event of calendar 1'
        )
        text = (proc.stdout or "").strip()
        return {"ok": True, "events": text, "error": proc.stderr.strip() or None}
    if op == "calendar.create":
        title = str(fields.get("title") or "Jarvis event").replace('"', " ")
        proc = _osa(
            f'tell application "Calendar" to tell calendar 1 to make new event at end with properties {{summary:"{title}", start date:current date, end date:(current date) + 30 * minutes}}'
        )
        if proc.returncode != 0:
            return {"ok": False, "error": proc.stderr.strip() or "calendar create failed"}
        return {"ok": True, "title": title}
    if op == "calendar.update":
        return {"ok": False, "error": "calendar.update needs an event id from list"}
    return {"ok": False, "error": f"unknown op {op}"}


def which_open() -> str | None:
    return shutil.which("open")

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any


def inspect() -> dict[str, Any]:
    if shutil.which("peekaboo"):
        proc = subprocess.run(["peekaboo", "see"], capture_output=True, text=True, check=False)
        return {"ok": proc.returncode == 0, "via": "peekaboo", "tree": proc.stdout}
    script = """
    tell application "System Events"
        set frontApp to name of first application process whose frontmost is true
        tell process frontApp
            set uiNames to name of every UI element of window 1
        end tell
        return frontApp & ": " & (uiNames as text)
    end tell
    """
    proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
    return {
        "ok": proc.returncode == 0,
        "via": "system-events",
        "tree": proc.stdout.strip(),
        "error": proc.stderr.strip() or None,
    }


def act(text: str) -> dict[str, Any]:
    if shutil.which("peekaboo"):
        proc = subprocess.run(
            ["peekaboo", "click", "--text", text],
            capture_output=True,
            text=True,
            check=False,
        )
        return {"ok": proc.returncode == 0, "via": "peekaboo", "text": text}
    safe = text.replace('"', " ")
    script = f"""
    tell application "System Events"
        tell (first application process whose frontmost is true)
            click (first button whose name is "{safe}")
        end tell
    end tell
    """
    proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
    return {
        "ok": proc.returncode == 0,
        "via": "system-events",
        "text": text,
        "error": proc.stderr.strip() or None,
    }


def dumps(result: dict[str, Any]) -> str:
    return json.dumps(result)

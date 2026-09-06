from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

_BROWSER_APPS = {
    "safari",
    "google chrome",
    "chrome",
    "chromium",
    "brave",
    "arc",
    "microsoft edge",
    "orion",
    "firefox",
}


def is_browser_app(app: str | None) -> bool:
    if not app:
        return False
    return app.strip().lower() in _BROWSER_APPS or "chrome" in app.lower()


def page_click_script(text: str, app: str) -> str:
    needle = json.dumps(text.lower())
    js = (
        "(() => { const n = "
        + needle
        + "; const nodes = Array.from(document.querySelectorAll("
        + "'button,a,[role=button],[gh=cm]')); "
        + "const hit = nodes.find(el => ((el.innerText||'') + ' ' + "
        + "(el.getAttribute('aria-label')||'')).toLowerCase().includes(n)); "
        + "if (!hit) return 'miss'; hit.click(); return 'clicked'; })()"
    )
    js_as = js.replace("\\", "\\\\").replace('"', '\\"')
    target = app.replace('"', " ")
    if "safari" in target.lower() or target.lower() == "orion":
        return (
            f'tell application "{target}" to activate\n'
            f'delay 0.2\n'
            f'tell application "{target}" to do JavaScript "{js_as}" in front document'
        )
    return (
        f'tell application "{target}" to activate\n'
        f'delay 0.2\n'
        f'tell application "{target}" to execute active tab of front window javascript "{js_as}"'
    )


def inspect() -> dict[str, Any]:
    if shutil.which("peekaboo"):
        proc = subprocess.run(["peekaboo", "see"], capture_output=True, text=True, check=False)
        return {"ok": proc.returncode == 0, "via": "peekaboo", "tree": proc.stdout}
    script = """
    tell application "System Events"
        set frontApp to name of first application process whose frontmost is true
        tell process frontApp
            try
                set winName to name of window 1
            on error
                set winName to "untitled"
            end try
            set labels to {}
            try
                set uiNames to name of every UI element of window 1
                repeat with n in uiNames
                    if n is not missing value then set end of labels to (n as text)
                end repeat
            end try
        end tell
        set AppleScript's text item delimiters to ", "
        return frontApp & ": " & winName & " — " & (labels as text)
    end tell
    """
    proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
    tree = proc.stdout.strip().replace("missing value", "").strip(" :—")
    return {
        "ok": proc.returncode == 0,
        "via": "system-events",
        "tree": tree or "the front window",
        "error": proc.stderr.strip() or None,
    }


def act_script(text: str, app: str | None = None) -> str:
    safe = text.replace('"', " ").replace("\\", " ")
    target = (app or "").replace('"', " ")
    activate = f'tell application "{target}" to activate\ndelay 0.3\n' if target else ""
    resolve = (
        f'set procName to name of first application process whose name is "{target}"'
        if target
        else 'set procName to name of first application process whose frontmost is true and name is not "Jarvis"'
    )
    return f"""
    {activate}
    tell application "System Events"
        set needle to "{safe}"
        {resolve}
        tell process procName
            set els to entire contents of window 1
            repeat with el in els
                try
                    if (name of el as text) contains needle then
                        click el
                        return "clicked"
                    end if
                end try
                try
                    if (description of el as text) contains needle then
                        click el
                        return "clicked"
                    end if
                end try
            end repeat
        end tell
    end tell
    error "no labeled control"
    """


def _run_osa(script: str, timeout: float = 8) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def _gmail_compose(app: str) -> bool:
    try:
        url = _run_osa(
            f'tell application "{app.replace(chr(34), " ")}" to return URL of front document',
            timeout=3,
        )
    except subprocess.TimeoutExpired:
        return False
    if url.returncode != 0 or "mail.google.com" not in (url.stdout or "").lower():
        return False
    try:
        typed = _run_osa(
            f'tell application "{app.replace(chr(34), " ")}" to activate\n'
            "delay 0.2\n"
            'tell application "System Events" to keystroke "c"',
            timeout=3,
        )
    except subprocess.TimeoutExpired:
        return False
    return typed.returncode == 0


def act(text: str, app: str | None = None) -> dict[str, Any]:
    if shutil.which("peekaboo"):
        cmd = ["peekaboo", "click", "--text", text]
        if app:
            cmd.extend(["--app", app])
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            return {"ok": True, "via": "peekaboo", "text": text, "app": app}
    try:
        proc = _run_osa(act_script(text, app), timeout=15)
    except subprocess.TimeoutExpired:
        proc = None
    if proc is not None and proc.returncode == 0 and "clicked" in (proc.stdout or ""):
        return {"ok": True, "via": "system-events", "text": text, "app": app}
    if is_browser_app(app) and text.lower() == "compose" and _gmail_compose(app):
        return {"ok": True, "via": "gmail-key", "text": text, "app": app}
    if is_browser_app(app):
        try:
            page = _run_osa(page_click_script(text, app))
        except subprocess.TimeoutExpired:
            page = None
        if page is not None and page.returncode == 0 and "clicked" in (page.stdout or ""):
            return {"ok": True, "via": "page", "text": text, "app": app}
    return {
        "ok": False,
        "via": "system-events",
        "text": text,
        "app": app,
        "error": f"No control named {text} in {app or 'the front app'}.",
    }


def dumps(result: dict[str, Any]) -> str:
    return json.dumps(result)

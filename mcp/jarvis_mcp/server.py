from __future__ import annotations

import json
import re
from typing import Any

from jarvis_mcp.host_client import HostClient, HostError
from memory.store import Store

TOOL_NAMES = ("memory", "desktop", "browser", "calendar")

CONFIRM_DESKTOP = {"quit", "close", "lock", "sleep", "act"}
CONFIRM_CALENDAR = {"create", "update"}
_PROTECTED = {
    "finder",
    "dock",
    "systemuiserver",
    "control center",
    "notification center",
    "loginwindow",
    "windowserver",
    "jarvis",
    "spotlight",
}
_EXCEPT = re.compile(r"except\s+(.+)", re.I)


def _split_keep(text: str) -> list[str]:
    match = _EXCEPT.search(text)
    rest = match.group(1) if match else ""
    return [
        part.strip()
        for part in re.split(r"\s+and\s+|,\s*", rest)
        if part.strip() and part.strip().lower() not in {"the", "app", "apps"}
    ]


class JarvisMcp:
    def __init__(self, store: Store | None = None, host: HostClient | None = None) -> None:
        self.store = store or Store()
        self.host = host or HostClient()
        self.last_confirm: dict[str, Any] | None = None
        self.last_app: str | None = None

    def tools(self) -> list[str]:
        return list(TOOL_NAMES)

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in TOOL_NAMES:
            raise ValueError(f"unknown tool {name}")
        action = arguments.get("action")
        if name == "memory":
            return self._memory(action, arguments)
        if name == "desktop":
            return self._desktop(action, arguments)
        if name == "browser":
            return self._browser(action, arguments)
        return self._calendar(action, arguments)

    def _memory(self, action: str | None, arguments: dict[str, Any]) -> dict[str, Any]:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        if action == "search":
            hits = self.store.search(str(arguments.get("query", "")), k=int(arguments.get("k", 20)))
            return {"ok": True, "facts": [h.fact for h in hits]}
        if action == "remember":
            fact = str(arguments.get("fact", ""))
            self.store.remember(fact, now, now, subject=arguments.get("subject"))
            return {"ok": True}
        raise ValueError("memory action must be search|remember")

    def _needs_confirm(self, tool: str, action: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
        if arguments.get("confirmed") is True:
            return None
        if tool == "desktop" and action in CONFIRM_DESKTOP:
            if action == "act" and not arguments.get("irreversible", True):
                return None
            return {
                "needs_confirm": True,
                "text": arguments.get("confirm_text") or f"{action} on the Mac",
            }
        if tool == "calendar" and action in CONFIRM_CALENDAR:
            return {
                "needs_confirm": True,
                "text": arguments.get("confirm_text") or f"calendar {action}",
            }
        return None

    def _keep_list(self, arguments: dict[str, Any]) -> list[str] | None:
        raw = arguments.get("except")
        if raw is None:
            raw = arguments.get("keep")
        if raw is not None:
            if isinstance(raw, list):
                return [str(x) for x in raw if str(x).strip()]
            return _split_keep(str(raw))
        name = str(arguments.get("name") or arguments.get("target") or "")
        low = name.lower()
        if "except" in low or low in {"all", "all apps"} or low.startswith("all app"):
            return _split_keep(name)
        return None

    def _quit_except(self, keep: list[str]) -> dict[str, Any]:
        keep_l = {k.lower() for k in keep} | _PROTECTED
        try:
            listed = self.host.call("app.list")
        except HostError as exc:
            return {"ok": False, "error": str(exc)}
        apps = listed.get("apps") if isinstance(listed.get("apps"), list) else []
        quit: list[str] = []
        for name in apps:
            label = str(name)
            if label.lower() in keep_l:
                continue
            try:
                self.host.call("app.quit", name=label)
                quit.append(label)
            except HostError:
                continue
        return {"ok": True, "quit": quit, "kept": [str(a) for a in apps if str(a).lower() in keep_l]}

    def _desktop(self, action: str | None, arguments: dict[str, Any]) -> dict[str, Any]:
        if action is None:
            raise ValueError("desktop action required")
        if action == "close":
            action = "quit"
            arguments = {**arguments, "action": "quit"}
        keep = self._keep_list(arguments) if action == "quit" else None
        if keep is not None:
            gate = self._needs_confirm("desktop", "quit", arguments)
            if gate:
                return gate
            return self._quit_except(keep)
        gate = self._needs_confirm("desktop", action, arguments)
        if gate:
            return gate
        if action == "clock":
            from datetime import datetime

            now = datetime.now()
            return {"ok": True, "now": now.strftime("%-I:%M %p on %A, %-d %B")}
        if action == "inspect":
            from jarvis_mcp.ax import inspect

            return inspect()
        if action == "act":
            from jarvis_mcp.ax import act

            label = str(arguments.get("text") or arguments.get("name") or "OK")
            return act(label, app=self.last_app)
        op = {
            "open": "app.open",
            "quit": "app.quit",
            "focus": "app.focus",
            "files_open": "files.open",
            "files_reveal": "files.reveal",
            "volume": "system.volume",
            "mute": "system.mute",
            "lock": "system.lock",
            "sleep": "system.sleep",
        }.get(action)
        if not op:
            raise ValueError(f"unknown desktop action {action}")
        fields = {k: v for k, v in arguments.items() if k not in {"action", "confirmed", "confirm_text", "irreversible"}}
        if action in {"open", "quit", "focus"}:
            app = fields.get("name") or fields.get("target") or fields.get("app") or fields.get("application")
            if app:
                fields = {"name": app, **{k: v for k, v in fields.items() if k not in {"name", "target", "app", "application"}}}
        try:
            result = self.host.call(op, **fields)
        except HostError as exc:
            return {"ok": False, "error": str(exc)}
        if action in {"open", "focus"} and result.get("ok"):
            name = fields.get("name") or fields.get("bundle_id")
            if name:
                self.last_app = str(name)
        return result

    def _browser(self, action: str | None, arguments: dict[str, Any]) -> dict[str, Any]:
        from jarvis_mcp import browser as web

        if action == "goto":
            return web.goto(str(arguments.get("url") or arguments.get("name") or ""))
        if action == "snapshot":
            return web.snapshot()
        if action == "click":
            return web.click(str(arguments.get("text") or ""))
        if action == "type":
            return web.type_text(str(arguments.get("text") or ""))
        raise ValueError("browser action must be goto|snapshot|click|type")

    def _calendar(self, action: str | None, arguments: dict[str, Any]) -> dict[str, Any]:
        if action is None:
            raise ValueError("calendar action required")
        gate = self._needs_confirm("calendar", action, arguments)
        if gate:
            return gate
        op = {
            "list": "calendar.list",
            "create": "calendar.create",
            "update": "calendar.update",
        }.get(action)
        if not op:
            raise ValueError(f"unknown calendar action {action}")
        fields = {k: v for k, v in arguments.items() if k not in {"action", "confirmed", "confirm_text"}}
        try:
            return self.host.call(op, **fields)
        except HostError as exc:
            return {"ok": False, "error": str(exc)}


def stdio_loop() -> None:
    mcp = JarvisMcp()
    print(json.dumps({"tools": list(TOOL_NAMES)}), flush=True)


if __name__ == "__main__":
    stdio_loop()

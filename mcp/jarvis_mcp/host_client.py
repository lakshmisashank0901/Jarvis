from __future__ import annotations

import json
import os
import socket
from typing import Any

from jarvis_mcp.macos_host import dispatch

HOST_SOCK = os.environ.get("JARVIS_HOST_SOCK", "/tmp/jarvis-host.sock")


class HostError(RuntimeError):
    pass


def _macos(op: str, **fields: Any) -> dict[str, Any]:
    data = dispatch(op, **fields)
    if not data.get("ok"):
        raise HostError(str(data.get("error") or "host op failed"))
    data.setdefault("via", "macos")
    return data


def _quit_missed(op: str, data: dict[str, Any]) -> bool:
    if op != "app.quit":
        return False
    return not (data.get("bundle_id") or data.get("name"))


class HostClient:
    def __init__(self, path: str = HOST_SOCK) -> None:
        self.path = path

    def call(self, op: str, **fields: Any) -> dict[str, Any]:
        payload = {"op": op, **fields}
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        try:
            sock.connect(self.path)
            sock.sendall((json.dumps(payload) + "\n").encode())
            raw = b""
            while b"\n" not in raw:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                raw += chunk
            sock.close()
            line = raw.decode().strip()
            if not line:
                return _macos(op, **fields)
            data = json.loads(line)
            if not data.get("ok") or _quit_missed(op, data):
                return _macos(op, **fields)
            data["via"] = "app-host"
            return data
        except (OSError, json.JSONDecodeError, TimeoutError):
            try:
                sock.close()
            except OSError:
                pass
            return _macos(op, **fields)

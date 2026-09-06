from __future__ import annotations

import json
import os
import socket
from typing import Any

HOST_SOCK = os.environ.get("JARVIS_HOST_SOCK", "/tmp/jarvis-host.sock")


class HostError(RuntimeError):
    pass


class HostClient:
    def __init__(self, path: str = HOST_SOCK) -> None:
        self.path = path

    def call(self, op: str, **fields: Any) -> dict[str, Any]:
        payload = {"op": op, **fields}
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(self.path)
            sock.sendall((json.dumps(payload) + "\n").encode())
            raw = sock.makefile().readline()
            sock.close()
            data = json.loads(raw)
            if not data.get("ok"):
                raise HostError(data.get("error", "host op failed"))
            data["via"] = "app-host"
            return data
        except OSError:
            sock.close()
            from jarvis_mcp.macos_host import dispatch

            data = dispatch(op, **fields)
            if not data.get("ok"):
                raise HostError(str(data.get("error") or "host op failed"))
            data.setdefault("via", "macos")
            return data

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
        except OSError as exc:
            raise HostError(f"host socket unavailable: {self.path}") from exc
        finally:
            sock.close()
        data = json.loads(raw)
        if not data.get("ok"):
            raise HostError(data.get("error", "host op failed"))
        return data

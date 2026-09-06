from __future__ import annotations

import subprocess
from typing import Any
from urllib.parse import urlparse


def _normalize_url(url: str) -> str:
    raw = url.strip()
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"bad url {url}")
    return raw


def goto(url: str) -> dict[str, Any]:
    target = _normalize_url(url)
    proc = subprocess.run(
        ["open", target],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    return {
        "ok": proc.returncode == 0,
        "via": "open",
        "url": target,
        "error": proc.stderr.strip() or None,
    }


def snapshot() -> dict[str, Any]:
    return {"ok": False, "error": "snapshot needs a live Playwright session"}


def click(text: str) -> dict[str, Any]:
    return {"ok": False, "error": f"click {text!r} needs Playwright page context"}


def type_text(text: str) -> dict[str, Any]:
    return {"ok": False, "error": f"type {text!r} needs Playwright page context"}

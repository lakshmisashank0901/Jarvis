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
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        proc = subprocess.run(["open", target], check=False, capture_output=True, text=True)
        return {
            "ok": proc.returncode == 0,
            "via": "open",
            "url": target,
            "error": proc.stderr.strip() or None,
        }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(target)
        title = page.title()
        # leave the window open
        return {"ok": True, "via": "playwright", "url": target, "title": title}


def snapshot() -> dict[str, Any]:
    return {"ok": False, "error": "snapshot needs a live Playwright session"}


def click(text: str) -> dict[str, Any]:
    return {"ok": False, "error": f"click {text!r} needs Playwright page context"}


def type_text(text: str) -> dict[str, Any]:
    return {"ok": False, "error": f"type {text!r} needs Playwright page context"}

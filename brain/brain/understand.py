from __future__ import annotations

import re
from pathlib import Path

SITES: dict[str, str] = {
    "hotstar": "https://www.hotstar.com",
    "jiohotstar": "https://www.hotstar.com",
    "disney": "https://www.hotstar.com",
    "disney+": "https://www.hotstar.com",
    "netflix": "https://www.netflix.com",
    "youtube": "https://www.youtube.com",
    "discord": "https://discord.com",
    "gmail": "https://mail.google.com",
    "google": "https://www.google.com",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "linkedin": "https://www.linkedin.com",
    "amazon": "https://www.amazon.in",
    "prime": "https://www.primevideo.com",
    "flipkart": "https://www.flipkart.com",
    "swiggy": "https://www.swiggy.com",
    "zomato": "https://www.zomato.com",
    "spotify": "https://open.spotify.com",
    "github": "https://github.com",
    "reddit": "https://www.reddit.com",
    "wikipedia": "https://wikipedia.org",
}

_APP_DIRS = (
    Path("/Applications"),
    Path("/System/Applications"),
    Path("/System/Applications/Utilities"),
    Path.home() / "Applications",
)

_APP_ALIAS = {
    "settings": "System Settings",
    "system settings": "System Settings",
    "system preferences": "System Settings",
}

_FILLER = re.compile(
    r"^(?:hey |ok |okay )?(?:jarvis[, ]*)?"
    r"(?:please |can you |could you |would you |i want (?:you )?to |i need (?:you )?to |"
    r"i'd like (?:you )?to |just )+",
    re.I,
)

_TRAIL = re.compile(r"\s+please[.!]?$", re.I)

_PHRASES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(?:tell me|what's|whats|what is) the time\b", re.I), "what is the time"),
    (re.compile(r"\b(?:tell me )?what time is it\b", re.I), "what is the time"),
    (re.compile(r"\b(?:put|send) (?:the )?(?:mac|computer|machine) to sleep\b", re.I), "sleep"),
    (re.compile(r"\b(?:show|what's on|whats on) (?:my )?calendar\b", re.I), "what's on my calendar"),
    (re.compile(r"\b(?:what are|what's|whats) my events\b", re.I), "what's on my calendar"),
    (re.compile(r"\b(?:turn|make|set) (?:the )?volume (?:up )?to\b", re.I), "set volume to"),
    (re.compile(r"\b(?:silence|quiet|mute) (?:the )?(?:mac|sound|volume)?\b", re.I), "mute the Mac"),
    (re.compile(r"\b(?:note that|save that|store that)\b", re.I), "remember"),
    (re.compile(r"\b(?:take me to|pull up|bring up|visit|watch|play|launch|start)\b", re.I), "open"),
    (re.compile(r"\b(?:navigate to|browse)\b", re.I), "go to"),
    (re.compile(r"\b(?:kill|exit)\b", re.I), "quit"),
)


def app_exists(name: str) -> bool:
    slug = _APP_ALIAS.get(name.strip().lower(), name.strip())
    slug = slug.removesuffix(".app")
    want = slug.lower()
    for folder in _APP_DIRS:
        if not folder.is_dir():
            continue
        for path in folder.glob("*.app"):
            if path.stem.lower() == want:
                return True
    return False


def site_url(name: str) -> str:
    key = name.strip().lower()
    if key in SITES:
        return SITES[key]
    host = re.sub(r"[^a-z0-9.-]", "", key.replace(" ", ""))
    if "." not in host:
        host = f"www.{host}.com"
    return f"https://{host}"


def normalize(text: str) -> str:
    out = text.strip()
    out = _FILLER.sub("", out).strip()
    out = _TRAIL.sub("", out).strip()
    for pat, repl in _PHRASES:
        out = pat.sub(repl, out)
    return out.strip() or text.strip()


_OPEN = re.compile(
    r"\b(?:open|go to|visit|watch|play|launch|start)\s+(.+)",
    re.I,
)
_BROWSER_FOLLOW = {
    "web browser",
    "browser",
    "the browser",
    "the website",
    "website",
    "the site",
    "site",
    "open the website",
    "open the browser",
    "yes",
    "yeah",
    "yep",
}
_STRIP_IN_BROWSER = re.compile(
    r"\s+(?:in|on|with)\s+(?:the\s+)?(?:browser|safari|chrome|firefox).*$",
    re.I,
)
_SPLIT_DESTS = re.compile(r"\s*(?:,(?:\s+and)?|\band\b|&)\s*", re.I)


def looks_like_site(name: str) -> bool:
    token = name.strip().lower().split()[0] if name.strip() else ""
    if token in SITES:
        return True
    if token.startswith(("http://", "https://", "www.")):
        return True
    return "." in token and not token.endswith(".app")


def _is_dest(name: str) -> bool:
    token = name.strip().lower()
    if not token or token in _BROWSER_FOLLOW:
        return False
    if token in SITES or looks_like_site(token):
        return True
    return app_exists(name)


def _one_destination(name: str) -> dict[str, object] | None:
    name = _STRIP_IN_BROWSER.sub("", name).strip(" .?!")
    if not name or name.lower() in _BROWSER_FOLLOW:
        return None
    if looks_like_site(name) or name.lower() in SITES or not app_exists(name):
        return {"name": "browser", "arguments": {"action": "goto", "url": site_url(name)}}
    return {"name": "desktop", "arguments": {"action": "open", "name": name}}


def _goto(url: str) -> dict[str, object]:
    return {"name": "browser", "arguments": {"action": "goto", "url": url}}


def _dest_parts(name: str) -> list[str]:
    parts = [part.strip(" .?!") for part in _SPLIT_DESTS.split(name) if part.strip(" .?!")]
    if len(parts) >= 2 and all(_is_dest(part) for part in parts):
        return parts
    tokens = name.lower().split()
    found: list[str] = []
    i = 0
    while i < len(tokens):
        two = " ".join(tokens[i : i + 2])
        if two in SITES:
            found.append(two)
            i += 2
            continue
        one = tokens[i]
        if one in SITES or looks_like_site(one):
            found.append(one)
            i += 1
            continue
        return []
    return found if len(found) >= 2 else []


def _site_from_history(prior: list[str]) -> str | None:
    for text in reversed(prior):
        dests = resolve_destinations(text, prior=[])
        browser = next((d for d in dests if d["name"] == "browser"), None)
        if browser:
            return str(browser["arguments"]["url"])
        norm = normalize(text).strip().lower()
        key = norm.split()[-1] if norm else ""
        if key in SITES:
            return SITES[key]
    return None


def resolve_destinations(text: str, prior: list[str] | None = None) -> list[dict[str, object]]:
    prior = prior or []
    norm = normalize(text)
    low = norm.lower().strip(" .?!")
    name = ""
    match = _OPEN.search(norm)
    if match:
        name = match.group(1).strip()
        name = re.sub(r"^(?:the )?(?:website|site|page|app)\s+", "", name, flags=re.I)
    elif low in SITES or looks_like_site(low):
        name = low
    elif low in _BROWSER_FOLLOW:
        url = _site_from_history(prior)
        return [_goto(url)] if url else []
    if not name:
        return []
    name = _STRIP_IN_BROWSER.sub("", name).strip(" .?!")
    if not name or name.lower() in _BROWSER_FOLLOW:
        url = _site_from_history(prior)
        return [_goto(url)] if url else []
    parts = _dest_parts(name)
    if parts:
        return [dest for part in parts if (dest := _one_destination(part))]
    one = _one_destination(name)
    return [one] if one else []


def resolve_destination(text: str, prior: list[str] | None = None) -> dict[str, object] | None:
    dests = resolve_destinations(text, prior)
    return dests[0] if dests else None

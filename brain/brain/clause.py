from __future__ import annotations

import re

_BOUNDARY = re.compile(r"(?<=[.?!;])")


def split_clauses(text: str) -> list[str]:
    """Split on `. ? ! ;`, keeping the delimiter on the left piece."""
    if not text:
        return []
    parts = [p for p in _BOUNDARY.split(text) if p != ""]
    if not parts:
        return [text]
    return parts


def emit_ready_clauses(buffer: str, *, min_words: int = 8) -> tuple[list[str], str]:
    """Streaming helper: emit complete clauses; hold a short tail."""
    clauses = split_clauses(buffer)
    if len(clauses) <= 1:
        return [], buffer
    ready = clauses[:-1]
    tail = clauses[-1]
    flushed: list[str] = []
    held = ""
    for clause in ready:
        candidate = held + clause
        if len(candidate.split()) >= min_words or held:
            flushed.append(candidate)
            held = ""
        else:
            held = candidate
    return flushed, held + tail

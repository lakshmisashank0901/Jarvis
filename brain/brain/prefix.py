from __future__ import annotations


class PrefixCache:
    def __init__(self) -> None:
        self._key: str | None = None

    def _make_key(self, system: str, tools_json: str) -> str:
        return f"{system}\0{tools_json}"

    def warm(self, system: str, tools_json: str) -> None:
        self._key = self._make_key(system, tools_json)

    def hit(self, system: str | None = None, tools_json: str | None = None) -> bool:
        if self._key is None:
            return False
        if system is None:
            return True
        return self._key == self._make_key(system, tools_json or "")

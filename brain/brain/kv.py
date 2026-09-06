from __future__ import annotations

from dataclasses import dataclass, field

MAX_KV_TOKENS = 16_384


@dataclass(frozen=True)
class Turn:
    role: str
    text: str
    n_tokens: int


@dataclass
class KvStore:
    cap: int = MAX_KV_TOKENS
    _turns: list[Turn] = field(default_factory=list)

    @property
    def tokens(self) -> int:
        return sum(t.n_tokens for t in self._turns)

    @property
    def turns(self) -> list[Turn]:
        return list(self._turns)

    def evict_oldest_turn(self) -> None:
        if self._turns:
            self._turns.pop(0)

    def append_turn(self, role: str, text: str, n_tokens: int) -> None:
        if n_tokens > self.cap:
            raise ValueError(f"turn tokens {n_tokens} exceed cap {self.cap}")
        while self._turns and self.tokens + n_tokens > self.cap:
            self.evict_oldest_turn()
        self._turns.append(Turn(role=role, text=text, n_tokens=n_tokens))

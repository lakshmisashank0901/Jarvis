from __future__ import annotations

from fastapi.testclient import TestClient

from brain.kv import MAX_KV_TOKENS, KvStore
from brain.server import create_app


def test_kv_evicts_oldest_turn_first() -> None:
    kv = KvStore(cap=MAX_KV_TOKENS)
    kv.append_turn("user", "oldest", 10_000)
    kv.append_turn("assistant", "middle", 5_000)
    kv.append_turn("user", "newest", 4_000)

    texts = [t.text for t in kv.turns]
    assert "oldest" not in texts
    assert "newest" in texts
    assert kv.tokens <= MAX_KV_TOKENS
    assert kv.tokens == 9_000


def test_health_reports_kv_cap() -> None:
    kv = KvStore(cap=MAX_KV_TOKENS)
    kv.append_turn("user", "hi", 2)
    client = TestClient(create_app(kv))
    res = client.get("/v1/health")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["kv_cap"] == 16_384
    assert body["kv_tokens"] == 2
    assert "model" in body

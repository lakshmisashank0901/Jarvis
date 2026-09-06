from fastapi.testclient import TestClient

from brain.kv import KvStore
from brain.prefix import PrefixCache
from brain.server import create_app


def test_stream_emits_clause_before_done() -> None:
    client = TestClient(create_app(KvStore(), PrefixCache()))
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "messages": [{"role": "user", "content": "Hello there, I can help. What next?"}],
            "stream": True,
        },
    ) as res:
        body = "".join(res.iter_text())
    assert "x-clause" in body
    assert "[DONE]" in body


def test_health_model_echo() -> None:
    client = TestClient(create_app())
    assert client.get("/v1/health").json()["model"] == "echo"

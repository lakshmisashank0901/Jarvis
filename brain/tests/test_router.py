from bench.toolcall import DEFAULT_FIXTURES, accuracy
from brain.router import route


def test_router_hits_all_v1_fixtures() -> None:
    pairs = [(route(f.prompt).name, f.expected) for f in DEFAULT_FIXTURES]
    assert accuracy(pairs) == 1.0


def test_open_safari_arguments() -> None:
    call = route("Open Safari")
    assert call.name == "desktop"
    assert call.arguments["action"] == "open"
    assert call.arguments["name"] == "Safari"

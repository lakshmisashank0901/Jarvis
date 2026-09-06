from bench.toolcall import DEFAULT_FIXTURES, accuracy
from brain.router import route, route_steps


def test_router_hits_all_v1_fixtures() -> None:
    pairs = [(route(f.prompt).name, f.expected) for f in DEFAULT_FIXTURES]
    assert accuracy(pairs) == 1.0


def test_open_safari_arguments() -> None:
    call = route("Open Safari")
    assert call.name == "desktop"
    assert call.arguments["action"] == "open"
    assert call.arguments["name"] == "Safari"


def test_click_strips_on_and_contact() -> None:
    call = route("click on contact Sunny")
    assert call.arguments["action"] == "act"
    assert call.arguments["text"] == "Sunny"


def test_what_is_the_time_is_clock() -> None:
    call = route("what is the time")
    assert call.name == "desktop"
    assert call.arguments["action"] == "clock"


def test_open_and_click_is_two_steps() -> None:
    steps = route_steps("open Safari and click Compose")
    assert [s.arguments["action"] for s in steps] == ["open", "act"]
    assert steps[0].arguments["name"] == "Safari"
    assert steps[1].arguments["text"] == "Compose"


def test_open_and_volume_is_two_steps() -> None:
    steps = route_steps("open safari and set volume to 100")
    assert [s.arguments["action"] for s in steps] == ["open", "volume"]
    assert steps[0].arguments["name"] == "safari"
    assert steps[1].arguments["level"] == 100


def test_remember_with_and_stays_one_step() -> None:
    steps = route_steps("Remember milk and eggs")
    assert len(steps) == 1
    assert steps[0].arguments["action"] == "remember"


def test_any_command_chain_splits() -> None:
    steps = route_steps(
        "go to https://example.com, set volume to 20, remember the wifi is test, what's on my calendar tomorrow"
    )
    assert [s.name for s in steps] == ["browser", "desktop", "memory", "calendar"]
    assert steps[1].arguments["action"] == "volume"
    also = route_steps("mute the Mac also lock the screen")
    assert [s.arguments["action"] for s in also] == ["mute", "lock"]


def test_quit_and_close_use_app_name() -> None:
    quit_call = route("Quit Notes")
    assert quit_call.arguments["action"] == "quit"
    assert quit_call.arguments["name"] == "Notes"
    close_call = route("Close the Safari")
    assert close_call.arguments["action"] == "quit"
    assert close_call.arguments["name"] == "Safari"

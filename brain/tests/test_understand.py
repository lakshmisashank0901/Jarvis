from brain.router import route, route_steps
from brain.understand import normalize, site_url


def test_youtube_is_a_known_site() -> None:
    from brain.understand import looks_like_site, resolve_destination

    assert looks_like_site("youtube")
    dest = resolve_destination("open youtube")
    assert dest is not None
    assert dest["name"] == "browser"
    assert dest["arguments"]["url"] == "https://www.youtube.com"


def test_open_several_sites_stays_separate() -> None:
    from brain.understand import resolve_destinations

    dests = resolve_destinations("open youtube, discord, instagram, linkedin")
    urls = [str(d["arguments"]["url"]) for d in dests]
    assert "youtubediscord" not in "".join(urls)
    assert urls == [
        "https://www.youtube.com",
        "https://discord.com",
        "https://www.instagram.com",
        "https://www.linkedin.com",
    ]


def test_open_space_separated_sites_stays_separate() -> None:
    from brain.understand import resolve_destinations

    dests = resolve_destinations("open youtube discord instagram linkedin")
    urls = [str(d["arguments"]["url"]) for d in dests]
    assert urls == [
        "https://www.youtube.com",
        "https://discord.com",
        "https://www.instagram.com",
        "https://www.linkedin.com",
    ]


def test_open_hotstar_goes_to_browser(monkeypatch) -> None:
    monkeypatch.setattr("brain.understand.app_exists", lambda _name: False)
    call = route("open hotstar")
    assert call.name == "browser"
    assert call.arguments["action"] == "goto"
    assert "hotstar" in call.arguments["url"].lower()


def test_open_safari_stays_app(monkeypatch) -> None:
    monkeypatch.setattr("brain.understand.app_exists", lambda name: name.lower() == "safari")
    call = route("open Safari")
    assert call.name == "desktop"
    assert call.arguments["action"] == "open"
    assert call.arguments["name"] == "Safari"


def test_polite_launch_and_time(monkeypatch) -> None:
    monkeypatch.setattr("brain.understand.app_exists", lambda name: name.lower() == "safari")
    assert normalize("can you launch safari please") == "open safari"
    assert route("tell me the time").arguments["action"] == "clock"
    assert route("visit youtube").name == "browser"
    assert "youtube" in site_url("youtube")


def test_events_today_is_calendar() -> None:
    call = route("what are my events today")
    assert call.name == "calendar"
    assert call.arguments["action"] == "list"
    assert "from" in call.arguments
    assert "to" in call.arguments


def test_hybrid_understands_site_then_volume(monkeypatch) -> None:
    monkeypatch.setattr("brain.understand.app_exists", lambda _name: False)
    steps = route_steps("open hotstar and set volume to 40")
    assert steps[0].name == "browser"
    assert steps[1].arguments["action"] == "volume"
    assert steps[1].arguments["level"] == 40

import json

from jarvisd.ws import HudState, make_hud


def test_hud_unknown_state_does_not_apply_in_python_mirror() -> None:
    raw = {"t": "hud", "state": "listening", "partial": "hi", "confirm": None}
    ev = make_hud(HudState(raw["state"]), partial=raw["partial"])
    encoded = json.dumps(ev.to_json())
    assert json.loads(encoded)["state"] == "listening"


def test_confirm_payload_deadline_is_3000() -> None:
    from jarvisd.ws import Confirm, make_hud

    ev = make_hud(HudState.confirm, confirm=Confirm(id="c1", text="Quit Notes"))
    body = ev.to_json()
    assert body["confirm"]["deadline_ms"] == 3000

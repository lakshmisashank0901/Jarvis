from jarvisd.pipeline import EOT_SILENCE_MS, should_fire_eot


def test_eot_fires_at_200ms_not_800() -> None:
    assert EOT_SILENCE_MS == 200
    assert should_fire_eot(200) is True
    assert should_fire_eot(199) is False
    assert should_fire_eot(800) is True

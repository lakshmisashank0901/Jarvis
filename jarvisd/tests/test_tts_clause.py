from jarvisd.tts_clause import ClauseTts


def test_tts_starts_on_first_clause_without_waiting() -> None:
    seen: list[bytes] = []
    tts = ClauseTts(on_audio=seen.append)
    tts.start("Hello there, I can help.")
    assert tts.started == ["Hello there, I can help."]
    assert seen

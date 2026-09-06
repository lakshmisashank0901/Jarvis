from datetime import datetime, timezone

from memory.store import RERANK_CAP, Store


def test_bitemporal_supersede_closes_valid_to() -> None:
    store = Store()
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t1 = datetime(2026, 2, 1, tzinfo=timezone.utc)
    store.remember("dentist tuesday 4pm", t0, t0, subject="dentist")
    store.remember("dentist wednesday 5pm", t1, t1, subject="dentist")
    open_rows = store.conn.execute(
        "SELECT fact, valid_to FROM facts WHERE subject = 'dentist' ORDER BY id"
    ).fetchall()
    assert open_rows[0]["valid_to"] is not None
    assert open_rows[1]["valid_to"] is None
    assert "wednesday" in open_rows[1]["fact"]


def test_search_rerank_cap_never_exceeds_30() -> None:
    store = Store()
    now = datetime(2026, 3, 1, tzinfo=timezone.utc)
    for i in range(80):
        store.remember(f"note number {i} about dentist", now, now, subject=f"note-{i}")
    hits = store.search("dentist", k=100)
    assert len(hits) <= RERANK_CAP
    assert len(hits) <= 30

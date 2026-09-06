from brain.clause import split_clauses


def test_split_clauses_two_sentences() -> None:
    assert split_clauses("Hello there, I can help. What next?") == [
        "Hello there, I can help.",
        " What next?",
    ]

from brain.grammar import Tool, schema_to_gbnf


def test_schema_to_gbnf_rejects_third_name() -> None:
    gbnf = schema_to_gbnf(
        [
            Tool(name="memory", schema={}),
            Tool(name="desktop", schema={}),
        ]
    )
    assert '"memory"' in gbnf
    assert '"desktop"' in gbnf
    assert '"browser"' not in gbnf
    assert "name ::= " in gbnf

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Tool:
    name: str
    schema: dict[str, Any]


def schema_to_gbnf(tools: list[Tool]) -> str:
    if not tools:
        raise ValueError("need at least one tool")
    names = " | ".join(f'"{t.name}"' for t in tools)
    return f"""
root ::= tool-call
tool-call ::= "{{" ws "\\"name\\"" ws ":" ws name ws "," ws "\\"arguments\\"" ws ":" ws object ws "}}"
name ::= {names}
object ::= "{{" ws (string ws ":" ws value (ws "," ws string ws ":" ws value)*)? ws "}}"
array ::= "[" ws (value (ws "," ws value)*)? ws "]"
value ::= object | array | string | number | "true" | "false" | "null"
string ::= "\\"" ([^"\\\\] | "\\\\" .)* "\\""
number ::= "-"? [0-9]+ ("." [0-9]+)?
ws ::= [ \\t\\n]*
""".strip()

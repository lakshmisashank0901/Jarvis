"""Tool-selection accuracy against the live four-tool schema."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

TOOL_NAMES: tuple[str, ...] = ("memory", "desktop", "browser", "calendar")


@dataclass(frozen=True)
class Fixture:
    prompt: str
    expected: str


DEFAULT_FIXTURES: tuple[Fixture, ...] = (
    Fixture("Remember my dentist is Tuesday 4pm", "memory"),
    Fixture("When is my dentist?", "memory"),
    Fixture("Open Safari", "desktop"),
    Fixture("Open the file ~/Desktop/notes.txt", "desktop"),
    Fixture("Set volume to 30", "desktop"),
    Fixture("What's on this screen?", "desktop"),
    Fixture("Click Save", "desktop"),
    Fixture("Go to https://example.com", "browser"),
    Fixture("Open the browser and go to example.com", "browser"),
    Fixture("What's on my calendar tomorrow?", "calendar"),
    Fixture("Book 30 minutes dentist Tuesday 4pm", "calendar"),
    Fixture("Create a calendar event Friday 2pm standup", "calendar"),
    Fixture("Mute the Mac", "desktop"),
    Fixture("Reveal ~/Downloads/a.pdf in Finder", "desktop"),
    Fixture("Quit Notes", "desktop"),
    Fixture("Focus Calendar", "desktop"),
    Fixture("Search my memory for the wifi password", "memory"),
    Fixture("Click the login button on this page", "browser"),
    Fixture("Change tomorrow's meeting to 3pm", "calendar"),
    Fixture("Lock the screen", "desktop"),
)


def accuracy(pairs: list[tuple[str, str]]) -> float:
    if not pairs:
        return 0.0
    hits = sum(1 for pred, exp in pairs if pred == exp)
    return hits / len(pairs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", default=None, help="JSON list of predicted tool names")
    args = parser.parse_args(argv)

    print("tools: " + ",".join(TOOL_NAMES))
    for fix in DEFAULT_FIXTURES:
        print(f"{fix.expected}\t{fix.prompt}")

    if args.predictions:
        preds = json.loads(args.predictions)
        pairs = list(zip(preds, [f.expected for f in DEFAULT_FIXTURES], strict=True))
        acc = accuracy(pairs)
        print(f"accuracy={acc:.3f} n={len(pairs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

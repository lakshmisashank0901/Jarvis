from __future__ import annotations

import argparse
import json

from brain.turn import default_mcp, run_user_turn


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ask Jarvis v1 (text)")
    parser.add_argument("text", nargs="+")
    parser.add_argument("--confirmed", action="store_true")
    args = parser.parse_args(argv)
    turn = run_user_turn(" ".join(args.text), default_mcp(), confirmed=args.confirmed)
    print(turn["spoken"])
    print(json.dumps(turn["call"]))
    return 0 if turn["result"].get("ok", True) or turn["confirm"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

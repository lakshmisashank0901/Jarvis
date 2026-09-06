"""Per-stage latency. Stage names are a contract."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

STAGE_NAMES: tuple[str, ...] = (
    "vad",
    "eot",
    "asr",
    "llm_ttft",
    "first_clause",
    "tts_ttfa",
    "outbuf",
)

P50_BUDGET_MS = 750.0


def print_stages() -> None:
    for name in STAGE_NAMES:
        print(name)


def summarize(timings: dict[str, float]) -> dict[str, Any]:
    missing = [n for n in STAGE_NAMES if n not in timings]
    total = sum(timings.get(n, 0.0) for n in STAGE_NAMES)
    return {
        "stages": {n: timings.get(n) for n in STAGE_NAMES},
        "missing": missing,
        "total_ms": total,
        "p50_budget_ms": P50_BUDGET_MS,
        "over_budget": total >= P50_BUDGET_MS,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Jarvis round-trip stage bench")
    parser.add_argument("--wav", default=None, help="optional wav fixture (wired in later phases)")
    parser.add_argument("--json-timings", default=None, help="path to {stage: ms} JSON")
    args = parser.parse_args(argv)

    if args.json_timings:
        with open(args.json_timings, encoding="utf-8") as fh:
            timings = json.load(fh)
        report = summarize({str(k): float(v) for k, v in timings.items()})
        print(json.dumps(report, indent=2))
        if report["missing"]:
            return 2
        if report["over_budget"]:
            return 3
        return 0

    print_stages()
    if args.wav:
        print(f"# wav={args.wav} (stage timers attach in jarvisd)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

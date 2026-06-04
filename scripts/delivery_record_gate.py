#!/usr/bin/env python3
"""Delivery loop gate helpers for pytest and implementation-review."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

STATE_PATH = Path(".cursor/delivery-state.json")


def _load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"gates": {}}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def record_full_pytest(exit_code: int) -> None:
    state = _load_state()
    state.setdefault("gates", {})["fullPytest"] = {
        "passed": exit_code == 0,
        "exitCode": exit_code,
    }
    _save_state(state)


def assert_full_pytest() -> None:
    state = _load_state()
    gate = state.get("gates", {}).get("fullPytest")
    if not gate or not gate.get("passed"):
        print(
            "BLOCKED: full pytest gate missing or failed. Run:\n"
            "  PYTHONPATH=src python -m pytest tests/ -q\n"
            "  python3 scripts/delivery_record_gate.py record-full-pytest --exit-code 0",
            file=sys.stderr,
        )
        sys.exit(1)


def record_implementation_review(review_path: str, parse: bool = False) -> None:
    state = _load_state()
    payload = {"reviewPath": review_path}
    if parse:
        text = Path(review_path).read_text()
        critical = len(re.findall(r"^\| C\d+", text, re.MULTILINE))
        important = len(re.findall(r"^\| I[-A-Z\d]+", text, re.MULTILINE))
        recommendation = "proceed" if "Final recommendation\n\n**proceed**" in text else "fix required"
        if "**proceed**" in text.split("Final recommendation")[-1]:
            recommendation = "proceed"
        payload.update({"critical": critical, "important": important, "recommendation": recommendation})
    state.setdefault("gates", {})["implementationReview"] = payload
    _save_state(state)


def assert_implementation_review() -> None:
    state = _load_state()
    gate = state.get("gates", {}).get("implementationReview")
    if not gate:
        print("BLOCKED: implementation review gate missing", file=sys.stderr)
        sys.exit(1)
    if gate.get("recommendation") != "proceed":
        print("BLOCKED: implementation review recommendation is not proceed", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p_record = sub.add_parser("record-full-pytest")
    p_record.add_argument("--exit-code", type=int, required=True)

    sub.add_parser("assert-full-pytest")

    p_review = sub.add_parser("record-implementation-review")
    p_review.add_argument("--review-path", required=True)
    p_review.add_argument("--parse", action="store_true")

    sub.add_parser("assert-implementation-review")

    args = parser.parse_args()

    if args.command == "record-full-pytest":
        record_full_pytest(args.exit_code)
    elif args.command == "assert-full-pytest":
        assert_full_pytest()
    elif args.command == "record-implementation-review":
        record_implementation_review(args.review_path, parse=args.parse)
    elif args.command == "assert-implementation-review":
        assert_implementation_review()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Local bootstrap entrypoint for docs/predictions artifacts."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import update_jobs  # noqa: E402

NON_ERROR_STATES = {
    "generated",
    "already_generated",
    "insufficient_history",
    "history_missing",
    "no_api_key",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate docs/predictions.json from docs/market-history.json using Gemini."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate predictions even if today's artifact already exists.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable status JSON after the run.",
    )
    args = parser.parse_args()

    result = update_jobs.predict_hiring_trends(force=args.force)
    state = result.get("state", "unknown")
    message = result.get("message", "No status message provided.")

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Prediction pipeline state: {state}")
        print(message)

    return 0 if state in NON_ERROR_STATES else 1


if __name__ == "__main__":
    raise SystemExit(main())

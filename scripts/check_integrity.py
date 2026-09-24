#!/usr/bin/env python3
"""Pipeline artifact integrity checker.

Validates the pipeline output dir (the optional first argument, else
$NGJ_OUTPUT_DIR, default site/public) — see quality.run_integrity_checks for
the full list: jobs.json contract, jobs-index.json/description-shard/feed.xml/
health.json consistency with jobs.json, URL safety. Prints a JSON report and
exits 1 when any check fails.

    python scripts/check_integrity.py [OUTPUT_DIR]
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path

from ngj.settings import resolve_output_dir
from quality import run_integrity_checks


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    repo_root = Path(__file__).resolve().parent.parent
    artifacts_dir = Path(args[0]) if args else resolve_output_dir(repo_root)
    ok, report = run_integrity_checks(artifacts_dir)
    print(json.dumps(report, indent=2))
    for error in report["errors"]:
        print(f"::error::integrity: {error}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Pipeline artifact integrity checker.

Checks, in the pipeline output dir ($NGJ_OUTPUT_DIR, default site/public):
- required artifacts exist and parse
- contract/schema compatibility
- count sanity across artifacts
- health consistency with published jobs
"""

from __future__ import annotations

import json
from pathlib import Path

from ngj.settings import resolve_output_dir
from quality import run_integrity_checks


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    ok, report = run_integrity_checks(resolve_output_dir(repo_root))
    print(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

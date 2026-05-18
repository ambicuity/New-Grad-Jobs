#!/usr/bin/env python3
"""Pipeline artifact integrity checker.

Checks:
- required artifacts exist and parse
- contract/schema compatibility
- count sanity across artifacts
- health consistency with published jobs
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from quality import run_integrity_checks
except ModuleNotFoundError:
    from scripts.quality import run_integrity_checks


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    ok, report = run_integrity_checks(repo_root)
    print(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

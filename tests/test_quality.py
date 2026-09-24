#!/usr/bin/env python3

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from quality import run_integrity_checks  # noqa: E402


def test_run_integrity_checks_fails_on_missing_artifacts(tmp_path: Path) -> None:
    out = tmp_path / 'public'
    out.mkdir(parents=True)
    ok, report = run_integrity_checks(out)
    assert ok is False
    assert report['status'] == 'failed'
    assert any('missing jobs.json' in err for err in report['errors'])

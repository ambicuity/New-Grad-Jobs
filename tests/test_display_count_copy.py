#!/usr/bin/env python3
"""Regression guards for displayed count copy drift in docs/README surfaces."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent
COUNT_SURFACES = [
    ROOT / "README.md",
    ROOT / "docs" / "index.html",
    ROOT / "docs" / "stats.html",
    ROOT / "docs" / "contributors.html",
    ROOT / "docs" / "app.js",
]


def test_no_stale_hardcoded_company_count_marketing_copy() -> None:
    """Public-facing count copy should not hardcode stale scale numbers."""
    stale_literals = re.compile(r"\b(?:150\+|70\+)\b")

    offenders = []
    for path in COUNT_SURFACES:
        content = path.read_text(encoding="utf-8")
        if stale_literals.search(content):
            offenders.append(str(path.relative_to(ROOT)))

    assert not offenders, (
        "Found stale hardcoded marketing count literals (150+/70+) in: "
        + ", ".join(offenders)
    )

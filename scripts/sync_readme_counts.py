#!/usr/bin/env python3
"""Sync the README job-count tokens to match docs/jobs.json.

README.md is a human-maintained document; the only piece of it the automated
pipeline owns is the set of count tokens marked by HTML comments:

    <!-- COUNT:<id> -->42<!-- /COUNT -->

Only the digits between the two markers are ever rewritten — no line is added,
removed, or reordered. Job tables, prose, and badges are untouched.

This is invoked from scripts/update_jobs.py after each scrape; it is also safe
to run by hand from the repo root::

    python scripts/sync_readme_counts.py
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
from typing import Dict, Mapping

# The marker regex. Strict: only ASCII digits between markers; id is
# [a-z_], so "total" and category ids like "software_engineering" match.
COUNT_TOKEN_RE = re.compile(
    r"<!--\s*COUNT:(?P<id>[a-z_]+)\s*-->(?P<value>\d+)<!--\s*/COUNT\s*-->"
)


def read_counts_from_jobs_json(jobs_path: pathlib.Path) -> Dict[str, int]:
    """Return {"total": N, "<category_id>": N, ...} from docs/jobs.json."""
    with open(jobs_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    meta = data.get("meta", {}) or {}
    counts: Dict[str, int] = {"total": int(meta.get("total_jobs", 0))}
    for cat in meta.get("categories", []) or []:
        cid = cat.get("id")
        if cid:
            counts[cid] = int(cat.get("count", 0))
    return counts


def apply_counts_to_readme(readme_text: str, counts: Mapping[str, int]) -> str:
    """Rewrite the digit portion of every recognised COUNT marker in README.

    - Markers whose id is not in `counts` are left unchanged.
    - Ids in `counts` whose marker is absent from README are silently skipped.
    - All non-marker bytes are byte-identical to the input.

    Raises TypeError/ValueError if any count value is not a non-negative integer.
    """
    for cid, val in counts.items():
        if isinstance(val, bool) or not isinstance(val, int):
            raise TypeError(
                f"sync_readme_counts: value for {cid!r} must be int, got {type(val).__name__}"
            )
        if val < 0:
            raise ValueError(f"sync_readme_counts: value for {cid!r} is negative: {val}")

    def repl(match: re.Match) -> str:
        cid = match.group("id")
        if cid not in counts:
            return match.group(0)
        return f"<!-- COUNT:{cid} -->{counts[cid]}<!-- /COUNT -->"

    return COUNT_TOKEN_RE.sub(repl, readme_text)


def sync_readme_counts(repo_root: pathlib.Path) -> bool:
    """Update README.md in place from docs/jobs.json. Returns True if changed."""
    repo_root = pathlib.Path(repo_root)
    readme_path = repo_root / "README.md"
    jobs_path = repo_root / "docs" / "jobs.json"

    if not readme_path.exists() or not jobs_path.exists():
        # First-run scenarios or missing artifacts shouldn't crash the scraper.
        return False

    counts = read_counts_from_jobs_json(jobs_path)
    original = readme_path.read_text(encoding="utf-8")
    updated = apply_counts_to_readme(original, counts)

    if updated == original:
        return False

    readme_path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    changed = sync_readme_counts(repo_root)
    print(f"sync_readme_counts: {'updated' if changed else 'no changes'} README.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Sync the README job-count tokens and "Last updated" stamp to match docs/jobs.json.

README.md is a human-maintained document; the pieces the automated pipeline
owns are:

  1. Count tokens marked by HTML comments:
         <!-- COUNT:<id> -->42<!-- /COUNT -->
     Only the digits between the two markers are ever rewritten.

  2. The trailing "Last updated" line at the bottom of the file:
         *Last updated: YYYY-MM-DD HH:MM:SS UTC*
     The timestamp is rewritten from `meta.generated_at` in docs/jobs.json so
     it advances on every scrape rather than rotting until someone edits it by
     hand. The surrounding line, prose, and tables are untouched.

This is invoked from scripts/update_jobs.py after each scrape; it is also safe
to run by hand from the repo root::

    python scripts/sync_readme_counts.py
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
from datetime import datetime, timezone
from typing import Dict, Mapping, Optional

# The marker regex. Strict: only ASCII digits between markers; id is
# [a-z_], so "total" and category ids like "software_engineering" match.
COUNT_TOKEN_RE = re.compile(
    r"<!--\s*COUNT:(?P<id>[a-z_]+)\s*-->(?P<value>\d+)<!--\s*/COUNT\s*-->"
)

# The trailing "*Last updated: ... UTC*" line. Anchored to the line itself
# (italic, prefix "Last updated:", suffix "UTC"), tolerant of whitespace
# and any non-asterisk timestamp content the prior script or a human wrote.
LAST_UPDATED_RE = re.compile(
    r"\*Last updated:\s*[^*]*?UTC\*"
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


def read_generated_at_from_jobs_json(jobs_path: pathlib.Path) -> Optional[datetime]:
    """Return the parsed `meta.generated_at` as a UTC datetime, or None if absent/invalid."""
    with open(jobs_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    raw = (data.get("meta") or {}).get("generated_at")
    if not raw or not isinstance(raw, str):
        return None
    try:
        # fromisoformat handles "+00:00" offsets and trailing microseconds; the
        # legacy "Z" suffix is handled by replacing with the explicit offset.
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def format_last_updated(ts: datetime) -> str:
    """Format a UTC datetime as the canonical README "Last updated" stamp."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    ts = ts.astimezone(timezone.utc)
    return f"*Last updated: {ts.strftime('%Y-%m-%d %H:%M:%S')} UTC*"


def apply_last_updated_to_readme(readme_text: str, ts: Optional[datetime]) -> str:
    """Rewrite the trailing "*Last updated: ... UTC*" line in README.

    No-op if:
      * `ts` is None (jobs.json had no parseable generated_at), or
      * README has no recognisable "Last updated: ... UTC" line.

    The marker is intentionally absent from this contract — the line itself is
    its own marker. This keeps the README readable for humans skimming the
    bottom of the file.
    """
    if ts is None:
        return readme_text
    if not LAST_UPDATED_RE.search(readme_text):
        return readme_text
    return LAST_UPDATED_RE.sub(format_last_updated(ts), readme_text, count=1)


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
    """Update README.md in place from docs/jobs.json. Returns True if changed.

    Rewrites both the COUNT-marker tokens and the trailing "Last updated" line.
    A no-op `apply_*` call (no markers found, or already in sync) is safe.
    """
    repo_root = pathlib.Path(repo_root)
    readme_path = repo_root / "README.md"
    jobs_path = repo_root / "docs" / "jobs.json"

    if not readme_path.exists() or not jobs_path.exists():
        # First-run scenarios or missing artifacts shouldn't crash the scraper.
        return False

    counts = read_counts_from_jobs_json(jobs_path)
    generated_at = read_generated_at_from_jobs_json(jobs_path)

    original = readme_path.read_text(encoding="utf-8")
    updated = apply_counts_to_readme(original, counts)
    updated = apply_last_updated_to_readme(updated, generated_at)

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

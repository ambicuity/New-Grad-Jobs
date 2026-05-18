#!/usr/bin/env python3
"""Tests for scripts/sync_readme_counts.py.

The README contains marker-bounded count tokens that must stay in sync with the
totals reported in docs/jobs.json. The sync helper:
  * reads counts from docs/jobs.json,
  * rewrites only the digits inside <!-- COUNT:<id> -->…<!-- /COUNT --> markers,
  * leaves every other byte of README.md untouched.

The final test in this module is the CI invariant the user asked for: README and
docs/jobs.json must agree at HEAD.
"""

import json
import pathlib
import re

import pytest

from sync_readme_counts import (
    COUNT_TOKEN_RE,
    apply_counts_to_readme,
    read_counts_from_jobs_json,
    sync_readme_counts,
)


REPO_ROOT = pathlib.Path(__file__).parent.parent


def _fixture_jobs_payload(total: int, categories: list[tuple[str, int]]) -> dict:
    return {
        "meta": {
            "generated_at": "2026-05-18T00:00:00",
            "total_jobs": total,
            "categories": [
                {"id": cid, "name": cid.replace("_", " ").title(), "emoji": "X", "count": n}
                for cid, n in categories
            ],
        },
        "jobs": [],
    }


# ---------------------------------------------------------------------------
# read_counts_from_jobs_json
# ---------------------------------------------------------------------------

def test_read_counts_extracts_total_and_categories(tmp_path) -> None:
    jobs_path = tmp_path / "jobs.json"
    jobs_path.write_text(json.dumps(_fixture_jobs_payload(
        total=997,
        categories=[("software_engineering", 540), ("other", 179)],
    )))

    counts = read_counts_from_jobs_json(jobs_path)

    assert counts == {
        "total": 997,
        "software_engineering": 540,
        "other": 179,
    }


# ---------------------------------------------------------------------------
# apply_counts_to_readme — marker-bounded substitution
# ---------------------------------------------------------------------------

GOLDEN_README = """# Title

## 📂 Browse <!-- COUNT:total -->1011<!-- /COUNT --> Jobs by Category

💻 [Software Engineering](#software-engineering) (<!-- COUNT:software_engineering -->568<!-- /COUNT -->)

📊 [Data Engineering](#data-engineering) (<!-- COUNT:data_engineering -->19<!-- /COUNT -->)

---

| Company | Role |
|---------|------|
| Waymo   | SWE  |
"""


def test_apply_counts_rewrites_only_marker_contents() -> None:
    counts = {"total": 997, "software_engineering": 540, "data_engineering": 19}

    updated = apply_counts_to_readme(GOLDEN_README, counts)

    # Numeric tokens inside markers updated:
    assert "<!-- COUNT:total -->997<!-- /COUNT -->" in updated
    assert "<!-- COUNT:software_engineering -->540<!-- /COUNT -->" in updated
    assert "<!-- COUNT:data_engineering -->19<!-- /COUNT -->" in updated

    # Job table row is byte-identical to the input:
    assert "| Waymo   | SWE  |" in updated
    # No new or missing lines:
    assert len(updated.splitlines()) == len(GOLDEN_README.splitlines())


def test_apply_counts_leaves_unknown_markers_alone() -> None:
    counts = {"total": 997}  # no entry for software_engineering or data_engineering
    updated = apply_counts_to_readme(GOLDEN_README, counts)
    # Unknown ids preserve their original digits:
    assert "<!-- COUNT:software_engineering -->568<!-- /COUNT -->" in updated
    assert "<!-- COUNT:total -->997<!-- /COUNT -->" in updated


def test_apply_counts_ignores_extraneous_ids() -> None:
    # An id with no marker in the README should be silently skipped, not raise.
    counts = {"total": 997, "ghost_category": 42}
    updated = apply_counts_to_readme(GOLDEN_README, counts)
    assert "ghost_category" not in updated


def test_apply_counts_is_idempotent() -> None:
    counts = {"total": 997, "software_engineering": 540, "data_engineering": 19}
    once = apply_counts_to_readme(GOLDEN_README, counts)
    twice = apply_counts_to_readme(once, counts)
    assert once == twice


def test_apply_counts_only_writes_digits() -> None:
    """The regex must reject non-digit content; markers can't be used to smuggle text."""
    counts = {"total": "999; DROP TABLE jobs"}  # type: ignore[dict-item]
    with pytest.raises((TypeError, ValueError)):
        apply_counts_to_readme(GOLDEN_README, counts)


# ---------------------------------------------------------------------------
# sync_readme_counts — end-to-end on a tmp copy
# ---------------------------------------------------------------------------

def test_sync_readme_counts_end_to_end(tmp_path) -> None:
    # Mimic repo layout: <root>/README.md and <root>/docs/jobs.json
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "jobs.json").write_text(json.dumps(_fixture_jobs_payload(
        total=997,
        categories=[("software_engineering", 540), ("data_engineering", 19)],
    )))
    (tmp_path / "README.md").write_text(GOLDEN_README)

    sync_readme_counts(tmp_path)

    written = (tmp_path / "README.md").read_text()
    assert "<!-- COUNT:total -->997<!-- /COUNT -->" in written
    assert "<!-- COUNT:software_engineering -->540<!-- /COUNT -->" in written
    assert "<!-- COUNT:data_engineering -->19<!-- /COUNT -->" in written


def test_sync_readme_counts_idempotent_when_in_sync(tmp_path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "jobs.json").write_text(json.dumps(_fixture_jobs_payload(
        total=997, categories=[("software_engineering", 540)],
    )))
    (tmp_path / "README.md").write_text(apply_counts_to_readme(
        GOLDEN_README, {"total": 997, "software_engineering": 540, "data_engineering": 19},
    ))
    before = (tmp_path / "README.md").read_text()
    sync_readme_counts(tmp_path)
    sync_readme_counts(tmp_path)
    after = (tmp_path / "README.md").read_text()
    assert before == after


# ---------------------------------------------------------------------------
# COUNT_TOKEN_RE: matches only the strict form
# ---------------------------------------------------------------------------

def test_count_token_re_matches_strict_form() -> None:
    assert COUNT_TOKEN_RE.search("<!-- COUNT:foo_bar -->42<!-- /COUNT -->")
    # Bare placeholder without digits is NOT a valid token.
    assert not COUNT_TOKEN_RE.search("<!-- COUNT:foo -->abc<!-- /COUNT -->")


# ---------------------------------------------------------------------------
# Cross-artifact invariant: README and docs/jobs.json agree at HEAD.
# This is the CI gate the user asked for.
# ---------------------------------------------------------------------------

def test_repo_readme_matches_jobs_json() -> None:
    """README counts at HEAD must match docs/jobs.json counts.

    If this fails, run `python scripts/sync_readme_counts.py` and commit the diff.
    The scraper does this automatically on every scheduled run.
    """
    jobs_path = REPO_ROOT / "docs" / "jobs.json"
    readme_path = REPO_ROOT / "README.md"

    counts_from_data = read_counts_from_jobs_json(jobs_path)
    readme_text = readme_path.read_text(encoding="utf-8")

    # Pull each marker's value out of README:
    counts_from_readme: dict[str, int] = {}
    for m in COUNT_TOKEN_RE.finditer(readme_text):
        counts_from_readme[m.group("id")] = int(m.group("value"))

    if not counts_from_readme:
        pytest.skip("README has no COUNT markers yet (run sync once to add them).")

    mismatches = []
    for cid, expected in counts_from_data.items():
        if cid in counts_from_readme and counts_from_readme[cid] != expected:
            mismatches.append(
                f"  {cid}: README={counts_from_readme[cid]} jobs.json={expected}"
            )
    assert not mismatches, (
        "README counts are out of sync with docs/jobs.json:\n"
        + "\n".join(mismatches)
        + "\nRun: python scripts/sync_readme_counts.py"
    )

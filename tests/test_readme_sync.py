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

from datetime import datetime, timezone, timedelta

from sync_readme_counts import (
    COUNT_TOKEN_RE,
    LAST_UPDATED_RE,
    apply_counts_to_readme,
    apply_last_updated_to_readme,
    format_last_updated,
    read_counts_from_jobs_json,
    read_generated_at_from_jobs_json,
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

# ---------------------------------------------------------------------------
# Last-updated stamp
# ---------------------------------------------------------------------------

def test_read_generated_at_parses_iso_with_microseconds_and_offset(tmp_path) -> None:
    jobs_path = tmp_path / "jobs.json"
    jobs_path.write_text(json.dumps({
        "meta": {"generated_at": "2026-05-26T19:52:33.997303+00:00", "total_jobs": 0, "categories": []},
        "jobs": [],
    }))
    ts = read_generated_at_from_jobs_json(jobs_path)
    assert ts == datetime(2026, 5, 26, 19, 52, 33, 997303, tzinfo=timezone.utc)


def test_read_generated_at_handles_z_suffix(tmp_path) -> None:
    jobs_path = tmp_path / "jobs.json"
    jobs_path.write_text(json.dumps({
        "meta": {"generated_at": "2026-05-26T19:52:33Z", "total_jobs": 0, "categories": []},
        "jobs": [],
    }))
    ts = read_generated_at_from_jobs_json(jobs_path)
    assert ts == datetime(2026, 5, 26, 19, 52, 33, tzinfo=timezone.utc)


def test_read_generated_at_returns_none_on_missing_or_invalid(tmp_path) -> None:
    cases = [
        {"meta": {}, "jobs": []},
        {"meta": {"generated_at": None}, "jobs": []},
        {"meta": {"generated_at": ""}, "jobs": []},
        {"meta": {"generated_at": "not-a-date"}, "jobs": []},
    ]
    for i, payload in enumerate(cases):
        jobs_path = tmp_path / f"jobs_{i}.json"
        jobs_path.write_text(json.dumps(payload))
        assert read_generated_at_from_jobs_json(jobs_path) is None


def test_format_last_updated_normalizes_to_utc() -> None:
    # Non-UTC input is converted to UTC.
    pacific = timezone(timedelta(hours=-7))
    ts = datetime(2026, 5, 26, 12, 30, 0, tzinfo=pacific)
    assert format_last_updated(ts) == "*Last updated: 2026-05-26 19:30:00 UTC*"

    # Naive datetimes are assumed UTC.
    naive = datetime(2026, 1, 1, 0, 0, 0)
    assert format_last_updated(naive) == "*Last updated: 2026-01-01 00:00:00 UTC*"


def test_apply_last_updated_rewrites_existing_line() -> None:
    readme = (
        "⭐ **Star this repo** to stay updated with the latest new grad opportunities!\n"
        "\n"
        "*Last updated: 2026-03-12 05:46:03 UTC*\n"
    )
    ts = datetime(2026, 5, 26, 19, 52, 33, tzinfo=timezone.utc)
    out = apply_last_updated_to_readme(readme, ts)
    assert "2026-03-12 05:46:03" not in out
    assert "*Last updated: 2026-05-26 19:52:33 UTC*" in out


def test_apply_last_updated_is_noop_when_ts_none() -> None:
    readme = "*Last updated: 2026-03-12 05:46:03 UTC*\n"
    assert apply_last_updated_to_readme(readme, None) == readme


def test_apply_last_updated_is_noop_when_line_absent() -> None:
    readme = "Some README without any last-updated line.\n"
    ts = datetime(2026, 5, 26, 19, 52, 33, tzinfo=timezone.utc)
    assert apply_last_updated_to_readme(readme, ts) == readme


def test_apply_last_updated_only_rewrites_first_match() -> None:
    # Defensive: if a future edit accidentally introduces multiple lines, we
    # only replace one so a runaway substitution can't corrupt the file.
    readme = (
        "*Last updated: 2025-01-01 00:00:00 UTC*\n"
        "Middle prose.\n"
        "*Last updated: 2026-01-01 00:00:00 UTC*\n"
    )
    ts = datetime(2026, 5, 26, 19, 52, 33, tzinfo=timezone.utc)
    out = apply_last_updated_to_readme(readme, ts)
    assert out.count("*Last updated: 2026-05-26 19:52:33 UTC*") == 1
    # Second line stays untouched.
    assert "*Last updated: 2026-01-01 00:00:00 UTC*" in out


def test_sync_readme_counts_rewrites_both_counts_and_stamp(tmp_path) -> None:
    jobs_path = tmp_path / "docs" / "jobs.json"
    jobs_path.parent.mkdir()
    jobs_path.write_text(json.dumps({
        "meta": {
            "generated_at": "2026-05-26T19:52:33.997303+00:00",
            "total_jobs": 1358,
            "categories": [
                {"id": "software_engineering", "name": "SWE", "emoji": "💻", "count": 880},
            ],
        },
        "jobs": [],
    }))
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        "# Repo\n"
        "<!-- COUNT:total -->0<!-- /COUNT -->\n"
        "<!-- COUNT:software_engineering -->0<!-- /COUNT -->\n"
        "\n"
        "*Last updated: 2026-03-12 05:46:03 UTC*\n"
    )

    changed = sync_readme_counts(tmp_path)
    assert changed is True

    text = readme_path.read_text(encoding="utf-8")
    assert "<!-- COUNT:total -->1358<!-- /COUNT -->" in text
    assert "<!-- COUNT:software_engineering -->880<!-- /COUNT -->" in text
    assert "*Last updated: 2026-05-26 19:52:33 UTC*" in text
    assert "2026-03-12" not in text


def test_repo_readme_last_updated_matches_jobs_json() -> None:
    """README's trailing "Last updated" line must reflect docs/jobs.json.

    If this fails, run `python scripts/sync_readme_counts.py` and commit the
    diff (the scheduled scrape does this automatically going forward).
    """
    jobs_path = REPO_ROOT / "docs" / "jobs.json"
    readme_path = REPO_ROOT / "README.md"

    ts = read_generated_at_from_jobs_json(jobs_path)
    if ts is None:
        pytest.skip("docs/jobs.json has no parseable generated_at.")

    readme_text = readme_path.read_text(encoding="utf-8")
    match = LAST_UPDATED_RE.search(readme_text)
    if not match:
        pytest.skip("README has no Last-updated line yet (run sync once to add it).")

    assert match.group(0) == format_last_updated(ts), (
        f"README 'Last updated' is out of sync with docs/jobs.json.\n"
        f"  README:    {match.group(0)}\n"
        f"  jobs.json: {format_last_updated(ts)}\n"
        f"Run: python scripts/sync_readme_counts.py"
    )


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

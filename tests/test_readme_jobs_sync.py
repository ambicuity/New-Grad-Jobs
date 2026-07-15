#!/usr/bin/env python3
"""Tests for the live README category-table generator (scripts/sync_readme_jobs.py)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from sync_readme_jobs import (  # noqa: E402
    END_MARKER,
    START_MARKER,
    TOP_N,
    render_category_listings,
    sync_readme_jobs,
)


def _job(cid, title, posted_at, company="Acme", closed=False, url="https://x.co/1", tier=None):
    return {
        "company": company,
        "title": title,
        "location": "Remote",
        "url": url,
        "posted_at": posted_at,
        "posted_display": posted_at[:10] if posted_at else "",
        "is_closed": closed,
        "category": {"id": cid},
        "company_tier": {"emoji": tier} if tier else {},
    }


def _data(jobs, categories):
    return {"jobs": jobs, "meta": {"total_jobs": len(jobs), "categories": categories}}


def test_block_has_markers_and_headings():
    data = _data(
        [_job("software_engineering", "SWE", "2026-07-10")],
        [{"id": "software_engineering", "name": "Software Engineering", "emoji": "💻", "count": 1}],
    )
    block = render_category_listings(data)
    assert block.startswith(START_MARKER)
    assert block.rstrip().endswith(END_MARKER)
    assert "## 💻 Software Engineering New Grad Roles" in block
    assert "[Back to top](#-2026-new-grad-positions)" in block
    assert "| Company | Role | Location | Posted | Apply |" in block


def test_top_n_cap_and_recency_sort():
    jobs = [_job("software_engineering", f"Role {i}", f"2026-07-{i:02d}") for i in range(1, 21)]
    data = _data(jobs, [{"id": "software_engineering", "name": "Software Engineering", "emoji": "💻", "count": 20}])
    block = render_category_listings(data)
    apply_rows = [ln for ln in block.splitlines() if "[Apply]" in ln]
    assert len(apply_rows) == TOP_N
    # newest first: Role 20 present, Role 1 (oldest) not among the top 10
    assert "Role 20" in block and "Role 19" in block
    assert "Role 01" not in block


def test_closed_jobs_excluded():
    jobs = [
        _job("security", "Open Sec Role", "2026-07-10", closed=False),
        _job("security", "Closed Sec Role", "2026-07-11", closed=True),
    ]
    data = _data(jobs, [{"id": "security", "name": "Security Engineering", "emoji": "🔒", "count": 1}])
    block = render_category_listings(data)
    assert "Open Sec Role" in block
    assert "Closed Sec Role" not in block


def test_view_all_link_only_when_more_than_shown():
    many = [_job("software_engineering", f"R{i}", f"2026-07-{i:02d}") for i in range(1, 16)]
    data = _data(many, [{"id": "software_engineering", "name": "Software Engineering", "emoji": "💻", "count": 15}])
    assert "View all 15 Software Engineering roles" in render_category_listings(data)

    few = [_job("quant_finance", "Quant", "2026-07-10")]
    data2 = _data(few, [{"id": "quant_finance", "name": "Quantitative Finance", "emoji": "📈", "count": 1}])
    assert "View all" not in render_category_listings(data2)


def test_pipe_in_title_is_sanitized():
    data = _data(
        [_job("other", "Analyst | Ops | Team", "2026-07-10")],
        [{"id": "other", "name": "Other", "emoji": "💼", "count": 1}],
    )
    block = render_category_listings(data)
    row = [ln for ln in block.splitlines() if "Analyst" in ln][0]
    # exactly 5 columns => 6 pipe separators; the title's pipes were replaced
    assert row.count("|") == 6
    assert "Analyst / Ops / Team" in row


def test_presentation_order_software_engineering_first():
    cats = [
        {"id": "security", "name": "Security Engineering", "emoji": "🔒", "count": 1},
        {"id": "software_engineering", "name": "Software Engineering", "emoji": "💻", "count": 1},
    ]
    jobs = [_job("security", "S", "2026-07-10"), _job("software_engineering", "E", "2026-07-10")]
    block = render_category_listings(_data(jobs, cats))
    assert block.index("Software Engineering New Grad") < block.index("Security Engineering New Grad")


def test_sync_rewrites_only_the_marked_block(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        f"# Title\n\nKeep me.\n\n{START_MARKER}\nOLD\n{END_MARKER}\n\n## Footer\nKeep me too.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir()
    import json

    (tmp_path / "docs" / "jobs.json").write_text(
        json.dumps(_data(
            [_job("other", "Role A", "2026-07-10")],
            [{"id": "other", "name": "Other", "emoji": "💼", "count": 1}],
        )),
        encoding="utf-8",
    )
    assert sync_readme_jobs(tmp_path) is True
    out = readme.read_text(encoding="utf-8")
    assert "Keep me." in out and "Keep me too." in out and "## Footer" in out
    assert "OLD" not in out
    assert "Role A" in out

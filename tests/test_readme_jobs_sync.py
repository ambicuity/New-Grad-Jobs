#!/usr/bin/env python3
"""Tests for the live README category-table generator (scripts/sync_readme_jobs.py)."""

import os
import sys
from datetime import UTC, datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from sync_readme_jobs import (  # noqa: E402
    END_MARKER,
    PRESENTATION_ORDER,
    START_MARKER,
    TOP_N,
    render_category_listings,
    sync_readme_jobs,
)


@pytest.fixture(autouse=True)
def _default_output_dir(monkeypatch):
    """jobs.json is read from <repo>/site/public unless NGJ_OUTPUT_DIR is set."""
    monkeypatch.delenv("NGJ_OUTPUT_DIR", raising=False)


def _job(cid, title, posted_at, company="Acme", closed=False, url="https://x.co/1", tier=None):
    return {
        "company": company,
        "title": title,
        "location": "Remote",
        "url": url,
        "posted_at": posted_at,
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
    # Plain heading (no emoji / no suffix) so the anchor matches the nav.
    assert "## Software Engineering\n" in block
    assert "💻" not in block  # no emoji in the generated block
    assert "[Back to top](#2026-new-grad-positions)" in block
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
    assert block.index("## Software Engineering") < block.index("## Security Engineering")


def test_sync_rewrites_only_the_marked_block(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        f"# Title\n\nKeep me.\n\n{START_MARKER}\nOLD\n{END_MARKER}\n\n## Footer\nKeep me too.\n",
        encoding="utf-8",
    )
    (tmp_path / "site" / "public").mkdir(parents=True)
    import json

    (tmp_path / "site" / "public" / "jobs.json").write_text(
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


# --------------------------------------------------------------------------- #
# Untrusted-input hardening: titles/companies/URLs come from scraped boards.
# --------------------------------------------------------------------------- #
def _one_row_block(**overrides):
    job = _job("other", overrides.pop("title", "Role"), "2026-07-10")
    job.update(overrides)
    return render_category_listings(_data([job], [{"id": "other", "name": "Other", "emoji": "💼", "count": 1}]))


def _row(block):
    return [ln for ln in block.splitlines() if ln.startswith("| ") and "Company" not in ln][0]


def test_html_in_company_is_escaped_not_rendered():
    row = _row(_one_row_block(company="Acme <img src=https://t.example/p.gif>"))
    assert "<img" not in row
    assert "&lt;img src=https\\://t.example/p.gif&gt;" in row


def test_markdown_specials_in_cells_are_escaped():
    row = _row(_one_row_block(title="[pwn](https://evil.com) *bold* _it_ `code` back\\slash"))
    assert "[pwn](https://evil.com)" not in row
    assert "\\[pwn\\]\\(https\\://evil.com\\)" in row
    assert "\\*bold\\*" in row and "\\_it\\_" in row and "\\`code\\`" in row
    assert "back\\\\slash" in row


def test_html_comment_markers_in_title_are_neutralized():
    block = _one_row_block(title=f"Evil {END_MARKER} <!-- hide the rest")
    assert block.count(END_MARKER) == 1
    assert block.rstrip().endswith(END_MARKER)
    assert "<!-- hide" not in block
    assert "&lt;!-- hide the rest" in block


def test_url_parenthesis_cannot_inject_a_second_link():
    row = _row(_one_row_block(url="https://a.com/x)[pwn](https://evil.com"))
    assert "[pwn](https://evil.com" not in row
    assert "[Apply](<https://a.com/x%29[pwn]%28https://evil.com>)" in row
    # The ")" that would close the first link is encoded; the rest stays
    # inert inside the <...> destination.
    assert "x)" not in row


def test_url_angle_brackets_spaces_and_pipes_are_percent_encoded():
    row = _row(_one_row_block(url="https://a.com/p q<b>|c"))
    assert "[Apply](<https://a.com/p%20q%3Cb%3E%7Cc>)" in row
    assert row.count("|") == 6


def test_unsafe_url_is_not_linked():
    row = _row(_one_row_block(url="javascript:alert(1)"))
    assert "javascript" not in row
    assert row.rstrip().endswith("| — |")


def test_normal_rows_render_readably():
    row = _row(_one_row_block(company="AT&T", title="Software Engineer (New Grad)",
                              url="https://boards.greenhouse.io/acme/jobs/123?gh_src=a&b=c"))
    assert "| AT&amp;T | Software Engineer \\(New Grad\\) |" in row
    assert "[Apply](<https://boards.greenhouse.io/acme/jobs/123?gh_src=a&b=c>)" in row


def _write_repo(tmp_path, readme_text):
    import json

    (tmp_path / "README.md").write_text(readme_text, encoding="utf-8")
    (tmp_path / "site" / "public").mkdir(parents=True)
    (tmp_path / "site" / "public" / "jobs.json").write_text(
        json.dumps(_data([_job("other", "Role A", "2026-07-10")],
                         [{"id": "other", "name": "Other", "emoji": "💼", "count": 1}])),
        encoding="utf-8",
    )


def test_duplicate_markers_raise_and_leave_readme_untouched(tmp_path):
    import pytest

    original = f"{START_MARKER}\nA\n{END_MARKER}\njunk\n{END_MARKER}\n"
    _write_repo(tmp_path, original)
    with pytest.raises(ValueError, match="CATEGORY-LISTINGS"):
        sync_readme_jobs(tmp_path)
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == original

    original2 = f"{START_MARKER}\nA\n{START_MARKER}\nB\n{END_MARKER}\n"
    (tmp_path / "README.md").write_text(original2, encoding="utf-8")
    with pytest.raises(ValueError, match="CATEGORY-LISTINGS"):
        sync_readme_jobs(tmp_path)


def test_hostile_title_sync_is_idempotent(tmp_path):
    import json

    _write_repo(tmp_path, f"# T\n\n{START_MARKER}\nOLD\n{END_MARKER}\n\nFooter\n")
    (tmp_path / "site" / "public" / "jobs.json").write_text(
        json.dumps(_data([_job("other", f"Evil {END_MARKER} <!--", "2026-07-10")],
                         [{"id": "other", "name": "Other", "emoji": "💼", "count": 1}])),
        encoding="utf-8",
    )
    assert sync_readme_jobs(tmp_path) is True
    first = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert sync_readme_jobs(tmp_path) is False  # second run is a no-op, no orphans
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == first
    assert first.count(END_MARKER) == 1 and first.rstrip().endswith("Footer")


def test_bare_urls_in_cells_are_not_autolinked():
    row = _row(_one_row_block(title="Apply at https://evil.com or WWW.evil.com"))
    # GFM extended autolinks trigger on "scheme://" and "www."; a backslash
    # escape keeps the text visible but inert.
    assert "https\\://evil.com" in row
    assert "WWW\\.evil.com" in row


def test_posted_column_is_rendered_from_posted_at_at_sync_time():
    """No baked posted_display: ages are computed from posted_at when rendering."""
    now = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)
    jobs = [
        _job("other", "Fresh", "2026-07-12T08:00:00Z"),
        _job("other", "Recent", "2026-07-09T08:00:00Z"),
        _job("other", "Older", "2026-06-01T08:00:00Z"),
        _job("other", "Undated", ""),
    ]
    block = render_category_listings(
        _data(jobs, [{"id": "other", "name": "Other", "emoji": "💼", "count": 4}]), now=now,
    )
    assert "| Fresh | Remote | Today |" in block
    assert "| Recent | Remote | 3 days ago |" in block
    assert "| Older | Remote | 2026-06-01 |" in block
    assert "| Undated | Remote | Unknown |" in block


def test_sync_reads_jobs_json_from_explicit_path(tmp_path):
    import json

    readme = tmp_path / "README.md"
    readme.write_text(f"{START_MARKER}\nOLD\n{END_MARKER}\n", encoding="utf-8")
    jobs_path = tmp_path / "somewhere" / "jobs.json"
    jobs_path.parent.mkdir()
    jobs_path.write_text(
        json.dumps(_data([_job("other", "Role B", "2026-07-10")],
                         [{"id": "other", "name": "Other", "emoji": "💼", "count": 1}])),
        encoding="utf-8",
    )
    assert sync_readme_jobs(tmp_path, jobs_path=jobs_path) is True
    assert "Role B" in readme.read_text(encoding="utf-8")


def test_zero_count_and_missing_categories_keep_their_section():
    """Every category section is rendered (nav anchors), with a placeholder line when empty."""
    data = _data(
        [_job("software_engineering", "SWE", "2026-07-10")],
        [
            {"id": "software_engineering", "name": "Software Engineering", "emoji": "💻", "count": 1},
            {"id": "quant_finance", "name": "Quantitative Finance", "emoji": "📈", "count": 0},
        ],
    )
    block = render_category_listings(data)
    headings = [ln[3:] for ln in block.splitlines() if ln.startswith("## ")]
    assert headings[0] == "Software Engineering"
    assert "Quantitative Finance" in headings  # zero count, present in meta
    assert "Hardware Engineering" in headings  # absent from meta entirely
    assert len(headings) == len(PRESENTATION_ORDER)
    assert block.count("_No open roles right now — check the [live board]") == len(PRESENTATION_ORDER) - 1

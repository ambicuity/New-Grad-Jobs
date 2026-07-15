#!/usr/bin/env python3
"""Regenerate the per-category job tables in README.md from docs/jobs.json.

The README's "Browse by Category" listings used to be a frozen, hand-maintained
snapshot that rotted (dead links, missing new roles) while the site refreshed
every 5 minutes. This module keeps them live: it rewrites *only* the block
between::

    <!-- CATEGORY-LISTINGS:START ... -->
    <!-- CATEGORY-LISTINGS:END -->

with, for each category, the ``TOP_N`` most recently posted **open** roles plus
a link to the live board for the complete, filterable list. Everything outside
the markers (badges, legend, About, contributing, …) is untouched.

Category order/names/emojis are read from ``docs/jobs.json`` ``meta.categories``
so this file never drifts from the scraper's taxonomy. Invoked from
scripts/update_jobs.py after each scrape; also safe to run by hand::

    python scripts/sync_readme_jobs.py
"""

from __future__ import annotations

import json
import pathlib
import re
from typing import Any, Dict, List

TOP_N = 10
LIVE_BOARD_URL = "https://jobs.riteshrana.engineer/"

# Presentation order for the README sections. The scraper's CATEGORY_PATTERNS is
# ordered for *matching precedence* (specialties first); this is the reader-facing
# order and matches the "Browse by Category" nav and the site's filter chips:
# the broad Software Engineering bucket leads, then its specialties, then the
# remaining disciplines.
PRESENTATION_ORDER = [
    "software_engineering",
    "frontend",
    "backend",
    "mobile",
    "security",
    "data_ml",
    "data_engineering",
    "infrastructure_sre",
    "product_management",
    "quant_finance",
    "hardware",
    "other",
]

START_MARKER = (
    "<!-- CATEGORY-LISTINGS:START - auto-generated from docs/jobs.json by "
    "scripts/sync_readme_jobs.py; do not edit by hand -->"
)
END_MARKER = "<!-- CATEGORY-LISTINGS:END -->"

_BLOCK_RE = re.compile(
    re.escape("<!-- CATEGORY-LISTINGS:START") + r".*?" + re.escape(END_MARKER),
    re.DOTALL,
)


def _cell(value: str) -> str:
    """Sanitize a value for a Markdown table cell (no pipes/newlines)."""
    return " ".join(str(value or "—").replace("|", "/").split()).strip() or "—"


def _company(job: Dict[str, Any]) -> str:
    emoji = (job.get("company_tier") or {}).get("emoji", "") or ""
    name = _cell(job.get("company", "—"))
    return f"{emoji} {name}".strip()


def _sort_key(job: Dict[str, Any]):
    # Most-recent first: ISO posted_at sorts chronologically; blanks sort last.
    return job.get("posted_at") or ""


def _recent_open_jobs(jobs: List[Dict[str, Any]], category_id: str, limit: int) -> List[Dict[str, Any]]:
    in_cat = [
        j
        for j in jobs
        if (j.get("category") or {}).get("id") == category_id and not j.get("is_closed")
    ]
    in_cat.sort(key=_sort_key, reverse=True)
    return in_cat[:limit]


def _render_table(rows: List[Dict[str, Any]]) -> str:
    lines = [
        "| Company | Role | Location | Posted | Apply |",
        "|---------|------|----------|--------|-------|",
    ]
    for job in rows:
        posted = _cell(job.get("posted_display") or (job.get("posted_at") or "")[:10])
        url = (job.get("url") or "").strip()
        apply_cell = f"[Apply]({url})" if url else "—"
        lines.append(
            f"| {_company(job)} | {_cell(job.get('title', '—'))} "
            f"| {_cell(job.get('location', '—'))} | {posted} | {apply_cell} |"
        )
    return "\n".join(lines)


def render_category_listings(data: Dict[str, Any]) -> str:
    """Return the full auto-generated block (markers included)."""
    jobs = data.get("jobs", []) or []
    meta = data.get("meta", {}) or {}
    categories = meta.get("categories", []) or []
    total = meta.get("total_jobs", len(jobs))

    # Present in reader-facing order; unknown ids keep their meta order at the end.
    order = {cid: i for i, cid in enumerate(PRESENTATION_ORDER)}
    categories = sorted(categories, key=lambda c: order.get(c.get("id"), len(order)))

    parts: List[str] = [
        START_MARKER,
        "",
        f"> 📋 **Live listings** — the {TOP_N} most recently posted roles per "
        f"category, refreshed every 5 minutes. Browse and filter all "
        f"**{total:,}** live roles on the **[live job board]({LIVE_BOARD_URL})**.",
        "",
    ]

    for cat in categories:
        cid = cat.get("id")
        name = cat.get("name", cid)
        emoji = cat.get("emoji", "")
        count = cat.get("count", 0)
        rows = _recent_open_jobs(jobs, cid, TOP_N)

        parts.append(f"## {emoji} {name} New Grad Roles".strip())
        parts.append("")
        parts.append("[Back to top](#-2026-new-grad-positions)")
        parts.append("")
        if rows:
            parts.append(_render_table(rows))
            parts.append("")
            if count > len(rows):
                parts.append(
                    f"**[→ View all {count:,} {name} roles on the live board]"
                    f"({LIVE_BOARD_URL})**"
                )
                parts.append("")
        else:
            parts.append("_No open roles in this category right now — "
                         f"check the [live board]({LIVE_BOARD_URL})._")
            parts.append("")

    parts.append(END_MARKER)
    return "\n".join(parts)


def sync_readme_jobs(repo_root: pathlib.Path | str = ".") -> bool:
    """Rewrite the category-listings block in README.md. Returns True if written."""
    repo_root = pathlib.Path(repo_root)
    readme_path = repo_root / "README.md"
    jobs_path = repo_root / "docs" / "jobs.json"

    readme = readme_path.read_text(encoding="utf-8")
    if not _BLOCK_RE.search(readme):
        print("sync_readme_jobs: CATEGORY-LISTINGS markers not found; skipping.")
        return False

    with open(jobs_path, encoding="utf-8") as f:
        data = json.load(f)

    new_block = render_category_listings(data)
    updated = _BLOCK_RE.sub(lambda _m: new_block, readme, count=1)
    if updated == readme:
        print("sync_readme_jobs: README.md already up to date.")
        return False
    readme_path.write_text(updated, encoding="utf-8")
    print("sync_readme_jobs: updated README.md category listings")
    return True


if __name__ == "__main__":
    import sys

    root = sys.argv[1] if len(sys.argv) > 1 else "."
    sync_readme_jobs(root)

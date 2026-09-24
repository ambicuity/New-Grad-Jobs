#!/usr/bin/env python3
"""Regenerate the per-category job tables in README.md from the generated jobs.json.

The README's "Browse by Category" listings used to be a frozen, hand-maintained
snapshot that rotted (dead links, missing new roles) while the site refreshed
about every 30 minutes. This module keeps them live: it rewrites *only* the block
between::

    <!-- CATEGORY-LISTINGS:START ... -->
    <!-- CATEGORY-LISTINGS:END -->

with, for each category, the ``TOP_N`` most recently posted **open** roles plus
a link to the live board for the complete, filterable list. Everything outside
the markers (badges, legend, About, contributing, …) is untouched.

Category order/names/emojis are read from jobs.json ``meta.categories`` so this
file never drifts from the scraper's taxonomy. jobs.json is read from the
pipeline output dir ($NGJ_OUTPUT_DIR, default site/public). The "Posted"
column is rendered at sync time from ``posted_at``. Invoked by the scraper
pipeline (ngj.pipeline) after each scrape; also safe to run by hand::

    python scripts/sync_readme_jobs.py
"""

from __future__ import annotations

import json
import logging
import pathlib
import re
from datetime import datetime
from typing import Any
from urllib.parse import quote

from ngj.dates import format_posted_date
from ngj.settings import resolve_output_dir
from url_safety import is_safe_url

logger = logging.getLogger(__name__)

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
    "<!-- CATEGORY-LISTINGS:START - auto-generated from the scraper output jobs.json by "
    "scripts/sync_readme_jobs.py; do not edit by hand -->"
)
END_MARKER = "<!-- CATEGORY-LISTINGS:END -->"

_START_PREFIX = "<!-- CATEGORY-LISTINGS:START"
_BLOCK_RE = re.compile(
    re.escape(_START_PREFIX) + r".*?" + re.escape(END_MARKER),
    re.DOTALL,
)

# Titles, companies and locations are scraped from third-party boards
# (LinkedIn/Indeed via JobSpy) and are untrusted. Escape everything GitHub
# would otherwise interpret: raw HTML (tracking pixels, ``<!--`` that hides the
# rest of the README or forges our END marker) and Markdown link/emphasis
# syntax. ``&`` is escaped first so the entities we emit are not double-escaped.
_HTML_ESCAPES = (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"))
_MD_SPECIALS = re.compile(r"([\\`*_\[\]()])")
# GFM "extended autolinks" turn bare ``https://…`` / ``www.…`` text into links;
# an escaped ``\:`` / ``\.`` keeps the text visible but not clickable.
_AUTOLINK_TRIGGERS = re.compile(r"(?i)(://|\bwww\.)")

# Characters that could terminate or confuse an ``<...>`` link destination or a
# GFM table row. Everything else is legal inside angle brackets.
_URL_ESCAPES = {
    "<": "%3C",
    ">": "%3E",
    "(": "%28",
    ")": "%29",
    "|": "%7C",
    "\\": "%5C",
    "`": "%60",
}


def _cell(value: str) -> str:
    """Sanitize an untrusted value for a Markdown table cell.

    Collapses whitespace, replaces pipes, backslash-escapes Markdown specials
    and entity-escapes ``& < >`` so no HTML (including comments) survives.
    """
    text = " ".join(str(value or "—").replace("|", "/").split()).strip() or "—"
    text = _MD_SPECIALS.sub(r"\\\1", text)
    text = _AUTOLINK_TRIGGERS.sub(lambda m: m.group(1).replace(":", "\\:").replace(".", "\\."), text)
    for raw, entity in _HTML_ESCAPES:
        text = text.replace(raw, entity)
    return text


def _apply_link(url: str) -> str:
    """Render ``[Apply](<url>)`` for a safe http(s) URL, else an em dash.

    The URL is wrapped in a CommonMark ``<...>`` destination, and every
    character that could end that destination, the link, a code span or the
    table row (``< > ( ) | \\ ` `` and whitespace) is percent-encoded, so a
    hostile URL cannot smuggle in a second link.
    """
    url = (url or "").strip()
    if not url or not is_safe_url(url):
        return "—"
    encoded = "".join(
        _URL_ESCAPES.get(ch) or (quote(ch, safe="") if ch.isspace() else ch)
        for ch in url
    )
    return f"[Apply](<{encoded}>)"


def _company(job: dict[str, Any]) -> str:
    return _cell(job.get("company", "—"))


def _sort_key(job: dict[str, Any]):
    # Most-recent first: ISO posted_at sorts chronologically; blanks sort last.
    return job.get("posted_at") or ""


def _recent_open_jobs(jobs: list[dict[str, Any]], category_id: str, limit: int) -> list[dict[str, Any]]:
    in_cat = [
        j
        for j in jobs
        if (j.get("category") or {}).get("id") == category_id and not j.get("is_closed")
    ]
    in_cat.sort(key=_sort_key, reverse=True)
    return in_cat[:limit]


def _posted(job: dict[str, Any], now: datetime | None) -> str:
    """Relative "Posted" text computed at render time ("Today", "3 days ago", date)."""
    posted_at = job.get("posted_at")
    if not posted_at:
        return "Unknown"
    return format_posted_date(posted_at, now)


def _render_table(rows: list[dict[str, Any]], now: datetime | None = None) -> str:
    lines = [
        "| Company | Role | Location | Posted | Apply |",
        "|---------|------|----------|--------|-------|",
    ]
    for job in rows:
        posted = _cell(_posted(job, now))
        apply_cell = _apply_link(job.get("url") or "")
        lines.append(
            f"| {_company(job)} | {_cell(job.get('title', '—'))} "
            f"| {_cell(job.get('location', '—'))} | {posted} | {apply_cell} |"
        )
    return "\n".join(lines)


def render_category_listings(data: dict[str, Any], now: datetime | None = None) -> str:
    """Return the full auto-generated block (markers included).

    ``now`` (UTC) anchors the relative "Posted" column; defaults to the current time.
    """
    jobs = data.get("jobs", []) or []
    meta = data.get("meta", {}) or {}
    categories = meta.get("categories", []) or []
    total = meta.get("total_jobs", len(jobs))

    # Present in reader-facing order; unknown ids keep their meta order at the end.
    order = {cid: i for i, cid in enumerate(PRESENTATION_ORDER)}
    categories = sorted(categories, key=lambda c: order.get(c.get("id"), len(order)))

    parts: list[str] = [
        START_MARKER,
        "",
        f"> **Live listings** — the {TOP_N} most recently posted roles per "
        f"category, refreshed about every 30 minutes. Browse and filter all "
        f"**{total:,}** live roles on the **[live job board]({LIVE_BOARD_URL})**.",
        "",
    ]

    for cat in categories:
        cid = cat.get("id")
        name = cat.get("name", cid)
        count = cat.get("count", 0)
        rows = _recent_open_jobs(jobs, cid, TOP_N)

        # Heading is the plain category name so its GitHub anchor matches the
        # "Browse by Category" nav links (e.g. "## Software Engineering" ->
        # #software-engineering).
        parts.append(f"## {name}")
        parts.append("")
        parts.append("[Back to top](#2026-new-grad-positions)")
        parts.append("")
        if rows:
            parts.append(_render_table(rows, now))
            parts.append("")
            if count > len(rows):
                parts.append(
                    f"**[View all {count:,} {name} roles on the live board]"
                    f"({LIVE_BOARD_URL})**"
                )
                parts.append("")
        else:
            parts.append("_No open roles in this category right now — "
                         f"check the [live board]({LIVE_BOARD_URL})._")
            parts.append("")

    parts.append(END_MARKER)
    return "\n".join(parts)


def sync_readme_jobs(repo_root: pathlib.Path | str = ".", jobs_path: pathlib.Path | None = None) -> bool:
    """Rewrite the category-listings block in README.md. Returns True if written.

    ``jobs_path`` defaults to ``<output dir>/jobs.json`` (see
    ngj.settings.resolve_output_dir).
    """
    repo_root = pathlib.Path(repo_root)
    readme_path = repo_root / "README.md"
    jobs_path = pathlib.Path(jobs_path) if jobs_path else resolve_output_dir(repo_root) / "jobs.json"

    readme = readme_path.read_text(encoding="utf-8")
    starts, ends = readme.count(_START_PREFIX), readme.count(END_MARKER)
    if starts > 1 or ends > 1:
        # A forged/duplicated marker would make the non-greedy block regex
        # stop early and leave orphaned rows behind on every run. Refuse to
        # touch the file so a human can repair it.
        raise ValueError(
            f"README.md has {starts} CATEGORY-LISTINGS START and {ends} END "
            "markers; expected exactly one of each. Fix README.md by hand."
        )
    if not _BLOCK_RE.search(readme):
        logger.info("sync_readme_jobs: CATEGORY-LISTINGS markers not found; skipping.")
        return False

    with open(jobs_path, encoding="utf-8") as f:
        data = json.load(f)

    new_block = render_category_listings(data)
    updated = _BLOCK_RE.sub(lambda _m: new_block, readme, count=1)
    if updated == readme:
        logger.info("sync_readme_jobs: README.md already up to date.")
        return False
    readme_path.write_text(updated, encoding="utf-8")
    logger.info("sync_readme_jobs: updated README.md category listings")
    return True


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    sync_readme_jobs(root)

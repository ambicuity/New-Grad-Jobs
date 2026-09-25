#!/usr/bin/env python3
"""Sync the README's configured-board counts and company list from config.yml.

The README used to quote hand-typed board counts ("Greenhouse: 170 configured
boards") and a hand-pasted company list that drifted from ``config.yml`` every
time a board was pruned or added. Both now derive from the config so the README
can never overstate coverage (hard rule: every published number is real).

Two README regions are owned by this module:

  1. ``boards_*`` COUNT markers, in the same ``<!-- COUNT:<id> -->N<!-- /COUNT -->``
     form that :mod:`sync_readme_counts` uses for job counts::

         <!-- COUNT:boards_greenhouse -->136<!-- /COUNT -->
         <!-- COUNT:boards_total -->272<!-- /COUNT -->

  2. The company list between::

         <!-- COMPANY-LISTINGS:START ... -->
         <!-- COMPANY-LISTINGS:END -->

Invoked by the scraper pipeline (ngj.pipeline) after each scrape; also safe to
run by hand from the repo root::

    python scripts/sync_readme_companies.py
"""

from __future__ import annotations

import html
import logging
import pathlib
import re
import sys
from collections.abc import Mapping
from typing import Any

from ngj.registry import source_registry
from ngj.settings import load_config
from sync_readme_counts import apply_counts_to_readme

logger = logging.getLogger(__name__)

# Company-API sources, in README presentation order.
BOARD_SOURCES: tuple[str, ...] = ("greenhouse", "ashby", "workday", "lever")
SOURCE_LABELS: dict[str, str] = {
    "greenhouse": "Greenhouse",
    "ashby": "Ashby",
    "workday": "Workday",
    "lever": "Lever",
}

START_MARKER = (
    "<!-- COMPANY-LISTINGS:START - auto-generated from config.yml by "
    "scripts/sync_readme_companies.py; do not edit by hand -->"
)
END_MARKER = "<!-- COMPANY-LISTINGS:END -->"

_START_PREFIX = "<!-- COMPANY-LISTINGS:START"
_BLOCK_RE = re.compile(re.escape(_START_PREFIX) + r".*?" + re.escape(END_MARKER), re.DOTALL)
_MD_SPECIALS = re.compile(r"([\\`*_\[\]#~|])")


def _company_name(entry: Any) -> str | None:
    if not isinstance(entry, Mapping):
        return None
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    return " ".join(name.split())


def read_boards_from_config(config: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    """Return ``{source: (company names sorted case-insensitively)}`` for every board source.

    Disabled or empty sources (per :func:`ngj.registry.source_registry`) map to
    an empty tuple, so the README shows 0 rather than a stale list.
    """
    registry = source_registry(config)
    boards: dict[str, tuple[str, ...]] = {}
    for source in BOARD_SOURCES:
        spec = registry.get(source)
        names = [n for n in map(_company_name, spec.units if spec else ()) if n]
        boards[source] = tuple(sorted(names, key=str.casefold))
    return boards


def board_counts(boards: Mapping[str, tuple[str, ...]]) -> dict[str, int]:
    """COUNT-marker ids (``boards_<source>`` plus ``boards_total``) to values."""
    counts = {f"boards_{source}": len(boards.get(source, ())) for source in BOARD_SOURCES}
    counts["boards_total"] = sum(counts.values())
    return counts


def _cell(name: str) -> str:
    """Escape a company name for inline Markdown (names come from config, but stay safe)."""
    return html.escape(_MD_SPECIALS.sub(r"\\\1", name), quote=False)


def render_companies_block(boards: Mapping[str, tuple[str, ...]]) -> str:
    """Render the marker-bounded company list."""
    lines = [START_MARKER, ""]
    for source in BOARD_SOURCES:
        names = boards.get(source, ())
        listed = ", ".join(_cell(n) for n in names) if names else "—"
        lines.append(f"**{SOURCE_LABELS[source]} ({len(names)})**: {listed}")
        lines.append("")
    lines.append(END_MARKER)
    return "\n".join(lines)


def apply_companies_block(readme_text: str, block: str) -> str:
    """Replace the COMPANY-LISTINGS block; no-op without markers, error on duplicates."""
    matches = _BLOCK_RE.findall(readme_text)
    if not matches:
        return readme_text
    if len(matches) > 1:
        raise ValueError("README has more than one COMPANY-LISTINGS block")
    return _BLOCK_RE.sub(lambda _m: block, readme_text, count=1)


def sync_readme_companies(repo_root: pathlib.Path | str = ".", config_path: pathlib.Path | None = None) -> bool:
    """Update README.md in place from config.yml. Returns True if changed."""
    repo_root = pathlib.Path(repo_root)
    readme_path = repo_root / "README.md"
    config_path = pathlib.Path(config_path) if config_path else repo_root / "config.yml"
    if not readme_path.exists() or not config_path.exists():
        return False

    boards = read_boards_from_config(load_config(config_path))
    original = readme_path.read_text(encoding="utf-8")
    updated = apply_counts_to_readme(original, board_counts(boards))
    updated = apply_companies_block(updated, render_companies_block(boards))
    if updated == original:
        return False
    readme_path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    changed = sync_readme_companies(repo_root)
    logger.info("sync_readme_companies: %s README.md", "updated" if changed else "no changes")
    return 0


if __name__ == "__main__":
    sys.exit(main())

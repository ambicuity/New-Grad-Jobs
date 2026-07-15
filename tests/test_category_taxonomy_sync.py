#!/usr/bin/env python3
"""Guard that the job-category taxonomy stays in sync across every surface.

The scraper's ``CATEGORY_PATTERNS`` (scripts/update_jobs.py) is the single
source of truth. These tests fail if the README count markers or the terminal
website (docs/terminal/*.jsx) drift away from it — the exact bug where
``product_management`` and ``quant_finance`` existed in the data but were
missing from the README and were silently folded into ``SWE`` on the site.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from update_jobs import CATEGORY_PATTERNS

_REPO = os.path.join(os.path.dirname(__file__), "..")
CANONICAL_IDS = set(CATEGORY_PATTERNS.keys())


def _read(*parts):
    with open(os.path.join(_REPO, *parts), encoding="utf-8") as f:
        return f.read()


def test_readme_has_a_count_marker_for_every_canonical_category():
    readme = _read("README.md")
    marker_ids = set(re.findall(r"<!--\s*COUNT:([a-z_]+)\s*-->", readme))
    marker_ids.discard("total")
    assert marker_ids == CANONICAL_IDS, (
        f"README category markers out of sync with CATEGORY_PATTERNS.\n"
        f"  missing from README: {sorted(CANONICAL_IDS - marker_ids)}\n"
        f"  extra in README:     {sorted(marker_ids - CANONICAL_IDS)}"
    )


def test_terminal_category_type_matches_canonical_ids():
    data_jsx = _read("docs", "terminal", "data.jsx")
    block = re.search(r"const CATEGORY_TYPE\s*=\s*\{(.*?)\}", data_jsx, re.DOTALL)
    assert block, "CATEGORY_TYPE object not found in data.jsx"
    keys = set(re.findall(r"(\w+):\s*'[A-Z]+'", block.group(1)))
    assert keys == CANONICAL_IDS, (
        f"Terminal CATEGORY_TYPE keys out of sync with CATEGORY_PATTERNS.\n"
        f"  missing on site: {sorted(CANONICAL_IDS - keys)}\n"
        f"  extra on site:   {sorted(keys - CANONICAL_IDS)}"
    )


def test_terminal_type_codes_are_consistent_across_map_labels_and_chips():
    data_jsx = _read("docs", "terminal", "data.jsx")
    dashboard = _read("docs", "terminal", "dashboard.jsx")

    cat_block = re.search(r"const CATEGORY_TYPE\s*=\s*\{(.*?)\}", data_jsx, re.DOTALL).group(1)
    code_values = set(re.findall(r":\s*'([A-Z]+)'", cat_block))

    label_block = re.search(r"const TYPE_LABEL\s*=\s*\{(.*?)\}", data_jsx, re.DOTALL).group(1)
    label_codes = set(re.findall(r"(\w+)\s*:", label_block))

    chip_block = re.search(r"\[((?:'[A-Z]+',?\s*)+)\]\.map\(t =>", dashboard).group(1)
    chip_codes = set(re.findall(r"'([A-Z]+)'", chip_block))

    assert code_values == label_codes, (
        f"TYPE_LABEL codes != CATEGORY_TYPE codes: "
        f"{code_values ^ label_codes}"
    )
    assert code_values == chip_codes, (
        f"dashboard filter chips != CATEGORY_TYPE codes: "
        f"{code_values ^ chip_codes}"
    )


def test_specialty_categories_are_backed_by_the_scraper():
    """Frontend/Backend/Mobile/Security are now real scraper categories, so the
    site's specialty filter chips must be present AND backed by CATEGORY_PATTERNS
    (i.e. not client-only title-regex types like the removed scheme)."""
    for specialty in ("frontend", "backend", "mobile", "security"):
        assert specialty in CANONICAL_IDS, f"{specialty} missing from CATEGORY_PATTERNS"

    dashboard = _read("docs", "terminal", "dashboard.jsx")
    chip_block = re.search(r"\[((?:'[A-Z]+',?\s*)+)\]\.map\(t =>", dashboard).group(1)
    chip_codes = set(re.findall(r"'([A-Z]+)'", chip_block))
    for code in ("FE", "BE", "MOBILE", "SEC"):
        assert code in chip_codes, f"specialty filter chip {code!r} missing"

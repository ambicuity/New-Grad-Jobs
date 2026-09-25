#!/usr/bin/env python3
"""Tests for scripts/sync_readme_companies.py.

The README's "Data Sources" and "Companies Monitored" sections used to quote
hand-typed board counts (170 / 72 / 92 / 7) that drifted from config.yml
(136 / 68 / 59 / 9). The sync helper derives both the ``boards_*`` COUNT
markers and the COMPANY-LISTINGS block from config.yml so they can no longer
disagree with the source of truth.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from sync_readme_companies import (
    BOARD_SOURCES,
    END_MARKER,
    START_MARKER,
    apply_companies_block,
    board_counts,
    read_boards_from_config,
    render_companies_block,
    sync_readme_companies,
)

REPO_ROOT = pathlib.Path(__file__).parent.parent


def _config(**overrides) -> dict:
    apis = {
        "greenhouse": {"companies": [{"name": "Stripe", "url": "u"}, {"name": "Affirm", "url": "u"}]},
        "lever": {"companies": [{"name": "Palantir", "url": "u"}]},
        "ashby": {"companies": [{"name": "OpenAI", "url": "u"}, {"name": "Notion", "url": "u"}, {"name": "Cursor", "url": "u"}]},
        "workday": {"enabled": True, "companies": [{"name": "Boeing", "workday_url": "u"}]},
        "google": {"enabled": False, "search_terms": ["x"]},
        "jobspy": {"enabled": True, "search_terms": ["x"]},
    }
    apis.update(overrides)
    return {"filtering": {}, "apis": apis}


# ---------------------------------------------------------------------------
# read_boards_from_config / board_counts
# ---------------------------------------------------------------------------

def test_read_boards_lists_every_company_source_sorted_by_name() -> None:
    boards = read_boards_from_config(_config())

    assert tuple(boards) == BOARD_SOURCES
    assert boards["greenhouse"] == ("Affirm", "Stripe")
    assert boards["ashby"] == ("Cursor", "Notion", "OpenAI")
    assert boards["workday"] == ("Boeing",)
    assert boards["lever"] == ("Palantir",)


def test_read_boards_skips_disabled_and_empty_sources() -> None:
    config = _config(workday={"enabled": False, "companies": [{"name": "Boeing", "workday_url": "u"}]}, lever={"companies": []})

    boards = read_boards_from_config(config)

    assert boards["workday"] == ()
    assert boards["lever"] == ()
    assert boards["greenhouse"] == ("Affirm", "Stripe")


def test_read_boards_ignores_entries_without_a_name() -> None:
    config = _config(lever={"companies": [{"url": "u"}, "not-a-mapping", {"name": "  ", "url": "u"}, {"name": "Palantir", "url": "u"}]})

    assert read_boards_from_config(config)["lever"] == ("Palantir",)


def test_board_counts_uses_marker_ids_and_a_total() -> None:
    counts = board_counts(read_boards_from_config(_config()))

    assert counts == {
        "boards_greenhouse": 2,
        "boards_lever": 1,
        "boards_ashby": 3,
        "boards_workday": 1,
        "boards_total": 7,
    }


# ---------------------------------------------------------------------------
# render / apply the COMPANY-LISTINGS block
# ---------------------------------------------------------------------------

def test_render_block_lists_each_source_with_its_count() -> None:
    block = render_companies_block(read_boards_from_config(_config()))

    assert block.startswith(START_MARKER)
    assert block.rstrip().endswith(END_MARKER)
    assert "**Greenhouse (2)**: Affirm, Stripe" in block
    assert "**Ashby (3)**: Cursor, Notion, OpenAI" in block
    assert "**Workday (1)**: Boeing" in block
    assert "**Lever (1)**: Palantir" in block


def test_render_block_escapes_markdown_in_company_names() -> None:
    config = _config(lever={"companies": [{"name": "Evil <img src=x> *Corp* | Ltd", "url": "u"}]})

    block = render_companies_block(read_boards_from_config(config))

    assert "<img" not in block
    assert "*Corp*" not in block
    assert "&lt;img src=x&gt;" in block


def test_apply_replaces_only_the_marked_block() -> None:
    readme = f"before\n{START_MARKER}\nold stuff\n{END_MARKER}\nafter\n"

    updated = apply_companies_block(readme, f"{START_MARKER}\nnew stuff\n{END_MARKER}")

    assert updated == f"before\n{START_MARKER}\nnew stuff\n{END_MARKER}\nafter\n"


def test_apply_is_a_no_op_without_markers() -> None:
    readme = "no markers here\n"
    assert apply_companies_block(readme, "anything") == readme


def test_apply_rejects_duplicate_markers() -> None:
    readme = f"{START_MARKER}\na\n{END_MARKER}\n{START_MARKER}\nb\n{END_MARKER}\n"
    with pytest.raises(ValueError):
        apply_companies_block(readme, "x")


# ---------------------------------------------------------------------------
# sync_readme_companies end to end
# ---------------------------------------------------------------------------

def _write_repo(tmp_path: pathlib.Path, readme: str, config: dict) -> pathlib.Path:
    (tmp_path / "README.md").write_text(readme, encoding="utf-8")
    (tmp_path / "config.yml").write_text(yaml.safe_dump(config), encoding="utf-8")
    return tmp_path


def test_sync_rewrites_counts_and_block_from_config(tmp_path) -> None:
    readme = (
        "Greenhouse: <!-- COUNT:boards_greenhouse -->170<!-- /COUNT --> boards\n"
        "Total <!-- COUNT:boards_total -->341<!-- /COUNT -->\n"
        "Jobs <!-- COUNT:total -->999<!-- /COUNT -->\n"
        f"{START_MARKER}\nstale\n{END_MARKER}\n"
    )
    repo = _write_repo(tmp_path, readme, _config())

    assert sync_readme_companies(repo) is True

    updated = (repo / "README.md").read_text(encoding="utf-8")
    assert "<!-- COUNT:boards_greenhouse -->2<!-- /COUNT -->" in updated
    assert "<!-- COUNT:boards_total -->7<!-- /COUNT -->" in updated
    assert "<!-- COUNT:total -->999<!-- /COUNT -->" in updated, "job counts belong to sync_readme_counts"
    assert "stale" not in updated
    assert "**Greenhouse (2)**: Affirm, Stripe" in updated


def test_sync_returns_false_when_already_in_sync(tmp_path) -> None:
    repo = _write_repo(tmp_path, "x\n", _config())
    assert sync_readme_companies(repo) is False


def test_sync_returns_false_when_files_are_missing(tmp_path) -> None:
    assert sync_readme_companies(tmp_path) is False


# ---------------------------------------------------------------------------
# The real README must carry the markers and agree with the real config
# ---------------------------------------------------------------------------

def test_real_readme_board_counts_match_config() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    with open(REPO_ROOT / "config.yml", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    counts = board_counts(read_boards_from_config(config))

    for marker_id, expected in counts.items():
        assert f"<!-- COUNT:{marker_id} -->{expected}<!-- /COUNT -->" in readme, (
            f"README marker {marker_id} does not match config.yml ({expected}); "
            "run scripts/sync_readme_companies.py"
        )
    assert START_MARKER in readme and END_MARKER in readme
    assert apply_companies_block(readme, render_companies_block(read_boards_from_config(config))) == readme

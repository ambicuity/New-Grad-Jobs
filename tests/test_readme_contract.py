#!/usr/bin/env python3
"""Tests for the README.md / docs/ staging contract (issue #156).

The scraper must NOT write README.md.  README.md is a static, human-maintained
document.  Only docs/ artefacts (jobs.json, market-history.json, health.json,
feed.xml) may be written by the automated pipeline.

These tests act as a persistent regression guard so the contract cannot drift
again without a test failure surfacing the violation.
"""
import ast
import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
SCRAPER = ROOT / "scripts" / "update_jobs.py"
WORKFLOW = ROOT / ".github" / "workflows" / "update-jobs.yml"


# ---------------------------------------------------------------------------
# Guard A: scraper must not define or call generate_readme
# ---------------------------------------------------------------------------

def _scraper_ast() -> ast.Module:
    return ast.parse(SCRAPER.read_text(encoding="utf-8"))


def test_scraper_does_not_define_generate_readme() -> None:
    """generate_readme function must not exist in update_jobs.py."""
    tree = _scraper_ast()
    defined = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    ]
    assert "generate_readme" not in defined, (
        "generate_readme is defined in update_jobs.py — README.md "
        "generation was re-introduced.  See issue #156."
    )


def test_scraper_does_not_open_readme() -> None:
    """update_jobs.py must not open() a path containing 'README'."""
    tree = _scraper_ast()
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            fn_name = (
                fn.id if isinstance(fn, ast.Name)
                else fn.attr if isinstance(fn, ast.Attribute)
                else ""
            )
            if fn_name == "open" and node.args:
                arg_str = ast.unparse(node.args[0])
                if "README" in arg_str or "readme" in arg_str.lower():
                    violations.append(f"line {node.lineno}: open({arg_str!r})")
    assert not violations, (
        "update_jobs.py opens a README path — README.md generation "
        "was re-introduced.  See issue #156.\n" + "\n".join(violations)
    )


def test_scraper_docstring_does_not_mention_readme() -> None:
    """Module-level docstring must not claim the scraper updates README.md."""
    source = SCRAPER.read_text(encoding="utf-8")
    # Only check the first 20 lines (module docstring area)
    header = "\n".join(source.splitlines()[:20])
    assert "README.md" not in header, (
        "Module docstring still mentions README.md — update it to reflect "
        "the current contract.  See issue #156."
    )


# ---------------------------------------------------------------------------
# Guard B: update-jobs.yml must not stage README.md
# ---------------------------------------------------------------------------

def test_workflow_does_not_stage_readme() -> None:
    """update-jobs.yml git-add step must not include README.md."""
    content = WORKFLOW.read_text(encoding="utf-8")
    # Matches "git add README.md" with optional surrounding tokens
    match = re.search(r"git add\s+[^\n]*README\.md", content)
    assert match is None, (
        f"update-jobs.yml stages README.md: {match.group()!r}\n"
        "README.md must not be committed by the automated scraper workflow.  "
        "See issue #156."
    )


def test_workflow_stages_docs_files() -> None:
    """update-jobs.yml must stage at least one docs/ file."""
    content = WORKFLOW.read_text(encoding="utf-8")
    assert "git add docs/" in content or "git add docs/jobs.json" in content, (
        "update-jobs.yml does not stage any docs/ files.  "
        "Expected 'git add docs/jobs.json ...'  See issue #156."
    )

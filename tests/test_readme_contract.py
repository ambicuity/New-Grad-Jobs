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
    """generate_readme must not be defined or called in update_jobs.py."""
    tree = _scraper_ast()
    # Check: no function definition
    defined = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    ]
    assert "generate_readme" not in defined, (
        "generate_readme is defined in update_jobs.py — README.md "
        "generation was re-introduced.  See issue #156."
    )
    # Check: no call site (ast.Name or ast.Attribute)
    called = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and (
            (isinstance(node.func, ast.Name) and node.func.id == "generate_readme")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "generate_readme")
        )
    ]
    assert not called, (
        f"generate_readme is called at line(s) "
        f"{[n.lineno for n in called]} in update_jobs.py — README.md "
        "generation was re-introduced.  See issue #156."
    )


def _readme_open_violations(tree: ast.Module) -> list[str]:
    """Return a list of AST violation strings for any open() call that targets README.

    Handles:
    - positional arg:   open("README.md", ...)
    - keyword arg:      open(file="README.md", ...)
    - attribute open:   Path("README.md").open(...)  /  pathlib.Path(...).open(...)
    """
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func

        # open(...) as a plain name or attribute (e.g. builtins.open)
        if isinstance(fn, ast.Name) and fn.id == "open":
            _check_open_args(node, violations)

        elif isinstance(fn, ast.Attribute) and fn.attr == "open":
            # Path("README.md").open() — check the receiver, not the call args
            receiver_str = ast.unparse(fn.value)
            if "readme" in receiver_str.lower():
                violations.append(
                    f"line {node.lineno}: <expr>.open() on {receiver_str!r}"
                )
            # Also check any args passed to .open() itself
            _check_open_args(node, violations)

    return violations


def _check_open_args(node: ast.Call, violations: list[str]) -> None:
    """Append a violation string if any open() argument names a README path."""
    candidates: list[str] = []
    # Positional arg[0] is the file path
    if node.args:
        candidates.append(ast.unparse(node.args[0]))
    # Keyword arg named "file"
    candidates.extend(
        ast.unparse(kw.value) for kw in node.keywords if kw.arg == "file"
    )
    for arg_str in candidates:
        if "README" in arg_str or "readme" in arg_str.lower():
            violations.append(f"line {node.lineno}: open({arg_str!r})")


def test_scraper_does_not_open_readme() -> None:
    """update_jobs.py must not open() a path containing 'README' (any form)."""
    tree = _scraper_ast()
    violations = _readme_open_violations(tree)
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
    """update-jobs.yml must stage the required docs/ artifacts."""
    content = WORKFLOW.read_text(encoding="utf-8")
    required = ["docs/jobs.json", "docs/health.json", "docs/feed.xml"]
    missing = [f for f in required if f not in content]
    assert not missing, (
        "update-jobs.yml is missing required docs/ artifacts in git add: "
        + ", ".join(missing)
        + "  See issue #156."
    )

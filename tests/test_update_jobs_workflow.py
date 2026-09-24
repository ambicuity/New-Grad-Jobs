#!/usr/bin/env python3
"""Behavioral tests for the persist job's commit/push step in update-jobs.yml.

The step's shell script is extracted from the workflow and run against real
throwaway git repositories (a bare "origin", a shallow "runner" checkout and an
"upstream" clone that races it), so these tests exercise the exact code that
runs in CI.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "update-jobs.yml"
STEP_NAME = "Commit and push changes"

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or shutil.which("bash") is None,
    reason="requires git and bash",
)


def _commit_step_script() -> str:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["persist"]["steps"]
    return next(s["run"] for s in steps if s.get("name") == STEP_NAME)


def _env(tmp_path: pathlib.Path) -> dict:
    # Isolate from the developer's git config (signing, hooks, templates) and
    # expose the running interpreter as `python`, as setup-python does in CI.
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    for name in ("python", "python3"):
        link = bindir / name
        if not link.exists():
            link.symlink_to(sys.executable)
    env = dict(os.environ)
    env.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
            "PATH": f"{bindir}{os.pathsep}{env.get('PATH', '')}",
        }
    )
    return env


def _git(cwd, env, *args, check=True):
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, check=check, capture_output=True, text=True
    )


def _write_site(repo: pathlib.Path, history_payload: dict) -> None:
    """Write the persistent state the persist job commits (README + history)."""
    data = repo / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "market-history.json").write_text(json.dumps(history_payload, indent=2) + "\n")
    (repo / "README.md").write_text(f"# Jobs ({len(history_payload['snapshots'])} snapshots)\n")


@pytest.fixture
def repos(tmp_path):
    env = _env(tmp_path)
    origin = tmp_path / "origin.git"
    _git(tmp_path, env, "init", "--bare", "-b", "main", str(origin))

    seed = tmp_path / "seed"
    _git(tmp_path, env, "init", "-b", "main", str(seed))
    _write_site(seed, {"snapshots": ["a", "b", "c"]})
    _git(seed, env, "add", "-A")
    _git(seed, env, "commit", "-m", "seed")
    _git(seed, env, "remote", "add", "origin", origin.as_uri())
    _git(seed, env, "push", "origin", "main")

    # Shallow checkout, as actions/checkout does with fetch-depth: 1.
    runner = tmp_path / "runner"
    _git(tmp_path, env, "clone", "--depth", "1", "-b", "main", origin.as_uri(), str(runner))
    upstream = tmp_path / "upstream"
    _git(tmp_path, env, "clone", "-b", "main", origin.as_uri(), str(upstream))
    return env, origin, runner, upstream


def _run_step(runner, env):
    # GitHub runs `run:` blocks with `bash -e {0}`.
    return subprocess.run(
        ["bash", "-e", "-c", _commit_step_script()],
        cwd=runner,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _origin_file(origin, env, path):
    return _git(origin, env, "show", f"main:{path}").stdout


def _origin_log(origin, env):
    return _git(origin, env, "log", "--format=%s", "main").stdout.splitlines()


def test_pushes_when_upstream_advanced_without_conflict(repos):
    env, origin, runner, upstream = repos
    (upstream / "CONTRIBUTING.md").write_text("hi\n")
    _git(upstream, env, "add", "CONTRIBUTING.md")
    _git(upstream, env, "commit", "-m", "docs: unrelated upstream change")
    _git(upstream, env, "push", "origin", "main")

    _write_site(runner, {"snapshots": ["fresh"]})
    result = _run_step(runner, env)

    assert result.returncode == 0, result.stdout + result.stderr
    log = _origin_log(origin, env)
    assert log[0] == "🤖 Update job listings [skip ci]"
    assert "docs: unrelated upstream change" in log
    assert json.loads(_origin_file(origin, env, "data/market-history.json")) == {"snapshots": ["fresh"]}


def test_conflicting_upstream_change_fails_without_pushing_markers(repos):
    env, origin, runner, upstream = repos
    (upstream / "data" / "market-history.json").write_text(json.dumps({"snapshots": ["upstream"]}, indent=2) + "\n")
    _git(upstream, env, "commit", "-am", "manual history edit")
    _git(upstream, env, "push", "origin", "main")
    before = _git(origin, env, "rev-parse", "main").stdout

    _write_site(runner, {"snapshots": ["fresh"]})
    result = _run_step(runner, env)

    assert result.returncode != 0, result.stdout + result.stderr
    assert _git(origin, env, "rev-parse", "main").stdout == before
    assert "<<<<<<<" not in _origin_file(origin, env, "data/market-history.json")
    # The runner is left clean: no half-finished rebase, no unmerged paths.
    assert not (runner / ".git" / "rebase-merge").exists()
    assert _git(runner, env, "diff", "--name-only", "--diff-filter=U").stdout == ""


def test_no_changes_is_a_successful_noop(repos):
    env, origin, runner, _ = repos
    before = _git(origin, env, "rev-parse", "main").stdout

    result = _run_step(runner, env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "No changes to commit" in result.stdout
    assert _git(origin, env, "rev-parse", "main").stdout == before


def test_invalid_generated_json_is_never_pushed(repos):
    env, origin, runner, _ = repos
    before = _git(origin, env, "rev-parse", "main").stdout
    _write_site(runner, {"snapshots": ["fresh"]})
    (runner / "data" / "market-history.json").write_text('{"truncated": \n')

    result = _run_step(runner, env)

    assert result.returncode != 0
    assert _git(origin, env, "rev-parse", "main").stdout == before


def test_conflict_markers_are_never_pushed(repos):
    env, origin, runner, _ = repos
    before = _git(origin, env, "rev-parse", "main").stdout
    _write_site(runner, {"snapshots": ["fresh"]})
    (runner / "README.md").write_text("<<<<<<< Updated upstream\n# Jobs\n=======\n>>>>>>> Stash\n")

    result = _run_step(runner, env)

    assert result.returncode != 0
    assert _git(origin, env, "rev-parse", "main").stdout == before


def test_step_does_not_use_autostash():
    # `git pull --autostash` exits 0 even when re-applying the stash conflicts,
    # which is how conflict markers used to get committed.
    code = [ln for ln in _commit_step_script().splitlines() if not ln.lstrip().startswith("#")]
    assert not any("--autostash" in ln for ln in code)

#!/usr/bin/env python3
"""Contract checks for stats forecast artifact loading and UI states."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
STATS_JS = ROOT / "docs" / "stats.js"
MAKEFILE = ROOT / "Makefile"
BOOTSTRAP_SCRIPT = ROOT / "scripts" / "generate_predictions.py"
CONTRACT_DOC = ROOT / "docs" / "predictions-artifacts.md"
UPDATE_JOBS_WORKFLOW = ROOT / ".github" / "workflows" / "update-jobs.yml"


def test_stats_js_includes_prediction_and_status_paths() -> None:
    content = STATS_JS.read_text(encoding="utf-8")
    required_paths = [
        "./predictions.json",
        "/New-Grad-Jobs/docs/predictions.json",
        "./predictions-status.json",
        "/New-Grad-Jobs/docs/predictions-status.json",
    ]
    missing = [path for path in required_paths if path not in content]
    assert not missing, f"Missing required forecast artifact paths in docs/stats.js: {missing}"


def test_stats_js_contains_explicit_prediction_states() -> None:
    content = STATS_JS.read_text(encoding="utf-8")
    required_states = [
        "pipeline_not_run",
        "artifact_missing",
        "no_api_key",
        "insufficient_history",
        "invalid_data",
        "fetch_failed",
        "generation_failed",
        "ready",
    ]
    missing = [state for state in required_states if f"'{state}'" not in content and f'"{state}"' not in content]
    assert not missing, f"Missing explicit forecast state handling in docs/stats.js: {missing}"


def test_local_bootstrap_command_is_exposed() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    assert "predict:" in makefile
    assert "generate_predictions.py" in makefile
    assert BOOTSTRAP_SCRIPT.exists(), "Local bootstrap script scripts/generate_predictions.py is missing"


def test_prediction_contract_document_exists() -> None:
    assert CONTRACT_DOC.exists(), "docs/predictions-artifacts.md must define the artifact contract"
    content = CONTRACT_DOC.read_text(encoding="utf-8")
    for required in (
        "docs/market-history.json",
        "docs/predictions.json",
        "docs/predictions-status.json",
        "Minimum history required",
        "make predict",
    ):
        assert required in content


def test_update_jobs_workflow_can_stage_prediction_status_artifact() -> None:
    content = UPDATE_JOBS_WORKFLOW.read_text(encoding="utf-8")
    assert "docs/predictions-status.json" in content


def test_update_jobs_workflow_skips_commit_push_for_non_main_dispatch() -> None:
    content = UPDATE_JOBS_WORKFLOW.read_text(encoding="utf-8")
    assert "if: github.ref != 'refs/heads/main'" in content
    assert "artifact verification run; commit/push skipped by design." in content
    assert "if: github.ref == 'refs/heads/main'" in content

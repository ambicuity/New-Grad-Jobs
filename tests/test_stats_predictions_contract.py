#!/usr/bin/env python3
"""Contract checks for stats forecast artifact loading and UI states."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = ROOT / "Makefile"
BOOTSTRAP_SCRIPT = ROOT / "scripts" / "generate_predictions.py"
CONTRACT_DOC = ROOT / "docs" / "predictions-artifacts.md"
UPDATE_JOBS_WORKFLOW = ROOT / ".github" / "workflows" / "update-jobs.yml"


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

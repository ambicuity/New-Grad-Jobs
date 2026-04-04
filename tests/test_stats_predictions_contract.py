#!/usr/bin/env python3
"""Contract checks for stats forecast artifact loading and UI states."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
STATS_JS = ROOT / "docs" / "stats.js"
MAKEFILE = ROOT / "Makefile"
BOOTSTRAP_SCRIPT = ROOT / "scripts" / "generate_predictions.py"
CONTRACT_DOC = ROOT / "docs" / "predictions-artifacts.md"
UPDATE_JOBS_WORKFLOW = ROOT / ".github" / "workflows" / "update-jobs.yml"
STATS_HTML = ROOT / "docs" / "stats.html"


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


def test_update_jobs_workflow_passes_google_api_key_to_scraper() -> None:
    content = UPDATE_JOBS_WORKFLOW.read_text(encoding="utf-8")
    assert "GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}" in content


def test_update_jobs_workflow_stages_prediction_artifacts_for_main_push() -> None:
    content = UPDATE_JOBS_WORKFLOW.read_text(encoding="utf-8")
    assert 'if [ -f "docs/predictions.json" ]; then' in content
    assert "git add docs/predictions.json" in content
    assert 'if [ -f "docs/predictions-status.json" ]; then' in content
    assert "git add docs/predictions-status.json" in content


def test_update_jobs_workflow_skips_commit_push_for_non_main_dispatch() -> None:
    content = UPDATE_JOBS_WORKFLOW.read_text(encoding="utf-8")
    assert "if: github.ref != 'refs/heads/main'" in content
    assert "artifact verification run; commit/push skipped by design." in content
    assert "if: github.ref == 'refs/heads/main'" in content


def test_update_jobs_workflow_uploads_prediction_artifacts_for_non_main_dispatch() -> None:
    content = UPDATE_JOBS_WORKFLOW.read_text(encoding="utf-8")
    assert "Upload prediction verification artifacts (non-main)" in content
    assert "uses: actions/upload-artifact" in content
    assert "if: github.ref != 'refs/heads/main'" in content
    assert "docs/predictions-status.json" in content
    assert "docs/predictions.json" in content
    assert "docs/market-history.json" in content
    assert "Publish prediction generation summary" in content
    assert "Prediction artifact status" in content


def test_stats_html_uses_versioned_stats_script_url() -> None:
    content = STATS_HTML.read_text(encoding="utf-8")
    assert 'src="stats.js?v=' in content


def test_stats_js_avoids_local_only_forecast_wording() -> None:
    content = STATS_JS.read_text(encoding="utf-8")
    assert "local run yet" not in content


def test_stats_js_renders_kpis_independently_of_forecast_state() -> None:
    content = STATS_JS.read_text(encoding="utf-8")
    assert "fetchJobsData()" in content
    assert "fetchPredictionStatus()" in content
    assert "renderStats(analysis, jobsData.meta.generated_at);" in content
    assert "renderPredictions(predictionRenderState);" in content
    assert content.index("renderStats(analysis, jobsData.meta.generated_at);") < content.index(
        "renderPredictions(predictionRenderState);"
    )


def test_stats_html_has_single_header_and_nav_containers() -> None:
    content = STATS_HTML.read_text(encoding="utf-8")
    assert content.count("<header class=\"header\">") == 1
    assert content.count("<div class=\"header-nav-desktop\">") == 1
    assert content.count("<div class=\"mobile-menu\" id=\"mobile-menu\"") == 1

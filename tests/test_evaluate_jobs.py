#!/usr/bin/env python3

import json

import evaluate_jobs
from contracts import EVALUATIONS_SCHEMA_VERSION, EVALUATION_PROMPT_VERSION, JOBS_SCHEMA_VERSION


def _base_job(**overrides) -> dict:
    job = {
        "schema_version": JOBS_SCHEMA_VERSION,
        "job_id": "job_abc123",
        "id": "acme-new-grad",
        "company": "Acme",
        "title": "New Grad Software Engineer",
        "location": "Remote - USA",
        "url": "https://example.com/jobs/abc123",
        "posted_at": "2026-04-10T00:00:00",
        "posted_display": "Today",
        "source": "Greenhouse",
        "category": {"id": "software_engineering", "name": "Software Engineering", "emoji": "💻"},
        "company_tier": {"tier": "unicorn", "emoji": "🚀", "label": "Unicorn"},
        "flags": {"no_sponsorship": False, "us_citizenship_required": False},
        "is_closed": False,
    }
    job.update(overrides)
    return job


def test_is_eligible_filters_closed_missing_id_and_bad_url() -> None:
    assert evaluate_jobs._is_eligible(_base_job()) is True
    assert evaluate_jobs._is_eligible(_base_job(is_closed=True)) is False
    assert evaluate_jobs._is_eligible(_base_job(job_id="")) is False
    assert evaluate_jobs._is_eligible(_base_job(url="careers.example.com/job")) is False


def test_score_job_returns_expected_reason_codes_and_bounds() -> None:
    score, confidence, reasons = evaluate_jobs._score_job(_base_job())

    assert score == 98.0
    assert confidence == 0.65
    assert "explicit_new_grad_signal" in reasons
    assert "core_track_signal" in reasons
    assert "high_signal_company_tier" in reasons
    assert "remote_friendly" in reasons
    assert "target_category" in reasons
    assert 0.0 <= score <= 100.0
    assert 0.0 <= confidence <= 1.0


def test_score_job_baseline_case_without_signals() -> None:
    score, confidence, reasons = evaluate_jobs._score_job(
        _base_job(
            title="Generalist",
            location="Onsite",
            category={"id": "other", "name": "Other", "emoji": "💼"},
            company_tier={"tier": "other", "emoji": "", "label": ""},
        )
    )

    assert score == 50.0
    assert confidence == 0.55
    assert reasons == []


def test_main_writes_evaluations_artifact_with_expected_meta(tmp_path, monkeypatch) -> None:
    repo_root = tmp_path
    docs_dir = repo_root / "docs"
    scripts_dir = repo_root / "scripts"
    docs_dir.mkdir(parents=True)
    scripts_dir.mkdir(parents=True)

    payload = {
        "meta": {
            "schema_version": JOBS_SCHEMA_VERSION,
            "generated_at": "2026-04-10T00:00:00",
            "total_jobs": 3,
            "categories": [],
        },
        "jobs": [
            _base_job(job_id="job_1"),
            _base_job(job_id="job_2", is_closed=True),
            _base_job(job_id="job_3", url="ftp://example.com/jobs/3"),
        ],
    }
    (docs_dir / "jobs.json").write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(
        evaluate_jobs,
        "Path",
        lambda *_args, **_kwargs: scripts_dir / "evaluate_jobs.py",
    )

    exit_code = evaluate_jobs.main()
    assert exit_code == 0

    output_path = docs_dir / "job-evaluations.json"
    assert output_path.exists()

    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output["schema_version"] == EVALUATIONS_SCHEMA_VERSION
    assert output["model"] == evaluate_jobs.MODEL_NAME
    assert output["prompt_version"] == EVALUATION_PROMPT_VERSION
    assert output["meta"]["total_jobs"] == 3
    assert output["meta"]["eligible_jobs"] == 1
    assert output["meta"]["evaluated_jobs"] == 1
    assert len(output["evaluations"]) == 1
    assert output["evaluations"][0]["job_id"] == "job_1"

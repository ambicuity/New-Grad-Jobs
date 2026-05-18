#!/usr/bin/env python3

import json

from contracts import JOBS_SCHEMA_VERSION
from quality import run_integrity_checks


def _valid_job() -> dict:
    return {
        "schema_version": JOBS_SCHEMA_VERSION,
        "job_id": "job_123",
        "id": "acme-swe-remote",
        "company": "Acme",
        "title": "Software Engineer",
        "location": "Remote",
        "url": "https://example.com/jobs/123",
        "posted_at": "2026-04-10T00:00:00",
        "posted_display": "Today",
        "source": "Greenhouse",
        "category": {"id": "software_engineering", "name": "Software Engineering", "emoji": "💻"},
        "company_tier": {"tier": "other", "emoji": "", "label": ""},
        "flags": {"no_sponsorship": False, "us_citizenship_required": False},
        "is_closed": False,
    }


def _valid_jobs_payload(total_jobs: int = 1) -> dict:
    jobs = [_valid_job()]
    return {
        "meta": {
            "schema_version": JOBS_SCHEMA_VERSION,
            "generated_at": "2026-04-10T00:00:00",
            "total_jobs": total_jobs,
            "categories": [],
        },
        "jobs": jobs,
    }


def _write_json(path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_run_integrity_checks_fails_when_health_artifact_missing(tmp_path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    _write_json(docs / "jobs.json", _valid_jobs_payload())

    ok, report = run_integrity_checks(tmp_path)

    assert ok is False
    assert report["status"] == "failed"
    assert any("missing docs/health.json" in err for err in report["errors"])


def test_run_integrity_checks_fails_for_invalid_jobs_json(tmp_path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "jobs.json").write_text("{invalid", encoding="utf-8")
    _write_json(docs / "health.json", {"total_jobs": 1})

    ok, report = run_integrity_checks(tmp_path)

    assert ok is False
    assert report["status"] == "failed"
    assert any("docs/jobs.json invalid JSON" in err for err in report["errors"])


def test_run_integrity_checks_reports_jobs_and_health_count_mismatches(tmp_path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    _write_json(docs / "jobs.json", _valid_jobs_payload(total_jobs=2))
    _write_json(docs / "health.json", {"total_jobs": 3})

    ok, report = run_integrity_checks(tmp_path)

    assert ok is False
    assert report["status"] == "failed"
    assert any("jobs count mismatch" in err for err in report["errors"])
    assert any("health total mismatch" in err for err in report["errors"])


def test_run_integrity_checks_surfaces_jobs_contract_errors(tmp_path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)

    bad_payload = _valid_jobs_payload()
    del bad_payload["jobs"][0]["job_id"]
    _write_json(docs / "jobs.json", bad_payload)
    _write_json(docs / "health.json", {"total_jobs": 1})

    ok, report = run_integrity_checks(tmp_path)

    assert ok is False
    assert report["status"] == "failed"
    assert any("jobs contract:" in err for err in report["errors"])

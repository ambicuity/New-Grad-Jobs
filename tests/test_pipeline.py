#!/usr/bin/env python3
"""End-to-end pipeline wiring with fake sources (no network), plus package hygiene."""

import importlib
import json
import logging
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from ngj import http as ngj_http  # noqa: E402
from ngj import pipeline  # noqa: E402
from ngj.enrich import enrich_jobs  # noqa: E402
from ngj.models import KIND_PARSE, KIND_UNEXPECTED, SourceError, SourceResult  # noqa: E402
from ngj.settings import Settings  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
NOW_ISO = datetime.now(UTC).isoformat()


def _job(company, title, url, location="New York, NY"):
    return {"company": company, "title": title, "url": url, "location": location,
            "posted_at": NOW_ISO, "source": "Fake", "description": "Build things."}


CONFIG = {
    "filtering": {
        "max_age_days": 30,
        "new_grad_signals": ["new grad"],
        "track_signals": ["software"],
        "exclusion_signals": ["senior"],
    },
    "apis": {"greenhouse": {"companies": [{"name": "x", "url": "https://x"}]}},
}


@pytest.fixture
def settings(tmp_path):
    return Settings(repo_root=tmp_path, output_dir=tmp_path / "public", history_path=tmp_path / "data" / "h.json")


def _plan(results):
    return lambda config, settings: {name: (lambda r=r: r) for name, r in results.items()}


def test_run_writes_all_artifacts_to_output_dir(settings, caplog):
    caplog.set_level(logging.INFO)
    good = SourceResult(jobs=(
        _job("Acme", "Software Engineer, New Grad", "https://jobs.acme.com/1"),
        _job("Acme", "Software Engineer, New Grad", "https://jobs.acme.com/1"),  # duplicate
        _job("Acme", "Senior Software Engineer, New Grad", "https://jobs.acme.com/2"),  # excluded
        _job("Beta", "Software Engineer, New Grad", "javascript:alert(1)"),  # unsafe URL
    ), raw_count=4)
    failed = SourceResult(errors=(SourceError("Gamma", "lever", KIND_PARSE, 200, "bad"),))

    with patch("ngj.pipeline.plan_sources", _plan({"greenhouse": good, "lever": failed})):
        summary = pipeline.run(CONFIG, settings, sync_readme=False)

    out = settings.output_dir
    for name in ("jobs.json", "jobs-index.json", "feed.xml", "health.json", "descriptions/0.json"):
        assert (out / name).exists(), name
    jobs = json.loads((out / "jobs.json").read_text())
    assert [j["url"] for j in jobs["jobs"]] == ["https://jobs.acme.com/1"]
    assert "posted_display" not in jobs["jobs"][0]

    health = json.loads((out / "health.json").read_text())
    assert health["source_counts"] == {"greenhouse": 4, "lever": 0}
    assert health["zero_sources"] == ["lever"]
    assert health["url_safety_blocked"] == 1
    assert health["status"] == "degraded"

    history = json.loads(settings.history_path.read_text())
    assert history["snapshots"][-1]["total_jobs"] == 1

    assert summary.published_jobs == 1
    assert summary.total_fetched == 4
    assert summary.source_results["lever"].errors[0].company == "Gamma"


def test_crashing_source_becomes_error_result_and_run_continues(settings):
    def boom():
        raise RuntimeError("kaboom")

    plan = {"greenhouse": lambda: SourceResult(jobs=(_job("Acme", "Software Engineer, New Grad", "https://jobs.acme.com/a1"),)),
            "workday": boom}
    with patch("ngj.pipeline.plan_sources", lambda c, s: plan):
        summary = pipeline.run(CONFIG, settings, sync_readme=False)

    assert summary.published_jobs == 1
    errors = summary.source_results["workday"].errors
    assert [(e.source, e.kind) for e in errors] == [("workday", KIND_UNEXPECTED)]


def test_corrupt_market_history_emits_actions_error_on_stdout(settings, capsys):
    settings.history_path.parent.mkdir(parents=True)
    settings.history_path.write_text("{not json")
    with patch("ngj.pipeline.plan_sources", _plan({})):
        pipeline.run(CONFIG, settings, sync_readme=False)
    out = capsys.readouterr().out
    assert "::error::Market history not updated (file left untouched)" in out
    assert settings.history_path.read_text() == "{not json"
    assert (settings.output_dir / "jobs.json").exists()


def test_run_syncs_readme_from_output_dir(settings):
    readme = settings.repo_root / "README.md"
    readme.write_text("<!-- COUNT:total -->0<!-- /COUNT -->\n")
    plan = {"greenhouse": lambda: SourceResult(jobs=(_job("Acme", "Software Engineer, New Grad", "https://jobs.acme.com/a1"),))}
    with patch("ngj.pipeline.plan_sources", lambda c, s: plan):
        pipeline.run(CONFIG, settings)
    assert readme.read_text() == "<!-- COUNT:total -->1<!-- /COUNT -->\n"


def test_enrich_jobs_does_not_mutate_inputs():
    job = _job("Google", "Software Engineer, New Grad", "https://careers.google.com/1")
    snapshot = dict(job)
    enriched = enrich_jobs([job])
    assert job == snapshot
    assert enriched[0] is not job
    assert enriched[0]["category"]["id"] == "software_engineering"
    assert enriched[0]["company_tier"]["tier"] == "faang_plus"


def test_company_tier_dicts_are_not_shared_between_jobs():
    a, b = enrich_jobs([_job("Google", "SWE New Grad", "https://careers.google.com/1"), _job("Google", "SWE New Grad", "https://careers.google.com/2")])
    a["company_tier"]["sectors"].append("mutated")
    assert b["company_tier"]["sectors"] == []


# ---------------------------------------------------------------------------
# Shared HTTP helpers
# ---------------------------------------------------------------------------

def test_fetch_json_with_retry_retries_parse_errors_then_reports(monkeypatch):
    monkeypatch.setattr(ngj_http, "limited_get", lambda url, **kw: MagicMock(status_code=200, json=lambda: {}))
    monkeypatch.setattr(ngj_http.time, "sleep", lambda s: None)
    calls = []

    def parse(data):
        calls.append(data)
        raise KeyError("jobs")

    result = ngj_http.fetch_json_with_retry("Acme", "greenhouse", "Greenhouse", "https://example.com/x", parse,
                                            timeout=5, max_retries=2)
    assert len(calls) == 3
    assert result.jobs == ()
    assert [(e.company, e.kind) for e in result.errors] == [("Acme", KIND_UNEXPECTED)]


def test_fan_out_merges_in_input_order_and_isolates_failures():
    import time as _time

    def fetch(n):
        if n == 2:
            raise ValueError("bad company")
        _time.sleep(0.01 * (5 - n))  # later items finish first
        return SourceResult(jobs=({"n": n},), raw_count=1)

    result = ngj_http.fan_out([1, 2, 3, 4], fetch, max_workers=4, source="lever",
                              describe=lambda n: f"co{n}", label="Lever")
    assert [job["n"] for job in result.jobs] == [1, 3, 4]
    assert [(e.company, e.kind) for e in result.errors] == [("co2", KIND_UNEXPECTED)]
    assert result.raw_count == 3


# ---------------------------------------------------------------------------
# Package hygiene
# ---------------------------------------------------------------------------

def test_importing_the_package_has_no_side_effects():
    """No HTTP session, no JobSpy warning, no output at import time."""
    code = (
        f"import sys; sys.path.insert(0, {str(SCRIPTS)!r})\n"
        "import ngj.pipeline, ngj.sources.jobspy, ngj.http\n"
        "assert ngj.http._session is None, 'session created at import'\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == ""
    assert proc.stderr == ""


def test_update_jobs_entrypoint_is_thin():
    module = importlib.import_module("update_jobs")
    assert module.main is pipeline.main
    source = (SCRIPTS / "update_jobs.py").read_text(encoding="utf-8")
    assert len(source.splitlines()) < 30


def test_get_session_is_lazy_and_reused(monkeypatch):
    monkeypatch.setattr(ngj_http, "_session", None)
    first = ngj_http.get_session()
    assert ngj_http.get_session() is first
    assert "gzip" in first.headers["Accept-Encoding"]

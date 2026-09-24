#!/usr/bin/env python3
"""Per-company failures are returned as SourceError instead of disappearing into logs."""

import os
import sys
from unittest.mock import MagicMock, patch

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from ngj import http as ngj_http  # noqa: E402
from ngj.models import (  # noqa: E402
    KIND_CONFIG,
    KIND_FORBIDDEN,
    KIND_HTTP,
    KIND_TIMEOUT,
    KIND_UNAVAILABLE,
    KIND_UNEXPECTED,
    SourceResult,
)
from ngj.sources.google import fetch_google_jobs  # noqa: E402
from ngj.sources.greenhouse import fetch_greenhouse_jobs  # noqa: E402
from ngj.sources.jobspy import fetch_jobspy_jobs  # noqa: E402
from ngj.sources.workday import fetch_workday_jobs  # noqa: E402
from source_cooldown import SourceCooldownTracker  # noqa: E402


def _response(status, payload=None):
    response = MagicMock()
    response.status_code = status
    response.ok = 200 <= status < 300
    response.json.return_value = payload if payload is not None else {}
    response.text = ""
    return response


def _workday(companies, post):
    with (
        patch("ngj.http.limited_post", side_effect=post),
        patch("ngj.sources.workday.get_workday_csrf_token", return_value=""),
        patch("ngj.http.get_session", return_value=MagicMock()),
        patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
    ):
        return fetch_workday_jobs(companies, max_retries=0)


def test_workday_http_error_is_reported_per_company_while_others_succeed():
    companies = [
        {"name": "Healthy", "workday_url": "https://healthy.wd1.myworkdayjobs.com/Careers"},
        {"name": "Broken", "workday_url": "https://broken.wd1.myworkdayjobs.com/Careers"},
    ]

    def post(url, **kwargs):
        if "broken" in url:
            return _response(500)
        offset = kwargs["json"]["offset"]
        postings = [{"title": "SWE", "externalPath": "/job/1", "postedOn": "Posted Today"}] if offset == 0 else []
        return _response(200, {"jobPostings": postings})

    result = _workday(companies, post)
    assert [job["company"] for job in result.jobs] == ["Healthy"]
    assert [(e.company, e.source, e.kind, e.status) for e in result.errors] == [("Broken", "workday", KIND_HTTP, 500)]


def test_workday_403_is_a_forbidden_error():
    result = _workday([{"name": "Blocked", "workday_url": "https://blocked.wd1.myworkdayjobs.com/C"}],
                      lambda url, **kw: _response(403))
    assert [(e.company, e.kind, e.status) for e in result.errors] == [("Blocked", KIND_FORBIDDEN, 403)]


def test_workday_exception_and_bad_config_are_reported():
    def post(url, **kwargs):
        raise RuntimeError("socket exploded")

    result = _workday([
        {"name": "Crashy", "workday_url": "https://crashy.wd1.myworkdayjobs.com/C"},
        {"name": "NoUrl"},
    ], post)
    assert [(e.company, e.kind) for e in result.errors] == [("Crashy", KIND_UNEXPECTED), ("NoUrl", KIND_CONFIG)]


def test_greenhouse_timeout_is_reported(monkeypatch):
    def timeout(url, **kwargs):
        raise requests.exceptions.Timeout("slow")

    monkeypatch.setattr(ngj_http, "limited_get", timeout)
    monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5))
    result = fetch_greenhouse_jobs("Slowco", "https://boards-api.greenhouse.io/v1/boards/slowco/jobs")
    assert [(e.company, e.source, e.kind) for e in result.errors] == [("Slowco", "greenhouse", KIND_TIMEOUT)]


def test_google_block_is_reported_as_forbidden():
    blocked = _response(429)
    blocked.raise_for_status.side_effect = requests.exceptions.HTTPError(response=blocked)
    with patch("ngj.http.limited_get", return_value=blocked):
        result = fetch_google_jobs(["term"], max_pages=1, max_retries=0)
    assert result.jobs == ()
    assert [(e.source, e.kind, e.status) for e in result.errors] == [("google", KIND_FORBIDDEN, 429)]


def test_jobspy_missing_library_is_reported():
    with patch("ngj.sources.jobspy.load_scrape_jobs", return_value=None):
        result = fetch_jobspy_jobs({"enabled": True})
    assert [(e.source, e.kind) for e in result.errors] == [("jobspy", KIND_UNAVAILABLE)]


def test_jobspy_failed_search_is_reported_and_other_searches_kept():
    import pandas as pd

    def scrape_jobs(site_name, search_term, **kwargs):
        if search_term == "bad":
            raise RuntimeError("blocked by indeed")
        return pd.DataFrame([{"title": "SWE New Grad", "company": "Acme", "job_url": "https://acme.com/1",
                              "location": "Remote", "date_posted": "2026-09-01", "description": ""}])

    config = {"enabled": True, "sites": ["indeed"], "search_terms": ["good", "bad"],
              "countries": [{"code": "USA", "location": "United States"}]}
    with (
        patch("ngj.sources.jobspy.load_scrape_jobs", return_value=scrape_jobs),
        patch("ngj.sources.jobspy.time.sleep"),
    ):
        result = fetch_jobspy_jobs(config, max_retries=1, workers=2)
    assert [job["company"] for job in result.jobs] == ["Acme"]
    assert [(e.company, e.kind) for e in result.errors] == [("indeed:bad:USA", KIND_UNEXPECTED)]


def test_source_result_merge_preserves_order_and_counts():
    a = SourceResult(jobs=({"n": 1},), raw_count=2)
    b = SourceResult.failure("X", "lever", KIND_HTTP, "HTTP 500", status=500)
    merged = SourceResult.merge([a, b])
    assert merged.jobs == ({"n": 1},)
    assert merged.raw_count == 2
    assert not merged.ok and a.ok

"""Greenhouse: list without content, hydrate descriptions for filter survivors only.

Also covers the no-duplicates guarantee of ``fetch_json_with_retry`` for the
board adapters (Greenhouse, Lever, Ashby).
"""

import io
import os
import sys
from unittest.mock import patch

import pytest
import requests
from urllib3.connectionpool import HTTPConnectionPool
from urllib3.response import HTTPResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ngj import http as ngj_http  # noqa: E402
from ngj.enrich import enrich_jobs  # noqa: E402
from ngj.models import KIND_UNEXPECTED  # noqa: E402
from ngj.sources import greenhouse  # noqa: E402
from ngj.sources.ashby import fetch_ashby_jobs  # noqa: E402
from ngj.sources.greenhouse import (  # noqa: E402
    fetch_greenhouse_jobs,
    hydrate_greenhouse_descriptions,
    posted_at,
)
from ngj.sources.lever import fetch_lever_jobs  # noqa: E402
from source_cooldown import SourceCooldownTracker  # noqa: E402

BOARD_URL = "https://boards-api.greenhouse.io/v1/boards/testco/jobs"


def _response(json_body, status=200):
    m = type("R", (), {})()
    m.status_code = status
    m.ok = 200 <= status < 300
    m.json = lambda: json_body
    m.text = ""
    return m


def _raw(job_id=1, **overrides):
    raw = {
        "id": job_id,
        "title": "Software Engineer, New Grad",
        "location": {"name": "Austin, TX"},
        "absolute_url": f"https://example.com/job/{job_id}",
        "first_published": "2026-09-01T00:00:00Z",
        "updated_at": "2026-09-20T00:00:00Z",
    }
    raw.update(overrides)
    return raw


# ---------------------------------------------------------------------------
# Phase 1: listing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (BOARD_URL, BOARD_URL),
        (BOARD_URL + "?content=true", BOARD_URL),
        (BOARD_URL + "?foo=bar&content=true", BOARD_URL + "?foo=bar"),
    ],
)
def test_list_is_requested_without_content(url, expected):
    captured = []
    with patch("ngj.http.limited_get", side_effect=lambda u, **kw: captured.append(u) or _response({"jobs": []})):
        fetch_greenhouse_jobs("TestCo", url)
    assert captured == [expected]


def test_listing_keeps_raw_fields_and_hydration_keys_only():
    with patch("ngj.http.limited_get", return_value=_response({"jobs": [_raw(7)]})):
        result = fetch_greenhouse_jobs("TestCo", BOARD_URL)
    [job] = result.jobs
    assert job["description"] == ""
    assert job["description_html"] == ""
    assert "comp" not in job  # derived in enrich, after filtering
    assert job[greenhouse.BOARD_KEY] == "testco"
    assert job[greenhouse.JOB_ID_KEY] == 7
    assert result.raw_count == 1


def test_missing_location_is_unknown_not_remote():
    with patch("ngj.http.limited_get", return_value=_response({"jobs": [_raw(location=None)]})):
        [job] = fetch_greenhouse_jobs("TestCo", BOARD_URL).jobs
    assert job["location"] == ""


def test_inline_content_is_kept_when_present():
    with patch("ngj.http.limited_get", return_value=_response({"jobs": [_raw(content="<p>Hi</p>")]})):
        [job] = fetch_greenhouse_jobs("TestCo", BOARD_URL).jobs
    assert job["description_html"] == "<p>Hi</p>"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ({"first_published": "A", "created_at": "B", "updated_at": "C"}, "A"),
        ({"created_at": "B", "updated_at": "C"}, "B"),
        ({"updated_at": "C"}, "C"),
        ({}, None),
    ],
)
def test_posted_at_prefers_first_published_over_updated_at(raw, expected):
    assert posted_at(raw) == expected


# ---------------------------------------------------------------------------
# Phase 2: hydration of survivors
# ---------------------------------------------------------------------------

def _listed_jobs(*ids):
    with patch("ngj.http.limited_get", return_value=_response({"jobs": [_raw(i) for i in ids]})):
        return list(fetch_greenhouse_jobs("TestCo", BOARD_URL).jobs)


def test_hydration_fetches_detail_only_for_given_jobs_and_keeps_order():
    jobs = _listed_jobs(1, 2, 3)
    survivors = [jobs[2], {"company": "Other", "title": "x", "source": "Lever", "description_html": "<p>l</p>"},
                 jobs[0]]
    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        job_id = url.rsplit("/", 1)[1]
        return _response({"id": int(job_id), "content": f"<p>Body {job_id}</p>"})

    with patch("ngj.http.limited_get", side_effect=fake_get):
        hydrated = hydrate_greenhouse_descriptions(survivors)

    assert sorted(calls) == [
        "https://boards-api.greenhouse.io/v1/boards/testco/jobs/1",
        "https://boards-api.greenhouse.io/v1/boards/testco/jobs/3",
    ]
    assert [j["description_html"] for j in hydrated] == ["<p>Body 3</p>", "<p>l</p>", "<p>Body 1</p>"]
    assert survivors[0]["description_html"] == ""  # inputs are not mutated
    assert hydrated[1] is survivors[1]


def test_hydration_failure_leaves_description_empty():
    jobs = _listed_jobs(5)
    with patch("ngj.http.limited_get", side_effect=requests.exceptions.Timeout("slow")):
        [job] = hydrate_greenhouse_descriptions(jobs)
    assert job["description_html"] == ""


def test_hydration_skips_jobs_that_already_have_content():
    jobs = [{**_listed_jobs(9)[0], "description_html": "<p>already</p>"}]
    with patch("ngj.http.limited_get") as get:
        assert hydrate_greenhouse_descriptions(jobs) == jobs
    get.assert_not_called()


def test_hydration_respects_board_cooldown(monkeypatch):
    tracker = SourceCooldownTracker(threshold=1)
    tracker.record_403(BOARD_URL)
    monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
    with patch("ngj.http.limited_get") as get:
        hydrate_greenhouse_descriptions(_listed_jobs(4))
    get.assert_not_called()


def test_hydrated_job_gets_description_and_comp_in_enrich():
    jobs = _listed_jobs(42)
    with patch("ngj.http.limited_get",
               return_value=_response({"id": 42, "content": "<p>The base salary range is $100,000 - $140,000.</p>"})):
        [enriched] = enrich_jobs(hydrate_greenhouse_descriptions(jobs))
    assert "base salary" in enriched["description"]
    assert enriched["comp"] == {"min": 100000, "max": 140000, "currency": "USD", "source": "posting"}


# ---------------------------------------------------------------------------
# No duplicates, no retry of deterministic parse failures
# ---------------------------------------------------------------------------

ADAPTERS = [
    pytest.param(fetch_greenhouse_jobs, BOARD_URL, {"jobs": [_raw(1), _raw(2)]}, id="greenhouse"),
    pytest.param(fetch_lever_jobs, "https://api.lever.co/v0/postings/testco",
                 [{"text": "SWE", "hostedUrl": "https://x/1"}, {"text": "SWE 2", "hostedUrl": "https://x/2"}],
                 id="lever"),
    pytest.param(fetch_ashby_jobs, "https://api.ashbyhq.com/posting-api/job-board/testco",
                 {"jobs": [{"title": "SWE", "jobUrl": "https://x/1"}, {"title": "SWE 2", "jobUrl": "https://x/2"}]},
                 id="ashby"),
]


@pytest.mark.parametrize(("fetch", "url", "body"), ADAPTERS)
def test_parse_failure_midway_is_reported_once_with_no_partial_jobs(fetch, url, body):
    """A record that breaks the mapper half-way through is deterministic: no retry, no partial list."""
    broken = body if isinstance(body, list) else body["jobs"]
    broken = [*broken[:1], "not-a-dict", *broken[1:]]
    payload = broken if isinstance(body, list) else {"jobs": broken}
    calls = []
    with patch("ngj.http.limited_get", side_effect=lambda u, **kw: calls.append(u) or _response(payload)):
        result = fetch("TestCo", url)
    assert len(calls) == 1
    assert result.jobs == ()
    assert [e.kind for e in result.errors] == [KIND_UNEXPECTED]


class _Wire:
    """Fake urllib3 wire: first a 503, then the real payload (transport-level retry)."""

    def __init__(self, monkeypatch, body: bytes):
        self.calls = 0
        wire = self

        def fake_make_request(pool, conn, method, url, *args, **kwargs):
            wire.calls += 1
            status, data = (503, b"") if wire.calls == 1 else (200, body)
            return HTTPResponse(body=io.BytesIO(data), status=status, headers={"Content-Type": "application/json"},
                                preload_content=False, request_method=method, request_url=url)

        monkeypatch.setattr(HTTPConnectionPool, "_make_request", fake_make_request)


def test_transport_retry_then_success_yields_each_job_once(monkeypatch):
    import json

    monkeypatch.setattr(ngj_http, "_session", ngj_http.create_session())
    monkeypatch.setattr("time.sleep", lambda s=0: None)
    wire = _Wire(monkeypatch, json.dumps({"jobs": [_raw(1), _raw(2)]}).encode())
    result = fetch_greenhouse_jobs("TestCo", BOARD_URL)
    assert wire.calls == 2
    assert [j["url"] for j in result.jobs] == ["https://example.com/job/1", "https://example.com/job/2"]
    assert result.errors == ()

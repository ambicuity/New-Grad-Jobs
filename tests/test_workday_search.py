"""Workday per-keyword search (apis.workday.search_filters.title_keywords)."""

import os
import sys
import threading
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ngj import pipeline  # noqa: E402
from ngj.models import KIND_CONFIG, KIND_HTTP, KIND_TIMEOUT  # noqa: E402
from ngj.settings import build_settings  # noqa: E402
from ngj.sources.workday import WORKDAY_MAX_PAGE_LIMIT, build_title_prefilter, fetch_workday_jobs  # noqa: E402

COMPANY = {"name": "Acme", "workday_url": "https://acme.wd5.myworkdayjobs.com/Careers"}
FILTERING = {"new_grad_signals": ["new grad", "junior"], "exclusion_signals": ["senior"]}


def _resp(items, status=200, body=None):
    m = MagicMock()
    m.status_code = status
    m.ok = 200 <= status < 300
    m.json.return_value = body if body is not None else {"jobPostings": items}
    m.text = ""
    return m


def _item(path, title="Software Engineer, New Grad"):
    return {"title": title, "externalPath": path, "locationsText": "Austin, TX", "postedOn": "Posted Today"}


class FakeTenant:
    """Serves per-keyword result lists in pages, recording every POST payload."""

    def __init__(self, results_by_keyword, page_size=20):
        self.results = results_by_keyword
        self.page_size = page_size
        self.payloads = []
        self._lock = threading.Lock()

    def __call__(self, url, json=None, **kwargs):
        with self._lock:
            self.payloads.append(dict(json))
        items = self.results.get(json["searchText"], [])
        return _resp(items[json["offset"]:json["offset"] + json["limit"]])

    def pages_for(self, keyword):
        return [p["offset"] for p in self.payloads if p["searchText"] == keyword]


def _fetch(tenant, **kwargs):
    with (
        patch("ngj.http.limited_post", side_effect=tenant),
        patch("ngj.sources.workday.get_workday_csrf_token", return_value=""),
        patch("ngj.http.get_session", return_value=MagicMock()),
    ):
        return fetch_workday_jobs([COMPANY], **kwargs)


def test_each_keyword_is_searched_and_results_are_deduplicated_by_external_path():
    tenant = FakeTenant({
        "new grad": [_item("/job/1"), _item("/job/2")],
        "junior": [_item("/job/2", "Junior Engineer"), _item("/job/3", "Junior Engineer")],
    })
    result = _fetch(tenant, search_keywords=["new grad", "junior"], title_filter=build_title_prefilter(FILTERING))
    assert sorted({p["searchText"] for p in tenant.payloads}) == ["junior", "new grad"]
    assert [j["url"] for j in result.jobs] == [
        "https://acme.wd5.myworkdayjobs.com/job/1",
        "https://acme.wd5.myworkdayjobs.com/job/2",
        "https://acme.wd5.myworkdayjobs.com/job/3",
    ]
    assert result.raw_count == 4
    assert result.errors == ()


def test_keyword_paging_stops_at_first_page_without_a_plausible_title():
    relevant = [_item(f"/job/{i}") for i in range(20)]
    irrelevant = [_item(f"/job/x{i}", "Staff Accountant") for i in range(60)]
    tenant = FakeTenant({"new grad": relevant + irrelevant})
    result = _fetch(tenant, search_keywords=["new grad"], title_filter=build_title_prefilter(FILTERING))
    assert tenant.pages_for("new grad") == [0, 20]  # page 2 had nothing relevant: stop
    assert len(result.jobs) == 40


def test_keyword_paging_is_capped_per_keyword():
    tenant = FakeTenant({"new grad": [_item(f"/job/{i}") for i in range(500)]})
    result = _fetch(tenant, search_keywords=["new grad"], max_jobs_per_keyword=60,
                    title_filter=build_title_prefilter(FILTERING))
    assert tenant.pages_for("new grad") == [0, 20, 40]
    assert len(result.jobs) == 60


def test_short_page_ends_the_keyword_without_an_extra_request():
    tenant = FakeTenant({"new grad": [_item("/job/1")]})
    _fetch(tenant, search_keywords=["new grad"])
    assert tenant.pages_for("new grad") == [0]


def test_total_cap_applies_across_keywords():
    tenant = FakeTenant({
        "new grad": [_item(f"/a/{i}") for i in range(20)],
        "junior": [_item(f"/b/{i}", "Junior Dev") for i in range(20)],
    })
    result = _fetch(tenant, search_keywords=["new grad", "junior"], max_total_limit=25, max_jobs_per_keyword=20)
    assert len(result.jobs) == 25


def test_without_keywords_the_full_listing_is_fetched_with_empty_search_text():
    tenant = FakeTenant({"": [_item(f"/job/{i}") for i in range(30)]})
    result = _fetch(tenant)
    assert {p["searchText"] for p in tenant.payloads} == {""}
    assert len(result.jobs) == 30


def test_blank_and_duplicate_keywords_are_ignored():
    tenant = FakeTenant({"new grad": [_item("/job/1")]})
    _fetch(tenant, search_keywords=["new grad", " ", "new grad ", ""])
    assert [p["searchText"] for p in tenant.payloads] == ["new grad"]


def test_http_422_is_reported_as_config_error():
    body = {"errorCode": "HTTP_422", "httpStatus": 422, "message": ""}
    with (
        patch("ngj.http.limited_post", return_value=_resp([], status=422, body=body)),
        patch("ngj.sources.workday.get_workday_csrf_token", return_value=""),
        patch("ngj.http.get_session", return_value=MagicMock()),
    ):
        result = fetch_workday_jobs([COMPANY])
    [error] = result.errors
    assert (error.kind, error.status) == (KIND_CONFIG, 422)
    assert "check workday_url" in error.message


def test_one_failing_keyword_keeps_jobs_from_the_others():
    def post(url, json=None, **kwargs):
        if json["searchText"] == "junior":
            return _resp([], status=400, body={"errorCode": "HTTP_400"})
        return _resp([_item("/job/1")])

    with (
        patch("ngj.http.limited_post", side_effect=post),
        patch("ngj.sources.workday.get_workday_csrf_token", return_value=""),
        patch("ngj.http.get_session", return_value=MagicMock()),
    ):
        result = fetch_workday_jobs([COMPANY], search_keywords=["new grad", "junior"], max_retries=0)
    assert len(result.jobs) == 1
    assert [(e.kind, e.status) for e in result.errors] == [(KIND_HTTP, 400)]


def test_request_timeout_in_one_keyword_keeps_the_company_jobs():
    import requests

    def post(url, json=None, **kwargs):
        if json["searchText"] == "junior":
            raise requests.exceptions.ReadTimeout("slow")
        return _resp([_item("/job/1")])

    with (
        patch("ngj.http.limited_post", side_effect=post),
        patch("ngj.sources.workday.get_workday_csrf_token", return_value=""),
        patch("ngj.http.get_session", return_value=MagicMock()),
    ):
        result = fetch_workday_jobs([COMPANY], search_keywords=["new grad", "junior"])
    assert len(result.jobs) == 1
    assert [e.kind for e in result.errors] == [KIND_TIMEOUT]


def test_time_budget_keeps_collected_jobs_and_stops_paging(monkeypatch, caplog):
    import logging

    caplog.set_level(logging.INFO)
    now = [0.0]
    monkeypatch.setattr("ngj.sources.workday.time.monotonic", lambda: now[0])
    tenant = FakeTenant({"new grad": [_item(f"/job/{i}") for i in range(100)]})

    def slow_post(url, json=None, **kwargs):
        now[0] += 100.0  # every page takes longer than the whole budget
        return tenant(url, json=json, **kwargs)

    result = _fetch(slow_post, search_keywords=["new grad"], max_seconds_per_company=45, keyword_workers=1)
    assert tenant.pages_for("new grad") == [0]
    assert len(result.jobs) == 20
    assert result.errors == ()
    assert "time budget" in caplog.text


def test_server_error_page_is_retried_once_then_succeeds():
    responses = iter([_resp([], status=502, body={}), _resp([_item("/job/1")])])
    with (
        patch("ngj.http.limited_post", side_effect=lambda *a, **k: next(responses)) as post,
        patch("ngj.sources.workday.get_workday_csrf_token", return_value=""),
        patch("ngj.http.get_session", return_value=MagicMock()),
    ):
        result = fetch_workday_jobs([COMPANY])
    assert post.call_count == 2
    assert len(result.jobs) == 1 and result.errors == ()


def test_page_limit_above_api_maximum_is_clamped(caplog):
    tenant = FakeTenant({"": []})
    _fetch(tenant, page_limit=50)
    assert tenant.payloads[0]["limit"] == WORKDAY_MAX_PAGE_LIMIT == 20


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Software Engineer, New Grad", True),
        ("Junior Data Analyst", True),
        ("Senior Software Engineer, New Grad", False),
        ("Staff Accountant", False),
        ("", False),
    ],
)
def test_title_prefilter(title, expected):
    assert build_title_prefilter(FILTERING)(title) is expected


def test_title_prefilter_is_none_without_signals():
    assert build_title_prefilter({}) is None
    assert build_title_prefilter(None) is None


# ---------------------------------------------------------------------------
# Settings + pipeline wiring
# ---------------------------------------------------------------------------

def _config(tmp_path, search_filters):
    return {
        "filtering": FILTERING,
        "apis": {"workday": {"enabled": True, "companies": [COMPANY], "search_filters": search_filters}},
    }


def test_settings_read_title_keywords(tmp_path):
    config = _config(tmp_path, {"title_keywords": ["new grad", "", "new grad", 7, " junior "],
                                "max_jobs_per_keyword": 80})
    settings = build_settings(config, env={}, repo_root=tmp_path)
    assert settings.workday_search_keywords == ("new grad", "junior")
    assert settings.workday_max_jobs_per_keyword == 80


def test_pipeline_passes_keywords_and_title_filter_to_workday(tmp_path):
    config = _config(tmp_path, {"title_keywords": ["new grad"]})
    settings = build_settings(config, env={}, repo_root=tmp_path)
    with patch("ngj.pipeline.fetch_workday_jobs") as fetch:
        pipeline.plan_sources(config, settings)["workday"]()
    kwargs = fetch.call_args.kwargs
    assert kwargs["search_keywords"] == ("new grad",)
    assert kwargs["max_jobs_per_keyword"] == settings.workday_max_jobs_per_keyword
    assert kwargs["title_filter"]("Software Engineer, New Grad") is True


def test_repo_config_uses_keyword_search_without_match_everything_keywords():
    from ngj.settings import DEFAULT_CONFIG_PATH, load_config

    settings = build_settings(load_config(DEFAULT_CONFIG_PATH), env={})
    keywords = {k.lower() for k in settings.workday_search_keywords}
    assert "new grad" in keywords
    # A one-letter searchText matches (nearly) every posting and defeats the point.
    assert not any(len(k) < 2 for k in keywords)

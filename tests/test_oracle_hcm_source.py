#!/usr/bin/env python3
"""Oracle HCM (Recruiting Cloud) adapter: site parsing, mapping, paging, countries, errors."""

import os
import re
import sys
from unittest.mock import MagicMock, patch
from urllib.parse import unquote

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from ngj import http as ngj_http  # noqa: E402
from ngj.models import KIND_CONFIG, KIND_HTTP  # noqa: E402
from ngj.sources.oracle_hcm import (  # noqa: E402
    PAGE_SIZE,
    careers_site,
    fetch_all_oracle_hcm_jobs,
    fetch_oracle_hcm_jobs,
)
from source_cooldown import SourceCooldownTracker  # noqa: E402

HOST = "iaziqy.fa.ocs.oraclecloud.com"
URL = f"https://{HOST}/hcmUI/CandidateExperience/en/sites/UberCareers"


def _req(rid: str, title: str = "Software Engineer I", **extra) -> dict:
    return {"Id": rid, "Title": title, "PostedDate": "2026-10-14", "PrimaryLocation": "San Francisco, CA, United States",
            "PrimaryLocationCountry": "US", "WorkplaceType": "", "BusinessUnitId": 300000007429409, **extra}


def _response(status: int, payload=None) -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.ok = 200 <= status < 300
    response.json.return_value = payload if payload is not None else {}
    response.text = ""
    return response


def _page(reqs: list, total: int) -> dict:
    return {"items": [{"TotalJobsCount": total, "requisitionList": reqs}]}


def _finder(url: str) -> dict:
    finder = unquote(re.search(r"finder=findReqs;([^&]*)", url).group(1))
    return dict(part.split("=", 1) for part in finder.split(","))


class _Api:
    """Fake requisitions endpoint: ``pages[(location, offset)]`` -> response; records each finder."""

    def __init__(self, pages: dict):
        self.pages = pages
        self.calls: list[dict] = []

    def __call__(self, url, **_kwargs):
        finder = _finder(url)
        self.calls.append(finder)
        return self.pages.get((finder.get("location"), int(finder["offset"])), _response(200, _page([], 0)))


def _fetch(api: _Api, url: str = URL, countries=("United States",), max_jobs: int = 1000):
    with (
        patch("ngj.http.limited_get", side_effect=api),
        patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
    ):
        return fetch_oracle_hcm_jobs("Uber", url, countries=countries, max_jobs_per_country=max_jobs, timeout=5)


class TestCareersSite:
    @pytest.mark.parametrize("url, expected", [
        (URL, (HOST, "en", "UberCareers")),
        (f"https://{HOST}/hcmUI/CandidateExperience/en/sites/CX_1/", (HOST, "en", "CX_1")),
        ("https://egup.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en-US/sites/CX", ("egup.fa.us2.oraclecloud.com", "en-US", "CX")),
        (f"https://{HOST}/hcmUI/CandidateExperience/en/sites/CX/job/123", None),
        ("https://evil.example.com/hcmUI/CandidateExperience/en/sites/CX", None),
        ("", None),
    ])
    def test_site_comes_from_the_careers_url(self, url, expected):
        assert careers_site(url) == expected


class TestMapping:
    def test_requisition_maps_to_a_job_on_the_careers_site(self):
        api = _Api({("United States", 0): _response(200, _page([_req("152014")], 1))})
        assert _fetch(api).jobs[0] == {
            "company": "Uber",
            "title": "Software Engineer I",
            "location": "San Francisco, CA, United States",
            "url": f"{URL}/job/152014",
            "posted_at": "2026-10-14",
            "source": "Oracle HCM",
            "description": "",
        }

    def test_internal_ids_are_never_copied(self):
        api = _Api({("United States", 0): _response(200, _page([_req("1")], 1))})
        assert "300000007429409" not in repr(_fetch(api).jobs[0])

    def test_title_whitespace_is_stripped_and_remote_is_marked(self):
        req = _req("1", title="  Data Analyst ", WorkplaceType="Remote")
        api = _Api({("United States", 0): _response(200, _page([req], 1))})
        job = _fetch(api).jobs[0]
        assert job["title"] == "Data Analyst"
        assert job["location"] == "Remote, San Francisco, CA, United States"

    def test_requisitions_without_an_id_are_skipped(self):
        no_id = {k: v for k, v in _req("x").items() if k != "Id"}
        api = _Api({("United States", 0): _response(200, _page([no_id, _req("1"), "junk"], 3))})
        assert [j["url"].rsplit("/", 1)[1] for j in _fetch(api).jobs] == ["1"]


class TestPaging:
    def test_query_is_newest_first_on_the_configured_site(self):
        api = _Api({("United States", 0): _response(200, _page([_req("1")], 1))})
        _fetch(api)
        assert api.calls[0] == {"siteNumber": "UberCareers", "location": "United States", "limit": str(PAGE_SIZE),
                                "offset": "0", "sortBy": "POSTING_DATES_DESC"}

    def test_pages_until_total_jobs_count(self):
        first = [_req(str(i)) for i in range(PAGE_SIZE)]
        api = _Api({
            ("United States", 0): _response(200, _page(first, PAGE_SIZE + 2)),
            ("United States", PAGE_SIZE): _response(200, _page([_req("a"), _req("b")], PAGE_SIZE + 2)),
        })
        result = _fetch(api)
        assert len(result.jobs) == PAGE_SIZE + 2 and result.raw_count == PAGE_SIZE + 2
        assert [c["offset"] for c in api.calls] == ["0", str(PAGE_SIZE)]

    def test_full_page_without_a_total_keeps_paging(self):
        first = [_req(str(i)) for i in range(PAGE_SIZE)]
        api = _Api({
            ("United States", 0): _response(200, {"items": [{"requisitionList": first}]}),
            ("United States", PAGE_SIZE): _response(200, {"items": [{"requisitionList": [_req("last")]}]}),
        })
        assert len(_fetch(api).jobs) == PAGE_SIZE + 1

    def test_cap_stops_paging(self):
        api = _Api({("United States", 0): _response(200, _page([_req(str(i)) for i in range(PAGE_SIZE)], 5000))})
        result = _fetch(api, max_jobs=30)
        assert len(result.jobs) == 30 and len(api.calls) == 1

    def test_pages_of_unusable_records_cannot_page_forever(self):
        junk = _response(200, _page(["junk"] * PAGE_SIZE, 10**9))
        api = _Api({("United States", PAGE_SIZE * i): junk for i in range(50)})
        assert _fetch(api).jobs == () and len(api.calls) == 1

    def test_each_country_is_queried_and_requisitions_are_deduplicated(self):
        api = _Api({
            ("United States", 0): _response(200, _page([_req("1"), _req("2")], 2)),
            ("Canada", 0): _response(200, _page([_req("2"), _req("3", PrimaryLocation="Toronto, ON, Canada")], 2)),
        })
        result = _fetch(api, countries=("United States", "Canada"))
        assert [c["location"] for c in api.calls] == ["United States", "Canada"]
        assert [j["url"].rsplit("/", 1)[1] for j in result.jobs] == ["1", "2", "3"]

    def test_no_countries_queries_the_whole_site_once(self):
        api = _Api({(None, 0): _response(200, _page([_req("1")], 1))})
        assert len(_fetch(api, countries=()).jobs) == 1
        assert "location" not in api.calls[0]


class TestErrors:
    def test_a_failing_page_keeps_earlier_jobs_and_reports_the_error(self):
        api = _Api({
            ("United States", 0): _response(200, _page([_req(str(i)) for i in range(PAGE_SIZE)], 500)),
            ("United States", PAGE_SIZE): _response(500),
        })
        result = _fetch(api)
        assert len(result.jobs) == PAGE_SIZE
        assert [(e.company, e.source, e.kind, e.status) for e in result.errors] == [("Uber", "oracle_hcm", KIND_HTTP, 500)]

    @pytest.mark.parametrize("payload", [{"items": []}, {"items": [{"requisitionList": "x"}]}, {"nope": 1}, []])
    def test_unexpected_shapes_are_parse_errors(self, payload):
        api = _Api({("United States", 0): _response(200, payload)})
        result = _fetch(api)
        assert result.jobs == () and result.errors[0].kind == "parse"

    def test_unusable_url_is_a_config_error_without_a_request(self):
        api = _Api({})
        result = _fetch(api, url=f"https://{HOST}/hcmUI/CandidateExperience/en/sites/CX/job/1")
        assert api.calls == [] and result.errors[0].kind == KIND_CONFIG

    def test_a_timeout_returns_no_partial_jobs_and_the_retry_does_not_duplicate(self):
        first = [_req(str(i)) for i in range(PAGE_SIZE)]
        timed_out = [False]

        def get(url, **_kwargs):
            finder = _finder(url)
            if finder["offset"] == str(PAGE_SIZE) and not timed_out[0]:
                timed_out[0] = True
                raise requests.exceptions.ReadTimeout("slow tenant")
            if finder["offset"] == "0":
                return _response(200, _page(first, PAGE_SIZE + 1))
            return _response(200, _page([_req("last")], PAGE_SIZE + 1))

        settings = MagicMock(oracle_hcm_max_workers=1, oracle_hcm_countries=("United States",),
                             oracle_hcm_max_jobs_per_country=1000, oracle_hcm_timeout=5,
                             oracle_hcm_max_seconds_per_company=300)
        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_all_oracle_hcm_jobs([{"name": "Uber", "url": URL}], settings)
        urls = [j["url"] for j in result.jobs]
        assert len(urls) == len(set(urls)) == PAGE_SIZE + 1
        assert result.raw_count == PAGE_SIZE + 1 and result.errors == ()


class TestFetchAll:
    def test_every_company_is_fetched_and_errors_travel_with_results(self):
        def get(url, **_kwargs):
            if "broken" in url:
                return _response(404)
            return _response(200, _page([_req("1")], 1))

        settings = MagicMock(oracle_hcm_max_workers=2, oracle_hcm_countries=("United States",),
                             oracle_hcm_max_jobs_per_country=100, oracle_hcm_timeout=5,
                             oracle_hcm_max_seconds_per_company=300)
        companies = [{"name": "Uber", "url": URL},
                     {"name": "Broken", "url": "https://broken.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX"}]
        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_all_oracle_hcm_jobs(companies, settings)
        assert [j["company"] for j in result.jobs] == ["Uber"]
        assert [(e.company, e.status) for e in result.errors] == [("Broken", 404)]


class TestRunTimeBounds:
    """Review finding: a slow tenant must not stall the whole pipeline."""

    def test_time_budget_keeps_collected_jobs_and_stops_paging(self, monkeypatch, caplog):
        import logging

        caplog.set_level(logging.WARNING)
        now = [0.0]
        monkeypatch.setattr("ngj.sources.oracle_hcm.time.monotonic", lambda: now[0])
        first = [_req(str(i)) for i in range(PAGE_SIZE)]
        api_pages = _Api({("United States", 0): _response(200, _page(first, 5000)),
                          ("Canada", 0): _response(200, _page([_req("ca")], 1))})

        def slow(url, **kwargs):
            now[0] += 500.0  # every page takes longer than the whole budget
            return api_pages(url, **kwargs)

        with (
            patch("ngj.http.limited_get", side_effect=slow),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_oracle_hcm_jobs("Uber", URL, countries=("United States", "Canada"),
                                           max_seconds=300, timeout=5)
        assert [c.get("location") for c in api_pages.calls] == ["United States"]
        assert len(result.jobs) == PAGE_SIZE and result.errors == ()
        assert "time budget" in caplog.text

    def test_a_timeout_skips_the_remaining_countries(self):
        api = _Api({("Canada", 0): _response(200, _page([_req("ca")], 1))})

        def get(url, **kwargs):
            if _finder(url).get("location") == "United States":
                raise requests.exceptions.ReadTimeout("slow tenant")
            return api(url, **kwargs)

        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_oracle_hcm_jobs("Uber", URL, countries=("United States", "Canada"), timeout=5)
        assert api.calls == []
        assert result.jobs == () and result.errors[0].kind == "timeout"

    def test_the_retry_pass_does_not_double_the_timeout(self):
        timeouts: list = []

        def get(url, timeout=None, **_kwargs):
            timeouts.append(timeout)
            raise requests.exceptions.ReadTimeout("slow tenant")

        settings = MagicMock(oracle_hcm_max_workers=1, oracle_hcm_countries=("United States",),
                             oracle_hcm_max_jobs_per_country=100, oracle_hcm_timeout=7,
                             oracle_hcm_max_seconds_per_company=300)
        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=50)),
        ):
            fetch_all_oracle_hcm_jobs([{"name": "Uber", "url": URL}], settings)
        assert timeouts == [7, 7]


class TestInputHardening:
    def test_country_names_are_fully_encoded_inside_the_finder(self):
        seen: list = []

        def get(url, **_kwargs):
            seen.append(url)
            return _response(200, _page([], 0))

        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            fetch_oracle_hcm_jobs("Uber", URL, countries=("Bosnia/Herzegovina",), timeout=5)
        assert "location=Bosnia%2FHerzegovina," in seen[0]

    @pytest.mark.parametrize("language", ["en-US", "zh-Hans", "en_US", "fra"])
    def test_language_variants_are_accepted(self, language):
        assert careers_site(f"https://{HOST}/hcmUI/CandidateExperience/{language}/sites/CX") == (HOST, language, "CX")

    def test_a_non_numeric_total_does_not_fail_the_company(self):
        api = _Api({("United States", 0): _response(200, {"items": [{"TotalJobsCount": "n/a",
                                                                      "requisitionList": [_req("1")]}]})})
        result = _fetch(api)
        assert len(result.jobs) == 1 and result.errors == ()

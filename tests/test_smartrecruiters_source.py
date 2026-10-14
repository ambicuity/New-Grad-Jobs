#!/usr/bin/env python3
"""SmartRecruiters Posting API adapter: mapping, paging, country queries, errors."""

import os
import sys
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from ngj import http as ngj_http  # noqa: E402
from ngj.models import KIND_CONFIG, KIND_HTTP  # noqa: E402
from ngj.sources.smartrecruiters import (  # noqa: E402
    PAGE_SIZE,
    company_identifier,
    fetch_all_smartrecruiters_jobs,
    fetch_smartrecruiters_jobs,
)
from source_cooldown import SourceCooldownTracker  # noqa: E402

URL = "https://api.smartrecruiters.com/v1/companies/AbbVie/postings"


def _posting(pid: str, name: str = "Associate Data Scientist I", **location) -> dict:
    return {
        "id": pid,
        "name": name,
        "releasedDate": "2026-10-14T17:06:26.356Z",
        "company": {"identifier": "AbbVie", "name": "AbbVie"},
        "location": {"city": "Irvine", "region": "CA", "country": "us", "remote": False,
                     "fullLocation": "Irvine, CA, United States", **location},
        "typeOfEmployment": {"id": "permanent", "label": "Full-time"},
        "customField": [{"fieldLabel": "Hiring Manager", "valueLabel": "Jane Doe (123)"}],
    }


def _response(status: int, payload=None) -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.ok = 200 <= status < 300
    response.json.return_value = payload if payload is not None else {}
    response.text = ""
    return response


def _page(postings: list[dict], total: int) -> dict:
    return {"offset": 0, "limit": PAGE_SIZE, "totalFound": total, "content": postings}


class _Api:
    """Fake list endpoint: ``pages[(country, offset)]`` -> response; records every request."""

    def __init__(self, pages: dict):
        self.pages = pages
        self.calls: list[dict] = []

    def __call__(self, url, **_kwargs):
        query = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
        self.calls.append(query)
        key = (query.get("country"), int(query.get("offset", 0)))
        return self.pages.get(key, _response(200, _page([], 0)))


def _fetch(api: _Api, url: str = URL, countries=("us",), max_jobs: int = 1000):
    with (
        patch("ngj.http.limited_get", side_effect=api),
        patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
    ):
        return fetch_smartrecruiters_jobs("AbbVie", url, countries=countries, max_jobs_per_country=max_jobs, timeout=5)


class TestCompanyIdentifier:
    @pytest.mark.parametrize("url, expected", [
        (URL, "AbbVie"),
        ("https://api.smartrecruiters.com/v1/companies/CheckPointSoftwareTechnologies2/postings/", "CheckPointSoftwareTechnologies2"),
        ("https://jobs.smartrecruiters.com/AbbVie/123-x", None),
        ("", None),
    ])
    def test_identifier_comes_from_the_postings_url(self, url, expected):
        assert company_identifier(url) == expected


class TestMapping:
    def test_posting_maps_to_a_job_with_a_stable_posting_url(self):
        api = _Api({("us", 0): _response(200, _page([_posting("3743990016070676")], 1))})
        job = _fetch(api).jobs[0]
        assert job == {
            "company": "AbbVie",
            "title": "Associate Data Scientist I",
            "location": "Irvine, CA, United States",
            "url": "https://jobs.smartrecruiters.com/AbbVie/3743990016070676",
            "posted_at": "2026-10-14T17:06:26.356Z",
            "source": "SmartRecruiters",
            "description": "",
        }

    def test_internal_custom_fields_are_never_copied(self):
        api = _Api({("us", 0): _response(200, _page([_posting("1")], 1))})
        job = _fetch(api).jobs[0]
        assert "Jane Doe" not in repr(job)

    def test_title_whitespace_is_stripped(self):
        api = _Api({("us", 0): _response(200, _page([_posting("1", name=" Jr. Front-End Developer ")], 1))})
        assert _fetch(api).jobs[0]["title"] == "Jr. Front-End Developer"

    def test_remote_postings_say_so(self):
        api = _Api({("us", 0): _response(200, _page([_posting("1", remote=True)], 1))})
        assert _fetch(api).jobs[0]["location"] == "Remote, Irvine, CA, United States"

    def test_location_falls_back_to_its_parts(self):
        posting = _posting("1", fullLocation="", city="Austin", region="TX", country="us")
        api = _Api({("us", 0): _response(200, _page([posting], 1))})
        assert _fetch(api).jobs[0]["location"] == "Austin, TX, US"


class TestPaging:
    def test_pages_until_total_found(self):
        first = [_posting(str(i)) for i in range(PAGE_SIZE)]
        second = [_posting(str(PAGE_SIZE + i)) for i in range(5)]
        api = _Api({
            ("us", 0): _response(200, _page(first, PAGE_SIZE + 5)),
            ("us", PAGE_SIZE): _response(200, _page(second, PAGE_SIZE + 5)),
        })
        result = _fetch(api)
        assert len(result.jobs) == PAGE_SIZE + 5
        assert result.raw_count == PAGE_SIZE + 5
        assert [c["offset"] for c in api.calls] == ["0", str(PAGE_SIZE)]
        assert all(c["limit"] == str(PAGE_SIZE) for c in api.calls)

    def test_short_page_ends_paging_without_an_extra_request(self):
        api = _Api({("us", 0): _response(200, _page([_posting("1")], 999))})
        _fetch(api)
        assert len(api.calls) == 1

    def test_cap_stops_paging_per_country(self):
        first = [_posting(str(i)) for i in range(PAGE_SIZE)]
        api = _Api({("us", 0): _response(200, _page(first, 5000))})
        result = _fetch(api, max_jobs=40)
        assert len(result.jobs) == 40
        assert len(api.calls) == 1

    def test_each_country_is_queried_and_postings_are_deduplicated(self):
        api = _Api({
            ("us", 0): _response(200, _page([_posting("1"), _posting("2")], 2)),
            ("ca", 0): _response(200, _page([_posting("2"), _posting("3", country="ca")], 2)),
        })
        result = _fetch(api, countries=("us", "ca"))
        assert [c["country"] for c in api.calls] == ["us", "ca"]
        assert [j["url"].rsplit("/", 1)[1] for j in result.jobs] == ["1", "2", "3"]

    def test_no_countries_queries_the_whole_board_once(self):
        api = _Api({(None, 0): _response(200, _page([_posting("1")], 1))})
        result = _fetch(api, countries=())
        assert len(result.jobs) == 1
        assert "country" not in api.calls[0]


class TestErrors:
    def test_a_failing_page_keeps_earlier_jobs_and_reports_the_error(self):
        first = [_posting(str(i)) for i in range(PAGE_SIZE)]
        api = _Api({
            ("us", 0): _response(200, _page(first, 500)),
            ("us", PAGE_SIZE): _response(500),
        })
        result = _fetch(api)
        assert len(result.jobs) == PAGE_SIZE
        assert [(e.company, e.source, e.kind, e.status) for e in result.errors] == [
            ("AbbVie", "smartrecruiters", KIND_HTTP, 500)]

    def test_a_failing_country_does_not_stop_the_next_one(self):
        api = _Api({
            ("us", 0): _response(500),
            ("ca", 0): _response(200, _page([_posting("9", country="ca")], 1)),
        })
        result = _fetch(api, countries=("us", "ca"))
        assert len(result.jobs) == 1 and len(result.errors) == 1

    def test_unexpected_shape_is_a_parse_error(self):
        api = _Api({("us", 0): _response(200, {"content": "nope"})})
        result = _fetch(api)
        assert result.jobs == () and result.errors[0].kind == "parse"

    def test_unusable_url_is_a_config_error_without_a_request(self):
        api = _Api({})
        result = _fetch(api, url="https://jobs.smartrecruiters.com/AbbVie")
        assert api.calls == []
        assert result.errors[0].kind == KIND_CONFIG


class TestFetchAll:
    def test_every_company_is_fetched_and_errors_travel_with_results(self):
        def get(url, **_kwargs):
            if "/Broken/" in url:
                return _response(404)
            return _response(200, _page([_posting(url.split("/companies/")[1].split("/")[0])], 1))

        settings = MagicMock(smartrecruiters_max_workers=2, smartrecruiters_countries=("us",),
                             smartrecruiters_max_jobs_per_country=100, http_timeout=5)
        companies = [{"name": "AbbVie", "url": URL},
                     {"name": "Broken", "url": "https://api.smartrecruiters.com/v1/companies/Broken/postings"}]
        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_all_smartrecruiters_jobs(companies, settings)
        assert [j["company"] for j in result.jobs] == ["AbbVie"]
        assert [(e.company, e.status) for e in result.errors] == [("Broken", 404)]


class TestRobustness:
    """Review findings: retry duplicates, unbounded paging, missing totals and ids."""

    def test_postings_without_an_id_are_skipped(self):
        no_id = {k: v for k, v in _posting("x").items() if k != "id"}
        api = _Api({("us", 0): _response(200, _page([no_id, _posting("1")], 2))})
        assert [j["url"].rsplit("/", 1)[1] for j in _fetch(api).jobs] == ["1"]

    def test_full_page_without_total_found_keeps_paging(self):
        first = [_posting(str(i)) for i in range(PAGE_SIZE)]
        api = _Api({
            ("us", 0): _response(200, {"content": first}),
            ("us", PAGE_SIZE): _response(200, {"content": [_posting("last")]}),
        })
        assert len(_fetch(api).jobs) == PAGE_SIZE + 1

    def test_pages_of_unusable_records_cannot_page_forever(self):
        junk = _response(200, _page(["not-a-posting"] * PAGE_SIZE, 10**9))
        api = _Api({("us", PAGE_SIZE * i): junk for i in range(50)})
        result = _fetch(api, max_jobs=1000)
        assert result.jobs == ()
        assert len(api.calls) == 1

    def test_a_timeout_mid_paging_is_retried_without_duplicating_jobs(self):
        first = [_posting(str(i)) for i in range(PAGE_SIZE)]
        timed_out = [False]

        def get(url, **_kwargs):
            query = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
            if query["offset"] == str(PAGE_SIZE) and not timed_out[0]:
                timed_out[0] = True
                raise requests.exceptions.ReadTimeout("slow")
            if query["offset"] == "0":
                return _response(200, _page(first, PAGE_SIZE + 1))
            return _response(200, _page([_posting("last")], PAGE_SIZE + 1))

        settings = MagicMock(smartrecruiters_max_workers=1, smartrecruiters_countries=("us",),
                             smartrecruiters_max_jobs_per_country=1000, http_timeout=5)
        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_all_smartrecruiters_jobs([{"name": "AbbVie", "url": URL}], settings)
        urls = [j["url"] for j in result.jobs]
        assert len(urls) == len(set(urls)) == PAGE_SIZE + 1
        assert result.raw_count == PAGE_SIZE + 1
        assert result.errors == ()

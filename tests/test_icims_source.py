#!/usr/bin/env python3
"""iCIMS career-site (Jibe) adapter: per-country paging, mapping, filtering, errors."""

import os
import sys
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from contracts import compute_job_id  # noqa: E402
from ngj import http as ngj_http  # noqa: E402
from ngj.models import KIND_CONFIG, KIND_HTTP, KIND_PARSE  # noqa: E402
from ngj.sources.icims import PAGE_SIZE, fetch_all_icims_jobs, fetch_icims_jobs, site_base  # noqa: E402
from source_cooldown import SourceCooldownTracker  # noqa: E402

BASE = "https://careers.amd.com"
COUNTRIES = ("United States", "Canada", "India")


def _job(slug: str, title: str = "Software Engineer I", **extra) -> dict:
    data = {"slug": slug, "req_id": slug, "title": title, "full_location": "Austin, Texas",
            "city": "Austin", "state": "Texas", "country": "United States",
            "posted_date": "2026-10-14T20:05:00+0000", "employment_type": "FULL_TIME", "searchable": True,
            "description": "<p>Build</p>", "responsibilities": "<ul><li>Ship</li></ul>",
            "qualifications": "<p>BS CS</p>", "apply_url": f"https://global-external-amd.icims.com/jobs/{slug}/login",
            "salary_min_value": 90000, "hiring_organization": "AMD", "meta_data": {"internal": "x"}}
    data.update(extra)
    return {"data": data}


def _payload(jobs: list, total: int | None = None) -> dict:
    return {"jobs": jobs, "totalCount": len(jobs) if total is None else total, "count": len(jobs)}


def _response(status: int, payload=None) -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.ok = 200 <= status < 300
    response.json.return_value = payload if payload is not None else {}
    response.text = ""
    return response


class _Api:
    """Pages keyed by (country, page number)."""

    def __init__(self, pages: dict[tuple[str, int], object]):
        self.pages, self.calls = pages, []

    def get(self, url, **_kwargs):
        self.calls.append(url)
        query = parse_qs(urlparse(url).query)
        key = (query["country"][0], int(query["page"][0]))
        page = self.pages.get(key, _payload([]))
        return page if isinstance(page, MagicMock) else _response(200, page)


def _fetch(api: _Api, url: str = BASE, max_jobs: int = 1000, countries=COUNTRIES):
    with (
        patch("ngj.http.limited_get", side_effect=api.get),
        patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
    ):
        return fetch_icims_jobs("AMD", url, countries=countries, max_jobs_per_country=max_jobs, timeout=5)


class TestSiteBase:
    @pytest.mark.parametrize("url, expected", [
        (BASE, BASE),
        (f"{BASE}/", BASE),
        ("https://Careers.Emory.EDU", "https://careers.emory.edu"),
        ("http://careers.amd.com", None),
        (f"{BASE}/api/jobs", None),
        ("https://careers-rovisys.icims.com", None),  # classic portals: not supported yet
        ("", None),
    ])
    def test_only_a_career_site_root_is_accepted(self, url, expected):
        assert site_base(url) == expected


class TestMapping:
    def test_job_maps_to_its_public_page(self):
        result = _fetch(_Api({("United States", 1): _payload([_job("93246")])}))
        assert result.jobs[0] == {
            "company": "AMD",
            "title": "Software Engineer I",
            "location": "Austin, Texas",
            "url": "https://careers.amd.com/jobs/93246",
            "posted_at": "2026-10-14T20:05:00+0000",
            "source": "iCIMS",
            "description": "",
            "description_html": "<p>Build</p>\n<ul><li>Ship</li></ul>\n<p>BS CS</p>",
        }

    def test_query_is_newest_first_and_per_country(self):
        api = _Api({})
        _fetch(api)
        queries = [parse_qs(urlparse(c).query) for c in api.calls]
        assert [q["country"][0] for q in queries] == list(COUNTRIES)
        assert all(q["sortBy"] == ["posted_date"] and q["descending"] == ["true"] for q in queries)
        assert all(q["limit"] == [str(PAGE_SIZE)] and q["page"] == ["1"] for q in queries)
        assert all(urlparse(c).path == "/api/jobs" for c in api.calls)

    def test_location_falls_back_to_city_state_country(self):
        api = _Api({("Canada", 1): _payload([_job("1", full_location="", city="Markham", state="Ontario",
                                                   country="Canada")])})
        assert _fetch(api).jobs[0]["location"] == "Markham, Ontario, Canada"

    def test_part_time_unsearchable_and_slugless_postings_are_skipped(self):
        api = _Api({("United States", 1): _payload([
            _job("1", employment_type="PART_TIME"), _job("2", searchable=False), _job(""),
            {"data": None}, "junk", _job("3", title="  Data Analyst ")])})
        result = _fetch(api)
        assert [j["title"] for j in result.jobs] == ["Data Analyst"]

    def test_unsafe_slugs_are_skipped(self):
        api = _Api({("United States", 1): _payload([_job("../x"), _job("a/b"), _job("@evil.com"), _job("7")])})
        assert [j["url"] for j in _fetch(api).jobs] == ["https://careers.amd.com/jobs/7"]

    def test_internal_fields_are_never_copied(self):
        job = _fetch(_Api({("United States", 1): _payload([_job("1")])})).jobs[0]
        assert "global-external-amd" not in repr(job) and "internal" not in repr(job)

    def test_a_posting_in_several_countries_is_kept_once(self):
        api = _Api({("United States", 1): _payload([_job("5")]), ("India", 1): _payload([_job("5"), _job("6")])})
        result = _fetch(api)
        assert [j["url"].rsplit("/", 1)[1] for j in result.jobs] == ["5", "6"]
        assert len({compute_job_id(j) for j in result.jobs}) == 2


class TestPaging:
    def test_pages_until_a_short_page(self):
        full = [_job(str(i)) for i in range(PAGE_SIZE)]
        api = _Api({("United States", 1): _payload(full, total=150),
                    ("United States", 2): _payload([_job(str(i)) for i in range(100, 150)], total=150)})
        result = _fetch(api, countries=("United States",))
        assert len(result.jobs) == 150 and len(api.calls) == 2

    def test_total_count_ends_paging_on_an_exact_multiple(self):
        api = _Api({("United States", 1): _payload([_job(str(i)) for i in range(PAGE_SIZE)], total=PAGE_SIZE)})
        _fetch(api, countries=("United States",))
        assert len(api.calls) == 1

    def test_the_cap_bounds_postings_and_pages_per_country(self):
        pages = {("United States", n): _payload([_job(f"{n}-{i}") for i in range(PAGE_SIZE)], total=10_000)
                 for n in range(1, 20)}
        api = _Api(pages)
        result = _fetch(api, max_jobs=250, countries=("United States",))
        assert len(result.jobs) == 250 and len(api.calls) == 3


class TestErrors:
    @pytest.mark.parametrize("payload", [{"jobs": "x", "totalCount": 1}, {"totalCount": 1}, ["x"]])
    def test_unexpected_shapes_are_parse_errors(self, payload):
        result = _fetch(_Api({("United States", 1): payload}), countries=("United States",))
        assert result.jobs == () and result.errors[0].kind == KIND_PARSE

    def test_http_errors_are_reported_and_other_countries_still_publish(self):
        api = _Api({("United States", 1): _response(500), ("Canada", 1): _payload([_job("9")])})
        result = _fetch(api)
        assert [j["url"].rsplit("/", 1)[1] for j in result.jobs] == ["9"]
        assert [(e.kind, e.status) for e in result.errors] == [(KIND_HTTP, 500)]

    def test_unusable_url_is_a_config_error_without_a_request(self):
        api = _Api({})
        result = _fetch(api, url="https://careers-rovisys.icims.com/jobs/search")
        assert api.calls == [] and result.errors[0].kind == KIND_CONFIG

    def test_a_timeout_returns_no_partial_jobs_and_the_retry_does_not_duplicate(self):
        state = {"timed_out": False}

        def get(url, **_kwargs):
            query = parse_qs(urlparse(url).query)
            if query["country"][0] == "Canada" and not state["timed_out"]:
                state["timed_out"] = True
                raise requests.exceptions.ReadTimeout("slow")
            if query["country"][0] == "United States":
                return _response(200, _payload([_job("1")]))
            return _response(200, _payload([]))

        settings = MagicMock(icims_max_workers=2, icims_countries=COUNTRIES, icims_max_jobs_per_country=100,
                             http_timeout=5)
        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_all_icims_jobs([{"name": "AMD", "url": BASE}], settings)
        assert [j["url"] for j in result.jobs] == ["https://careers.amd.com/jobs/1"] and result.errors == ()


class TestFetchAll:
    def test_every_site_is_fetched_and_errors_travel_with_results(self):
        def get(url, **_kwargs):
            host = urlparse(url).netloc
            if host == "jobs.broken.com":
                return _response(404)
            query = parse_qs(urlparse(url).query)
            if query["country"][0] != "United States":
                return _response(200, _payload([]))
            return _response(200, _payload([_job("1" if host == "careers.amd.com" else "2")]))

        settings = MagicMock(icims_max_workers=2, icims_countries=COUNTRIES, icims_max_jobs_per_country=100,
                             http_timeout=5)
        companies = [{"name": "AMD", "url": BASE}, {"name": "Emory", "url": "https://careers.emory.edu"},
                     {"name": "Broken", "url": "https://jobs.broken.com"}]
        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_all_icims_jobs(companies, settings)
        assert sorted(j["company"] for j in result.jobs) == ["AMD", "Emory"]
        assert {(e.company, e.status) for e in result.errors} == {("Broken", 404)}


class TestReviewHardening:
    @pytest.mark.parametrize("value", ["false", "False", 0])
    def test_non_boolean_false_searchable_is_skipped(self, value):
        api = _Api({("United States", 1): _payload([_job("1", searchable=value), _job("2")])})
        assert [j["url"].rsplit("/", 1)[1] for j in _fetch(api).jobs] == ["2"]

    @pytest.mark.parametrize("title", ["", "   ", None])
    def test_postings_without_a_title_are_skipped(self, title):
        api = _Api({("United States", 1): _payload([_job("1", title=title), _job("2")])})
        assert [j["url"].rsplit("/", 1)[1] for j in _fetch(api).jobs] == ["2"]

    def test_a_full_page_of_skipped_postings_keeps_paging(self):
        skipped = [_job(str(i), employment_type="PART_TIME") for i in range(PAGE_SIZE)]
        api = _Api({("United States", 1): _payload(skipped, total=101),
                    ("United States", 2): _payload([_job("good")], total=101)})
        result = _fetch(api, countries=("United States",))
        assert [j["url"].rsplit("/", 1)[1] for j in result.jobs] == ["good"] and result.raw_count == 101

    def test_the_api_date_format_is_recent(self):
        from datetime import UTC, datetime

        from ngj.dates import is_recent_job

        assert is_recent_job("2026-10-14T20:05:00+0000", 30, now=datetime(2026, 10, 15, tzinfo=UTC))

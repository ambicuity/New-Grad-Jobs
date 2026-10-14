#!/usr/bin/env python3
"""Rippling ATS board adapter: list paging, detail pass, mapping, errors."""

import os
import sys
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from ngj import http as ngj_http  # noqa: E402
from ngj.models import KIND_CONFIG, KIND_HTTP  # noqa: E402
from ngj.sources.rippling import (  # noqa: E402
    PAGE_SIZE,
    board_slug,
    fetch_all_rippling_jobs,
    fetch_rippling_jobs,
)
from source_cooldown import SourceCooldownTracker  # noqa: E402

URL = "https://ats.rippling.com/api/v2/board/cintal/jobs"
FILTERING = {
    "new_grad_signals": ["junior", "new grad", "I"],
    "track_signals": ["engineer", "developer"],
    "exclusion_signals": ["senior"],
    "level_signals": ["I", "II"],
}


def _item(jid: str, name: str = "Junior C++ Developer", **location) -> dict:
    return {"id": jid, "name": name, "url": f"https://ats.rippling.com/cintal/jobs/{jid}",
            "department": {"name": "Engineering"}, "language": "en-US",
            "locations": [{"name": "Chillicothe, IL", "country": "United States", "countryCode": "US",
                           "workplaceType": "ON_SITE", **location}]}


def _detail(jid: str, **extra) -> dict:
    return {"uuid": jid, "name": "Junior C++ Developer", "createdOn": "2026-10-13T07:00:58.170000-07:00",
            "description": {"company": "<p>About Cintal</p>", "role": "<p>Build autonomy</p>"},
            "payRangeDetails": [{"currency": "USD", "frequency": "YEAR", "rangeStart": 98000.0, "rangeEnd": 105000.0}],
            "unlistedFromSearch": False, "eeocQuestionnaireEnabled": True, **extra}


def _response(status: int, payload=None) -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.ok = 200 <= status < 300
    response.json.return_value = payload if payload is not None else {}
    response.text = ""
    return response


def _list(items: list, total_pages: int = 1) -> dict:
    return {"items": items, "page": 0, "pageSize": PAGE_SIZE, "totalItems": len(items), "totalPages": total_pages}


class _Api:
    """Fake board: ``pages[n]`` and ``details[id]`` -> response; records every request path/query."""

    def __init__(self, pages: dict, details: dict | None = None):
        self.pages, self.details = pages, details or {}
        self.calls: list[str] = []

    def __call__(self, url, **_kwargs):
        parsed = urlparse(url)
        self.calls.append(parsed.path + ("?" + parsed.query if parsed.query else ""))
        if parsed.path.endswith("/jobs"):
            page = int(parse_qs(parsed.query).get("page", ["0"])[0])
            return self.pages.get(page, _response(200, _list([])))
        jid = parsed.path.rsplit("/", 1)[1]
        return self.details.get(jid, _response(404))

    def detail_calls(self):
        return [c for c in self.calls if not c.split("?")[0].endswith("/jobs")]


def _fetch(api, url=URL, filtering=FILTERING, max_jobs=1000):
    with (
        patch("ngj.http.limited_get", side_effect=api),
        patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
    ):
        return fetch_rippling_jobs("Cintal", url, filtering=filtering, max_jobs=max_jobs, timeout=5)


class TestBoardSlug:
    @pytest.mark.parametrize("url, expected", [
        (URL, "cintal"),
        ("https://ats.rippling.com/api/v2/board/bamboo-health-careers/jobs/", "bamboo-health-careers"),
        ("https://ats.rippling.com/cintal/jobs", None),
        ("https://api.rippling.com/platform/api/ats/v1/board/cintal/jobs", None),
        ("", None),
    ])
    def test_slug_comes_from_the_board_api_url(self, url, expected):
        assert board_slug(url) == expected


class TestDetailPass:
    def test_plausible_titles_get_their_date_description_and_pay(self):
        api = _Api({0: _response(200, _list([_item("a")]))}, {"a": _response(200, _detail("a"))})
        job = _fetch(api).jobs[0]
        assert job == {
            "company": "Cintal",
            "title": "Junior C++ Developer",
            "location": "Chillicothe, IL",
            "url": "https://ats.rippling.com/cintal/jobs/a",
            "posted_at": "2026-10-13T07:00:58.170000-07:00",
            "source": "Rippling",
            "description": "",
            "description_html": "<p>Build autonomy</p>\n<p>About Cintal</p>",
            "comp": {"min": 98000, "max": 105000, "currency": "USD", "source": "rippling"},
        }

    def test_titles_that_cannot_pass_skip_the_detail_request_but_stay_in_the_corpus(self):
        api = _Api({0: _response(200, _list([_item("a"), _item("b", name="Senior Developer")]))},
                   {"a": _response(200, _detail("a"))})
        result = _fetch(api)
        assert [c.rsplit("/", 1)[1] for c in api.detail_calls()] == ["a"]
        senior = next(j for j in result.jobs if j["url"].endswith("/b"))
        assert senior["posted_at"] == "" and senior["title"] == "Senior Developer"

    @pytest.mark.parametrize("filtering", [{}, {"new_grad_signals": ["junior"]}, {"track_signals": ["engineer"]}])
    def test_missing_filter_signals_fail_closed_without_a_request(self, filtering):
        api = _Api({0: _response(200, _list([_item("a")]))}, {"a": _response(200, _detail("a"))})
        result = _fetch(api, filtering=filtering)
        assert api.calls == [] and result.jobs == ()
        assert result.errors[0].kind == KIND_CONFIG and "filtering" in result.errors[0].message

    def test_unlisted_postings_are_skipped(self):
        api = _Api({0: _response(200, _list([_item("a")]))},
                   {"a": _response(200, _detail("a", unlistedFromSearch=True))})
        assert _fetch(api).jobs == ()

    def test_internal_fields_are_never_copied(self):
        api = _Api({0: _response(200, _list([_item("a")]))}, {"a": _response(200, _detail("a"))})
        assert "eeoc" not in repr(_fetch(api).jobs[0]).lower()

    def test_hourly_or_malformed_pay_is_not_reported_as_salary(self):
        detail = _detail("a", payRangeDetails=[{"currency": "USD", "frequency": "HOUR", "rangeStart": 30, "rangeEnd": 40},
                                               {"frequency": "YEAR", "rangeStart": "x", "rangeEnd": "y"}])
        api = _Api({0: _response(200, _list([_item("a")]))}, {"a": _response(200, detail)})
        assert _fetch(api).jobs[0]["comp"] is None


class TestMapping:
    def test_remote_and_multiple_locations(self):
        item = _item("a", workplaceType="REMOTE")
        item["locations"].append({"name": "Austin, TX", "workplaceType": "ON_SITE"})
        api = _Api({0: _response(200, _list([item]))}, {"a": _response(200, _detail("a"))})
        assert _fetch(api).jobs[0]["location"] == "Remote, Chillicothe, IL; Austin, TX"

    def test_remote_is_not_repeated_when_the_name_already_says_so(self):
        api = _Api({0: _response(200, _list([_item("a", name="Junior C++ Developer")]) )}, {"a": _response(200, _detail("a"))})
        api.pages[0].json.return_value["items"][0]["locations"] = [
            {"name": "Remote (United States)", "workplaceType": "REMOTE"}]
        assert _fetch(api).jobs[0]["location"] == "Remote (United States)"

    def test_unusable_locations_and_descriptions_are_ignored(self):
        item = _item("a")
        item["locations"] = ["Chillicothe", {"workplaceType": "REMOTE"}, {"name": "Austin, TX"}]
        api = _Api({0: _response(200, _list([item]))}, {"a": _response(200, _detail("a", description="plain"))})
        job = _fetch(api).jobs[0]
        assert job["location"] == "Austin, TX" and job["description_html"] == ""

    def test_title_whitespace_is_stripped_and_items_without_an_id_are_skipped(self):
        no_id = {k: v for k, v in _item("x").items() if k != "id"}
        api = _Api({0: _response(200, _list([no_id, _item("a", name=" Junior C++ Developer ")]))},
                   {"a": _response(200, _detail("a"))})
        jobs = _fetch(api).jobs
        assert [j["title"] for j in jobs] == ["Junior C++ Developer"]


class TestPaging:
    def test_pages_until_total_pages(self):
        api = _Api({0: _response(200, _list([_item("a")], total_pages=2)),
                    1: _response(200, _list([_item("b")], total_pages=2))},
                   {"a": _response(200, _detail("a")), "b": _response(200, _detail("b"))})
        result = _fetch(api)
        assert len(result.jobs) == 2 and result.raw_count == 2
        list_calls = [c for c in api.calls if c.split("?")[0].endswith("/jobs")]
        assert [parse_qs(c.split("?")[1])["page"][0] for c in list_calls] == ["0", "1"]
        assert all(parse_qs(c.split("?")[1])["pageSize"][0] == str(PAGE_SIZE) for c in list_calls)

    def test_cap_bounds_pages_and_postings(self):
        api = _Api({i: _response(200, _list([_item(f"{i}-{j}", name="Senior Developer") for j in range(PAGE_SIZE)],
                                            total_pages=50)) for i in range(50)})
        result = _fetch(api, max_jobs=150)
        assert len(result.jobs) == 150
        assert len([c for c in api.calls if c.split("?")[0].endswith("/jobs")]) == 2

    def test_empty_page_ends_paging(self):
        api = _Api({0: _response(200, _list([], total_pages=9))})
        assert _fetch(api).jobs == () and len(api.calls) == 1


class TestErrors:
    @pytest.mark.parametrize("status", [404, 410])
    def test_a_posting_closed_between_list_and_detail_is_dropped_quietly(self, status):
        api = _Api({0: _response(200, _list([_item("a"), _item("b")]))},
                   {"a": _response(status), "b": _response(200, _detail("b"))})
        result = _fetch(api)
        assert [j["url"].rsplit("/", 1)[1] for j in result.jobs] == ["b"] and result.errors == ()

    @pytest.mark.parametrize("status, kind", [(403, "forbidden"), (429, KIND_HTTP), (500, KIND_HTTP)])
    def test_any_other_detail_error_fails_the_board_instead_of_shrinking_it(self, status, kind):
        api = _Api({0: _response(200, _list([_item("a"), _item("b")]))},
                   {"a": _response(status), "b": _response(200, _detail("b"))})
        result = _fetch(api)
        assert result.jobs == ()
        assert [(e.company, e.source, e.kind) for e in result.errors] == [("Cintal", "rippling", kind)]
        assert len(api.detail_calls()) == 1

    def test_a_failing_list_page_keeps_earlier_pages(self):
        api = _Api({0: _response(200, _list([_item("a")], total_pages=3)), 1: _response(500)},
                   {"a": _response(200, _detail("a"))})
        result = _fetch(api)
        assert len(result.jobs) == 1 and result.errors[0].status == 500

    def test_a_timeout_while_listing_returns_no_partial_jobs(self):
        api = _Api({0: _response(200, _list([_item("a")], total_pages=2))}, {"a": _response(200, _detail("a"))})

        def get(url, **kwargs):
            if "page=1" in url:
                raise requests.exceptions.ReadTimeout("slow")
            return api(url, **kwargs)

        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_rippling_jobs("Cintal", URL, filtering=FILTERING, timeout=5)
        assert result.jobs == () and result.errors[0].kind == "timeout"

    @pytest.mark.parametrize("payload", [{"items": "x"}, [], {"nope": 1}])
    def test_unexpected_shapes_are_parse_errors(self, payload):
        result = _fetch(_Api({0: _response(200, payload)}))
        assert result.jobs == () and result.errors[0].kind == "parse"

    def test_unusable_url_is_a_config_error_without_a_request(self):
        api = _Api({})
        result = _fetch(api, url="https://ats.rippling.com/cintal/jobs")
        assert api.calls == [] and result.errors[0].kind == KIND_CONFIG

    def test_a_timeout_returns_no_partial_jobs_and_the_retry_does_not_duplicate(self):
        state = {"timed_out": False}
        base = _Api({0: _response(200, _list([_item("a"), _item("b")]))},
                    {"a": _response(200, _detail("a")), "b": _response(200, _detail("b"))})

        def get(url, **kwargs):
            if url.endswith("/jobs/b") and not state["timed_out"]:
                state["timed_out"] = True
                raise requests.exceptions.ReadTimeout("slow")
            return base(url, **kwargs)

        settings = MagicMock(rippling_max_workers=1, rippling_max_jobs_per_company=1000, http_timeout=5)
        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_all_rippling_jobs([{"name": "Cintal", "url": URL}], settings, filtering=FILTERING)
        urls = [j["url"] for j in result.jobs]
        assert len(urls) == len(set(urls)) == 2 and result.errors == () and result.raw_count == 2


class TestFetchAll:
    def test_every_board_is_fetched_and_errors_travel_with_results(self):
        def get(url, **_kwargs):
            if "/broken/" in url:
                return _response(404)
            if url.split("?")[0].endswith("/jobs"):
                return _response(200, _list([_item("a", name="Senior Developer")]))
            return _response(404)

        settings = MagicMock(rippling_max_workers=2, rippling_max_jobs_per_company=100, http_timeout=5)
        companies = [{"name": "Cintal", "url": URL},
                     {"name": "Broken", "url": "https://ats.rippling.com/api/v2/board/broken/jobs"}]
        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_all_rippling_jobs(companies, settings, filtering=FILTERING)
        assert [j["company"] for j in result.jobs] == ["Cintal"]
        assert [(e.company, e.status) for e in result.errors] == [("Broken", 404)]


class TestOneRowPerLocation:
    """The board list returns one row per location for the same posting (Rippling's own
    board: 609 rows, ~400 postings). Rows are merged into one job per posting id."""

    def test_rows_of_one_posting_merge_their_locations_and_fetch_the_detail_once(self):
        sf = _item("a")
        sf["locations"] = [{"name": "San Francisco, CA", "workplaceType": "ON_SITE"}]
        ny = _item("a")
        ny["locations"] = [{"name": "New York, NY", "workplaceType": "ON_SITE"},
                           {"name": "San Francisco, CA", "workplaceType": "ON_SITE"}]
        api = _Api({0: _response(200, _list([sf, _item("b", name="Senior Developer"), ny]))},
                   {"a": _response(200, _detail("a"))})
        result = _fetch(api)
        assert [j["url"].rsplit("/", 1)[1] for j in result.jobs] == ["a", "b"]
        assert result.jobs[0]["location"] == "San Francisco, CA; New York, NY"
        assert [c.rsplit("/", 1)[1] for c in api.detail_calls()] == ["a"]
        assert result.raw_count == 2

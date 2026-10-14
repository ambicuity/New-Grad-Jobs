#!/usr/bin/env python3
"""UKG Pro Recruiting (UltiPro) adapter: board parsing, search body, mapping, paging, errors."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from ngj import http as ngj_http  # noqa: E402
from ngj.models import KIND_CONFIG, KIND_HTTP  # noqa: E402
from ngj.sources.ukg import (  # noqa: E402
    PAGE_SIZE,
    fetch_all_ukg_jobs,
    fetch_ukg_jobs,
    job_board,
)
from source_cooldown import SourceCooldownTracker  # noqa: E402

BOARD = "https://recruiting.ultipro.com/AFL1002/JobBoard/d535bad2-e3ea-c8c8-2fb2-63621892e293"
SEARCH = f"{BOARD}/JobBoardView/LoadSearchResults"


def _location(city="Abilene", state="TX", country="USA", country_name="United States", name=None) -> dict:
    return {"Id": "loc", "LocalizedName": name, "Coordinates": {"Latitude": 32.4},
            "Address": {"City": city, "State": {"Code": state, "Name": "Texas"} if state else None,
                        "Country": {"Code": country, "Name": country_name} if country else None}}


def _opp(oid: str, title: str = "EHS Specialist I", locations=None, **extra) -> dict:
    return {"Id": oid, "Title": title, "RequisitionNumber": "EHSSP009420", "PostedDate": "2026-10-14T13:55:08.565Z",
            "BriefDescription": "An entry-level field safety role.", "Locations": locations or [_location()],
            "JobLocationType": 1, "MatchScore": 1.0, **extra}


def _response(status: int, payload=None) -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.ok = 200 <= status < 300
    response.json.return_value = payload if payload is not None else {}
    response.text = ""
    return response


def _page(opps: list, total: int) -> dict:
    return {"opportunities": opps, "totalCount": total, "locations": []}


class _Api:
    """Fake search endpoint: ``pages[skip]`` -> response; records each (url, body)."""

    def __init__(self, pages: dict):
        self.pages = pages
        self.calls: list = []

    def __call__(self, url, json=None, **_kwargs):
        self.calls.append((url, json))
        return self.pages.get(json["opportunitySearch"]["Skip"], _response(200, _page([], 0)))

    def skips(self):
        return [body["opportunitySearch"]["Skip"] for _, body in self.calls]


def _fetch(api, url=BOARD, max_jobs=1000):
    with (
        patch("ngj.http.limited_post", side_effect=api),
        patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
    ):
        return fetch_ukg_jobs("AFL", url, max_jobs=max_jobs, timeout=5)


class TestJobBoard:
    @pytest.mark.parametrize("url, expected", [
        (BOARD, BOARD),
        (BOARD + "/", BOARD),
        ("https://recruiting2.ultipro.com/BRO1018BRACA/JobBoard/a06992cf-10e7-4e24-8932-26d607a3049e",
         "https://recruiting2.ultipro.com/BRO1018BRACA/JobBoard/a06992cf-10e7-4e24-8932-26d607a3049e"),
        ("https://toshibausa.rec.pro.ukg.net/tos1004tshb/JobBoard/985e2423-dec5-4284-acff-4c6fcb30f1e4",
         "https://toshibausa.rec.pro.ukg.net/tos1004tshb/JobBoard/985e2423-dec5-4284-acff-4c6fcb30f1e4"),
        (f"{BOARD}/OpportunityDetail?opportunityId=1", None),
        ("https://evil.example.com/AFL1002/JobBoard/d535bad2-e3ea-c8c8-2fb2-63621892e293", None),
        ("", None),
    ])
    def test_board_comes_from_the_job_board_url(self, url, expected):
        assert job_board(url) == expected


class TestSearch:
    def test_search_is_a_post_newest_first(self):
        api = _Api({0: _response(200, _page([_opp("1")], 1))})
        _fetch(api)
        url, body = api.calls[0]
        assert url == SEARCH
        search = body["opportunitySearch"]
        assert (search["Top"], search["Skip"], search["Filters"]) == (PAGE_SIZE, 0, [])
        assert search["OrderBy"][0]["Value"] == "postedDateDesc" and search["OrderBy"][0]["Ascending"] is False


class TestMapping:
    def test_opportunity_maps_to_a_job_on_the_board(self):
        api = _Api({0: _response(200, _page([_opp("9da3e6be")], 1))})
        assert _fetch(api).jobs[0] == {
            "company": "AFL",
            "title": "EHS Specialist I",
            "location": "Abilene, TX, United States",
            "url": f"{BOARD}/OpportunityDetail?opportunityId=9da3e6be",
            "posted_at": "2026-10-14T13:55:08.565Z",
            "source": "UKG",
            "description": "",
            "description_html": "An entry-level field safety role.",
        }

    def test_postings_on_one_board_get_distinct_job_ids(self):
        # The posting id lives only in the query string, so canonical_url must keep it;
        # otherwise every posting on a board collapses into one job_id in dedup.
        from contracts import compute_job_id

        api = _Api({0: _response(200, _page([_opp("aaa"), _opp("bbb")], 2))})
        jobs = _fetch(api).jobs
        assert len({compute_job_id(job) for job in jobs}) == 2

    def test_internal_fields_are_never_copied(self):
        api = _Api({0: _response(200, _page([_opp("1")], 1))})
        job = repr(_fetch(api).jobs[0])
        assert "EHSSP009420" not in job and "Latitude" not in job

    def test_localized_name_wins_and_several_locations_are_joined(self):
        locations = [_location(name="Remote / Virtual", city=None, state=None), _location(city="Vancouver", state="BC",
                     country="CAN", country_name="Canada"), {"Address": None}, "junk"]
        api = _Api({0: _response(200, _page([_opp("1", locations=locations)], 1))})
        assert _fetch(api).jobs[0]["location"] == "Remote / Virtual; Vancouver, BC, Canada"

    def test_title_is_stripped_and_opportunities_without_an_id_are_skipped(self):
        no_id = {k: v for k, v in _opp("x").items() if k != "Id"}
        api = _Api({0: _response(200, _page([no_id, _opp("1", title="  Data Analyst "), "junk"], 3))})
        assert [j["title"] for j in _fetch(api).jobs] == ["Data Analyst"]


class TestPaging:
    def test_pages_until_total_count(self):
        api = _Api({0: _response(200, _page([_opp(str(i)) for i in range(PAGE_SIZE)], PAGE_SIZE + 1)),
                    PAGE_SIZE: _response(200, _page([_opp("last")], PAGE_SIZE + 1))})
        result = _fetch(api)
        assert len(result.jobs) == PAGE_SIZE + 1 and result.raw_count == PAGE_SIZE + 1
        assert api.skips() == [0, PAGE_SIZE]

    def test_full_page_without_a_total_keeps_paging(self):
        api = _Api({0: _response(200, {"opportunities": [_opp(str(i)) for i in range(PAGE_SIZE)], "totalCount": "?"}),
                    PAGE_SIZE: _response(200, {"opportunities": [_opp("last")]})})
        assert len(_fetch(api).jobs) == PAGE_SIZE + 1

    def test_cap_bounds_pages_and_postings(self):
        api = _Api({i * PAGE_SIZE: _response(200, _page([_opp(f"{i}-{j}") for j in range(PAGE_SIZE)], 10**6))
                    for i in range(20)})
        result = _fetch(api, max_jobs=150)
        assert len(result.jobs) == 150 and api.skips() == [0, PAGE_SIZE]

    def test_pages_of_unusable_records_cannot_page_forever(self):
        api = _Api({i * PAGE_SIZE: _response(200, _page(["junk"] * PAGE_SIZE, 10**9)) for i in range(50)})
        assert _fetch(api).jobs == () and len(api.calls) == 1


class TestErrors:
    def test_a_failing_page_keeps_earlier_pages_and_reports_the_error(self):
        api = _Api({0: _response(200, _page([_opp(str(i)) for i in range(PAGE_SIZE)], 500)), PAGE_SIZE: _response(500)})
        result = _fetch(api)
        assert len(result.jobs) == PAGE_SIZE
        assert [(e.company, e.source, e.kind, e.status) for e in result.errors] == [("AFL", "ukg", KIND_HTTP, 500)]

    @pytest.mark.parametrize("status", [429, 500, 503])
    def test_a_rate_limit_or_server_blip_is_retried(self, status):
        api = _Api({0: _response(200, _page([_opp("1")], 1))})
        replies = iter([_response(status), _response(status)])

        def post(url, json=None, **kwargs):
            return next(replies, None) or api(url, json=json, **kwargs)

        with (
            patch("ngj.http.limited_post", side_effect=post),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_ukg_jobs("AFL", BOARD, timeout=5)
        assert len(result.jobs) == 1 and result.errors == ()

    def test_a_persistent_server_error_is_reported_after_the_retries(self):
        calls = []

        def post(url, json=None, **_kwargs):
            calls.append(url)
            return _response(503)

        with (
            patch("ngj.http.limited_post", side_effect=post),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_ukg_jobs("AFL", BOARD, timeout=5)
        assert len(calls) == 3 and [(e.kind, e.status) for e in result.errors] == [(KIND_HTTP, 503)]

    def test_a_client_error_is_not_retried(self):
        api = _Api({0: _response(404)})
        result = _fetch(api)
        assert len(api.calls) == 1 and result.errors[0].status == 404

    @pytest.mark.parametrize("payload", [{"opportunities": "x"}, [], {"nope": 1}])
    def test_unexpected_shapes_are_parse_errors(self, payload):
        result = _fetch(_Api({0: _response(200, payload)}))
        assert result.jobs == () and result.errors[0].kind == "parse"

    def test_unusable_url_is_a_config_error_without_a_request(self):
        api = _Api({})
        result = _fetch(api, url=f"{BOARD}/OpportunityDetail?opportunityId=1")
        assert api.calls == [] and result.errors[0].kind == KIND_CONFIG

    def test_a_timeout_returns_no_partial_jobs_and_the_retry_does_not_duplicate(self):
        first = [_opp(str(i)) for i in range(PAGE_SIZE)]
        state = {"timed_out": False}

        def post(url, json=None, **_kwargs):
            skip = json["opportunitySearch"]["Skip"]
            if skip == PAGE_SIZE and not state["timed_out"]:
                state["timed_out"] = True
                raise requests.exceptions.ReadTimeout("slow")
            return _response(200, _page(first if skip == 0 else [_opp("last")], PAGE_SIZE + 1))

        settings = MagicMock(ukg_max_workers=1, ukg_max_jobs_per_company=1000, http_timeout=5)
        with (
            patch("ngj.http.limited_post", side_effect=post),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_all_ukg_jobs([{"name": "AFL", "url": BOARD}], settings)
        urls = [j["url"] for j in result.jobs]
        assert len(urls) == len(set(urls)) == PAGE_SIZE + 1
        assert result.raw_count == PAGE_SIZE + 1 and result.errors == ()


class TestFetchAll:
    def test_every_board_is_fetched_and_errors_travel_with_results(self):
        def post(url, json=None, **_kwargs):
            if "/BROKEN/" in url:
                return _response(404)
            return _response(200, _page([_opp("1")], 1))

        settings = MagicMock(ukg_max_workers=2, ukg_max_jobs_per_company=100, http_timeout=5)
        companies = [{"name": "AFL", "url": BOARD},
                     {"name": "Broken", "url": "https://recruiting.ultipro.com/BROKEN/JobBoard/d535bad2-e3ea-c8c8-2fb2-63621892e293"}]
        with (
            patch("ngj.http.limited_post", side_effect=post),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_all_ukg_jobs(companies, settings)
        assert [j["company"] for j in result.jobs] == ["AFL"]
        assert [(e.company, e.status) for e in result.errors] == [("Broken", 404)]

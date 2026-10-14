#!/usr/bin/env python3
"""ADP Workforce Now career-center adapter: careers URL, mapping, paging quirks, errors."""

import os
import sys
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from contracts import compute_job_id  # noqa: E402
from ngj import http as ngj_http  # noqa: E402
from ngj.models import KIND_CONFIG, KIND_HTTP  # noqa: E402
from ngj.sources.adp import (  # noqa: E402
    PAGE_SIZE,
    careers_cid,
    fetch_adp_jobs,
    fetch_all_adp_jobs,
)
from source_cooldown import SourceCooldownTracker  # noqa: E402

CID = "7c116ec3-ef0f-42e8-8bf0-491739a45ba3"
CAREERS = f"https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid={CID}"


def _req(ext: str | None, title: str = "Junior Environmental Technician", **extra) -> dict:
    strings = [{"stringValue": "", "nameCode": {"codeValue": "HomeDepartment"}}]
    if ext is not None:
        strings.append({"stringValue": ext, "nameCode": {"codeValue": "ExternalJobID"}})
    return {"itemID": f"9203173728810_{ext}", "requisitionTitle": title, "postDate": "2026-10-02T16:40:00.000-04:00",
            "clientRequisitionID": "3268", "workLevelCode": {"shortName": "Full Time"},
            "customFieldGroup": {"stringFields": strings, "numberFields": [{"numberValue": 3.0}]},
            "requisitionLocations": [{"address": {"cityName": "Atlantic Beach", "countrySubdivisionLevel1": {"codeValue": "FL"}},
                                      "nameCode": {"shortName": " Atlantic Beach, FL, US"}}], **extra}


def _response(status: int, payload=None) -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.ok = 200 <= status < 300
    response.json.return_value = payload if payload is not None else {}
    response.text = ""
    return response


def _page(reqs: list, total: int) -> dict:
    return {"jobRequisitions": reqs, "meta": {"startSequence": 1, "totalNumber": total, "links": []}}


class _Api:
    """Fake requisitions endpoint: ``pages[skip]`` -> response; records every query."""

    def __init__(self, pages: dict):
        self.pages = pages
        self.calls: list[dict] = []

    def __call__(self, url, **_kwargs):
        query = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
        self.calls.append(query)
        return self.pages.get(int(query.get("$skip", 0)), _response(200, _page([], 0)))

    def skips(self):
        return [int(c["$skip"]) for c in self.calls]


def _fetch(api, url=CAREERS, max_jobs=1000):
    with (
        patch("ngj.http.limited_get", side_effect=api),
        patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
    ):
        return fetch_adp_jobs("Moran", url, max_jobs=max_jobs, timeout=5)


class TestCareersUrl:
    @pytest.mark.parametrize("url, expected", [
        (CAREERS, CID),
        (CAREERS.replace(CID, CID.upper()), CID.upper()),
        (f"{CAREERS}&jobId=595411", None),
        (f"https://workforcenow.adp.com/mascsr/default/careercenter/public/events/staffing/v1/job-requisitions?cid={CID}", None),
        (f"https://evil.example.com/mascsr/default/mdf/recruitment/recruitment.html?cid={CID}", None),
        ("", None),
    ])
    def test_cid_comes_from_the_career_center_url(self, url, expected):
        assert careers_cid(url) == expected


class TestMapping:
    def test_requisition_maps_to_a_job_on_the_career_center(self):
        api = _Api({0: _response(200, _page([_req("595411")], 1))})
        assert _fetch(api).jobs[0] == {
            "company": "Moran",
            "title": "Junior Environmental Technician",
            "location": "Atlantic Beach, FL, US",
            "url": f"{CAREERS}&jobId=595411",
            "posted_at": "2026-10-02T16:40:00.000-04:00",
            "source": "ADP",
            "description": "",
        }

    def test_an_uppercase_cid_yields_the_same_job_url(self):
        api = _Api({0: _response(200, _page([_req("595411")], 1))})
        job = _fetch(api, url=CAREERS.replace(CID, CID.upper())).jobs[0]
        assert job["url"] == f"{CAREERS}&jobId=595411"

    def test_query_uses_the_tenant_and_the_page_size(self):
        api = _Api({0: _response(200, _page([_req("1")], 1))})
        _fetch(api)
        assert (api.calls[0]["cid"], api.calls[0]["$top"], api.calls[0]["$skip"]) == (CID, str(PAGE_SIZE), "0")

    def test_internal_fields_are_never_copied(self):
        api = _Api({0: _response(200, _page([_req("1")], 1))})
        job = repr(_fetch(api).jobs[0])
        assert "9203173728810" not in job and "3268" not in job

    def test_address_is_used_when_there_is_no_location_name_and_names_are_not_repeated(self):
        locations = [{"address": {"cityName": "Murray", "countrySubdivisionLevel1": {"codeValue": "KY"}}},
                     {"nameCode": {"shortName": "Murray, KY"}}, "junk", {"nameCode": {"shortName": "Tampa, FL, US"}}]
        api = _Api({0: _response(200, _page([_req("1", requisitionLocations=locations)], 1))})
        assert _fetch(api).jobs[0]["location"] == "Murray, KY; Tampa, FL, US"

    def test_title_is_stripped_and_requisitions_without_a_public_id_are_skipped(self):
        api = _Api({0: _response(200, _page([_req(None), _req("1", title="  Data Analyst "), "junk"], 3))})
        assert [j["title"] for j in _fetch(api).jobs] == ["Data Analyst"]

    def test_job_ids_are_distinct_per_posting_and_per_company(self):
        other = CAREERS.replace(CID, "2ac19c2c-cd24-4fd1-8ab6-b1d93b864c78")
        jobs = [*_fetch(_Api({0: _response(200, _page([_req("1"), _req("2")], 2))})).jobs,
                *_fetch(_Api({0: _response(200, _page([_req("1")], 1))}), url=other).jobs]
        assert len({compute_job_id(job) for job in jobs}) == 3


class TestPaging:
    def test_steps_by_rows_returned_and_drops_the_repeated_boundary_row(self):
        first = [_req(str(i)) for i in range(PAGE_SIZE)]
        second = [_req(str(PAGE_SIZE - 1)), _req("a"), _req("b")]  # $skip is 1-based: one row repeats
        api = _Api({0: _response(200, _page(first, PAGE_SIZE + 2)), PAGE_SIZE: _response(200, _page(second, PAGE_SIZE + 2))})
        result = _fetch(api)
        assert len(result.jobs) == PAGE_SIZE + 2 == result.raw_count
        assert len({j["url"] for j in result.jobs}) == PAGE_SIZE + 2
        assert api.skips() == [0, PAGE_SIZE]

    def test_a_server_that_ignores_skip_cannot_page_forever(self):
        same = _response(200, _page([_req(str(i)) for i in range(PAGE_SIZE)], 10**6))
        api = _Api({PAGE_SIZE * i: same for i in range(100)})
        result = _fetch(api)
        assert len(result.jobs) == PAGE_SIZE and len(api.calls) == 2

    def test_cap_bounds_pages_and_postings(self):
        api = _Api({PAGE_SIZE * i: _response(200, _page([_req(f"{i}-{j}") for j in range(PAGE_SIZE)], 10**6))
                    for i in range(100)})
        result = _fetch(api, max_jobs=30)
        assert len(result.jobs) == 30 and api.skips() == [0, PAGE_SIZE]

    def test_a_page_without_public_ids_does_not_end_paging(self):
        api = _Api({0: _response(200, _page([_req(None) for _ in range(PAGE_SIZE)], PAGE_SIZE + 1)),
                    PAGE_SIZE: _response(200, _page([_req("1")], PAGE_SIZE + 1))})
        assert [j["url"].rsplit("=", 1)[1] for j in _fetch(api).jobs] == ["1"]

    def test_empty_page_ends_paging(self):
        api = _Api({0: _response(200, _page([], 50))})
        assert _fetch(api).jobs == () and len(api.calls) == 1


class TestErrors:
    def test_a_failing_page_keeps_earlier_pages_and_reports_the_error(self):
        api = _Api({0: _response(200, _page([_req(str(i)) for i in range(PAGE_SIZE)], 100)), PAGE_SIZE: _response(500)})
        result = _fetch(api)
        assert len(result.jobs) == PAGE_SIZE
        assert [(e.company, e.source, e.kind, e.status) for e in result.errors] == [("Moran", "adp", KIND_HTTP, 500)]

    @pytest.mark.parametrize("payload", [{"jobRequisitions": "x"}, [], {"meta": {}}])
    def test_unexpected_shapes_are_parse_errors(self, payload):
        result = _fetch(_Api({0: _response(200, payload)}))
        assert result.jobs == () and result.errors[0].kind == "parse"

    def test_unusable_url_is_a_config_error_without_a_request(self):
        api = _Api({})
        result = _fetch(api, url=f"{CAREERS}&jobId=1")
        assert api.calls == [] and result.errors[0].kind == KIND_CONFIG

    def test_a_timeout_returns_no_partial_jobs_and_the_retry_does_not_duplicate(self):
        first = [_req(str(i)) for i in range(PAGE_SIZE)]
        state = {"timed_out": False}

        def get(url, **_kwargs):
            skip = int(parse_qs(urlparse(url).query)["$skip"][0])
            if skip == PAGE_SIZE and not state["timed_out"]:
                state["timed_out"] = True
                raise requests.exceptions.ReadTimeout("slow")
            return _response(200, _page(first if skip == 0 else [_req("last")], PAGE_SIZE + 1))

        settings = MagicMock(adp_max_workers=1, adp_max_jobs_per_company=1000, http_timeout=5)
        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_all_adp_jobs([{"name": "Moran", "url": CAREERS}], settings)
        urls = [j["url"] for j in result.jobs]
        assert len(urls) == len(set(urls)) == PAGE_SIZE + 1 and result.errors == ()


class TestFetchAll:
    def test_every_company_is_fetched_and_errors_travel_with_results(self):
        broken = "2ac19c2c-cd24-4fd1-8ab6-b1d93b864c78"

        def get(url, **_kwargs):
            if broken in url:
                return _response(404)
            return _response(200, _page([_req("1")], 1))

        settings = MagicMock(adp_max_workers=2, adp_max_jobs_per_company=100, http_timeout=5)
        companies = [{"name": "Moran", "url": CAREERS}, {"name": "Broken", "url": CAREERS.replace(CID, broken)}]
        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_all_adp_jobs(companies, settings)
        assert [j["company"] for j in result.jobs] == ["Moran"]
        assert [(e.company, e.status) for e in result.errors] == [("Broken", 404)]

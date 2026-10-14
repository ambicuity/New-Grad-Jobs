#!/usr/bin/env python3
"""Paylocity board adapter: board URL, embedded pageData parsing, mapping, errors."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from contracts import compute_job_id  # noqa: E402
from ngj import http as ngj_http  # noqa: E402
from ngj.models import KIND_CONFIG, KIND_HTTP  # noqa: E402
from ngj.sources.paylocity import board_guid, fetch_all_paylocity_jobs, fetch_paylocity_jobs  # noqa: E402
from source_cooldown import SourceCooldownTracker  # noqa: E402

GUID = "6a14a346-cc8d-4490-a772-4a087d8cab39"
URL = f"https://recruiting.paylocity.com/Recruiting/Jobs/All/{GUID}"


def _job(jid: int | None, title: str = "Associates Software Engineer", **extra) -> dict:
    job = {"JobTitle": title, "LocationName": "C3 EOC - Washington, D.C.", "ShouldDisplayLocation": True,
           "PublishedDate": "2026-10-14T15:29:58-05:00", "Description": "Concept Solutions is seeking an engineer",
           "IsInternal": False, "HiringDepartment": None, "IsRemote": False,
           "JobLocation": {"LocationId": 4512719, "ModuleId": 13776, "Name": "C3 EOC", "City": "Washington",
                           "State": "DC", "Zip": "20591", "Country": "USA", "County": "District of Columbia"},
           **extra}
    if jid is not None:
        job["JobId"] = jid
    return job


def _page(jobs: list, title: str = "CONCEPT SOLUTIONS LLC") -> str:
    data = json.dumps({"ModuleId": 13776, "ModuleTitle": title, "Jobs": jobs, "ShowInternal": False})
    return (f"<html><head><script>window.dataLayer = [{{}}];</script></head><body>"
            f"<script>\n    window.pageData = {data};\n  </script><script>var x = 1;</script></body></html>")


def _response(status: int, text: str = "") -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.ok = 200 <= status < 300
    response.text = text
    response.json.side_effect = ValueError("not json")
    return response


def _fetch(text: str | MagicMock, url: str = URL):
    calls = []

    def get(u, **_kwargs):
        calls.append(u)
        return text if isinstance(text, MagicMock) else _response(200, text)

    with (
        patch("ngj.http.limited_get", side_effect=get),
        patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
    ):
        return fetch_paylocity_jobs("Concept Solutions", url, timeout=5), calls


class TestBoardGuid:
    @pytest.mark.parametrize("url, expected", [
        (URL, GUID),
        (f"{URL}/", GUID),
        (URL.replace(GUID, GUID.upper()), GUID),
        ("https://recruiting.paylocity.com/Recruiting/Jobs/Details/4579798", None),
        (f"https://evil.example.com/Recruiting/Jobs/All/{GUID}", None),
        ("", None),
    ])
    def test_guid_comes_from_the_board_url(self, url, expected):
        assert board_guid(url) == expected


class TestMapping:
    def test_job_maps_to_a_posting_page(self):
        result, calls = _fetch(_page([_job(4579798)]))
        assert result.jobs[0] == {
            "company": "Concept Solutions",
            "title": "Associates Software Engineer",
            "location": "Washington, DC, USA",
            "url": "https://recruiting.paylocity.com/Recruiting/Jobs/Details/4579798",
            "posted_at": "2026-10-14T15:29:58-05:00",
            "source": "Paylocity",
            "description": "",
            "description_html": "Concept Solutions is seeking an engineer",
        }
        assert calls == [f"https://recruiting.paylocity.com/Recruiting/Jobs/All/{GUID}"]

    def test_remote_is_marked_once(self):
        result, _ = _fetch(_page([_job(1, IsRemote=True), _job(2, IsRemote=True, JobLocation=None, LocationName="Remote, US")]))
        assert [j["location"] for j in result.jobs] == ["Remote, Washington, DC, USA", "Remote, US"]

    def test_location_name_is_the_fallback_and_hidden_locations_stay_hidden(self):
        result, _ = _fetch(_page([_job(1, JobLocation=None), _job(2, JobLocation=None, ShouldDisplayLocation=False)]))
        assert [j["location"] for j in result.jobs] == ["C3 EOC - Washington, D.C.", ""]

    def test_a_remote_job_with_a_hidden_location_is_just_remote(self):
        result, _ = _fetch(_page([_job(1, IsRemote=True, ShouldDisplayLocation=False)]))
        assert result.jobs[0]["location"] == "Remote"

    def test_internal_and_id_less_jobs_are_skipped_and_titles_stripped(self):
        result, _ = _fetch(_page([_job(None), _job(1, IsInternal=True), _job(2, title="  Data Analyst "), "junk"]))
        assert [j["title"] for j in result.jobs] == ["Data Analyst"] and result.raw_count == 1

    def test_internal_ids_are_never_copied_and_job_ids_are_distinct(self):
        result, _ = _fetch(_page([_job(1), _job(2)]))
        assert "4512719" not in repr(result.jobs) and "13776" not in repr(result.jobs)
        assert len({compute_job_id(j) for j in result.jobs}) == 2

    def test_an_earlier_decoy_assignment_does_not_hide_the_real_page_data(self):
        decoy = "<script>window.pageData = window.pageData || {};</script><script>window.pageData = {\"x\": 1};</script>"
        result, _ = _fetch(decoy + _page([_job(7)]))
        assert [j["url"].rsplit("/", 1)[1] for j in result.jobs] == ["7"] and result.errors == ()

    def test_a_script_tag_inside_a_description_does_not_cut_the_data_short(self):
        result, _ = _fetch(_page([_job(1, Description="see </script> here")]))
        assert result.jobs[0]["description_html"] == "see </script> here"


class TestErrors:
    @pytest.mark.parametrize("text", ["<html>no data here</html>", "<script>window.pageData = {broken;</script>",
                                      _page("not-a-list"), "<script>window.pageData = [];</script>"])
    def test_a_page_without_usable_page_data_is_a_parse_error(self, text):
        result, _ = _fetch(text)
        assert result.jobs == () and result.errors[0].kind == "parse"

    def test_http_errors_are_reported(self):
        result, _ = _fetch(_response(404))
        assert [(e.company, e.source, e.kind, e.status) for e in result.errors] == [
            ("Concept Solutions", "paylocity", KIND_HTTP, 404)]

    def test_unusable_url_is_a_config_error_without_a_request(self):
        result, calls = _fetch(_page([]), url="https://recruiting.paylocity.com/Recruiting/Jobs/Details/1")
        assert calls == [] and result.errors[0].kind == KIND_CONFIG


class TestFetchAll:
    def test_every_board_is_fetched_errors_travel_and_timeouts_are_retried(self):
        state = {"timed_out": False}
        other = "4731cca6-0000-4000-8000-000000000000"

        def get(url, **_kwargs):
            if url.endswith("deadbeef-0000-4000-8000-000000000000"):
                return _response(404)
            if url.endswith(other) and not state["timed_out"]:
                state["timed_out"] = True
                raise requests.exceptions.ReadTimeout("slow")
            return _response(200, _page([_job(1 if url.endswith(GUID) else 2)]))

        settings = MagicMock(paylocity_max_workers=2, http_timeout=5)
        companies = [{"name": "Concept Solutions", "url": URL},
                     {"name": "E&M", "url": URL.replace(GUID, other)},
                     {"name": "Broken", "url": URL.replace(GUID, "deadbeef-0000-4000-8000-000000000000")}]
        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_all_paylocity_jobs(companies, settings)
        assert sorted(j["company"] for j in result.jobs) == ["Concept Solutions", "E&M"]
        assert [(e.company, e.status) for e in result.errors] == [("Broken", 404)]

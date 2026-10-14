#!/usr/bin/env python3
"""Workable account-widget adapter: account URL, row merging, mapping, errors."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from contracts import compute_job_id  # noqa: E402
from ngj import http as ngj_http  # noqa: E402
from ngj.models import KIND_CONFIG, KIND_HTTP  # noqa: E402
from ngj.sources.workable import (  # noqa: E402
    account_slug,
    fetch_all_workable_jobs,
    fetch_workable_jobs,
)
from source_cooldown import SourceCooldownTracker  # noqa: E402

URL = "https://apply.workable.com/api/v1/widget/accounts/credence"


def _row(code: str | None, title: str = "Business Analyst", city="McLean", state="Virginia", country="United States",
         **extra) -> dict:
    row = {"title": title, "code": "2026-10299", "employment_type": "Full-time", "telecommuting": False,
           "department": "Agency", "url": f"https://apply.workable.com/j/{code}", "published_on": "2026-10-01",
           "created_at": "2026-09-30", "country": country, "city": city, "state": state,
           "locations": [{"country": country, "countryCode": "US", "city": city, "region": state, "hidden": False}],
           "experience": "Entry level", **extra}
    if code is not None:
        row["shortcode"] = code
    return row


def _response(status: int, payload=None) -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.ok = 200 <= status < 300
    response.json.return_value = payload if payload is not None else {}
    response.text = ""
    return response


def _account(rows: list) -> dict:
    return {"name": "Credence", "description": "<p>About</p>", "jobs": rows}


def _fetch(get, url=URL):
    with (
        patch("ngj.http.limited_get", side_effect=get),
        patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
    ):
        return fetch_workable_jobs("Credence", url, timeout=5)


def _serve(payload):
    calls = []

    def get(url, **_kwargs):
        calls.append(url)
        return _response(200, payload) if not isinstance(payload, MagicMock) else payload

    return get, calls


class TestAccountSlug:
    @pytest.mark.parametrize("url, expected", [
        (URL, "credence"),
        ("https://apply.workable.com/api/v1/widget/accounts/texas-sports-academy-main/", "texas-sports-academy-main"),
        ("https://apply.workable.com/credence/j/053C4602C2", None),
        ("https://evil.example.com/api/v1/widget/accounts/credence", None),
        ("", None),
    ])
    def test_slug_comes_from_the_widget_url(self, url, expected):
        assert account_slug(url) == expected


class TestMapping:
    def test_row_maps_to_a_job(self):
        get, calls = _serve(_account([_row("053C4602C2")]))
        assert _fetch(get).jobs[0] == {
            "company": "Credence",
            "title": "Business Analyst",
            "location": "McLean, Virginia, United States",
            "url": "https://apply.workable.com/j/053C4602C2",
            "posted_at": "2026-10-01",
            "source": "Workable",
            "description": "",
        }
        assert calls == [URL]

    def test_one_row_per_location_is_merged_into_one_posting(self):
        rows = [_row("A1"), _row("B2"), _row("A1", city="Dayton", state="Ohio"), _row("A1")]
        get, _ = _serve(_account(rows))
        result = _fetch(get)
        assert [j["url"].rsplit("/", 1)[1] for j in result.jobs] == ["A1", "B2"]
        assert result.jobs[0]["location"] == "McLean, Virginia, United States; Dayton, Ohio, United States"
        assert result.raw_count == 2
        assert len({compute_job_id(j) for j in result.jobs}) == 2

    def test_remote_postings_say_so_once(self):
        get, _ = _serve(_account([_row("A1", telecommuting=True), _row("B2", telecommuting=True, city="Remote")]))
        jobs = _fetch(get).jobs
        assert jobs[0]["location"] == "Remote, McLean, Virginia, United States"
        assert jobs[1]["location"] == "Remote, Virginia, United States"

    def test_hidden_locations_are_never_exposed_through_the_row_fields(self):
        row = _row("A1", locations=[{"city": "Secret", "hidden": True}, "junk"])
        get, _ = _serve(_account([row]))
        assert _fetch(get).jobs[0]["location"] == ""

    def test_row_fields_are_used_when_there_is_no_locations_list(self):
        row = {k: v for k, v in _row("A1").items() if k != "locations"}
        get, _ = _serve(_account([row]))
        assert _fetch(get).jobs[0]["location"] == "McLean, Virginia, United States"

    def test_a_place_repeated_inside_one_row_is_listed_once(self):
        place = {"country": "United States", "city": "McLean", "region": "Virginia", "hidden": False}
        get, _ = _serve(_account([_row("A1", locations=[place, place])]))
        assert _fetch(get).jobs[0]["location"] == "McLean, Virginia, United States"

    def test_url_is_always_built_from_the_shortcode(self):
        rows = [_row("A1", url="https://apply.workable.com/credence/j/A1/apply"), _row("B2", url="")]
        get, _ = _serve(_account(rows))
        assert [j["url"] for j in _fetch(get).jobs] == ["https://apply.workable.com/j/A1", "https://apply.workable.com/j/B2"]

    def test_merged_rows_keep_the_first_title_and_the_earliest_date(self):
        rows = [_row("A1", title="", published_on="2026-10-05"), _row("A1", title="Data Analyst", published_on="2026-10-01"),
                _row("A1", title="Data Analyst II", published_on="", created_at="")]
        get, _ = _serve(_account(rows))
        job = _fetch(get).jobs[0]
        assert (job["title"], job["posted_at"]) == ("Data Analyst", "2026-10-01")

    def test_date_falls_back_to_created_at(self):
        get, _ = _serve(_account([_row("A1", published_on="")]))
        assert _fetch(get).jobs[0]["posted_at"] == "2026-09-30"

    def test_rows_without_a_shortcode_are_skipped_and_titles_stripped(self):
        get, _ = _serve(_account([_row(None), _row("A1", title="  Data Analyst "), "junk"]))
        assert [j["title"] for j in _fetch(get).jobs] == ["Data Analyst"]

    def test_internal_fields_are_never_copied(self):
        get, _ = _serve(_account([_row("A1")]))
        job = repr(_fetch(get).jobs[0])
        assert "2026-10299" not in job and "Agency" not in job


class TestErrors:
    @pytest.mark.parametrize("payload", [{"jobs": "x"}, [], {"name": "x"}])
    def test_unexpected_shapes_are_parse_errors(self, payload):
        get, _ = _serve(payload)
        result = _fetch(get)
        assert result.jobs == () and result.errors[0].kind == "parse"

    def test_http_errors_are_reported(self):
        get, _ = _serve(_response(404))
        assert [(e.company, e.source, e.kind, e.status) for e in _fetch(get).errors] == [("Credence", "workable", KIND_HTTP, 404)]

    def test_unusable_url_is_a_config_error_without_a_request(self):
        get, calls = _serve(_account([]))
        result = _fetch(get, url="https://apply.workable.com/credence/j/053C4602C2")
        assert calls == [] and result.errors[0].kind == KIND_CONFIG


class TestFetchAll:
    def test_every_account_is_fetched_errors_travel_and_timeouts_are_retried(self):
        state = {"timed_out": False}

        def get(url, **_kwargs):
            if url.endswith("/broken"):
                return _response(404)
            if url.endswith("/zifo") and not state["timed_out"]:
                state["timed_out"] = True
                raise requests.exceptions.ReadTimeout("slow")
            return _response(200, _account([_row(url.rsplit("/", 1)[1])]))

        settings = MagicMock(workable_max_workers=2, http_timeout=5)
        companies = [{"name": n, "url": f"https://apply.workable.com/api/v1/widget/accounts/{s}"}
                     for n, s in (("Credence", "credence"), ("Zifo", "zifo"), ("Broken", "broken"))]
        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_all_workable_jobs(companies, settings)
        assert sorted(j["company"] for j in result.jobs) == ["Credence", "Zifo"]
        assert [(e.company, e.status) for e in result.errors] == [("Broken", 404)]

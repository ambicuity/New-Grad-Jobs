"""Workday "N Locations" postings: the real locations come from the job endpoint (#427)."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ngj import http as ngj_http  # noqa: E402
from ngj.locations import is_valid_location  # noqa: E402
from ngj.sources.workday import (  # noqa: E402
    _resolve_locations,
    _Tenant,
    build_title_prefilter,
    fetch_workday_jobs,
    location_from_detail,
)
from source_cooldown import SourceCooldownTracker  # noqa: E402

COMPANY = {"name": "Acme", "workday_url": "https://acme.wd5.myworkdayjobs.com/Careers"}
FILTERING = {"new_grad_signals": ["new grad", "junior"], "exclusion_signals": ["senior"]}
DETAIL_BASE = "https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/Careers"
TITLE_FILTER = build_title_prefilter(FILTERING)


def _resp(status=200, body=None):
    m = MagicMock()
    m.status_code = status
    m.ok = 200 <= status < 300
    m.json.return_value = body
    m.text = ""
    return m


def _item(path, title="Software Engineer, New Grad", locations="2 Locations"):
    return {"title": title, "externalPath": path, "locationsText": locations, "postedOn": "Posted Today"}


def _info(location="Durham", additional=("Remote United States",), country="United States of America"):
    info = {"title": "x", "location": location, "additionalLocations": list(additional)}
    if country:
        info["country"] = {"descriptor": country}
    return {"jobPostingInfo": info}


class FakeTenant:
    """One search page of ``items``; job endpoints answer from ``details`` (path -> response or exception)."""

    def __init__(self, items, details=None):
        self.items, self.details, self.gets = items, details or {}, []

    def post(self, url, json=None, **kwargs):
        return _resp(body={"jobPostings": self.items if json["offset"] == 0 else []})

    def get(self, url, **kwargs):
        self.gets.append(url)
        path = url.removeprefix(DETAIL_BASE)
        assert path.startswith("/job/"), url  # a lookup never leaves the tenant's job endpoint
        detail = self.details.get(path, _resp(body=_info()))
        if isinstance(detail, Exception):
            raise detail
        return detail


def _fetch(tenant, title_filter=TITLE_FILTER, **kwargs):
    with (
        patch("ngj.http.limited_post", side_effect=tenant.post),
        patch("ngj.http.limited_get", side_effect=tenant.get),
        patch("ngj.sources.workday.get_workday_csrf_token", return_value=""),
        patch("ngj.http.get_session", return_value=MagicMock()),
        patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
    ):
        return fetch_workday_jobs([COMPANY], title_filter=title_filter, **kwargs)


class TestLocationFromDetail:
    @pytest.mark.parametrize("payload, expected", [
        (_info(), "Durham, United States of America; Remote United States"),
        (_info("Toronto, Ontario, Canada", (), "Canada"), "Toronto, Ontario, Canada"),
        (_info("Austin", ("Austin",), None), "Austin"),
        (_info("", ("Remote United States",), "United States of America"), "Remote United States"),
        # A country already written as the last part is not repeated.
        (_info("Houston, Texas, US", ("Cary, North Carolina, US",), "United States of America"),
         "Houston, Texas, US; Cary, North Carolina, US"),
        (_info("Indianapolis", (), "India"), "Indianapolis, India"),
        (_info("Baltimore, Maryland, United States", (), "United States of America"), "Baltimore, Maryland, United States"),
        (_info("Austin, TX, USA", (), "United States of America"), "Austin, TX, USA"),
        # A foreign primary with qualified additional locations: the gate can judge every place.
        (_info("London", ("Plano, TX",), "United Kingdom"), "London, United Kingdom; Plano, TX"),
        (_info("Sydney", ("Melbourne, Australia",), "Australia"), "Sydney, Australia; Melbourne, Australia"),
    ])
    def test_primary_location_gets_its_country_and_others_follow(self, payload, expected):
        assert location_from_detail(payload) == expected

    @pytest.mark.parametrize("payload", [
        None, [], {}, {"jobPostingInfo": "x"}, {"jobPostingInfo": {}},
        # Ambiguous: a foreign primary, and bare additional cities whose country is unknown
        # ("Plano" may be in the US). The posting keeps its listed text rather than be dropped.
        _info("London", ("Plano", "Jersey City"), "United Kingdom"),
        _info("Sydney", ("Melbourne", "Adelaide"), "Australia"),
    ])
    def test_unusable_or_ambiguous_payloads_give_nothing(self, payload):
        assert location_from_detail(payload) == ""


class TestLookups:
    def test_a_plausible_multi_location_posting_gets_its_real_locations(self):
        tenant = FakeTenant([_item("/job/1")])
        (job,) = _fetch(tenant).jobs
        assert tenant.gets == [f"{DETAIL_BASE}/job/1"]
        assert job["location"] == "Durham, United States of America; Remote United States"
        assert job["url"] == "https://acme.wd5.myworkdayjobs.com/Careers/job/1"

    def test_a_foreign_only_posting_now_reads_as_foreign(self):
        tenant = FakeTenant([_item("/job/1")], {"/job/1": _resp(body=_info("Sydney", ("Melbourne, Australia",), "Australia"))})
        assert _fetch(tenant).jobs[0]["location"] == "Sydney, Australia; Melbourne, Australia"

    def test_single_location_and_implausible_titles_are_not_looked_up(self):
        tenant = FakeTenant([_item("/job/1", locations="Austin, TX"), _item("/job/2", title="Senior Engineer")])
        result = _fetch(tenant)
        assert tenant.gets == []
        assert [j["location"] for j in result.jobs] == ["Austin, TX", "2 Locations"]

    def test_without_a_title_filter_every_multi_location_posting_is_looked_up(self):
        tenant = FakeTenant([_item("/job/1", title="Senior Engineer")])
        _fetch(tenant, title_filter=None)
        assert tenant.gets == [f"{DETAIL_BASE}/job/1"]

    def test_the_lookup_cap_keeps_the_rest_as_listed(self):
        tenant = FakeTenant([_item(f"/job/{n}") for n in range(3)])
        result = _fetch(tenant, max_location_lookups=2)
        assert len(tenant.gets) == 2
        resolved = "Durham, United States of America; Remote United States"
        assert [j["location"] for j in result.jobs] == [resolved, resolved, "2 Locations"]

    @pytest.mark.parametrize("failure", [
        _resp(500), _resp(404), _resp(200, {"unexpected": True}), requests.exceptions.ReadTimeout("slow")])
    def test_a_failed_lookup_keeps_the_posting_as_listed_without_an_error(self, failure):
        tenant = FakeTenant([_item("/job/1"), _item("/job/2")], {"/job/1": failure})
        result = _fetch(tenant)
        assert [j["location"] for j in result.jobs] == [
            "2 Locations", "Durham, United States of America; Remote United States"]
        assert result.errors == ()

    @pytest.mark.parametrize("status", [403, 429])
    def test_a_blocked_lookup_stops_the_remaining_lookups(self, status):
        tenant = FakeTenant([_item(f"/job/{n}") for n in range(3)], {"/job/0": _resp(status)})
        result = _fetch(tenant)
        assert len(tenant.gets) == 1 and [j["location"] for j in result.jobs] == ["2 Locations"] * 3
        assert result.errors == ()

    def test_a_forbidden_lookup_counts_toward_the_tenant_cooldown(self):
        tracker = SourceCooldownTracker(threshold=1)
        tenant = FakeTenant([_item("/job/1")], {"/job/1": _resp(403)})
        with (
            patch("ngj.http.limited_post", side_effect=tenant.post),
            patch("ngj.http.limited_get", side_effect=tenant.get),
            patch("ngj.sources.workday.get_workday_csrf_token", return_value=""),
            patch("ngj.http.get_session", return_value=MagicMock()),
            patch.object(ngj_http, "SOURCE_COOLDOWN", tracker),
        ):
            fetch_workday_jobs([COMPANY], title_filter=TITLE_FILTER)
        assert tracker.is_tripped(f"{DETAIL_BASE}/jobs")

    @pytest.mark.parametrize("path", ["/job/../../x", "/job/%2e%2e/x", "/job/x\n", "/other/1", "/job/x?y=1"])
    def test_unusual_external_paths_are_not_looked_up(self, path):
        tenant = FakeTenant([_item(path)])
        _fetch(tenant)
        assert tenant.gets == []

    def test_a_foreign_only_posting_now_fails_the_location_gate(self):
        tenant = FakeTenant([_item("/job/1"), _item("/job/2")],
                            {"/job/1": _resp(body=_info("Munich", ("Berlin, Germany",), "Germany"))})
        jobs = _fetch(tenant).jobs
        assert [is_valid_location(j["location"]) for j in jobs] == [False, True]
        assert is_valid_location("2 Locations")  # what the listing alone gives: passes

    def test_no_lookups_once_the_time_budget_is_used_up(self):
        tenant = FakeTenant([_item("/job/1")])
        clock = {"now": 0.0}
        search = tenant.post

        def slow_search(url, **kwargs):
            clock["now"] = 1e9  # the search used up the whole budget
            return search(url, **kwargs)

        tenant.post = slow_search
        with patch("ngj.sources.workday.time.monotonic", side_effect=lambda: clock["now"]):
            result = _fetch(tenant, max_seconds_per_company=60)
        assert tenant.gets == [] and result.jobs[0]["location"] == "2 Locations"

    def test_resolving_returns_new_dicts_and_leaves_the_input_alone(self):
        tenant = _Tenant("Acme", "https://acme.wd5.myworkdayjobs.com/Careers", f"{DETAIL_BASE}/jobs", {}, 20, 1, 5)
        job = {"title": "Junior Engineer", "location": "2 Locations", "url": "u"}
        with (
            patch("ngj.http.limited_get", return_value=_resp(body=_info())),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            (resolved,) = _resolve_locations(tenant, (("/job/1", job),), TITLE_FILTER, 5)
        assert job == {"title": "Junior Engineer", "location": "2 Locations", "url": "u"}
        assert resolved is not job and resolved["location"].startswith("Durham")

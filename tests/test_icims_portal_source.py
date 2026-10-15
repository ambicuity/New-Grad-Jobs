#!/usr/bin/env python3
"""Classic iCIMS portal adapter (``careers-<co>.icims.com``): list cards, job pages, locations, errors."""

import json
import os
import sys
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from contracts import compute_job_id  # noqa: E402
from ngj import http as ngj_http  # noqa: E402
from ngj.models import KIND_CONFIG, KIND_HTTP, KIND_PARSE  # noqa: E402
from ngj.sources.icims_portal import (  # noqa: E402
    fetch_icims_portal_jobs,
    parse_detail,
    parse_search_page,
    portal_base,
    portal_location,
)
from source_cooldown import SourceCooldownTracker  # noqa: E402

BASE = "https://careers-rovisys.icims.com"
NOW = datetime(2026, 10, 15, 14, 14, tzinfo=UTC)
FILTERING = {
    "new_grad_signals": ["junior", "new grad", "entry level", "associate", "I"],
    "track_signals": ["engineer", "developer", "analyst"],
    "exclusion_signals": ["senior", "manager"],
    "level_signals": ["I", "II"],
}


def _card(jid: int, title: str, location: str | None = "US-OH-Dublin", *, host: str = BASE,
          fields: dict[str, str] | None = None, date: str | None = None, location_in_list: bool = False) -> str:
    """One ``li.iCIMS_JobCardItem``: the header carries a location (or a date), the dl carries fields."""
    slug = title.lower().replace(" ", "-")
    header = ""
    if location is not None and not location_in_list:
        header += ('<div class="col-xs-6 header left"><span class="sr-only field-label">Job Locations</span>'
                   f'<span >\n{location}</span></div>')
    if date is not None:
        header += ('<div class="col-xs-6 header right"><span class="sr-only field-label">Posted Date</span>'
                   f'<span title="{date}">\n17 hours ago<span class="sr-only">({date})</span></span></div>')
    items = dict(fields or {})
    if location is not None and location_in_list:
        items = {"Location": location, **items}
    dl = "".join(
        '<div class="iCIMS_JobHeaderTag"><dt class="iCIMS_JobHeaderField">'
        + (('<span class="glyphicons glyphicons-map-marker" aria-hidden="true"></span>'
            f'<span class="sr-only field-label">{label}</span>') if label == "Location" else label)
        + f'</dt><dd class="iCIMS_JobHeaderData"><span >\n{value}</span>\n</dd></div>'
        for label, value in items.items()
    )
    return (
        f'<li class="iCIMS_JobCardItem"><div class="row">{header}<div class="col-xs-12 title">'
        f'<a href="{host}/jobs/{jid}/{slug}/job?in_iframe=1" class="iCIMS_Anchor" title="{jid} - {title}">'
        f'<span class="sr-only field-label">Title</span><h3 >\n{title}</h3></a></div>'
        '<div class="col-xs-12 description">Overview text that mentions US-NY-Elsewhere.</div>'
        f'<div class="col-xs-12 additionalFields"><dl class="iCIMS_JobHeaderGroup">{dl}</dl></div></div></li>'
    )


def _page(cards: str = "", page: int = 1, pages: int = 1) -> str:
    paging = f'<h2 class="iCIMS_SubHeader">Search Results\nPage {page} of {pages} \n</h2>' if cards else ""
    return (
        "<html><head><script>$('.iCIMS_JobsTable').find('.iCIMS_JobListingRow');</script></head><body>"
        f'{paging}<ul class="container-fluid iCIMS_JobsTable">{cards}</ul></body></html>'
    )


def _detail(date: str = "2026-10-13T04:00:00.000Z", addresses=(("Dublin", "OH", "US"),),
            employment: object = "FULL_TIME", description: str = "<h2>Overview</h2><p>Build</p>") -> str:
    posting = {
        "@context": "http://schema.org", "@type": "JobPosting", "title": "x", "datePosted": date,
        "employmentType": employment, "description": description,
        "jobLocation": [{"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": city,
                                                       "addressRegion": region, "addressCountry": country,
                                                       "streetAddress": "UNAVAILABLE"}}
                        for city, region, country in addresses],
    }
    return (f'<html><head><script type="application/ld+json">{json.dumps(posting)}</script></head>'
            '<body>job</body></html>')


def _response(status: int, text: str = "") -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.ok = 200 <= status < 300
    response.text = text
    response.json.side_effect = ValueError("not json")
    return response


class _Portal:
    """Search pages keyed by ``pr``; job pages keyed by job id."""

    def __init__(self, pages: dict[int, str | MagicMock], details: dict[str, str | MagicMock] | None = None):
        self.pages, self.details, self.calls = pages, details or {}, []

    def get(self, url, **_kwargs):
        self.calls.append(url)
        parsed = urlparse(url)
        if parsed.path == "/jobs/search":
            page = self.pages.get(int(parse_qs(parsed.query)["pr"][0]), _page())
            return page if isinstance(page, MagicMock) else _response(200, page)
        detail = self.details.get(parsed.path.split("/")[2], _detail())
        return detail if isinstance(detail, MagicMock) else _response(200, detail)

    @property
    def detail_calls(self) -> list[str]:
        return [c for c in self.calls if "/jobs/search" not in c]


def _fetch(portal: _Portal, url: str = BASE, filtering=FILTERING, max_jobs: int = 1000, max_details: int = 100):
    with (
        patch("ngj.http.limited_get", side_effect=portal.get),
        patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
    ):
        return fetch_icims_portal_jobs("RoviSys", url, filtering=filtering, max_jobs=max_jobs,
                                       max_details=max_details, timeout=5, now=NOW)


class TestPortalBase:
    @pytest.mark.parametrize("url, expected", [
        (BASE, BASE),
        (f"{BASE}/", BASE),
        ("https://Careers-NYU.icims.com", "https://careers-nyu.icims.com"),
        ("http://careers-rovisys.icims.com", None),
        (f"{BASE}/jobs/search", None),
        ("https://internal-nyu.icims.com", None),  # employee-only portals
        ("https://internalcareers-aus.icims.com", None),
        ("https://login.icims.com", None),
        ("https://careers.amd.com", None),
        ("https://a.b.icims.com", None),
        ("", None),
    ])
    def test_only_a_public_portal_root_is_accepted(self, url, expected):
        assert portal_base(url) == expected


class TestPortalLocation:
    @pytest.mark.parametrize("raw, expected", [
        ("US-OH-Dublin", "Dublin, OH, United States"),
        ("CA-ON-TORONTO", "TORONTO, ON, Canada"),
        ("IN-KA-Bengaluru", "Bengaluru, KA, India"),
        ("US-Remote", "Remote, United States"),
        ("US-Reston", "Reston, United States"),
        ("US", "United States"),
        ("US-NC-Winston-Salem", "Winston-Salem, NC, United States"),
        ("US-Winston-Salem", "Winston-Salem, United States"),
        ("VA-Arlington", "Arlington, VA"),  # a portal that leaves the country out
        ("MX-Mexico City", "Mexico City, MX"),
        ("IE-Dublin", "Dublin, IE"),
        ("DE-BY-Munich", "Munich, Germany"),
        ("Dahlgren, VA, USA", "Dahlgren, VA, USA"),
        ("Europe-Remote", "Europe-Remote"),
        ("US-IL-Bolingbrook | US-IN-Hobart", "Bolingbrook, IL, United States; Hobart, IN, United States"),
        ("US-VA-Richmond\xa0 | US-VA-Richmond", "Richmond, VA, United States"),
        ("", ""),
    ])
    def test_country_state_city_reads_as_city_state_country(self, raw, expected):
        assert portal_location(raw) == expected


class TestParseSearchPage:
    def test_cards_give_id_title_link_location_and_pages(self):
        html = _page(_card(2187, "Entry Level Engineer") + _card(2180, "Systems Engineer", "US-OH-Aurora"), 1, 2)
        rows, pages = parse_search_page(html, BASE)
        assert pages == 2
        assert rows == [
            {"id": "2187", "url": f"{BASE}/jobs/2187/job", "title": "Entry Level Engineer",
             "location": "Dublin, OH, United States", "date": "", "part_time": False},
            {"id": "2180", "url": f"{BASE}/jobs/2180/job", "title": "Systems Engineer",
             "location": "Aurora, OH, United States", "date": "", "part_time": False},
        ]

    def test_a_location_field_and_a_posted_date_are_read(self):
        card = _card(12139, "Data Analyst", "US-NY-New York", date="10/14/2026 5:23 PM", location_in_list=True,
                     fields={"Department": "Dentistry"})
        (row,), _ = parse_search_page(_page(card), BASE)
        assert (row["location"], row["date"]) == ("New York, NY, United States", "2026-10-14")

    def test_labels_match_whole_words_only(self):
        card = _card(1, "Analyst", None, fields={"Candidate Type": "External", "Relocation Assistance": "Yes",
                                                 "Job Location": "US-TX-Austin", "Posted Date": "10/14/2026"})
        (row,), _ = parse_search_page(_page(card), BASE)
        assert (row["location"], row["date"]) == ("Austin, TX, United States", "2026-10-14")

    @pytest.mark.parametrize("raw", ["14/10/2026", "02/30/2026", "00/10/2026"])
    def test_impossible_list_dates_are_unknown(self, raw):
        (row,), _ = parse_search_page(_page(_card(1, "Analyst", fields={"Date Posted": raw})), BASE)
        assert row["date"] == ""

    def test_part_time_is_read_from_the_position_type_only(self):
        card = _card(1, "Analyst", fields={"Department": "Part-Time Student Services", "Position Type": "Full-Time"})
        (row,), _ = parse_search_page(_page(card), BASE)
        assert row["part_time"] is False

    def test_a_link_to_an_employee_only_portal_is_dropped(self):
        rows, _ = parse_search_page(_page(_card(1, "Analyst", host="https://internal-rovisys.icims.com")
                                          + _card(2, "Engineer")), BASE)
        assert [r["id"] for r in rows] == ["2"]

    def test_free_text_locations_are_kept(self):
        (row,), _ = parse_search_page(_page(_card(1, "Analyst", "Dahlgren, VA, USA", location_in_list=True)), BASE)
        assert row["location"] == "Dahlgren, VA, USA"

    @pytest.mark.parametrize("value, part_time", [
        ("Part Time", True), ("Regular Part-Time", True), ("Part-time", True),
        ("Regular Full-Time", False), ("Contingent (Full-Time, Part-Time, or On-Call)", False), ("Co-op", False),
    ])
    def test_part_time_position_types_are_flagged(self, value, part_time):
        (row,), _ = parse_search_page(_page(_card(1, "Analyst", fields={"Position Type": value})), BASE)
        assert row["part_time"] is part_time

    def test_links_on_a_sibling_portal_of_the_same_employer_are_kept(self):
        base = "https://careers-nyu.icims.com"
        card = _card(12139, "Analyst", host="https://uscareers-nyu.icims.com")
        (row,), _ = parse_search_page(_page(card), base)
        assert row["url"] == "https://uscareers-nyu.icims.com/jobs/12139/job"

    @pytest.mark.parametrize("host", [
        "https://careers-evil.icims.com", "https://evil.com", "http://careers-rovisys.icims.com",
        "https://careers-rovisys.icims.com.evil.com", "//careers-rovisys.icims.com",
    ])
    def test_links_that_leave_the_employer_are_dropped(self, host):
        rows, _ = parse_search_page(_page(_card(1, "Analyst", host=host) + _card(2, "Engineer")), BASE)
        assert [r["id"] for r in rows] == ["2"]

    def test_a_page_past_the_end_is_an_empty_list(self):
        assert parse_search_page(_page(), BASE) == ([], 0)

    @pytest.mark.parametrize("html", [
        "<script>window.top.location.href = 'https:\\/\\/careers.amd.com\\/jobs';</script>", "", None, 3])
    def test_a_page_without_the_portal_markup_is_none(self, html):
        assert parse_search_page(html, BASE) is None


class TestParseDetail:
    def test_date_locations_type_and_description(self):
        detail = parse_detail(_detail(addresses=(("Dublin", "OH", "US"), ("Toronto", "ON", "CA"))))
        assert detail == {"date": "2026-10-13T04:00:00.000Z",
                          "location": "Dublin, OH, United States; Toronto, ON, Canada",
                          "description_html": "<h2>Overview</h2><p>Build</p>", "part_time": False}

    @pytest.mark.parametrize("employment, part_time", [
        ("PART_TIME", True), (["PART_TIME"], True), (["FULL_TIME", "PART_TIME"], False), ("OTHER", False), (None, False),
    ])
    def test_only_a_part_time_only_posting_is_part_time(self, employment, part_time):
        assert parse_detail(_detail(employment=employment))["part_time"] is part_time

    @pytest.mark.parametrize("date, expected", [
        ("2026-10-13T04:00:00.000Z", "2026-10-13T04:00:00.000Z"),  # local midnight: a real date
        ("2026-10-13T18:30:00.000Z", "2026-10-13T18:30:00.000Z"),  # midnight in India
        ("2026-10-13", "2026-10-13"),
        # A portal that hides the date makes one up: the request time two years back.
        ("2024-10-15T14:14:08.651Z", ""),
        ("2024-10-15T14:14:08Z", ""),
        ("2024-10-15T14:14:00.120Z", ""),
        # A real timestamp with seconds is recent, so it is kept.
        ("2026-10-13T17:23:45Z", "2026-10-13T17:23:45Z"),
        ("2026-10-13T17:23:45.120+00:00", "2026-10-13T17:23:45.120+00:00"),
        ("2026-10-13T17:23:45", "2026-10-13T17:23:45"),
        ("2024-13-45T14:14:08.651Z", ""),  # unreadable request time
    ])
    def test_a_made_up_date_is_unknown(self, date, expected):
        assert parse_detail(_detail(date=date), now=NOW)["date"] == expected

    def test_a_foreign_address_is_spelled_out_and_unavailable_parts_are_dropped(self):
        detail = parse_detail(_detail(addresses=(("Munich", "UNAVAILABLE", "DE"),)))
        assert detail["location"] == "Munich, Germany"

    @pytest.mark.parametrize("html", [
        "<html>no data</html>",
        '<script type="application/ld+json">{not json</script>',
        '<script type="application/ld+json">{"@type": "Organization", "name": "x"}</script>',
    ])
    def test_a_page_without_a_job_posting_gives_empty_fields(self, html):
        assert parse_detail(html) == {"date": "", "location": "", "description_html": "", "part_time": False}


class TestFetch:
    def test_plausible_titles_get_their_job_page_and_others_keep_the_list_data(self):
        portal = _Portal({0: _page(_card(1, "Entry Level Engineer") + _card(2, "Senior Engineer")
                                   + _card(3, "Junior Analyst", "IE-Dublin"))})
        result = _fetch(portal)
        assert [urlparse(c).path for c in portal.detail_calls] == ["/jobs/1/job"]
        assert parse_qs(urlparse(portal.detail_calls[0]).query) == {"in_iframe": ["1"]}
        first, second, third = result.jobs
        assert first == {
            "company": "RoviSys", "title": "Entry Level Engineer", "location": "Dublin, OH, United States",
            "url": f"{BASE}/jobs/1/job", "posted_at": "2026-10-13T04:00:00.000Z",
            "source": "iCIMS", "description": "", "description_html": "<h2>Overview</h2><p>Build</p>",
        }
        assert (second["posted_at"], "description_html" in second) == ("", False)
        assert third["location"] == "Dublin, IE"
        assert result.raw_count == 3

    def test_the_search_reads_the_portal_inside_its_frame(self):
        portal = _Portal({})
        _fetch(portal)
        query = parse_qs(urlparse(portal.calls[0]).query)
        assert (query["pr"], query["in_iframe"], query["ss"]) == (["0"], ["1"], ["1"])

    def test_pages_are_read_until_the_last_page(self):
        portal = _Portal({0: _page(_card(1, "Senior Engineer"), 1, 3), 1: _page(_card(2, "Senior Analyst"), 2, 3),
                          2: _page(_card(3, "Senior Developer"), 3, 3)})
        assert [j["title"] for j in _fetch(portal).jobs] == ["Senior Engineer", "Senior Analyst", "Senior Developer"]
        assert len(portal.calls) == 3

    def test_a_page_that_adds_nothing_new_ends_paging(self):
        same = _page(_card(1, "Senior Engineer"), 1, 50)
        portal = _Portal({n: same for n in range(50)})
        assert len(_fetch(portal).jobs) == 1 and len(portal.calls) == 2

    def test_the_cap_bounds_postings_and_pages(self):
        portal = _Portal({n: _page(_card(2 * n, "Senior A") + _card(2 * n + 1, "Senior B"), n + 1, 100)
                          for n in range(100)})
        result = _fetch(portal, max_jobs=5)
        assert len(result.jobs) == 5 and len(portal.calls) == 3

    def test_the_job_page_cap_keeps_the_rest_with_list_data(self):
        portal = _Portal({0: _page("".join(_card(i, f"Junior Analyst {i}") for i in range(4)))})
        result = _fetch(portal, max_details=2)
        assert len(portal.detail_calls) == 2 and len(result.jobs) == 4
        assert [bool(j["posted_at"]) for j in result.jobs] == [True, True, False, False]

    def test_part_time_postings_are_skipped_from_the_list_or_the_job_page(self):
        portal = _Portal({0: _page(_card(1, "Junior Analyst", fields={"Position Type": "Part Time"})
                                   + _card(2, "Junior Engineer") + _card(3, "Junior Developer"))},
                         {"2": _detail(employment="PART_TIME")})
        result = _fetch(portal)
        assert [j["title"] for j in result.jobs] == ["Junior Developer"]
        assert [urlparse(c).path.split("/")[2] for c in portal.detail_calls] == ["2", "3"]

    def test_a_listed_date_is_kept_when_the_job_page_has_none(self):
        portal = _Portal({0: _page(_card(1, "Junior Analyst", date="10/14/2026 5:23 PM"))}, {"1": _detail(date="")})
        assert _fetch(portal).jobs[0]["posted_at"] == "2026-10-14"

    def test_the_job_page_location_fills_a_card_without_one(self):
        portal = _Portal({0: _page(_card(1, "Junior Analyst", None))}, {"1": _detail(addresses=(("Austin", "TX", "US"),))})
        assert _fetch(portal).jobs[0]["location"] == "Austin, TX, United States"

    @pytest.mark.parametrize("status", [404, 410])
    def test_a_posting_closed_between_list_and_job_page_is_dropped(self, status):
        portal = _Portal({0: _page(_card(1, "Junior Analyst") + _card(2, "Senior Analyst"))}, {"1": _response(status)})
        assert [j["title"] for j in _fetch(portal).jobs] == ["Senior Analyst"]

    def test_another_job_page_error_keeps_the_posting_with_its_list_data_and_reports_it(self):
        portal = _Portal({0: _page(_card(1, "Junior Analyst") + _card(2, "Junior Engineer"))}, {"1": _response(500)})
        result = _fetch(portal)
        assert [(j["title"], bool(j["posted_at"])) for j in result.jobs] == [
            ("Junior Analyst", False), ("Junior Engineer", True)]
        assert [(e.kind, e.status) for e in result.errors] == [(KIND_HTTP, 500)]

    def test_a_job_page_timeout_returns_no_partial_jobs(self):
        portal = _Portal({0: _page(_card(1, "Junior Analyst") + _card(2, "Junior Engineer"))})

        def get(url, **kwargs):
            if "/jobs/2/" in url:
                raise requests.exceptions.ReadTimeout("slow")
            return portal.get(url, **kwargs)

        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_icims_portal_jobs("RoviSys", BASE, filtering=FILTERING, timeout=5, now=NOW)
        assert result.jobs == () and {e.kind for e in result.errors} <= ngj_http.TRANSIENT_KINDS

    def test_cards_without_one_usable_link_are_a_parse_error(self):
        cards = _card(1, "Analyst", host="https://careers-evil.icims.com") + _card(2, "Engineer", host="https://evil.com")
        result = _fetch(_Portal({0: _page(cards)}))
        assert result.jobs == () and result.errors[0].kind == KIND_PARSE

    def test_without_a_page_count_paging_continues_until_a_page_adds_nothing(self):
        pages = {n: _page(_card(n, f"Senior Analyst {n}")).replace("Page 1 of 1", "") for n in range(3)}
        portal = _Portal(pages)
        assert len(_fetch(portal).jobs) == 3 and len(portal.calls) == 4

    def test_a_page_without_the_portal_markup_is_a_parse_error(self):
        result = _fetch(_Portal({0: "<script>window.top.location.href = 'https://careers.amd.com/jobs';</script>"}))
        assert result.jobs == () and result.errors[0].kind == KIND_PARSE

    def test_a_failing_later_page_keeps_earlier_pages_and_reports_the_error(self):
        portal = _Portal({0: _page(_card(1, "Senior Engineer"), 1, 2), 1: _response(500)})
        result = _fetch(portal)
        assert [j["title"] for j in result.jobs] == ["Senior Engineer"]
        assert [(e.kind, e.status) for e in result.errors] == [(KIND_HTTP, 500)]

    def test_a_timeout_returns_no_partial_jobs(self):
        def get(url, **_kwargs):
            if "/jobs/search" in url and "pr=1" in url:
                raise requests.exceptions.ReadTimeout("slow")
            return _response(200, _page(_card(1, "Senior Engineer"), 1, 2))

        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_icims_portal_jobs("RoviSys", BASE, filtering=FILTERING, timeout=5, now=NOW)
        assert result.jobs == () and {e.kind for e in result.errors} <= ngj_http.TRANSIENT_KINDS

    def test_job_ids_are_distinct_per_posting(self):
        portal = _Portal({0: _page(_card(1, "Senior Engineer") + _card(2, "Senior Engineer"))})
        assert len({compute_job_id(j) for j in _fetch(portal).jobs}) == 2

    def test_unusable_url_is_a_config_error_without_a_request(self):
        portal = _Portal({})
        result = _fetch(portal, url="https://internal-rovisys.icims.com")
        assert portal.calls == [] and result.errors[0].kind == KIND_CONFIG

    @pytest.mark.parametrize("filtering", [None, {}, {"new_grad_signals": ["junior"]}])
    def test_missing_filter_signals_fail_closed_without_a_request(self, filtering):
        portal = _Portal({})
        result = _fetch(portal, filtering=filtering)
        assert portal.calls == [] and result.errors[0].kind == KIND_CONFIG

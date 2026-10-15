#!/usr/bin/env python3
"""SAP SuccessFactors Career Site Builder adapter: search pages, detail pass, locations, errors."""

import os
import sys
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from contracts import compute_job_id  # noqa: E402
from ngj import http as ngj_http  # noqa: E402
from ngj.locations import is_valid_location  # noqa: E402
from ngj.models import KIND_CONFIG, KIND_HTTP, KIND_PARSE  # noqa: E402
from ngj.sources.successfactors import (  # noqa: E402
    fetch_all_successfactors_jobs,
    fetch_successfactors_jobs,
    normalize_location,
    parse_detail,
    parse_search_page,
    site_base,
)
from source_cooldown import SourceCooldownTracker  # noqa: E402

BASE = "https://careers.duke.edu"
FILTERING = {
    "new_grad_signals": ["junior", "new grad", "associate", "I"],
    "track_signals": ["engineer", "developer", "analyst"],
    "exclusion_signals": ["senior", "manager"],
    "level_signals": ["I", "II"],
}


def _row(jid: int, title: str, location: str = "Durham, NC, US, 27710", date: str = "Oct 14, 2026") -> str:
    href = f"/job/Durham-{title.replace(' ', '-')}/{jid}/"
    return (
        '<tr class="data-row"><td class="colTitle" headers="hdrTitle">'
        f'<span class="jobTitle hidden-phone"><a href="{href}" class="jobTitle-link">{title}</a></span>'
        '<div class="jobdetail-phone visible-phone">'
        f'<span class="jobTitle visible-phone"><a class="jobTitle-link" href="{href}">{title}</a></span>'
        f'<span class="jobLocation visible-phone"><span class="jobLocation">\n  {location}\n  </span></span>'
        '<span class="jobDate visible-phone">\t</span></div></td>'
        f'<td class="colLocation hidden-phone"><span class="jobLocation">{location}</span></td>'
        f'<td class="colDate hidden-phone" nowrap="nowrap"><span class="jobDate">{date}\n</span></td></tr>'
    )


def _tile(jid: int, title: str, **fields: str) -> str:
    href = f"/job/Schweinfurt-{title.replace(' ', '-')}/{jid}/"
    cells = "".join(
        f'<div id="job-{jid}-desktop-section-{name}" class="section-field {name}">'
        f'<span class="section-label sr-only">{name}</span>'
        f'<div id="job-{jid}-desktop-section-{name}-value">{value}\n</div></div>'
        for name, value in fields.items()
    )
    return (
        f'<li class="job-tile job-id-{jid}" data-url="{href}" data-row-index="1"><div class="job-tile-cell">'
        f'<div class="tiletitle"><span class="section-title title">'
        f'<a class="jobTitle-link fontcolorb6a533a1" href="{href}">\n {title}\n </a></span></div>{cells}'
        # The tablet copy of the tile repeats every field.
        f'<a class="jobTitle-link" href="{href}">{title}</a>{cells}</div></li>'
    )


def _page(rows: str = "", tiles: str = "") -> str:
    body = f'<table id="searchresults" class="searchResults"><tbody>{rows}</tbody></table>' if rows or not tiles \
        else f'<ul id="job-tile-list">{tiles}</ul>'
    return f'<html><body><div id="search-wrapper">{body}</div><div id="noresults"></div></body></html>'


def _detail(date: str = "Thu Oct 15 00:00:00 UTC 2026", city: str = "Durham", region: str = "NC",
            country: str = "US", description: str = "<p>Build <b>things</b>.</p><span>More</span>") -> str:
    address = "".join(f'<meta itemprop="{key}" content="{value}">' for key, value in
                      (("addressLocality", city), ("addressRegion", region), ("addressCountry", country)) if value)
    return (
        f'<html><head><meta itemprop="datePosted" content="{date}"></head><body>'
        f'<span itemprop="jobLocation" itemscope><span itemprop="address" itemscope>{address}</span></span>'
        f'<span itemprop="description" class="jobdescription">{description}</span><span class="other">x</span>'
        '</body></html>'
    )


def _response(status: int, text: str = "") -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.ok = 200 <= status < 300
    response.text = text
    response.json.side_effect = ValueError("not json")
    return response


class _Site:
    """Search pages keyed by startrow; detail pages keyed by job path."""

    def __init__(self, pages: dict[int, str | MagicMock], details: dict[str, MagicMock | str] | None = None):
        self.pages, self.details, self.calls = pages, details or {}, []

    def get(self, url, **_kwargs):
        self.calls.append(url)
        parsed = urlparse(url)
        if parsed.path == "/search/":
            start = int(parse_qs(parsed.query)["startrow"][0])
            page = self.pages.get(start, _page())
            return page if isinstance(page, MagicMock) else _response(200, page)
        detail = self.details.get(parsed.path, _detail())
        return detail if isinstance(detail, MagicMock) else _response(200, detail)

    @property
    def detail_calls(self) -> list[str]:
        return [c for c in self.calls if "/job/" in c]


def _fetch(site: _Site, url: str = BASE, filtering=FILTERING, max_jobs: int = 1000, max_details: int = 100):
    with (
        patch("ngj.http.limited_get", side_effect=site.get),
        patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
    ):
        return fetch_successfactors_jobs("Duke University", url, filtering=filtering, max_jobs=max_jobs,
                                         max_details=max_details, timeout=5)


class TestSiteBase:
    @pytest.mark.parametrize("url, expected", [
        (BASE, BASE),
        (f"{BASE}/", BASE),
        ("https://JOBS.Example.com", "https://jobs.example.com"),
        ("http://careers.duke.edu", None),
        (f"{BASE}/search/?q=", None),
        ("https://localhost", None),
        ("", None),
    ])
    def test_only_a_bare_https_site_root_is_accepted(self, url, expected):
        assert site_base(url) == expected


class TestNormalizeLocation:
    @pytest.mark.parametrize("raw, expected", [
        ("Durham, NC, US, 27710", "Durham, NC, United States"),
        ("Chattanooga, US", "Chattanooga, United States"),
        ("Toronto, ON, CA", "Toronto, ON, Canada"),
        ("PB, IN, 160059", "PB, India"),
        ("San Juan, PR, US", "San Juan, PR, United States"),
        ("Schweinfurt, BY, DE, 97421", "Schweinfurt, Germany"),
        ("Casablanca, 06, MA, 20000", "Casablanca, Morocco"),
        ("Perth, WA, AU, 6000", "Perth, AU"),
        ("Tokyo, JP", "Tokyo, JP"),
        ("Lexington, MA", "Lexington, MA"),
        # A US-state-looking code is a country only with a short region before it or a non-US
        # postcode after it; otherwise it is the state ("City, County, ST").
        ("Carmel, Hamilton County, IN", "Carmel, Hamilton County, IN"),
        ("Boston, MA, 02110", "Boston, MA"),
        ("Beaumont, Texas, United States", "Beaumont, Texas, United States"),
        ("  Webster or Remote, MA, US ", "Webster or Remote, MA, United States"),
        ("", ""),
    ])
    def test_the_trailing_country_code_becomes_a_country(self, raw, expected):
        assert normalize_location(raw) == expected

    @pytest.mark.parametrize("raw", ["Schweinfurt, BY, DE, 97421", "Casablanca, 06, MA, 20000",
                                     "Perth, WA, AU, 6000", "Panama City, 8, PA"])
    def test_foreign_codes_that_look_like_us_states_are_not_in_scope(self, raw):
        assert is_valid_location(raw) is True  # the bug this module exists to avoid
        assert is_valid_location(normalize_location(raw)) is False

    @pytest.mark.parametrize("raw", ["Durham, NC, US, 27710", "Toronto, ON, CA", "PB, IN, 160059", "Lexington, MA"])
    def test_target_locations_stay_in_scope(self, raw):
        assert is_valid_location(normalize_location(raw)) is True

    @pytest.mark.parametrize("raw, expected", [
        ("Göppingen, Bade, DE", "Göppingen, Germany"),
        ("Rabat, MA", "Rabat, Morocco"),
        ("Lexington, MA, US", "Lexington, MA, United States"),
        ("Toronto, ON, CA", "Toronto, ON, Canada"),
    ])
    def test_on_a_site_that_writes_country_codes_the_last_code_is_always_the_country(self, raw, expected):
        assert normalize_location(raw, codes_are_countries=True) == expected


class TestParseSearchPage:
    def test_table_rows(self):
        rows = parse_search_page(_page(_row(11, "Associate Software Engineer") + _row(12, "Data Analyst I",
                                                                                     "Toronto, ON, CA", "")))
        assert rows == [
            {"id": "11", "path": "/job/Durham-Associate-Software-Engineer/11/", "title": "Associate Software Engineer",
             "location": "Durham, NC, US, 27710", "date": "Oct 14, 2026"},
            {"id": "12", "path": "/job/Durham-Data-Analyst-I/12/", "title": "Data Analyst I",
             "location": "Toronto, ON, CA", "date": ""},
        ]

    def test_tiles_join_city_state_and_country_or_use_a_location_field(self):
        tiles = (_tile(21, "Junior Developer", city="Fort Mill", state="SC", country="US", date="Oct 15, 2026")
                 + _tile(22, "Rechtsreferendar", city="Schweinfurt", customfield2="Legal")
                 + _tile(23, "Analyst I", location="Pune, MH, IN"))
        rows = parse_search_page(_page(tiles=tiles))
        assert [(r["id"], r["title"], r["location"], r["date"]) for r in rows] == [
            ("21", "Junior Developer", "Fort Mill, SC, US", "Oct 15, 2026"),
            ("22", "Rechtsreferendar", "Schweinfurt", ""),
            ("23", "Analyst I", "Pune, MH, IN", ""),
        ]

    def test_a_page_past_the_end_is_an_empty_list(self):
        assert parse_search_page(_page()) == []

    @pytest.mark.parametrize("html", ["", "<html><body>Content Error</body></html>", None, 42,
                                      '<form action="/search-jobs"></form>'])
    def test_a_page_without_the_search_markup_is_none(self, html):
        assert parse_search_page(html) is None

    def test_rows_without_a_job_link_are_skipped(self):
        assert parse_search_page(_page('<tr class="data-row"><td>no link</td></tr>')) == []


class TestParseDetail:
    def test_date_location_and_description(self):
        assert parse_detail(_detail()) == {
            "date": "Thu Oct 15 00:00:00 UTC 2026",
            "location": "Durham, NC, United States",
            "description_html": "<p>Build <b>things</b>.</p><span>More</span>",
        }

    def test_missing_fields_are_empty(self):
        assert parse_detail("<html></html>") == {"date": "", "location": "", "description_html": ""}

    def test_a_foreign_address_is_out_of_scope(self):
        assert parse_detail(_detail(city="Munich", region="BY", country="DE"))["location"] == "Munich, Germany"


class TestFetch:
    def test_plausible_titles_get_their_detail_and_others_keep_the_list_data(self):
        site = _Site({0: _page(_row(1, "Associate Software Engineer", date="")
                               + _row(2, "Senior Manager", date="Oct 01, 2026")
                               + _row(3, "Junior Developer", "Munich, BY, DE, 80331", ""))})
        result = _fetch(site)
        jobs = {j["title"]: j for j in result.jobs}
        assert jobs["Associate Software Engineer"] == {
            "company": "Duke University", "title": "Associate Software Engineer",
            "location": "Durham, NC, United States", "url": f"{BASE}/job/Durham-Associate-Software-Engineer/1/",
            "posted_at": "Thu Oct 15 00:00:00 UTC 2026", "source": "SuccessFactors", "description": "",
            "description_html": "<p>Build <b>things</b>.</p><span>More</span>",
        }
        assert jobs["Senior Manager"]["posted_at"] == "Oct 01, 2026" and "description_html" not in jobs["Senior Manager"]
        assert jobs["Junior Developer"]["location"] == "Munich, Germany" and jobs["Junior Developer"]["posted_at"] == ""
        assert site.detail_calls == [f"{BASE}/job/Durham-Associate-Software-Engineer/1/"]
        assert result.errors == () and result.raw_count == 3

    def test_the_search_is_newest_first_and_english(self):
        site = _Site({0: _page(_row(1, "Data Analyst I"))})
        _fetch(site)
        query = parse_qs(urlparse(site.calls[0]).query)
        assert query["sortColumn"] == ["referencedate"] and query["sortDirection"] == ["desc"]
        assert query["locale"] == ["en_US"] and query["startrow"] == ["0"]

    def test_a_site_that_writes_country_codes_reads_every_trailing_code_as_a_country(self):
        site = _Site({0: _page(_row(1, "Senior A", "Traverse City, MI, US") + _row(2, "Senior B", "Rabat, MA")
                               + _row(3, "Senior C", "Göppingen, Bade, DE"))})
        assert [j["location"] for j in _fetch(site).jobs] == [
            "Traverse City, MI, United States", "Rabat, Morocco", "Göppingen, Germany"]

    def test_a_site_without_country_codes_keeps_state_codes(self):
        site = _Site({0: _page(_row(1, "Senior A", "Lexington, MA") + _row(2, "Senior B", "Ottawa, ON"))})
        assert [j["location"] for j in _fetch(site).jobs] == ["Lexington, MA", "Ottawa, ON"]

    def test_a_detail_without_a_date_keeps_the_list_date(self):
        site = _Site({0: _page(_row(1, "Data Analyst I", date="Oct 14, 2026"))},
                     {"/job/Durham-Data-Analyst-I/1/": _detail(date="", city="", region="", country="")})
        job = _fetch(site).jobs[0]
        assert job["posted_at"] == "Oct 14, 2026" and job["location"] == "Durham, NC, United States"

    def test_pages_advance_by_the_rows_returned_until_a_page_adds_nothing(self):
        site = _Site({0: _page(_row(1, "Senior A") + _row(2, "Senior B")),
                      2: _page(_row(2, "Senior B") + _row(3, "Senior C")),
                      4: _page(_row(3, "Senior C"))})
        result = _fetch(site)
        assert [j["title"] for j in result.jobs] == ["Senior A", "Senior B", "Senior C"]
        assert [parse_qs(urlparse(c).query)["startrow"][0] for c in site.calls] == ["0", "2", "4"]

    def test_the_cap_bounds_postings_and_pages(self):
        site = _Site({i: _page("".join(_row(i + k, f"Senior {i + k}") for k in range(2))) for i in range(0, 40, 2)})
        result = _fetch(site, max_jobs=5)
        assert len(result.jobs) == 5 and len(site.calls) == 3

    def test_the_detail_cap_keeps_the_rest_with_list_data(self):
        site = _Site({0: _page("".join(_row(i, f"Associate Engineer {i}") for i in range(1, 5)))})
        result = _fetch(site, max_details=2)
        assert len(site.detail_calls) == 2 and len(result.jobs) == 4
        assert sum(1 for j in result.jobs if "description_html" in j) == 2

    @pytest.mark.parametrize("status", [404, 410])
    def test_a_posting_closed_between_list_and_detail_is_dropped(self, status):
        site = _Site({0: _page(_row(1, "Associate Engineer") + _row(2, "Senior Engineer"))},
                     {"/job/Durham-Associate-Engineer/1/": _response(status)})
        result = _fetch(site)
        assert [j["title"] for j in result.jobs] == ["Senior Engineer"] and result.errors == ()

    def test_any_other_detail_error_fails_the_site_instead_of_shrinking_it(self):
        site = _Site({0: _page(_row(1, "Associate Engineer") + _row(2, "Senior Engineer"))},
                     {"/job/Durham-Associate-Engineer/1/": _response(500)})
        result = _fetch(site)
        assert result.jobs == () and [(e.kind, e.status) for e in result.errors] == [(KIND_HTTP, 500)]

    def test_a_page_without_the_search_markup_is_a_parse_error(self):
        result = _fetch(_Site({0: "<html><body>Content Error</body></html>"}))
        assert result.jobs == () and result.errors[0].kind == KIND_PARSE

    def test_a_failing_later_page_keeps_earlier_pages_and_reports_the_error(self):
        site = _Site({0: _page(_row(1, "Senior A")), 1: "<html>broken</html>"})
        result = _fetch(site)
        assert [j["title"] for j in result.jobs] == ["Senior A"] and result.errors[0].kind == KIND_PARSE

    def test_job_ids_are_distinct_per_posting(self):
        site = _Site({0: _page(_row(1, "Senior A") + _row(2, "Senior A"))})
        assert len({compute_job_id(j) for j in _fetch(site).jobs}) == 2

    def test_unusable_url_is_a_config_error_without_a_request(self):
        site = _Site({})
        result = _fetch(site, url=f"{BASE}/search/")
        assert site.calls == [] and result.errors[0].kind == KIND_CONFIG

    @pytest.mark.parametrize("filtering", [{}, {"new_grad_signals": ["junior"]}, {"track_signals": ["engineer"]}])
    def test_missing_filter_signals_fail_closed_without_a_request(self, filtering):
        site = _Site({})
        result = _fetch(site, filtering=filtering)
        assert site.calls == [] and result.errors[0].kind == KIND_CONFIG and "filtering" in result.errors[0].message


class TestFetchAll:
    def test_every_site_is_fetched_errors_travel_and_timeouts_are_retried(self):
        state = {"timed_out": False}

        def get(url, **_kwargs):
            host = urlparse(url).netloc
            if host == "jobs.broken.com":
                return _response(404)
            if host == "jobs.slow.com" and not state["timed_out"]:
                state["timed_out"] = True
                raise requests.exceptions.ReadTimeout("slow")
            return _response(200, _page(_row(1 if host == "careers.duke.edu" else 2, "Senior Engineer")))

        settings = MagicMock(successfactors_max_workers=2, successfactors_max_jobs_per_company=100,
                             successfactors_max_details_per_company=10, http_timeout=5)
        companies = [{"name": "Duke University", "url": BASE}, {"name": "Slow", "url": "https://jobs.slow.com"},
                     {"name": "Broken", "url": "https://jobs.broken.com"}]
        with (
            patch("ngj.http.limited_get", side_effect=get),
            patch.object(ngj_http, "SOURCE_COOLDOWN", SourceCooldownTracker(threshold=5)),
        ):
            result = fetch_all_successfactors_jobs(companies, settings, filtering=FILTERING)
        assert sorted(j["company"] for j in result.jobs) == ["Duke University", "Slow"]
        assert [(e.company, e.status) for e in result.errors] == [("Broken", 404)]


class TestReviewHardening:
    """Edge cases from review (Oct 2026)."""

    @pytest.mark.parametrize("href", ["@evil.com/job/x/1/", ".evil.com/job/x/1/", "//evil.com/job/x/1/",
                                      "https://evil.com/job/x/1/", "job/x/1/", "/job/x/1/?next=@evil"])
    def test_job_links_that_could_leave_the_site_are_dropped(self, href):
        html = _page(f'<tr class="data-row"><td><a class="jobTitle-link" href="{href}">Analyst I</a></td></tr>')
        assert parse_search_page(html) == []

    def test_a_detail_address_without_a_country_keeps_its_state(self):
        html = '<meta itemprop="addressLocality" content="Boston"><meta itemprop="addressRegion" content="MA">'
        assert parse_detail(html)["location"] == "Boston, MA"

    def test_meta_attributes_in_any_order_quoting_and_entities(self):
        html = ("<meta content='O&#39;Fallon' itemprop='addressLocality'/>"
                '<META CONTENT="MO" ITEMPROP="addressRegion"><meta itemprop="addressCountry" content="US"/>'
                "<meta content='Wed Oct 14 07:00:00 UTC 2026' itemprop='datePosted'>")
        assert parse_detail(html)["location"] == "O'Fallon, MO, United States"
        assert parse_detail(html)["date"] == "Wed Oct 14 07:00:00 UTC 2026"

    def test_paging_advances_by_every_row_returned_even_unparseable_ones(self):
        bad = '<tr class="data-row"><td>no link</td></tr>'
        site = _Site({0: _page(_row(1, "Senior A") + bad), 2: _page(_row(2, "Senior B"))})
        _fetch(site)
        assert [parse_qs(urlparse(c).query)["startrow"][0] for c in site.calls[:2]] == ["0", "2"]

    def test_the_page_bound_follows_the_job_cap(self):
        site = _Site({i: _page("".join(_row(i + k + 1, f"Senior {i + k}") for k in range(10)))
                      for i in range(0, 3000, 10)})
        result = _fetch(site, max_jobs=2500)
        assert len(result.jobs) == 2500 and len(site.calls) == 250

    def test_rows_of_one_posting_merge_their_locations(self):
        site = _Site({0: _page(_row(7, "Senior A", "Munich, BY, DE") + _row(7, "Senior A", "Austin, TX, US"))})
        jobs = _fetch(site).jobs
        assert len(jobs) == 1 and jobs[0]["location"] == "Munich, Germany; Austin, TX, United States"
        assert is_valid_location(jobs[0]["location"]) is True

    def test_fields_outside_a_row_are_not_captured(self):
        html = _page('<tr class="data-row"><td><a class="jobTitle-link" href="/job/x/9/">Analyst I</a></td></tr>'
                     '<div class="footer"><span class="jobLocation">Hamburg, DE</span></div>')
        assert parse_search_page(html)[0]["location"] == ""

    def test_a_failing_later_page_keeps_newer_postings_with_the_error(self):
        site = _Site({0: _page(_row(1, "Senior A")), 1: _response(503)})
        result = _fetch(site)
        assert [j["title"] for j in result.jobs] == ["Senior A"] and result.errors[0].status == 503

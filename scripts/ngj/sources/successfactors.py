"""SAP SuccessFactors Career Site Builder adapter (``https://<careers-site>/search/``).

Career Site Builder sites run on the employer's own domain (``careers.duke.edu``,
``jobs.bostonscientific.com``). There is no keyless JSON API
(``/services/recruiting/v1/jobs`` answers 401), but every site server-renders
the same public search page, newest first with
``sortColumn=referencedate&sortDirection=desc``, ``startrow`` paging and 10-100
rows a page, in one of two layouts:

* table: ``tr.data-row`` with ``a.jobTitle-link``, ``span.jobLocation`` and
  (on most sites) ``span.jobDate``;
* tiles: ``li.job-tile`` with ``a.jobTitle-link`` and ``...-section-<field>-value``
  cells (``location`` or ``city``/``state``/``country``, sometimes ``date``).

Every search page, even one past the end, carries ``id="search-wrapper"``; a
page without it (another product, a block page) is a parse error, so a layout
change shows up in health.json.

Several sites show no date column, and an undated posting never passes the
recency rule. So, as for Rippling, a second pass fetches the job page of each
posting whose title passes :func:`ngj.filters.passes_title_rules` and whose
list location is empty or in the US/Canada/India. Its microdata gives the date
(``itemprop="datePosted"``), a structured address and the description
(``span.jobdescription``). The pass is capped per site; the rest keep their
list data so the Explore corpus stays complete.

List locations read ``City, ST, CC, ZIP`` with an ISO country code, and
several codes are also US state codes (Germany ``DE``, Morocco ``MA``, Panama
``PA``). :func:`normalize_location` spells out ``US``/``CA``/``IN`` and reduces
any other country to ``City, Country``, so the location gate cannot read a
foreign posting as a US state. A site whose locations carry an unambiguous
country code anywhere (``US``, ``JP``) writes codes as countries, so its
trailing codes are always read that way ("Rabat, MA" is Morocco there).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Mapping, Sequence
from html.parser import HTMLParser
from typing import Any

from ngj import http as ngj_http
from ngj.filters import passes_title_rules
from ngj.locations import USA_STATE_CODES, is_valid_location
from ngj.models import KIND_CONFIG, KIND_HTTP, SourceError, SourceResult
from ngj.settings import DEFAULT_HTTP_TIMEOUT, Settings

logger = logging.getLogger(__name__)

SOURCE = "successfactors"
SOURCE_LABEL = "SuccessFactors"
SEARCH_PATH = "/search/?q=&sortColumn=referencedate&sortDirection=desc&locale=en_US&startrow={start}"
# Pages hold at least 10 rows; paging is bounded by the request count this implies.
MIN_PAGE_ROWS = 10
GONE_STATUSES = frozenset({404, 410})

_SITE_RE = re.compile(r"^https://((?:[a-z0-9-]+\.)+[a-z]{2,})/?$")
# A same-site path only ("/job/<slug>/<id>/"): no scheme, "//", userinfo, query or fragment.
_JOB_PATH_RE = re.compile(r"^/(?!/)[^\s@\\?#:]*/(\d+)/?$")
_SEARCH_MARKER_RE = re.compile(r'id="search-wrapper"')
_TILE_FIELD_RE = re.compile(r"-section-([a-z0-9]+)-value$")
_TILE_FIELDS = frozenset({"location", "city", "state", "country", "date"})
_COUNTRY_CODE_RE = re.compile(r"^[A-Z]{2}$")
_US_ZIP_RE = re.compile(r"^\d{5}(?:-\d{4})?$")
_META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_DESCRIPTION_RE = re.compile(r"""<span\b[^>]*class=["'](?:[^"']*\s)?jobdescription(?:\s[^"']*)?["'][^>]*>""",
                             re.IGNORECASE)
_SPAN_TAG_RE = re.compile(r"<(/?)span\b[^>]*?(/?)>", re.IGNORECASE)

TARGET_COUNTRIES = {"US": "United States", "CA": "Canada", "IN": "India"}
# ISO codes that are also US state codes: spelled out so they cannot read as a state.
_FOREIGN_LOOKALIKES = {
    "AL": "Albania", "AR": "Argentina", "AZ": "Azerbaijan", "CO": "Colombia", "DE": "Germany", "GA": "Gabon",
    "ID": "Indonesia", "IL": "Israel", "KY": "Cayman Islands", "LA": "Laos", "MA": "Morocco", "MD": "Moldova",
    "ME": "Montenegro", "MN": "Mongolia", "MO": "Macao", "MS": "Montserrat", "MT": "Malta", "NC": "New Caledonia",
    "NE": "Niger", "PA": "Panama", "SC": "Seychelles", "SD": "Sudan", "TN": "Tunisia", "VA": "Vatican City",
}
_STATE_CODES = frozenset(code.upper() for code in USA_STATE_CODES)
# Canadian province codes appear as the region of "City, ON" on sites without country codes.
_PROVINCE_CODES = frozenset({"ON", "QC", "BC", "AB", "MB", "SK", "NS", "NB", "NL", "PE", "NT", "YT", "NU"})
_SHORT_REGION = 3


def site_base(url: str) -> str | None:
    """``https://<host>`` for a configured careers-site root, else None."""
    match = _SITE_RE.match((url or "").strip().lower())
    return f"https://{match.group(1)}" if match else None


def _split(raw: str) -> tuple[list[str], list[str]]:
    """Comma tokens, and the trailing postcode tokens split off."""
    tokens = [t for t in (part.strip() for part in (raw or "").split(",")) if t]
    trailing: list[str] = []
    while len(tokens) > 1 and any(ch.isdigit() for ch in tokens[-1]):
        trailing.insert(0, tokens.pop())
    return tokens, trailing


def writes_country_codes(raw_locations: Sequence[str]) -> bool:
    """True when any location ends in a code that can only be a country ("US", "JP", "GB")."""
    for raw in raw_locations:
        tokens, _ = _split(raw)
        code = tokens[-1] if len(tokens) >= 2 else ""
        if _COUNTRY_CODE_RE.match(code) and code not in _STATE_CODES and code not in _PROVINCE_CODES:
            return True
    return False


def _is_country_code(tokens: Sequence[str], trailing: Sequence[str], codes_are_countries: bool) -> bool:
    """Whether the last token is a country code rather than a US state code."""
    code = tokens[-1]
    if codes_are_countries or code not in _STATE_CODES:
        return True
    if len(tokens) >= 3 and len(tokens[-2]) <= _SHORT_REGION:  # City, RR, CC
        return True
    return bool(trailing) and not _US_ZIP_RE.match(trailing[0])  # City, CC, <non-US postcode>


def normalize_location(raw: str, *, codes_are_countries: bool = False) -> str:
    """Spell out a trailing ISO country code; any non-target country becomes ``City, Country``.

    ``codes_are_countries`` is for a site known to write country codes (see
    :func:`writes_country_codes`) and for an explicit ``addressCountry``.
    """
    tokens, trailing = _split(raw)
    if (len(tokens) < 2 or not _COUNTRY_CODE_RE.match(tokens[-1])
            or not _is_country_code(tokens, trailing, codes_are_countries)):
        return ", ".join(tokens)
    code = tokens[-1]
    if code in TARGET_COUNTRIES:
        return ", ".join([*tokens[:-1], TARGET_COUNTRIES[code]])
    return f"{tokens[0]}, {_FOREIGN_LOOKALIKES.get(code, code)}"


class _SearchRows(HTMLParser):
    """Collects one record per ``tr.data-row`` / ``li.job-tile`` (first value of each field wins)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict[str, str]] = []
        self._row: dict[str, str] | None = None
        self._field: str | None = None
        self._tag = ""
        self._depth = 0
        self._row_tag = ""
        self._row_depth = 0
        self.raw_rows = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        classes = attr.get("class", "").split()
        if (tag == "tr" and "data-row" in classes) or (tag == "li" and "job-tile" in classes):
            self._row, self._field, self._row_tag, self._row_depth = {}, None, tag, 1
            self.rows.append(self._row)
            return
        if self._row is None:
            return
        self._row_depth += tag == self._row_tag
        if self._field is not None:
            self._depth += tag == self._tag
            return
        field = self._field_for(tag, classes, attr)
        if field and field not in self._row:
            self._field, self._tag, self._depth = field, tag, 1
            if field == "title":
                self._row["path"] = attr.get("href", "")

    def _field_for(self, tag: str, classes: list[str], attr: Mapping[str, str]) -> str | None:
        if tag == "a" and "jobTitle-link" in classes:
            return "title"
        if tag == "span" and "jobLocation" in classes:
            return "location"
        if tag == "span" and "jobDate" in classes:
            return "date"
        match = _TILE_FIELD_RE.search(attr.get("id", "")) if tag == "div" else None
        return match.group(1) if match and match.group(1) in _TILE_FIELDS else None

    def handle_endtag(self, tag: str) -> None:
        if self._field is not None and tag == self._tag:
            self._depth -= 1
            if self._depth == 0:
                self._field = None
        if self._row is not None and tag == self._row_tag:
            self._row_depth -= 1
            if self._row_depth == 0:
                self._row, self._field = None, None

    def handle_data(self, data: str) -> None:
        if self._row is None or self._field is None:
            return
        text = " ".join(data.split())
        if text:
            current = self._row.get(self._field, "")
            self._row[self._field] = f"{current} {text}".strip()


def _row_location(row: Mapping[str, str]) -> str:
    return row.get("location") or ", ".join(row[key] for key in ("city", "state", "country") if row.get(key))


def _parse_search(html: Any) -> tuple[list[dict[str, str]], int] | None:
    """(usable postings, rows on the page), or None when the page is not a search page."""
    if not isinstance(html, str) or not _SEARCH_MARKER_RE.search(html):
        return None
    parser = _SearchRows()
    parser.feed(html)
    rows = []
    for row in parser.rows:
        match = _JOB_PATH_RE.match(row.get("path", "").strip())
        if not match or not row.get("title"):
            continue
        rows.append({"id": match.group(1), "path": row["path"].strip(), "title": row["title"],
                     "location": _row_location(row), "date": row.get("date", "")})
    return rows, len(parser.rows)


def parse_search_page(html: Any) -> list[dict[str, str]] | None:
    """The postings on one search page (raw list locations), or None when it is not a search page.

    A row whose link is not a same-site ``/job/.../<id>/`` path is dropped, so a
    page cannot point a job-page request at another host.
    """
    parsed = _parse_search(html)
    return None if parsed is None else parsed[0]


class _Metas(HTMLParser):
    """First ``content`` per ``itemprop`` of ``<meta>`` tags (any attribute order, entities decoded)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        prop = attr.get("itemprop", "")
        if tag == "meta" and prop and prop not in self.values:
            self.values[prop] = attr.get("content", "").strip()

    handle_startendtag = handle_starttag


def _metas(html: str) -> dict[str, str]:
    parser = _Metas()
    parser.feed("".join(_META_TAG_RE.findall(html)))
    return parser.values


def _description_html(html: str) -> str:
    """Inner HTML of the first ``span.jobdescription`` (nested spans included)."""
    opening = _DESCRIPTION_RE.search(html)
    if not opening:
        return ""
    depth = 1
    for tag in _SPAN_TAG_RE.finditer(html, opening.end()):
        if tag.group(2):  # self-closing <span/>
            continue
        depth += -1 if tag.group(1) else 1
        if depth == 0:
            return html[opening.end():tag.start()].strip()
    return ""


def parse_detail(html: str, *, codes_are_countries: bool = False) -> dict[str, str]:
    """Date, normalized location and description HTML from a job page's microdata.

    An explicit ``addressCountry`` is a country; without one, a trailing region
    code is read as on the site's list (``codes_are_countries``).
    """
    metas = _metas(html)
    parts = [metas.get(k, "") for k in ("addressLocality", "addressRegion", "addressCountry")]
    location = normalize_location(", ".join(p for p in parts if p),
                                  codes_are_countries=bool(parts[2]) or codes_are_countries)
    return {"date": metas.get("datePosted", ""), "location": location, "description_html": _description_html(html)}


def _to_job(company_name: str, base: str, row: Mapping[str, str], detail: Mapping[str, str] | None) -> dict[str, Any]:
    job: dict[str, Any] = {
        "company": company_name,
        "title": row["title"],
        "location": row["location"],
        "url": f"{base}{row['path']}",
        "posted_at": row["date"],
        "source": SOURCE_LABEL,
        "description": "",
    }
    if detail is None:
        return job
    # Raw only, as for Ashby: cleaned text and flags come from ngj.enrich.
    return {**job, "location": detail["location"] or job["location"], "posted_at": detail["date"] or job["posted_at"],
            "description_html": detail["description_html"]}


def _page_parser(data: Any) -> SourceResult | None:
    parsed = _parse_search(data)
    # Raw rows travel in ``jobs`` here only; they are mapped below. ``raw_count``
    # counts every row on the page, so ``startrow`` advances past unusable ones too.
    return None if parsed is None else SourceResult(jobs=tuple(parsed[0]), raw_count=parsed[1])


def _detail_parser(codes_are_countries: bool) -> Callable[[Any], SourceResult | None]:
    def parse(data: Any) -> SourceResult | None:
        if not isinstance(data, str):
            return None
        return SourceResult(jobs=(parse_detail(data, codes_are_countries=codes_are_countries),), raw_count=1)

    return parse


def _list_site(company_name: str, base: str, max_jobs: int, timeout: int) -> SourceResult:
    """Unique postings, newest first, up to ``max_jobs``; a page adding nothing new ends paging.

    A posting listed once per location (same id) is one posting with every raw
    location kept in ``locations``. A non-transient error on a later page keeps
    the newer postings already read, with the error; a transient one is
    handled by the caller.
    """
    postings: dict[str, dict[str, Any]] = {}
    start = 0
    for _ in range(-(-max_jobs // MIN_PAGE_ROWS) + 2):
        page = ngj_http.fetch_json_with_retry(
            company_name, SOURCE, SOURCE_LABEL, base + SEARCH_PATH.format(start=start), _page_parser,
            timeout=timeout, as_text=True)
        if page.errors:
            return SourceResult(jobs=tuple(postings.values()), errors=page.errors, raw_count=len(postings))
        fresh = 0
        for row in page.jobs:
            known = postings.get(row["id"])
            if known is None:
                if len(postings) < max_jobs:
                    postings[row["id"]] = {**row, "locations": [row["location"]]}
                    fresh += 1
            elif row["location"] not in known["locations"]:
                postings[row["id"]] = {**known, "locations": [*known["locations"], row["location"]]}
        if not fresh or len(postings) >= max_jobs or not page.raw_count:
            break
        start += page.raw_count
    return SourceResult(jobs=tuple(postings.values()), raw_count=len(postings))


def _joined_location(raw_locations: Sequence[str], codes_are_countries: bool) -> str:
    places = [normalize_location(raw, codes_are_countries=codes_are_countries) for raw in raw_locations]
    return "; ".join(dict.fromkeys(p for p in places if p))


def _wants_detail(row: Mapping[str, str], rules: Mapping[str, Any]) -> bool:
    return passes_title_rules(row["title"], dict(rules)) and (not row["location"] or is_valid_location(row["location"]))


def fetch_successfactors_jobs(
    company_name: str,
    url: str,
    *,
    filtering: Mapping[str, Any] | None = None,
    max_jobs: int = 1000,
    max_details: int = 100,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> SourceResult:
    """Fetch one careers site: the search pages, then job pages for postings that can pass.

    ``filtering`` must carry ``new_grad_signals`` and ``track_signals``, or the
    site fails closed with a config error (they choose the job-page requests).
    A posting whose page is gone (404/410) is dropped; any other job-page error,
    and a timeout or network error anywhere, returns no jobs, so the site is
    reported as failed rather than published short.
    """
    base = site_base(url)
    if base is None:
        message = f"not a SuccessFactors careers-site root (https://<host>): {url}"
        return SourceResult(errors=(SourceError(company_name, SOURCE, KIND_CONFIG, None, message),))
    rules = dict(filtering or {})
    if not (rules.get("new_grad_signals") and rules.get("track_signals")):
        message = "filtering.new_grad_signals and filtering.track_signals are required to pick job-page requests"
        return SourceResult(errors=(SourceError(company_name, SOURCE, KIND_CONFIG, None, message),))

    listing = _list_site(company_name, base, max_jobs, timeout)
    if any(e.kind in ngj_http.TRANSIENT_KINDS for e in listing.errors):
        return SourceResult(errors=listing.errors)
    countries = writes_country_codes([raw for row in listing.jobs for raw in row["locations"]])
    rows = [{**row, "location": _joined_location(row["locations"], countries)} for row in listing.jobs]
    parse_job_page = _detail_parser(countries)
    jobs: list[dict[str, Any]] = []
    details_left = max_details
    skipped = 0
    for row in rows:
        wanted = _wants_detail(row, rules)
        if details_left <= 0 or not wanted:
            skipped += wanted
            jobs.append(_to_job(company_name, base, row, None))
            continue
        details_left -= 1
        detail = ngj_http.fetch_json_with_retry(
            company_name, SOURCE, SOURCE_LABEL, base + row["path"], parse_job_page, timeout=timeout, as_text=True)
        if detail.errors:
            if all(e.kind == KIND_HTTP and e.status in GONE_STATUSES for e in detail.errors):
                continue
            return SourceResult(errors=(*listing.errors, *detail.errors))
        jobs.append(_to_job(company_name, base, row, detail.jobs[0]))
    if skipped:
        logger.warning("  ⚠️  %s: job-page cap (%s) reached; %s plausible postings keep their list data",
                       company_name, max_details, skipped)
    return SourceResult(jobs=tuple(jobs), errors=listing.errors, raw_count=len(rows))


def fetch_all_successfactors_jobs(
    companies: Sequence[dict[str, Any]],
    settings: Settings,
    *,
    filtering: Mapping[str, Any] | None = None,
) -> SourceResult:
    """Fetch every configured careers site, a few at a time (each site is its own host)."""

    def fetch(company: dict[str, Any], timeout: int) -> SourceResult:
        return fetch_successfactors_jobs(
            company["name"], company["url"], filtering=filtering,
            max_jobs=settings.successfactors_max_jobs_per_company,
            max_details=settings.successfactors_max_details_per_company, timeout=timeout)

    describe: Callable[[dict[str, Any]], str] = lambda c: c.get("name", "<unknown>")  # noqa: E731
    first_pass = ngj_http.fan_out(
        list(companies),
        lambda c: fetch(c, settings.http_timeout),
        max_workers=min(settings.successfactors_max_workers, max(1, len(companies))),
        source=SOURCE,
        describe=describe,
        label=SOURCE_LABEL,
    )
    return ngj_http.retry_transient_failures(
        list(companies), first_pass, lambda c: fetch(c, settings.http_timeout * 2), describe=describe)

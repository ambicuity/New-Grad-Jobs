"""Classic iCIMS portal adapter (``https://careers-<company>.icims.com``).

Employers without an iCIMS career site on their own domain publish a portal
on ``*.icims.com``. Its search page, read inside its frame
(``/jobs/search?ss=1&in_iframe=1&pr=<page>``, 0-based), server-renders 10-50
``li.iCIMS_JobCardItem`` cards a page, newest first, and says ``Page 1 of N``.
Each card links to ``/jobs/<id>/<slug>/job``. Every employer configures its
own card fields, so a field is found by its label: the first label naming a
location gives the location (``US-OH-Dublin``: country, state, city; several
are joined by ``|``), and a label naming a date gives the posted date from
the span's ``title`` (``10/14/2026 5:23 PM``). Many portals show no date.

An undated posting never passes the recency rule, so, as for SuccessFactors,
a second pass fetches the job page of each posting whose title passes
:func:`ngj.filters.passes_title_rules` and whose location is empty or in the
US/Canada/India. Its JSON-LD ``JobPosting`` gives ``datePosted``, the
addresses, ``employmentType`` and the description. The pass is capped per
portal; the rest keep their list data so the Explore corpus stays complete.

Part-time postings (owner rule, #390) are skipped: a card whose field reads
part-time but not full-time, and a job page whose only employment type is
``PART_TIME``.

A portal that hides its posted dates still writes a ``datePosted``: the
request time two years back (``2024-10-15T14:14:08.651Z``). Real dates are a
calendar day at local midnight, so a date with seconds or milliseconds is
read as unknown rather than published as two years old.

Employee-only portals (``internal-<co>``) are rejected, and a
card link must stay on a portal of the same employer (``careers-nyu`` lists
jobs on ``uscareers-nyu``), so a page cannot point a request at another host.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from html.parser import HTMLParser
from typing import Any

from ngj import http as ngj_http
from ngj.filters import passes_title_rules
from ngj.locations import USA_STATE_CODES, is_valid_location
from ngj.models import KIND_CONFIG, KIND_HTTP, SourceError, SourceResult
from ngj.settings import DEFAULT_HTTP_TIMEOUT
from ngj.sources.successfactors import TARGET_COUNTRIES, normalize_location

logger = logging.getLogger(__name__)

SOURCE = "icims"
SOURCE_LABEL = "iCIMS"
SEARCH_PATH = "/jobs/search?ss=1&in_iframe=1&pr={page}"
# The job page outside its frame is a wrapper without the posting data.
DETAIL_QUERY = "?in_iframe=1"
# Pages hold at least 10 cards; paging is bounded by the request count this implies.
MIN_PAGE_CARDS = 10
GONE_STATUSES = frozenset({404, 410})

# "careers-nyu": a prefix, a hyphen and the employer's tenant name; "internal..." portals are for staff.
_PORTAL_RE = re.compile(r"^https://([a-z0-9]+(?:-[a-z0-9]+)+)\.icims\.com/?$")
# The slug is dropped from the published URL (``/jobs/<id>/job`` serves the same page), so an
# edited title keeps its job_id.
_JOB_LINK_RE = re.compile(r"^https://([a-z0-9-]+)\.icims\.com/jobs/(\d+)/[^/?#\s]+/job(?:\?[^#\s]*)?$")
_PORTAL_MARKER = "iCIMS_JobsTable"
_PAGES_RE = re.compile(r"Page\s+\d+\s+of\s+(\d+)")
_LIST_DATE_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
# Card labels are matched as whole words ("Candidate Type" is not a date, "Relocation" not a location).
_LOCATION_LABEL_RE = re.compile(r"\blocations?\b", re.IGNORECASE)
_DATE_LABEL_RE = re.compile(r"\bdate\b", re.IGNORECASE)
_TYPE_LABEL_RE = re.compile(r"\b(?:position|employment|job)\s*type\b|\bft\s*/\s*pt\b|\bschedule\b", re.IGNORECASE)
_PART_TIME_RE = re.compile(r"\bpart[\s-]?time\b", re.IGNORECASE)
_FULL_TIME_RE = re.compile(r"\bfull[\s-]?time\b", re.IGNORECASE)
_LD_JSON_RE = re.compile(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL)
# A real datePosted is a day at local midnight; a made-up one carries the request time
# (seconds, milliseconds) two years back.
_REQUEST_TIME_RE = re.compile(r"T\d{2}:\d{2}:(?!00(?:\.0+)?(?:Z|[+-]|$))\d{2}")
_MADE_UP_DATE_AGE = timedelta(days=365)
_CODE_RE = re.compile(r"^[A-Z]{2}$")
_STATE_CODES = frozenset(code.upper() for code in USA_STATE_CODES)
_SHORT_REGION = 3
_UNAVAILABLE = "UNAVAILABLE"


def _tenant(label: str) -> str:
    return label.split("-", 1)[-1]


def portal_base(url: str) -> str | None:
    """``https://<portal>.icims.com`` for a configured public portal root, else None."""
    match = _PORTAL_RE.match((url or "").strip().lower())
    if not match or "internal" in match.group(1):
        return None
    return f"https://{match.group(1)}.icims.com"


def _one_location(raw: str) -> str:
    """``CC-ST-City`` / ``CC-City`` / ``CC`` as ``City, ST, Country``; anything else as written."""
    text = " ".join(raw.split())
    parts = text.split("-", 2)
    if "," in text or not _CODE_RE.match(parts[0]):
        return text
    code = parts[0]
    if len(parts) == 1:
        return TARGET_COUNTRIES.get(code, code)
    if len(parts) == 3 and len(parts[1]) <= _SHORT_REGION and parts[1].isalpha():
        return normalize_location(f"{parts[2]}, {parts[1]}, {code}", codes_are_countries=True)
    rest = text.split("-", 1)[1]
    if code in _STATE_CODES and code not in TARGET_COUNTRIES:
        return f"{rest}, {code}"  # a portal that writes ST-City, without the country
    return normalize_location(f"{rest}, {code}", codes_are_countries=True)


def portal_location(raw: str) -> str:
    """Every ``|``-separated location, normalized and joined with ``; `` (repeats dropped)."""
    places = (_one_location(part) for part in (raw or "").replace("\xa0", " ").split("|"))
    return "; ".join(dict.fromkeys(p for p in places if p))


class _Cards(HTMLParser):
    """One record per ``li.iCIMS_JobCardItem``: link, title and ``(label, value)`` fields."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cards: list[dict[str, Any]] = []
        self._card: dict[str, Any] | None = None
        self._li_depth = 0
        self._in_anchor = False
        self._capture: str | None = None  # "title", "label", "value", "dt", "dd"
        self._capture_tag = ""
        self._capture_depth = 0
        self._text = ""
        self._text_is_fixed = False  # a span's ``title`` already holds its full value
        self._label = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        classes = attr.get("class", "").split()
        if tag == "li" and "iCIMS_JobCardItem" in classes:
            self._card = {"href": "", "title": "", "fields": []}
            self.cards.append(self._card)
            self._li_depth, self._capture, self._label = 1, None, ""
            return
        if self._card is None:
            return
        self._li_depth += tag == "li"
        if self._capture is not None:
            self._capture_depth += tag == self._capture_tag
            return
        if tag == "a" and "iCIMS_Anchor" in classes:
            self._in_anchor = True
            self._card["href"] = attr.get("href", "")
        elif tag == "h3" and self._in_anchor:
            self._start("title", tag)
        elif tag in ("dt", "dd"):
            self._start(tag, tag)
        elif tag == "span" and not self._in_anchor:
            if "field-label" in classes:
                self._start("label", tag)
            elif self._label:
                self._start("value", tag)
                self._text = attr.get("title", "")
                self._text_is_fixed = bool(self._text)

    def _start(self, kind: str, tag: str) -> None:
        self._capture, self._capture_tag, self._capture_depth = kind, tag, 1
        self._text, self._text_is_fixed = "", False

    def handle_endtag(self, tag: str) -> None:
        if self._card is None:
            return
        if self._capture is not None and tag == self._capture_tag:
            self._capture_depth -= 1
            if self._capture_depth == 0:
                self._finish()
        if tag == "a":
            self._in_anchor = False
        if tag == "li":
            self._li_depth -= 1
            if self._li_depth == 0:
                self._card, self._capture = None, None

    def _finish(self) -> None:
        assert self._card is not None
        kind, text = self._capture, " ".join(self._text.split())
        self._capture = None
        if kind == "title":
            self._card["title"] = text
        elif kind in ("label", "dt"):
            self._label = text
        elif kind in ("value", "dd") and self._label:
            self._card["fields"].append((self._label, text))
            self._label = ""

    def handle_data(self, data: str) -> None:
        if self._capture is not None and not self._text_is_fixed:
            self._text += data


def _field(fields: Sequence[tuple[str, str]], label_re: re.Pattern[str]) -> str:
    return next((value for label, value in fields if label_re.search(label)), "")


def _list_date(raw: str) -> str:
    """``MM/DD/YYYY`` as an ISO day; an impossible date is unknown."""
    match = _LIST_DATE_RE.search(raw)
    if not match:
        return ""
    month, day, year = (int(g) for g in match.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return ""


def _is_part_time(value: str) -> bool:
    return bool(_PART_TIME_RE.search(value)) and not _FULL_TIME_RE.search(value)


def _row(card: Mapping[str, Any], tenant: str) -> dict[str, Any] | None:
    match = _JOB_LINK_RE.match(str(card["href"]).strip())
    host = match.group(1) if match else ""
    if not match or "internal" in host or _tenant(host) != tenant or not card["title"]:
        return None
    fields = card["fields"]
    return {
        "id": match.group(2),
        "url": f"https://{host}.icims.com/jobs/{match.group(2)}/job",
        "title": card["title"],
        "location": portal_location(_field(fields, _LOCATION_LABEL_RE)),
        "date": _list_date(_field(fields, _DATE_LABEL_RE)),
        "part_time": any(_is_part_time(value) for label, value in fields if _TYPE_LABEL_RE.search(label)),
    }


def _parse_search(html: Any, base: str) -> tuple[list[dict[str, Any]], int, int] | None:
    """(usable postings, cards on the page, page count), or None when it is not a portal search page."""
    if not isinstance(html, str) or _PORTAL_MARKER not in html:
        return None
    parser = _Cards()
    parser.feed(html)
    tenant = _tenant(base.removeprefix("https://").split(".", 1)[0])
    rows = [row for row in (_row(card, tenant) for card in parser.cards) if row is not None]
    pages = _PAGES_RE.search(html)
    return rows, len(parser.cards), int(pages.group(1)) if pages else 0


def parse_search_page(html: Any, base: str) -> tuple[list[dict[str, Any]], int] | None:
    """(postings, page count) on one search page, or None when it is not a portal search page."""
    parsed = _parse_search(html, base)
    return None if parsed is None else (parsed[0], parsed[2])


def _job_posting(html: str) -> Mapping[str, Any]:
    for block in _LD_JSON_RE.findall(html):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, Mapping) and item.get("@type") == "JobPosting":
                return item
    return {}


def _address(place: Any) -> str:
    address = place.get("address") if isinstance(place, Mapping) else None
    if not isinstance(address, Mapping):
        return ""
    parts = [str(address.get(key) or "").strip() for key in ("addressLocality", "addressRegion", "addressCountry")]
    return ", ".join(p for p in parts if p and p.upper() != _UNAVAILABLE)


def _posted_date(value: Any, now: datetime) -> str:
    """``datePosted``, or "" when it is a request time more than a year old (made up by the portal)."""
    raw = str(value or "").strip()
    if not _REQUEST_TIME_RE.search(raw):
        return raw
    try:
        posted = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return ""
    posted = posted if posted.tzinfo else posted.replace(tzinfo=UTC)
    return "" if now - posted > _MADE_UP_DATE_AGE else raw


def parse_detail(html: str, *, now: datetime | None = None) -> dict[str, Any]:
    """Date, normalized locations, description HTML and part-time flag from a job page's JSON-LD."""
    posting = _job_posting(html)
    places = posting.get("jobLocation")
    raw = [_address(place) for place in (places if isinstance(places, list) else [places])]
    location = "; ".join(dict.fromkeys(
        normalize_location(r, codes_are_countries=True) for r in raw if r))
    types = posting.get("employmentType")
    types = [types] if isinstance(types, str) else types if isinstance(types, list) else []
    return {
        "date": _posted_date(posting.get("datePosted"), now or datetime.now(UTC)),
        "location": location,
        "description_html": str(posting.get("description") or ""),
        "part_time": bool(types) and all(str(t).upper() == "PART_TIME" for t in types),
    }


def _page_parser(base: str, pages: list[int]) -> Callable[[Any], SourceResult | None]:
    def parse(data: Any) -> SourceResult | None:
        parsed = _parse_search(data, base)
        if parsed is None or (parsed[1] and not parsed[0]):
            return None  # not a search page, or cards none of which could be read: a parse error
        pages.append(parsed[2])
        # Raw rows travel in ``jobs`` here only; they are mapped below.
        return SourceResult(jobs=tuple(parsed[0]), raw_count=parsed[1])

    return parse


def _detail_parser(now: datetime) -> Callable[[Any], SourceResult | None]:
    def parse(data: Any) -> SourceResult | None:
        return SourceResult(jobs=(parse_detail(data, now=now),), raw_count=1) if isinstance(data, str) else None

    return parse


def _list_portal(company_name: str, base: str, max_jobs: int, timeout: int) -> SourceResult:
    """Unique postings, newest first, up to ``max_jobs``; the last page or a page adding nothing ends paging.

    A non-transient error on a later page keeps the postings already read,
    with the error; a transient one is handled by the caller.
    """
    postings: dict[str, dict[str, Any]] = {}
    pages: list[int] = []
    parse = _page_parser(base, pages)
    for page_number in range(-(-max_jobs // MIN_PAGE_CARDS) + 2):
        page = ngj_http.fetch_json_with_retry(
            company_name, SOURCE, SOURCE_LABEL, base + SEARCH_PATH.format(page=page_number), parse,
            timeout=timeout, as_text=True)
        if page.errors:
            return SourceResult(jobs=tuple(postings.values()), errors=page.errors, raw_count=len(postings))
        fresh = 0
        for row in page.jobs:
            if row["id"] not in postings and len(postings) < max_jobs:
                postings[row["id"]] = row
                fresh += 1
        page_count = pages[-1] if pages else 0
        # Without a "Page x of N" count, paging goes on until a page adds nothing new.
        if not fresh or len(postings) >= max_jobs or 0 < page_count <= page_number + 1:
            break
    return SourceResult(jobs=tuple(postings.values()), raw_count=len(postings))


def _wants_detail(row: Mapping[str, Any], rules: Mapping[str, Any]) -> bool:
    return passes_title_rules(row["title"], dict(rules)) and (not row["location"] or is_valid_location(row["location"]))


def _to_job(company_name: str, row: Mapping[str, Any], detail: Mapping[str, Any] | None) -> dict[str, Any]:
    job: dict[str, Any] = {
        "company": company_name,
        "title": row["title"],
        "location": row["location"],
        "url": row["url"],
        "posted_at": row["date"],
        "source": SOURCE_LABEL,
        "description": "",
    }
    if detail is None:
        return job
    # Raw only, as for Ashby: cleaned text and flags come from ngj.enrich.
    return {**job, "location": job["location"] or detail["location"], "posted_at": detail["date"] or job["posted_at"],
            "description_html": detail["description_html"]}


def fetch_icims_portal_jobs(
    company_name: str,
    url: str,
    *,
    filtering: Mapping[str, Any] | None = None,
    max_jobs: int = 1000,
    max_details: int = 100,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
    now: datetime | None = None,
) -> SourceResult:
    """Fetch one portal: the search pages, then job pages for postings that can pass.

    ``filtering`` must carry ``new_grad_signals`` and ``track_signals``, or the
    portal fails closed with a config error (they choose the job-page requests).
    A posting whose page is gone (404/410) is dropped. Any other job-page error
    keeps the posting with its list data and is reported. A timeout or network
    error anywhere returns no jobs: ``retry_transient_failures`` keeps first-pass
    jobs, so a partial result would be published twice.
    """
    base = portal_base(url)
    if base is None:
        message = f"not a public iCIMS portal root (https://<prefix>-<company>.icims.com): {url}"
        return SourceResult(errors=(SourceError(company_name, SOURCE, KIND_CONFIG, None, message),))
    rules = dict(filtering or {})
    if not (rules.get("new_grad_signals") and rules.get("track_signals")):
        message = "filtering.new_grad_signals and filtering.track_signals are required to pick job-page requests"
        return SourceResult(errors=(SourceError(company_name, SOURCE, KIND_CONFIG, None, message),))

    listing = _list_portal(company_name, base, max_jobs, timeout)
    if any(e.kind in ngj_http.TRANSIENT_KINDS for e in listing.errors):
        return SourceResult(errors=listing.errors)
    parse_job_page = _detail_parser(now or datetime.now(UTC))
    errors: list[SourceError] = list(listing.errors)
    jobs: list[dict[str, Any]] = []
    details_left = max_details
    skipped = 0
    for row in listing.jobs:
        if row["part_time"]:
            continue
        wanted = _wants_detail(row, rules)
        if details_left <= 0 or not wanted:
            skipped += wanted
            jobs.append(_to_job(company_name, row, None))
            continue
        details_left -= 1
        detail = ngj_http.fetch_json_with_retry(
            company_name, SOURCE, SOURCE_LABEL, row["url"] + DETAIL_QUERY, parse_job_page, timeout=timeout,
            as_text=True)
        if any(e.kind in ngj_http.TRANSIENT_KINDS for e in detail.errors):
            return SourceResult(errors=(*errors, *detail.errors))
        if detail.errors:
            if not all(e.kind == KIND_HTTP and e.status in GONE_STATUSES for e in detail.errors):
                errors = [*errors, *detail.errors]
                jobs.append(_to_job(company_name, row, None))
            continue
        if detail.jobs[0]["part_time"]:
            continue
        jobs.append(_to_job(company_name, row, detail.jobs[0]))
    if skipped:
        logger.warning("  ⚠️  %s: job-page cap (%s) reached; %s plausible postings keep their list data",
                       company_name, max_details, skipped)
    return SourceResult(jobs=tuple(jobs), errors=tuple(errors), raw_count=len(listing.jobs))

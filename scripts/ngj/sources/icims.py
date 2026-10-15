"""iCIMS career-site adapter (the "Jibe" job search at ``https://<careers-site>/api/jobs``).

iCIMS customers that run an iCIMS career site on their own domain
(``careers.amd.com``, ``careers.emory.edu``) expose its public JSON search,
which needs no key: ``/api/jobs?page=N&limit=100&sortBy=posted_date&descending=true``
returns ``{totalCount, jobs: [{data: {...}}]}``. ``country`` takes a country
name, so each site is queried once per target country, as for SmartRecruiters,
newest first and capped per country.

Each posting carries its title, ``full_location``, ``posted_date``,
``employment_type``, ``searchable`` and the description in three HTML fields
(``description``, ``responsibilities``, ``qualifications``). Its public page
is ``https://<site>/jobs/<slug>``. Postings that are not ``searchable`` and
``PART_TIME`` postings (owner rule, #390) are skipped. The ``apply_url``
(the employer's internal iCIMS portal) and the other internal fields are never
copied.

A career site can sit in front of another job system (S&P Global's applies
on Workday): check ``apply_url`` before adding one, so a board already read
from its own source is not published twice. Its ``apply_url`` hosts are the
employer's classic portals, so do not configure those as well.

Classic portals on ``*.icims.com`` have no such API; :func:`fetch_all_icims_jobs`
sends them to :mod:`ngj.sources.icims_portal`, which reads their pages.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any
from urllib.parse import urlencode

from ngj import http as ngj_http
from ngj.models import KIND_CONFIG, SourceError, SourceResult
from ngj.settings import DEFAULT_HTTP_TIMEOUT, Settings
from ngj.sources.icims_portal import fetch_icims_portal_jobs, portal_base

SOURCE = "icims"
SOURCE_LABEL = "iCIMS"
# The career-site API serves at most 100 postings per page.
PAGE_SIZE = 100
SKIPPED_EMPLOYMENT_TYPES = frozenset({"PART_TIME"})

_SITE_RE = re.compile(r"^https://((?:[a-z0-9-]+\.)+[a-z]{2,})/?$")
_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_DESCRIPTION_FIELDS = ("description", "responsibilities", "qualifications")


def site_base(url: str) -> str | None:
    """``https://<host>`` for a configured career-site root (not an ``*.icims.com`` portal), else None."""
    match = _SITE_RE.match((url or "").strip().lower())
    if not match or match.group(1).endswith(".icims.com"):
        return None
    return f"https://{match.group(1)}"


def _location(data: Mapping[str, Any]) -> str:
    full = str(data.get("full_location") or "").strip()
    if full:
        return full
    return ", ".join(str(data[key]).strip() for key in ("city", "state", "country") if data.get(key))


def _to_job(company_name: str, base: str, data: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "company": company_name,
        "title": str(data.get("title") or "").strip(),
        "location": _location(data),
        "url": f"{base}/jobs/{data['slug']}",
        "posted_at": data.get("posted_date") or "",
        "source": SOURCE_LABEL,
        # Raw only, as for Ashby: cleaned text and flags come from ngj.enrich.
        "description": "",
        "description_html": "\n".join(str(data[f]) for f in _DESCRIPTION_FIELDS if data.get(f)),
    }


def _listable(data: Any) -> bool:
    return (
        isinstance(data, Mapping)
        and _SLUG_RE.match(str(data.get("slug") or "")) is not None
        and str(data.get("title") or "").strip() != ""
        and data.get("searchable", True) not in (False, 0, "false", "False")
        and str(data.get("employment_type") or "").upper() not in SKIPPED_EMPLOYMENT_TYPES
    )


def _page_parser(company_name: str, base: str, totals: list[int]) -> Callable[[Any], SourceResult | None]:
    """Parse one search page; record its ``totalCount`` in ``totals`` for the paging loop."""

    def parse(payload: Any) -> SourceResult | None:
        rows = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            return None
        total = payload.get("totalCount")
        totals.append(total if isinstance(total, int) and not isinstance(total, bool) else 0)
        jobs = tuple(_to_job(company_name, base, row["data"]) for row in rows
                     if isinstance(row, Mapping) and _listable(row.get("data")))
        return SourceResult(jobs=jobs, raw_count=len(rows))

    return parse


def _page_url(base: str, page: int, country: str) -> str:
    query = {"page": page, "limit": PAGE_SIZE, "sortBy": "posted_date", "descending": "true", "country": country}
    return f"{base}/api/jobs?{urlencode(query)}"


def _fetch_country(company_name: str, base: str, country: str, max_jobs: int, timeout: int) -> SourceResult:
    """Page one country query until a short page, ``totalCount`` or ``max_jobs`` ends it.

    Paging is bounded by request count (``max_jobs`` / ``PAGE_SIZE`` pages).
    """
    jobs: list[dict[str, Any]] = []
    raw_count = 0
    totals: list[int] = []
    parse = _page_parser(company_name, base, totals)
    for page_number in range(1, max(1, -(-max_jobs // PAGE_SIZE)) + 1):
        page = ngj_http.fetch_json_with_retry(
            company_name, SOURCE, SOURCE_LABEL, _page_url(base, page_number, country), parse, timeout=timeout)
        if page.errors:
            return SourceResult(jobs=tuple(jobs), errors=page.errors, raw_count=raw_count)
        jobs = [*jobs, *page.jobs[: max_jobs - len(jobs)]]
        raw_count += page.raw_count
        reported_total = totals[-1] if totals else 0
        if (len(jobs) >= max_jobs or page.raw_count < PAGE_SIZE
                or 0 < reported_total <= page_number * PAGE_SIZE):
            break
    return SourceResult(jobs=tuple(jobs), raw_count=raw_count)


def fetch_icims_jobs(
    company_name: str,
    url: str,
    *,
    countries: Sequence[str] = ("United States", "Canada", "India"),
    max_jobs_per_country: int = 1000,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> SourceResult:
    """Fetch one career site, one query per country; a posting found twice is kept once."""
    base = site_base(url)
    if base is None:
        message = f"not an iCIMS career-site root (https://<host>, not *.icims.com): {url}"
        return SourceResult(errors=(SourceError(company_name, SOURCE, KIND_CONFIG, None, message),))

    results = [_fetch_country(company_name, base, country, max_jobs_per_country, timeout) for country in countries]
    seen: set[str] = set()
    ordered: list[dict[str, Any]] = []
    for job in (job for result in results for job in result.jobs):
        if job["url"] not in seen:
            seen.add(job["url"])
            ordered.append(job)
    errors = tuple(error for result in results for error in result.errors)
    if any(error.kind in ngj_http.TRANSIENT_KINDS for error in errors):
        # All or nothing on a timeout/network error: retry_transient_failures
        # keeps first-pass jobs, so partial pages would be published twice.
        return SourceResult(errors=errors)
    return SourceResult(jobs=tuple(ordered), errors=errors, raw_count=sum(r.raw_count for r in results))


def fetch_all_icims_jobs(
    companies: Sequence[dict[str, Any]],
    settings: Settings,
    *,
    filtering: Mapping[str, Any] | None = None,
) -> SourceResult:
    """Fetch every configured career site and classic portal, a few at a time (each is its own host)."""

    def fetch(company: dict[str, Any], timeout: int) -> SourceResult:
        if portal_base(company["url"]) is not None:
            return fetch_icims_portal_jobs(
                company["name"], company["url"], filtering=filtering,
                max_jobs=settings.icims_max_jobs_per_portal, max_details=settings.icims_max_details_per_portal,
                timeout=timeout)
        return fetch_icims_jobs(company["name"], company["url"], countries=settings.icims_countries,
                                max_jobs_per_country=settings.icims_max_jobs_per_country, timeout=timeout)

    first_pass = ngj_http.fan_out(
        list(companies),
        lambda c: fetch(c, settings.http_timeout),
        max_workers=min(settings.icims_max_workers, max(1, len(companies))),
        source=SOURCE,
        describe=lambda c: c.get("name", "<unknown>"),
        label=SOURCE_LABEL,
    )
    return ngj_http.retry_transient_failures(
        list(companies),
        first_pass,
        lambda c: fetch(c, settings.http_timeout * 2),
        describe=lambda c: c.get("name", "<unknown>"),
    )

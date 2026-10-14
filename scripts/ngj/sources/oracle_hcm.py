"""Oracle HCM (Recruiting Cloud) candidate-experience REST adapter.

A company is configured by its public careers site,
``https://<host>/hcmUI/CandidateExperience/<lang>/sites/<site>``, and fetched
from the same tenant's requisition search, which needs no key::

    https://<host>/hcmRestApi/resources/latest/recruitingCEJobRequisitions
        ?onlyData=true&expand=requisitionList
        &finder=findReqs;siteNumber=<site>,location=<country>,limit=100,offset=N,sortBy=POSTING_DATES_DESC

Results are newest first, so a per-query cap keeps the most recent postings.
Each company is queried once per target country (``location=United States``):
global tenants (Uber, Nokia, WSP) list most postings abroad. The location
search is the tenant's own geography match and can return a few postings
elsewhere; the location gate drops those. ``location=India`` does not match
Indiana.

The posting page is ``<careers site>/job/<Id>``. Descriptions would cost one
detail request per posting, so they are left empty, as for Workday. Internal
ids (business unit, legal employer, geography) are never copied.

Some tenants take more than 30 s per page, hence ``apis.oracle_hcm.timeout``.
Run time is bounded so one slow tenant cannot stall the scrape: a company
stops paging once ``max_seconds_per_company`` is spent (keeping what it has),
a timeout skips its remaining countries, and the retry pass does not double
the timeout.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable, Sequence
from typing import Any
from urllib.parse import quote

from ngj import http as ngj_http
from ngj.models import KIND_CONFIG, SourceError, SourceResult
from ngj.settings import DEFAULT_ORACLE_HCM_TIMEOUT, Settings

logger = logging.getLogger(__name__)

SOURCE = "oracle_hcm"
SOURCE_LABEL = "Oracle HCM"
# The API silently caps pages at 200; 100 keeps responses small on slow tenants.
PAGE_SIZE = 100
SORT_NEWEST_FIRST = "POSTING_DATES_DESC"

_CAREERS_SITE_RE = re.compile(
    r"^https://([a-z0-9-]+(?:\.[a-z0-9-]+)*\.oraclecloud\.com)"
    r"/hcmUI/CandidateExperience/([A-Za-z]{2,3}(?:[-_][A-Za-z]{2,4})?)/sites/([A-Za-z0-9_-]+)/?$"
)


def careers_site(url: str) -> tuple[str, str, str] | None:
    """``(host, language, site)`` of a configured careers-site URL, else None."""
    match = _CAREERS_SITE_RE.match((url or "").strip())
    return (match.group(1), match.group(2), match.group(3)) if match else None


def _to_job(company_name: str, site_url: str, raw: dict[str, Any]) -> dict[str, Any]:
    location = raw.get("PrimaryLocation") or ""
    if "remote" in str(raw.get("WorkplaceType") or "").lower():
        location = f"Remote, {location}" if location else "Remote"
    return {
        "company": company_name,
        "title": (raw.get("Title") or "").strip(),
        "location": location,
        "url": f"{site_url}/job/{raw['Id']}",
        "posted_at": raw.get("PostedDate") or "",
        "source": SOURCE_LABEL,
        "description": "",  # Not in the search payload: one extra request per posting.
    }


def _page_parser(company_name: str, site_url: str, totals: list[int]) -> Callable[[Any], SourceResult | None]:
    """Parse one search page; record its ``TotalJobsCount`` in ``totals`` for the paging loop."""

    def parse(data: Any) -> SourceResult | None:
        items = data.get("items") if isinstance(data, dict) else None
        search = items[0] if isinstance(items, list) and items and isinstance(items[0], dict) else None
        if search is None:
            return None
        requisitions = search.get("requisitionList")
        if not isinstance(requisitions, list):
            return None
        total = search.get("TotalJobsCount")
        totals.append(total if isinstance(total, int) and not isinstance(total, bool) else 0)
        return SourceResult(
            # A requisition without an Id has no posting page, so it is skipped.
            jobs=tuple(_to_job(company_name, site_url, raw) for raw in requisitions
                       if isinstance(raw, dict) and raw.get("Id")),
            raw_count=len(requisitions),
        )

    return parse


def _search_url(host: str, site: str, offset: int, country: str | None) -> str:
    finder = [f"siteNumber={site}"]
    if country:
        finder.append(f"location={quote(country, safe='')}")
    finder += [f"limit={PAGE_SIZE}", f"offset={offset}", f"sortBy={SORT_NEWEST_FIRST}"]
    return (f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
            f"?onlyData=true&expand=requisitionList&finder=findReqs;{','.join(finder)}")


def _out_of_time(deadline: float | None) -> bool:
    return deadline is not None and time.monotonic() >= deadline


def _fetch_country(
    company_name: str,
    host: str,
    site: str,
    site_url: str,
    country: str | None,
    max_jobs: int,
    timeout: int,
    deadline: float | None,
) -> SourceResult:
    """Page one country query until the site, a short page or ``max_jobs`` ends it.

    Paging is bounded by request count (``max_jobs`` / ``PAGE_SIZE`` pages), so
    pages of unusable records cannot loop forever. ``TotalJobsCount`` only ends
    paging early when the API reports it. No page is requested after ``deadline``.
    """
    jobs: list[dict[str, Any]] = []
    raw_count = 0
    offset = 0
    totals: list[int] = []
    parse = _page_parser(company_name, site_url, totals)
    for page_index in range(max(1, -(-max_jobs // PAGE_SIZE))):
        if page_index and _out_of_time(deadline):
            break
        page = ngj_http.fetch_json_with_retry(
            company_name, SOURCE, SOURCE_LABEL, _search_url(host, site, offset, country), parse, timeout=timeout)
        if page.errors:
            return SourceResult(jobs=tuple(jobs), errors=page.errors, raw_count=raw_count)
        jobs = [*jobs, *page.jobs[: max_jobs - len(jobs)]]
        raw_count += page.raw_count
        offset += PAGE_SIZE
        reported_total = totals[-1] if totals else 0
        if (len(jobs) >= max_jobs or page.raw_count < PAGE_SIZE or not page.jobs
                or 0 < reported_total <= offset):
            break
    return SourceResult(jobs=tuple(jobs), raw_count=raw_count)


def fetch_oracle_hcm_jobs(
    company_name: str,
    url: str,
    *,
    countries: Sequence[str] = (),
    max_jobs_per_country: int = 1000,
    timeout: int = DEFAULT_ORACLE_HCM_TIMEOUT,
    max_seconds: float | None = None,
) -> SourceResult:
    """Fetch one careers site, one query per country (the whole site when none).

    Countries run in order until ``max_seconds`` is spent; a timeout or network
    error ends the company at once and returns no jobs (see module docstring).
    """
    parsed = careers_site(url)
    if parsed is None:
        message = f"not an Oracle HCM careers-site URL: {url}"
        return SourceResult(errors=(SourceError(company_name, SOURCE, KIND_CONFIG, None, message),))

    host, language, site = parsed
    site_url = f"https://{host}/hcmUI/CandidateExperience/{language}/sites/{site}"
    deadline = time.monotonic() + max_seconds if max_seconds else None
    results: list[SourceResult] = []
    for country in tuple(countries) or (None,):
        if results and _out_of_time(deadline):
            break
        result = _fetch_country(
            company_name, host, site, site_url, country, max_jobs_per_country, timeout, deadline)
        if any(error.kind in ngj_http.TRANSIENT_KINDS for error in result.errors):
            # All or nothing on a timeout/network error: retry_transient_failures
            # re-fetches the company and keeps first-pass jobs, so partial pages
            # here would be published twice. The other countries are skipped too:
            # a tenant that timed out once is likely to time out again.
            return SourceResult(errors=tuple(e for r in [*results, result] for e in r.errors))
        results.append(result)
    if _out_of_time(deadline):
        logger.warning("  ⏱️  %s: Oracle HCM time budget (%ss) spent; keeping %s postings",
                       company_name, max_seconds, sum(len(r.jobs) for r in results))
    errors = tuple(error for result in results for error in result.errors)
    # A posting with several locations can surface in more than one country query.
    seen: set[str] = set()
    ordered: list[dict[str, Any]] = []
    for job in (job for result in results for job in result.jobs):
        if job["url"] not in seen:
            seen.add(job["url"])
            ordered.append(job)
    return SourceResult(jobs=tuple(ordered), errors=errors, raw_count=sum(r.raw_count for r in results))


def fetch_all_oracle_hcm_jobs(companies: Sequence[dict[str, Any]], settings: Settings) -> SourceResult:
    """Fetch every configured Oracle HCM careers site in parallel."""

    def fetch(company: dict[str, Any], timeout: int) -> SourceResult:
        return fetch_oracle_hcm_jobs(
            company["name"], company["url"],
            countries=settings.oracle_hcm_countries,
            max_jobs_per_country=settings.oracle_hcm_max_jobs_per_country,
            timeout=timeout,
            max_seconds=settings.oracle_hcm_max_seconds_per_company,
        )

    first_pass = ngj_http.fan_out(
        list(companies),
        lambda c: fetch(c, settings.oracle_hcm_timeout),
        max_workers=min(settings.oracle_hcm_max_workers, max(1, len(companies))),
        source=SOURCE,
        describe=lambda c: c.get("name", "<unknown>"),
        label=SOURCE_LABEL,
    )
    # Same timeout on the retry pass: it runs sequentially, and these tenants
    # are slow rather than briefly congested, so doubling only adds wall time.
    return ngj_http.retry_transient_failures(
        list(companies),
        first_pass,
        lambda c: fetch(c, settings.oracle_hcm_timeout),
        describe=lambda c: c.get("name", "<unknown>"),
    )

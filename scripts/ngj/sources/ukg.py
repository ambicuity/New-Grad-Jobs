"""UKG Pro Recruiting (UltiPro) public job-board adapter.

A company is configured by its job board,
``https://<host>/<tenant>/JobBoard/<board-id>`` on ``recruiting[N].ultipro.com``
or ``<company>.rec.pro.ukg.net``. The board's own search needs no key::

    POST <board>/JobBoardView/LoadSearchResults
    {"opportunitySearch": {"Top": 100, "Skip": N, "OrderBy": [postedDateDesc], "Filters": []}}

Results are newest first with a ``totalCount``, so a per-board cap keeps the
most recent postings. Each opportunity carries its title, posting date, a brief
description and structured addresses. ``LocalizedName`` is often null, so the
location is built from the address. ``JobLocationType`` is not used: it does
not reliably mark remote work. The posting page is
``<board>/OpportunityDetail?opportunityId=<Id>``. Requisition numbers and
coordinates are never copied.

The search is a POST, which the session never retries at the transport level
(GET gets urllib3's retries). It is read-only, so the adapter retries a page
itself on 429/5xx (:data:`POST_ATTEMPTS`, short backoff); otherwise one blip
would drop the board for the run. A timeout gets the board-level retry pass
like every other source.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from ngj import http as ngj_http
from ngj.models import KIND_CONFIG, KIND_HTTP, SourceError, SourceResult
from ngj.settings import DEFAULT_HTTP_TIMEOUT, Settings

SOURCE = "ukg"
SOURCE_LABEL = "UKG"
PAGE_SIZE = 100
# Attempts per search page on 429/5xx, and the backoff step between them (seconds).
POST_ATTEMPTS = 3
POST_RETRY_BACKOFF = 1.0

_JOB_BOARD_RE = re.compile(
    r"^(https://(?:recruiting\d*\.ultipro\.com|[a-z0-9-]+\.rec\.pro\.ukg\.net)"
    r"/[A-Za-z0-9]+/JobBoard/[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})/?$"
)


def job_board(url: str) -> str | None:
    """The canonical job-board URL (no trailing slash) of a configured entry, else None."""
    match = _JOB_BOARD_RE.match((url or "").strip())
    return match.group(1) if match else None


def _search_body(skip: int) -> dict[str, Any]:
    return {
        "opportunitySearch": {
            "Top": PAGE_SIZE,
            "Skip": skip,
            "QueryString": "",
            "OrderBy": [{"Value": "postedDateDesc", "PropertyName": "PostedDate", "Ascending": False}],
            "Filters": [],
        },
        "matchCriteria": {},
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _place(location: Any) -> str:
    if not isinstance(location, Mapping):
        return ""
    if location.get("LocalizedName"):
        return str(location["LocalizedName"]).strip()
    address = _mapping(location.get("Address"))
    state = _mapping(address.get("State"))
    country = _mapping(address.get("Country"))
    parts = (address.get("City"), state.get("Code"), country.get("Name") or country.get("Code"))
    return ", ".join(str(part) for part in parts if part)


def _to_job(company_name: str, board: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    places = [place for place in (_place(loc) for loc in raw.get("Locations") or ()) if place]
    return {
        "company": company_name,
        "title": (raw.get("Title") or "").strip(),
        "location": "; ".join(places),
        "url": f"{board}/OpportunityDetail?opportunityId={raw['Id']}",
        "posted_at": raw.get("PostedDate") or "",
        "source": SOURCE_LABEL,
        # Raw only, as for Ashby: cleaned text and flags come from ngj.enrich.
        "description": "",
        "description_html": raw.get("BriefDescription") or "",
    }


def _page_parser(company_name: str, board: str, totals: list[int]) -> Callable[[Any], SourceResult | None]:
    def parse(data: Any) -> SourceResult | None:
        opportunities = data.get("opportunities") if isinstance(data, dict) else None
        if not isinstance(opportunities, list):
            return None
        total = data.get("totalCount")
        totals.append(total if isinstance(total, int) and not isinstance(total, bool) else 0)
        return SourceResult(
            # An opportunity without an Id has no posting page, so it is skipped.
            jobs=tuple(_to_job(company_name, board, raw) for raw in opportunities
                       if isinstance(raw, dict) and raw.get("Id")),
            raw_count=len(opportunities),
        )

    return parse


def _search_page(
    company_name: str,
    search_url: str,
    parse: Callable[[Any], SourceResult | None],
    skip: int,
    timeout: int,
) -> SourceResult:
    """One search page, retried on a retryable status (the POST has no transport retry)."""
    def attempt() -> SourceResult:
        return ngj_http.fetch_json_with_retry(
            company_name, SOURCE, SOURCE_LABEL, search_url, parse, timeout=timeout, json_body=_search_body(skip))

    for retry in range(1, POST_ATTEMPTS):
        page = attempt()
        if not any(e.kind == KIND_HTTP and e.status in ngj_http.RETRY_STATUS_FORCELIST for e in page.errors):
            return page
        time.sleep(POST_RETRY_BACKOFF * retry)
    return attempt()


def fetch_ukg_jobs(
    company_name: str,
    url: str,
    *,
    max_jobs: int = 1000,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> SourceResult:
    """Fetch one job board, newest first, up to ``max_jobs`` postings.

    Paging is bounded by request count; ``totalCount`` only ends it early when
    the API reports one. A timeout or network error returns no jobs, so the
    retry pass cannot publish the board twice.
    """
    board = job_board(url)
    if board is None:
        message = f"not a UKG Pro Recruiting job-board URL: {url}"
        return SourceResult(errors=(SourceError(company_name, SOURCE, KIND_CONFIG, None, message),))

    search_url = f"{board}/JobBoardView/LoadSearchResults"
    jobs: list[dict[str, Any]] = []
    raw_count = 0
    totals: list[int] = []
    parse = _page_parser(company_name, board, totals)
    for page_number in range(max(1, -(-max_jobs // PAGE_SIZE))):
        skip = page_number * PAGE_SIZE
        page = _search_page(company_name, search_url, parse, skip, timeout)
        if page.errors:
            if any(error.kind in ngj_http.TRANSIENT_KINDS for error in page.errors):
                return SourceResult(errors=page.errors)
            return SourceResult(jobs=tuple(jobs), errors=page.errors, raw_count=raw_count)
        jobs = [*jobs, *page.jobs[: max_jobs - len(jobs)]]
        raw_count += page.raw_count
        reported_total = totals[-1] if totals else 0
        if (len(jobs) >= max_jobs or page.raw_count < PAGE_SIZE or not page.jobs
                or 0 < reported_total <= skip + PAGE_SIZE):
            break
    return SourceResult(jobs=tuple(jobs), raw_count=raw_count)


def fetch_all_ukg_jobs(companies: Sequence[dict[str, Any]], settings: Settings) -> SourceResult:
    """Fetch every configured UKG job board in parallel."""

    def fetch(company: dict[str, Any], timeout: int) -> SourceResult:
        return fetch_ukg_jobs(company["name"], company["url"], max_jobs=settings.ukg_max_jobs_per_company,
                              timeout=timeout)

    first_pass = ngj_http.fan_out(
        list(companies),
        lambda c: fetch(c, settings.http_timeout),
        max_workers=min(settings.ukg_max_workers, max(1, len(companies))),
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

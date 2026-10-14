"""SmartRecruiters public Posting API adapter (``api.smartrecruiters.com/v1/companies/<id>/postings``).

The list endpoint needs no key, is paged (``limit`` <= 100, ``offset``) and is
sorted newest first, so a per-query cap keeps the most recent postings. Each
company is queried once per target country (``country=us``): large employers
list thousands of postings abroad that the location gate would drop anyway.

The list carries no posting URL and no description. The posting page is
``jobs.smartrecruiters.com/<id>/<postingId>`` (the title slug some links add is
cosmetic), which keeps ``job_id`` stable when a title is edited. Descriptions
would cost one detail request per posting, so they are left empty, as for
Workday. ``customField`` (hiring-manager names, internal codes) is never copied.

Only postings whose country is a target country are queried, so a remote
posting the employer files under another country is not seen; the location
gate would treat it as foreign anyway.

An unknown company id answers HTTP 200 with ``totalFound: 0``, so a mistyped id
looks like an empty board: probe new ids before adding them to config.yml.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import Any

from ngj import http as ngj_http
from ngj.models import KIND_CONFIG, SourceError, SourceResult
from ngj.settings import DEFAULT_HTTP_TIMEOUT, Settings

SOURCE = "smartrecruiters"
SOURCE_LABEL = "SmartRecruiters"
# The Posting API rejects larger pages.
PAGE_SIZE = 100
POSTING_URL = "https://jobs.smartrecruiters.com/{company}/{posting}"

_POSTINGS_URL_RE = re.compile(r"^https://api\.smartrecruiters\.com/v1/companies/([^/?#]+)/postings/?$")


def company_identifier(url: str) -> str | None:
    """The company id in a configured ``.../v1/companies/<id>/postings`` URL, else None."""
    match = _POSTINGS_URL_RE.match((url or "").strip())
    return match.group(1) if match else None


def _location(raw: dict[str, Any]) -> str:
    location = raw.get("location") or {}
    text = location.get("fullLocation") or ", ".join(
        str(part).upper() if key == "country" else str(part)
        for key in ("city", "region", "country")
        if (part := location.get(key))
    )
    if location.get("remote"):
        return f"Remote, {text}" if text else "Remote"
    return text


def _to_job(company_name: str, identifier: str, raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "company": company_name,
        "title": (raw.get("name") or "").strip(),
        "location": _location(raw),
        "url": POSTING_URL.format(company=identifier, posting=raw.get("id", "")),
        "posted_at": raw.get("releasedDate") or "",
        "source": SOURCE_LABEL,
        "description": "",  # Not in the list payload: one extra request per posting.
    }


def _page_parser(company_name: str, identifier: str, totals: list[int]) -> Callable[[Any], SourceResult | None]:
    """Parse one list page; record its ``totalFound`` in ``totals`` for the paging loop."""

    def parse(data: Any) -> SourceResult | None:
        content = data.get("content") if isinstance(data, dict) else None
        if not isinstance(content, list):
            return None
        totals.append(int(data.get("totalFound") or 0))
        return SourceResult(
            # A posting without an id has no page of its own (and would collapse
            # every such posting onto one URL), so it is skipped.
            jobs=tuple(_to_job(company_name, identifier, raw) for raw in content
                       if isinstance(raw, dict) and raw.get("id")),
            raw_count=len(content),
        )

    return parse


def _page_url(base: str, offset: int, country: str | None) -> str:
    url = f"{base}?limit={PAGE_SIZE}&offset={offset}"
    return f"{url}&country={country}" if country else url


def _fetch_country(
    company_name: str,
    identifier: str,
    base: str,
    country: str | None,
    max_jobs: int,
    timeout: int,
) -> SourceResult:
    """Page one country query until the board, a short page or ``max_jobs`` ends it.

    Paging is bounded by request count (``max_jobs`` / ``PAGE_SIZE`` pages), not
    by jobs kept, so pages of unusable records cannot loop forever. ``totalFound``
    only ends paging early when the API reports it.
    """
    jobs: list[dict[str, Any]] = []
    raw_count = 0
    offset = 0
    totals: list[int] = []
    parse = _page_parser(company_name, identifier, totals)
    max_pages = max(1, -(-max_jobs // PAGE_SIZE))
    for _ in range(max_pages):
        page = ngj_http.fetch_json_with_retry(
            company_name, SOURCE, SOURCE_LABEL, _page_url(base, offset, country), parse, timeout=timeout)
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


def fetch_smartrecruiters_jobs(
    company_name: str,
    url: str,
    *,
    countries: Sequence[str] = (),
    max_jobs_per_country: int = 1000,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> SourceResult:
    """Fetch one company's postings, one query per country (the whole board when none)."""
    identifier = company_identifier(url)
    if identifier is None:
        message = f"not a SmartRecruiters postings URL: {url}"
        return SourceResult(errors=(SourceError(company_name, SOURCE, KIND_CONFIG, None, message),))

    base = url.strip().rstrip("/")
    results = [
        _fetch_country(company_name, identifier, base, country, max_jobs_per_country, timeout)
        for country in (tuple(countries) or (None,))
    ]
    # A posting has one country, but a remote one can surface in several queries.
    seen: set[str] = set()
    ordered: list[dict[str, Any]] = []
    for job in (job for result in results for job in result.jobs):
        if job["url"] not in seen:
            seen.add(job["url"])
            ordered.append(job)
    errors = tuple(error for result in results for error in result.errors)
    if any(error.kind in ngj_http.TRANSIENT_KINDS for error in errors):
        # All or nothing on a timeout/network error, like the other adapters:
        # retry_transient_failures re-fetches the company and keeps first-pass
        # jobs, so partial pages here would be published twice.
        return SourceResult(errors=errors)
    return SourceResult(
        jobs=tuple(ordered),
        errors=errors,
        raw_count=sum(result.raw_count for result in results),
    )


def fetch_all_smartrecruiters_jobs(companies: Sequence[dict[str, Any]], settings: Settings) -> SourceResult:
    """Fetch every configured SmartRecruiters company in parallel."""

    def fetch(company: dict[str, Any], timeout: int) -> SourceResult:
        return fetch_smartrecruiters_jobs(
            company["name"], company["url"],
            countries=settings.smartrecruiters_countries,
            max_jobs_per_country=settings.smartrecruiters_max_jobs_per_country,
            timeout=timeout,
        )

    first_pass = ngj_http.fan_out(
        list(companies),
        lambda c: fetch(c, settings.http_timeout),
        max_workers=min(settings.smartrecruiters_max_workers, max(1, len(companies))),
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

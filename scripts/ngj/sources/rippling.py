"""Rippling ATS public board adapter (``ats.rippling.com/api/v2/board/<slug>/jobs``).

The board list needs no key and is paged (``page``, ``pageSize`` <= 100,
``totalPages``). It has the title, posting URL and structured locations, but
no posting date, and a posting without a date never passes the recency rule.
The date (``createdOn``), the description and a structured pay range live on
the per-posting detail endpoint (``.../jobs/<id>``).

So a board is read in two passes: the list, then the detail of each posting
whose title passes :func:`ngj.filters.passes_title_rules` (about 5% of
postings). The rest are still returned, without a date, so the Explore corpus
stays complete; they fail the title rules, so no date would change their fate.
Postings the detail marks ``unlistedFromSearch`` are dropped.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from ngj import http as ngj_http
from ngj.compensation import bounded_comp
from ngj.filters import passes_title_rules
from ngj.models import KIND_CONFIG, KIND_HTTP, SourceError, SourceResult
from ngj.settings import DEFAULT_HTTP_TIMEOUT, Settings

SOURCE = "rippling"
SOURCE_LABEL = "Rippling"
PAGE_SIZE = 100
POSTING_URL = "https://ats.rippling.com/{slug}/jobs/{posting}"
# A detail that answers one of these closed between the list and the detail
# request: the posting is dropped. Any other detail failure fails the board.
GONE_STATUSES = frozenset({404, 410})

_BOARD_URL_RE = re.compile(r"^https://ats\.rippling\.com/api/v2/board/([A-Za-z0-9_.-]+)/jobs/?$")


def board_slug(url: str) -> str | None:
    """The board slug in a configured ``.../api/v2/board/<slug>/jobs`` URL, else None."""
    match = _BOARD_URL_RE.match((url or "").strip())
    return match.group(1) if match else None


def _location(item: Mapping[str, Any]) -> str:
    parts = []
    for location in item.get("locations") or ():
        if not isinstance(location, Mapping) or not location.get("name"):
            continue
        name = str(location["name"]).strip()
        is_remote = location.get("workplaceType") == "REMOTE" and "remote" not in name.lower()
        parts.append(f"Remote, {name}" if is_remote else name)
    return "; ".join(parts)


def _comp(detail: Mapping[str, Any]) -> dict[str, Any] | None:
    """First yearly pay range within its currency's sanity bounds."""
    for pay in detail.get("payRangeDetails") or ():
        try:
            if str(pay.get("frequency") or "").upper() == "YEAR":
                comp = bounded_comp(pay.get("rangeStart"), pay.get("rangeEnd"), SOURCE,
                                    currency=(pay.get("currency") or "USD").upper())
                if comp:
                    return comp
        except (TypeError, ValueError, AttributeError):
            continue
    return None


def _description_html(detail: Mapping[str, Any]) -> str:
    description = detail.get("description")
    if not isinstance(description, Mapping):
        return ""
    return "\n".join(str(description[key]) for key in ("role", "company") if description.get(key))


def _to_job(company_name: str, slug: str, item: Mapping[str, Any], detail: Mapping[str, Any] | None) -> dict[str, Any]:
    job: dict[str, Any] = {
        "company": company_name,
        "title": (item.get("name") or "").strip(),
        "location": _location(item),
        "url": item.get("url") or POSTING_URL.format(slug=slug, posting=item["id"]),
        "posted_at": "",
        "source": SOURCE_LABEL,
        "description": "",
    }
    if detail is None:
        return job
    # Raw only, as for Ashby: cleaned text and regex comp come from ngj.enrich.
    return {**job, "posted_at": detail.get("createdOn") or "",
            "description_html": _description_html(detail), "comp": _comp(detail)}


def _list_parser(totals: list[int]) -> Callable[[Any], SourceResult | None]:
    def parse(data: Any) -> SourceResult | None:
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return None
        pages = data.get("totalPages")
        totals.append(pages if isinstance(pages, int) and not isinstance(pages, bool) else 0)
        # Raw items travel in ``jobs`` here only; they are mapped below.
        return SourceResult(jobs=tuple(i for i in items if isinstance(i, dict) and i.get("id")),
                            raw_count=len(items))

    return parse


def _detail_parser(data: Any) -> SourceResult | None:
    return SourceResult(jobs=(data,), raw_count=1) if isinstance(data, dict) else None


def _list_board(company_name: str, base: str, max_jobs: int, timeout: int) -> SourceResult:
    """Every list item up to ``max_jobs``; paging is bounded by request count."""
    items: list[dict[str, Any]] = []
    raw_count = 0
    totals: list[int] = []
    parse = _list_parser(totals)
    for page_number in range(max(1, -(-max_jobs // PAGE_SIZE))):
        page = ngj_http.fetch_json_with_retry(
            company_name, SOURCE, SOURCE_LABEL, f"{base}?page={page_number}&pageSize={PAGE_SIZE}", parse,
            timeout=timeout)
        if page.errors:
            return SourceResult(jobs=tuple(items), errors=page.errors, raw_count=raw_count)
        items = [*items, *page.jobs[: max_jobs - len(items)]]
        raw_count += page.raw_count
        if len(items) >= max_jobs or not page.jobs or page_number + 1 >= (totals[-1] if totals else 0):
            break
    return SourceResult(jobs=tuple(items), raw_count=raw_count)


def fetch_rippling_jobs(
    company_name: str,
    url: str,
    *,
    filtering: Mapping[str, Any] | None = None,
    max_jobs: int = 1000,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> SourceResult:
    """Fetch one board: the list, then details for postings whose title can pass the filter.

    ``filtering`` must carry ``new_grad_signals`` and ``track_signals``: without
    them every posting would need a detail request, so the board fails closed
    with a config error instead. A posting whose detail is gone (404/410) is
    dropped; any other detail error, and a timeout or network error anywhere,
    returns no jobs, so the board is reported as failed rather than published
    short (and the retry pass cannot publish it twice).
    """
    slug = board_slug(url)
    if slug is None:
        message = f"not a Rippling board API URL: {url}"
        return SourceResult(errors=(SourceError(company_name, SOURCE, KIND_CONFIG, None, message),))

    rules = dict(filtering or {})
    if not (rules.get("new_grad_signals") and rules.get("track_signals")):
        message = "filtering.new_grad_signals and filtering.track_signals are required to pick detail requests"
        return SourceResult(errors=(SourceError(company_name, SOURCE, KIND_CONFIG, None, message),))

    base = url.strip().rstrip("/")
    listing = _list_board(company_name, base, max_jobs, timeout)
    errors = list(listing.errors)
    jobs: list[dict[str, Any]] = []
    for item in listing.jobs:
        title = (item.get("name") or "").strip()
        if not passes_title_rules(title, rules):
            jobs.append(_to_job(company_name, slug, item, None))
            continue
        detail = ngj_http.fetch_json_with_retry(
            company_name, SOURCE, SOURCE_LABEL, f"{base}/{item['id']}", _detail_parser, timeout=timeout)
        if detail.errors:
            if all(e.kind == KIND_HTTP and e.status in GONE_STATUSES for e in detail.errors):
                continue
            return SourceResult(errors=(*errors, *detail.errors))
        payload = detail.jobs[0]
        if not payload.get("unlistedFromSearch"):
            jobs.append(_to_job(company_name, slug, item, payload))

    if any(e.kind in ngj_http.TRANSIENT_KINDS for e in errors):
        return SourceResult(errors=tuple(errors))
    return SourceResult(jobs=tuple(jobs), errors=tuple(errors), raw_count=listing.raw_count)


def fetch_all_rippling_jobs(
    companies: Sequence[dict[str, Any]],
    settings: Settings,
    *,
    filtering: Mapping[str, Any] | None = None,
) -> SourceResult:
    """Fetch every configured Rippling board in parallel."""

    def fetch(company: dict[str, Any], timeout: int) -> SourceResult:
        return fetch_rippling_jobs(company["name"], company["url"], filtering=filtering,
                                   max_jobs=settings.rippling_max_jobs_per_company, timeout=timeout)

    first_pass = ngj_http.fan_out(
        list(companies),
        lambda c: fetch(c, settings.http_timeout),
        max_workers=min(settings.rippling_max_workers, max(1, len(companies))),
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

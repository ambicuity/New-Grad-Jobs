"""Workable public account-widget adapter (``apply.workable.com/api/v1/widget/accounts/<slug>``).

One GET per account returns every published job, so there is no paging. The
widget returns one row per location for the same posting (Credence: 129 rows
for 117 postings), so rows are merged by ``shortcode`` with their locations
combined, as for Rippling: the first non-empty title and the earliest non-empty
date win, so the result does not depend on row order. Postings always link to
``apply.workable.com/j/<shortcode>`` (globally unique), built from the shortcode
rather than the row's own URL, so URL variants cannot split a posting's job_id.
Locations the account marks ``hidden`` are never published, not even through
the row-level city fields. Requisition codes and departments are never copied;
the widget carries no description.

The widget has no paging or total, so completeness for very large accounts
(more than a few hundred postings) is not verified; the configured accounts
list 23-117 postings.

Only direct employers are configured: recruiters posting for unnamed clients
were left out (owner decision, #404; see docs/removed-companies.md).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from ngj import http as ngj_http
from ngj.models import KIND_CONFIG, SourceError, SourceResult
from ngj.settings import DEFAULT_HTTP_TIMEOUT, Settings

SOURCE = "workable"
SOURCE_LABEL = "Workable"
POSTING_URL = "https://apply.workable.com/j/{shortcode}"

_ACCOUNT_URL_RE = re.compile(r"^https://apply\.workable\.com/api/v1/widget/accounts/([A-Za-z0-9_-]+)/?$")


def account_slug(url: str) -> str | None:
    """The account slug in a configured widget URL, else None."""
    match = _ACCOUNT_URL_RE.match((url or "").strip())
    return match.group(1) if match else None


def _join(*parts: Any) -> str:
    return ", ".join(str(part) for part in parts if part)


def _places(row: Mapping[str, Any]) -> list[str]:
    """The row's public places, remote-marked when the posting is remote."""
    locations = row.get("locations")
    if isinstance(locations, list) and locations:
        places = [_join(loc.get("city"), loc.get("region"), loc.get("country"))
                  for loc in locations if isinstance(loc, Mapping) and not loc.get("hidden")]
    else:
        places = [_join(row.get("city"), row.get("state"), row.get("country"))]
    places = [place for place in places if place]
    if row.get("telecommuting"):
        places = [p if "remote" in p.lower() else f"Remote, {p}" for p in places] or ["Remote"]
    return places


def _merge(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """One posting from its rows: first non-empty title, earliest date, every place once."""
    dates = sorted(d for d in (r.get("published_on") or r.get("created_at") for r in rows) if d)
    places = list(dict.fromkeys(place for row in rows for place in _places(row)))
    return {
        "title": next((str(r["title"]).strip() for r in rows if str(r.get("title") or "").strip()), ""),
        "posted_at": dates[0] if dates else "",
        "location": "; ".join(places),
    }


def _parse_account(company_name: str) -> Callable[[Any], SourceResult | None]:
    def parse(data: Any) -> SourceResult | None:
        rows = data.get("jobs") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            return None
        by_code: dict[str, list[Mapping[str, Any]]] = {}
        for row in rows:
            if isinstance(row, Mapping) and row.get("shortcode"):
                code = str(row["shortcode"])
                by_code[code] = [*by_code.get(code, []), row]
        jobs = tuple(
            {
                "company": company_name,
                **_merge(code_rows),
                "url": POSTING_URL.format(shortcode=code),
                "source": SOURCE_LABEL,
                "description": "",  # Not in the widget payload.
            }
            for code, code_rows in by_code.items()
        )
        return SourceResult(jobs=jobs, raw_count=len(jobs))

    return parse


def fetch_workable_jobs(company_name: str, url: str, *, timeout: int = DEFAULT_HTTP_TIMEOUT) -> SourceResult:
    """Fetch one Workable account (a single request; rows merged per posting)."""
    if account_slug(url) is None:
        message = f"not a Workable account-widget URL: {url}"
        return SourceResult(errors=(SourceError(company_name, SOURCE, KIND_CONFIG, None, message),))
    return ngj_http.fetch_json_with_retry(
        company_name, SOURCE, SOURCE_LABEL, url.strip(), _parse_account(company_name), timeout=timeout)


def fetch_all_workable_jobs(companies: Sequence[dict[str, Any]], settings: Settings) -> SourceResult:
    """Fetch every configured Workable account in parallel."""
    first_pass = ngj_http.fan_out(
        list(companies),
        lambda c: fetch_workable_jobs(c["name"], c["url"], timeout=settings.http_timeout),
        max_workers=min(settings.workable_max_workers, max(1, len(companies))),
        source=SOURCE,
        describe=lambda c: c.get("name", "<unknown>"),
        label=SOURCE_LABEL,
    )
    return ngj_http.retry_transient_failures(
        list(companies),
        first_pass,
        lambda c: fetch_workable_jobs(c["name"], c["url"], timeout=settings.http_timeout * 2),
        describe=lambda c: c.get("name", "<unknown>"),
    )

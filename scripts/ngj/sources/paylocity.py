"""Paylocity public recruiting-board adapter (``recruiting.paylocity.com/Recruiting/Jobs/All/<guid>``).

Paylocity has no public JSON API for a company's jobs, but its public board
page embeds the full list as ``window.pageData = {...}`` (``Jobs``: ``JobId``,
``JobTitle``, ``PublishedDate``, ``JobLocation``, ``IsRemote``, ``IsInternal``,
``Description`` snippet). The page is fetched as text (one request per
company) and the object is decoded with ``json.JSONDecoder.raw_decode`` from
its opening brace, so a ``</script>`` inside a description cannot cut it short.
A page without that object is a parse error, so a Paylocity layout change
shows up in health.json instead of silently returning nothing.

Internal jobs and jobs without an id are skipped; a location the board hides
(``ShouldDisplayLocation: false``) is not published. Postings link to
``/Recruiting/Jobs/Details/<JobId>``. Location and module ids are never copied.

Paylocity rate-limits bursts (HTTP 429), so boards are fetched one at a time
by default (one request each, about a second for all of them); GET requests
already get urllib3's backoff and ``Retry-After`` handling.

A company's board GUID comes from the "View All Jobs" link on any of its live
job pages. Only direct employers are configured (owner rule, #404).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from ngj import http as ngj_http
from ngj.models import KIND_CONFIG, SourceError, SourceResult
from ngj.settings import DEFAULT_HTTP_TIMEOUT, Settings

SOURCE = "paylocity"
SOURCE_LABEL = "Paylocity"
BOARD_URL = "https://recruiting.paylocity.com/Recruiting/Jobs/All/{guid}"
POSTING_URL = "https://recruiting.paylocity.com/Recruiting/Jobs/Details/{job_id}"

_BOARD_URL_RE = re.compile(
    r"^https://recruiting\.paylocity\.com/Recruiting/Jobs/All/"
    r"([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})/?$"
)
_PAGE_DATA_RE = re.compile(r"window\.pageData\s*=\s*")
_DECODER = json.JSONDecoder()


def board_guid(url: str) -> str | None:
    """The lowercased company GUID of a configured board URL, else None."""
    match = _BOARD_URL_RE.match((url or "").strip())
    return match.group(1).lower() if match else None


def page_data(html: str) -> Mapping[str, Any] | None:
    """The ``window.pageData`` object with a ``Jobs`` list embedded in a board page, else None.

    Every assignment is tried in order, so an earlier one that is not the data
    (``window.pageData = window.pageData || {}``) cannot hide the real object.
    """
    for match in _PAGE_DATA_RE.finditer(html or ""):
        try:
            data, _end = _DECODER.raw_decode(html, match.end())
        except ValueError:
            continue
        if isinstance(data, Mapping) and isinstance(data.get("Jobs"), list):
            return data
    return None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _location(job: Mapping[str, Any]) -> str:
    place = ""
    if job.get("ShouldDisplayLocation", True):
        loc = _mapping(job.get("JobLocation"))
        place = ", ".join(str(p) for p in (loc.get("City"), loc.get("State"), loc.get("Country")) if p)
        place = place or str(job.get("LocationName") or "").strip()
    if job.get("IsRemote"):
        if not place:
            return "Remote"
        return place if "remote" in place.lower() else f"Remote, {place}"
    return place


def _to_job(company_name: str, job: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "company": company_name,
        "title": str(job.get("JobTitle") or "").strip(),
        "location": _location(job),
        "url": POSTING_URL.format(job_id=job["JobId"]),
        "posted_at": job.get("PublishedDate") or "",
        "source": SOURCE_LABEL,
        # Raw only, as for Ashby: cleaned text and flags come from ngj.enrich.
        "description": "",
        "description_html": job.get("Description") or "",
    }


def _parser(company_name: str) -> Callable[[Any], SourceResult | None]:
    def parse(html: Any) -> SourceResult | None:
        data = page_data(html) if isinstance(html, str) else None
        jobs = data.get("Jobs") if data is not None else None
        if not isinstance(jobs, list):
            return None
        public = tuple(
            _to_job(company_name, job) for job in jobs
            if isinstance(job, Mapping) and job.get("JobId") and not job.get("IsInternal")
        )
        return SourceResult(jobs=public, raw_count=len(public))

    return parse


def fetch_paylocity_jobs(company_name: str, url: str, *, timeout: int = DEFAULT_HTTP_TIMEOUT) -> SourceResult:
    """Fetch one Paylocity board page and read its embedded job list."""
    guid = board_guid(url)
    if guid is None:
        message = f"not a Paylocity board URL: {url}"
        return SourceResult(errors=(SourceError(company_name, SOURCE, KIND_CONFIG, None, message),))
    return ngj_http.fetch_json_with_retry(
        company_name, SOURCE, SOURCE_LABEL, BOARD_URL.format(guid=guid), _parser(company_name),
        timeout=timeout, as_text=True)


def fetch_all_paylocity_jobs(companies: Sequence[dict[str, Any]], settings: Settings) -> SourceResult:
    """Fetch every configured Paylocity board, a few at a time (Paylocity rate-limits bursts)."""
    first_pass = ngj_http.fan_out(
        list(companies),
        lambda c: fetch_paylocity_jobs(c["name"], c["url"], timeout=settings.http_timeout),
        max_workers=min(settings.paylocity_max_workers, max(1, len(companies))),
        source=SOURCE,
        describe=lambda c: c.get("name", "<unknown>"),
        label=SOURCE_LABEL,
    )
    return ngj_http.retry_transient_failures(
        list(companies),
        first_pass,
        lambda c: fetch_paylocity_jobs(c["name"], c["url"], timeout=settings.http_timeout * 2),
        describe=lambda c: c.get("name", "<unknown>"),
    )

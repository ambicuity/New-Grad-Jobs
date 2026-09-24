"""Greenhouse job-board API adapter (boards-api.greenhouse.io).

Two phases, so descriptions are only downloaded for jobs that can be published:

1. :func:`fetch_all_greenhouse_jobs` lists every board *without*
   ``?content=true`` (~19 MB for ~19.7k jobs instead of ~254 MB). Jobs carry
   an empty ``description_html`` plus the board token / job id needed later.
2. After deduplication and filtering, :func:`hydrate_greenhouse_descriptions`
   fetches the individual-job endpoint (which always has full content) for
   the surviving Greenhouse jobs only (~5% of the listing).

The filters only look at title / location / posted date, which the list
endpoint already returns, so filtering before hydration loses nothing.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ngj import http as ngj_http
from ngj.models import SourceResult
from ngj.settings import DEFAULT_HTTP_TIMEOUT, Settings

logger = logging.getLogger(__name__)

SOURCE = "greenhouse"
SOURCE_LABEL = "Greenhouse"
DETAIL_URL = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}"
_BOARD_TOKEN_RE = re.compile(r'/boards/([^/]+)/jobs')

# Internal (non-public) job keys used to hydrate descriptions after filtering.
BOARD_KEY = '_gh_board'
JOB_ID_KEY = '_gh_id'

# Detail requests are additionally capped per domain by ngj.http.DOMAIN_LIMITER.
DEFAULT_HYDRATE_WORKERS = ngj_http.GREENHOUSE_CONCURRENCY


def _without_content_flag(url: str) -> str:
    """Drop ``content=true``: the list is fetched without descriptions (see module docstring)."""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != 'content']
    return urlunsplit(parts._replace(query=urlencode(query)))


def posted_at(raw: dict[str, Any]) -> Any:
    """First publication time; ``updated_at`` only as a last resort.

    ``updated_at`` moves on every edit, which made months-old reqs look new.
    """
    return raw.get('first_published') or raw.get('created_at') or raw.get('updated_at')


def _to_job(company_name: str, raw: dict[str, Any], board_token: str | None) -> dict[str, Any]:
    return {
        'company': company_name,
        'title': raw.get('title') or '',
        'location': (raw.get('location') or {}).get('name') or '',
        'url': raw.get('absolute_url') or '',
        'posted_at': posted_at(raw),
        'source': SOURCE_LABEL,
        # Raw HTML only; cleaned text / comp / flags are derived in ngj.enrich
        # after filtering. Empty here unless the board URL asked for content.
        'description': '',
        'description_html': raw.get('content') or '',
        BOARD_KEY: board_token,
        JOB_ID_KEY: raw.get('id'),
    }


def fetch_greenhouse_jobs(
    company_name: str,
    url: str,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> SourceResult:
    """List one Greenhouse board (titles/locations/dates, no descriptions)."""
    url = _without_content_flag(url)
    board_match = _BOARD_TOKEN_RE.search(url)
    board_token = board_match.group(1) if board_match else None

    def parse(data: Any) -> SourceResult | None:
        if not isinstance(data, dict) or not isinstance(data.get('jobs'), list):
            return None
        raw_jobs = data['jobs']
        jobs = tuple(_to_job(company_name, raw, board_token) for raw in raw_jobs)
        return SourceResult(jobs=jobs, raw_count=len(raw_jobs))

    return ngj_http.fetch_json_with_retry(company_name, SOURCE, SOURCE_LABEL, url, parse, timeout=timeout)


def fetch_greenhouse_job_detail(
    board_token: str,
    job_id: Any,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> dict[str, Any] | None:
    """Fetch one job from the individual-job endpoint (always has full content).

    Best effort: returns None on any failure (logged at debug level). Boards in
    403 cooldown are skipped; a 403 here counts toward the board's cooldown.
    """
    url = DETAIL_URL.format(board=board_token, job_id=job_id)
    if ngj_http.SOURCE_COOLDOWN.is_tripped(url):
        return None
    try:
        response = ngj_http.limited_get(url, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            return data if isinstance(data, dict) else None
        if response.status_code == 403:
            ngj_http.SOURCE_COOLDOWN.try_admit(url)
        logger.debug("Greenhouse detail %s returned HTTP %s", url, response.status_code)
    except Exception as exc:
        logger.debug("Greenhouse detail %s failed: %s", url, exc)
    return None


def _needs_hydration(job: dict[str, Any]) -> bool:
    return bool(not job.get('description_html') and job.get(BOARD_KEY) and job.get(JOB_ID_KEY))


def _hydrate_one(job: dict[str, Any], timeout: int) -> dict[str, Any]:
    detail = fetch_greenhouse_job_detail(job[BOARD_KEY], job[JOB_ID_KEY], timeout=timeout)
    content = detail.get('content') if detail else None
    if not content:
        return job
    return {**job, 'description_html': content}


def hydrate_greenhouse_descriptions(
    jobs: Sequence[dict[str, Any]],
    timeout: int = DEFAULT_HTTP_TIMEOUT,
    max_workers: int = DEFAULT_HYDRATE_WORKERS,
) -> list[dict[str, Any]]:
    """Return ``jobs`` with empty Greenhouse descriptions fetched per job.

    Order is preserved; non-Greenhouse jobs and jobs that already have a
    description pass through untouched (same dict objects). A failed detail
    fetch leaves that job's description empty.
    """
    jobs = list(jobs)
    todo = [i for i, job in enumerate(jobs) if _needs_hydration(job)]
    if not todo:
        return jobs
    logger.info("  📋 Fetching descriptions for %s surviving Greenhouse jobs...", len(todo))
    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(todo)))) as executor:
        hydrated = list(executor.map(lambda i: _hydrate_one(jobs[i], timeout), todo))
    by_index = dict(zip(todo, hydrated, strict=True))
    missing = sum(1 for job in hydrated if not job.get('description_html'))
    if missing:
        logger.info("  ⚠️  %s Greenhouse jobs still have no description", missing)
    return [by_index.get(i, job) for i, job in enumerate(jobs)]


def fetch_all_greenhouse_jobs(companies: Sequence[dict[str, Any]], settings: Settings) -> SourceResult:
    """List every configured Greenhouse board in parallel."""
    # One worker per 3 companies, clamped to the configured pool bounds.
    workers = min(settings.greenhouse_max_workers, max(settings.greenhouse_min_workers, len(companies) // 3))
    first_pass = ngj_http.fan_out(
        list(companies),
        lambda c: fetch_greenhouse_jobs(c['name'], c['url'], timeout=settings.http_timeout),
        max_workers=workers,
        source=SOURCE,
        describe=lambda c: c.get('name', '<unknown>'),
        label='Greenhouse',
    )
    # Big boards can stall past the read timeout while every source runs at
    # once; give timed-out ones a sequential second chance with a longer timeout.
    return ngj_http.retry_transient_failures(
        list(companies),
        first_pass,
        lambda c: fetch_greenhouse_jobs(c['name'], c['url'], timeout=settings.http_timeout * 2),
        describe=lambda c: c.get('name', '<unknown>'),
    )

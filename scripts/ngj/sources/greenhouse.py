"""Greenhouse job-board API adapter (boards-api.greenhouse.io)."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional, Sequence

from ngj import http as ngj_http
from ngj.compensation import extract_compensation
from ngj.models import SourceResult
from ngj.settings import DEFAULT_HTTP_TIMEOUT, Settings
from ngj.text import clean_description

logger = logging.getLogger(__name__)

SOURCE = "greenhouse"
DETAIL_URL = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}"
_BOARD_TOKEN_RE = re.compile(r'/boards/([^/]+)/jobs')


def _with_content_flag(url: str) -> str:
    # Greenhouse omits the description body unless ?content=true is set; the
    # comp/flags/closed detectors need it.
    if 'content=' in url:
        return url
    return url + ('&' if '?' in url else '?') + 'content=true'


def fetch_greenhouse_job_detail(
    board_token: str,
    job_id: int,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> Optional[Dict[str, Any]]:
    """Fetch one job from the individual-job endpoint (always has full content).

    Used when the list endpoint returned an empty description. Best effort:
    returns None on any failure (logged at debug level).
    """
    url = DETAIL_URL.format(board=board_token, job_id=job_id)
    try:
        response = ngj_http.limited_get(url, timeout=timeout)
        if response.status_code == 200:
            return response.json()
        logger.debug("Greenhouse detail %s returned HTTP %s", url, response.status_code)
    except Exception as exc:
        logger.debug("Greenhouse detail %s failed: %s", url, exc)
    return None


def _to_job(company_name: str, raw: Dict[str, Any], description: str) -> Dict[str, Any]:
    return {
        'company': company_name,
        'title': raw.get('title', ''),
        'location': raw.get('location', {}).get('name', 'Remote'),
        'url': raw.get('absolute_url', ''),
        'posted_at': raw.get('updated_at') or raw.get('created_at'),
        'source': 'Greenhouse',
        'description': clean_description(description),
        'description_html': description,
        'comp': extract_compensation(description),
    }


def _fill_empty_description(
    job: Dict[str, Any],
    gh_id: Any,
    board_token: Optional[str],
    timeout: int,
) -> Dict[str, Any]:
    if job['description_html'] or not gh_id or not board_token:
        return job
    detail = fetch_greenhouse_job_detail(board_token, gh_id, timeout=timeout)
    content = detail.get('content') if detail else None
    if not content:
        return job
    return {
        **job,
        'description': clean_description(content),
        'description_html': content,
        'comp': extract_compensation(content) or job['comp'],
    }


def fetch_greenhouse_jobs(
    company_name: str,
    url: str,
    max_retries: int = 2,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> SourceResult:
    """Fetch one Greenhouse board; empty descriptions are back-filled per job."""
    url = _with_content_flag(url)
    board_match = _BOARD_TOKEN_RE.search(url)
    board_token = board_match.group(1) if board_match else None

    def parse(data: Any) -> Optional[SourceResult]:
        if not isinstance(data, dict) or 'jobs' not in data:
            return None
        raw_jobs = data.get('jobs', [])
        jobs = [_to_job(company_name, raw, raw.get('content', '') or '') for raw in raw_jobs]
        empty = sum(1 for job, raw in zip(jobs, raw_jobs) if not job['description_html'] and raw.get('id'))
        if empty and board_token:
            logger.info("  📋 Enriching %s jobs with empty descriptions...", empty)
            jobs = [
                _fill_empty_description(job, raw.get('id'), board_token, timeout)
                for job, raw in zip(jobs, raw_jobs)
            ]
        return SourceResult(jobs=tuple(jobs), raw_count=len(raw_jobs))

    return ngj_http.fetch_json_with_retry(
        company_name, SOURCE, 'Greenhouse', url, parse, timeout=timeout, max_retries=max_retries,
    )


def fetch_all_greenhouse_jobs(companies: Sequence[Dict[str, Any]], settings: Settings) -> SourceResult:
    """Fetch every configured Greenhouse board in parallel."""
    # One worker per 3 companies, clamped to the configured pool bounds.
    workers = min(settings.greenhouse_max_workers, max(settings.greenhouse_min_workers, len(companies) // 3))
    return ngj_http.fan_out(
        list(companies),
        lambda c: fetch_greenhouse_jobs(c['name'], c['url'], timeout=settings.http_timeout),
        max_workers=workers,
        source=SOURCE,
        describe=lambda c: c.get('name', '<unknown>'),
        label='Greenhouse',
    )

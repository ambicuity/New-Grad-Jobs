"""Google Careers adapter: parses the ``AF_initDataCallback`` payload embedded in
the public results page (the old ``/api/v3/search`` JSON endpoint 404s).

Gated on ``apis.google.enabled`` in config.yml.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import requests

from ngj import http as ngj_http
from ngj.models import KIND_FORBIDDEN, KIND_HTTP, KIND_NETWORK, KIND_PARSE, SourceError, SourceResult
from ngj.settings import DEFAULT_GOOGLE_MAX_PAGES, DEFAULT_HTTP_TIMEOUT

logger = logging.getLogger(__name__)

SOURCE = "google"
COMPANY = "Google"
RESULTS_URL = "https://www.google.com/about/careers/applications/jobs/results/"
_DATA_CALLBACK_RE = re.compile(r"AF_initDataCallback\(\{key: 'ds:1', hash: '[^']+', data:([^<]+)\}\);</script>")
_DESCRIPTION_CHARS = 500
_BACKOFF_BASE = 3.0

# Positions inside each job row of the ds:1 payload.
_IDX_ID = 0
_IDX_TITLE = 1
_IDX_LINK = 2
_IDX_COMPANY = 7
_IDX_LOCATIONS = 9
_IDX_DESCRIPTION = 10
_IDX_DATE = 12


def _page_url(search_term: str, page: int) -> str:
    params = urlencode({
        'q': search_term,
        'hl': 'en',
        'location': 'United States',
        'target_level': 'EARLY',
    })
    return f"{RESULTS_URL}?{params}&target_level=INTERN_AND_APPRENTICE&page={page}"


def _find_jobs_array(obj: Any) -> list | None:
    """Depth-first search for the list whose rows start with a numeric id string."""
    if isinstance(obj, list):
        if obj and isinstance(obj[0], list) and obj[0] and isinstance(obj[0][0], str) and obj[0][0].isdigit():
            return obj
        for item in obj:
            found = _find_jobs_array(item)
            if found:
                return found
    return None


def _parse_row(job: list) -> dict[str, Any] | None:
    job_id = job[_IDX_ID]
    title = job[_IDX_TITLE]
    link = job[_IDX_LINK]
    if not isinstance(title, str) or not title.strip():
        return None
    if not link:
        link = f"{RESULTS_URL}{job_id}"
    if not isinstance(link, str) or not link.strip():
        return None

    raw_company = job[_IDX_COMPANY] if len(job) > _IDX_COMPANY else None
    company = raw_company if isinstance(raw_company, str) and raw_company.strip() else COMPANY

    locations = []
    if len(job) > _IDX_LOCATIONS and isinstance(job[_IDX_LOCATIONS], list):
        locations = [loc[0] for loc in job[_IDX_LOCATIONS] if isinstance(loc, list) and loc]

    posted_at = ""
    if len(job) > _IDX_DATE and isinstance(job[_IDX_DATE], list) and job[_IDX_DATE]:
        ts = job[_IDX_DATE][0]
        if isinstance(ts, (int, float)):
            posted_at = datetime.fromtimestamp(ts, tz=UTC).isoformat()

    desc_html = ""
    if len(job) > _IDX_DESCRIPTION and isinstance(job[_IDX_DESCRIPTION], list) and len(job[_IDX_DESCRIPTION]) > 1:
        desc_html = job[_IDX_DESCRIPTION][1] or ""
    desc_text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', desc_html)).strip()

    return {
        "company": company,
        "title": title,
        "location": " | ".join(locations),
        "url": link,
        "posted_at": posted_at,
        "source": "Google Careers",
        "description": desc_text[:_DESCRIPTION_CHARS],
    }


def _fetch_page(url: str, max_retries: int, timeout: int) -> tuple[str, SourceError | None, bool]:
    """Return (html, error, abort_all). ``abort_all`` is set on 403/429."""
    error: SourceError | None = None
    for attempt in range(max_retries + 1):
        response = None
        try:
            response = ngj_http.limited_get(url, timeout=timeout)
            response.raise_for_status()
            return response.text, None, False
        except requests.exceptions.HTTPError:
            status = response.status_code if response is not None else None
            if status in (403, 429):
                logger.warning(
                    "  ⚠️  Google: Rate limited or blocked (HTTP %s). Aborting remaining Google Careers requests.",
                    status,
                )
                return "", SourceError(COMPANY, SOURCE, KIND_FORBIDDEN, status, f"HTTP {status}"), True
            error = SourceError(COMPANY, SOURCE, KIND_HTTP, status, f"HTTP {status} for {url}")
            if status == 404:
                logger.warning("  ⚠️  Google: Endpoint not found (404) for %s.", url)
                break
        except requests.exceptions.RequestException as exc:
            logger.warning("  ⚠️  Google: Request error for %s: %s", url, exc)
            error = SourceError(COMPANY, SOURCE, KIND_NETWORK, None, str(exc))

        if attempt < max_retries:
            time.sleep(_BACKOFF_BASE * (2 ** attempt))
    return "", error, False


def fetch_google_jobs(
    search_terms: Sequence[str],
    max_pages: int = DEFAULT_GOOGLE_MAX_PAGES,
    max_retries: int = 0,  # GETs are already retried by the session (ngj.http.build_retry)
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> SourceResult:
    """Scrape Google Careers result pages for each search term (deduplicated by URL).

    Any page failure (empty HTML, missing/invalid payload) stops the whole
    fetch and returns what was collected so far, matching the scraper's
    historical behaviour.
    """
    all_jobs: list[dict[str, Any]] = []
    errors: list[SourceError] = []
    seen_urls: set[str] = set()
    raw_count = 0

    def done() -> SourceResult:
        logger.info("✓ Found Google Career Jobs returned: %s", len(all_jobs))
        return SourceResult(jobs=tuple(all_jobs), errors=tuple(errors), raw_count=raw_count)

    for search_term in search_terms:
        page = 1
        while True:
            url = _page_url(search_term, page)
            html, error, abort_all = _fetch_page(url, max_retries, timeout)
            if error is not None:
                errors.append(error)
            if abort_all or not html:
                return done()

            match = _DATA_CALLBACK_RE.search(html)
            if not match:
                errors.append(SourceError(COMPANY, SOURCE, KIND_PARSE, None, "AF_initDataCallback ds:1 not found"))
                return done()

            data_str = match.group(1)
            try:
                parsed = json.loads(data_str[data_str.find('['):data_str.rfind(']') + 1])
            except (json.JSONDecodeError, IndexError, TypeError, ValueError) as exc:
                errors.append(SourceError(COMPANY, SOURCE, KIND_PARSE, None, f"invalid ds:1 payload: {exc}"))
                return done()

            jobs_list = _find_jobs_array(parsed)
            if not jobs_list:
                break
            raw_count += len(jobs_list)

            new_jobs = 0
            for row in jobs_list:
                try:
                    job = _parse_row(row)
                except (IndexError, TypeError, ValueError):
                    continue
                if job is None or job['url'] in seen_urls:
                    continue
                seen_urls.add(job['url'])
                all_jobs.append(job)
                new_jobs += 1

            if new_jobs == 0 or page >= max_pages:
                break
            page += 1

    return done()

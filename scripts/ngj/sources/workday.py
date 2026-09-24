"""Workday CXS jobs API adapter (``https://<host>/wday/cxs/<tenant>/<site>/jobs``)."""

from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import requests
from ngj import http as ngj_http
from ngj.models import KIND_CONFIG, KIND_FORBIDDEN, KIND_HTTP, KIND_UNEXPECTED, SourceResult
from ngj.settings import (
    DEFAULT_HTTP_TIMEOUT,
    DEFAULT_WORKDAY_MAX_JOBS_PER_COMPANY,
    DEFAULT_WORKDAY_MAX_WORKERS,
    DEFAULT_WORKDAY_PAGE_LIMIT,
    DEFAULT_WORKDAY_TIMEOUT,
)
from ngj.util import coerce_positive_int

logger = logging.getLogger(__name__)

SOURCE = "workday"
_BROWSER_USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)
_SERVER_ERROR_STATUSES = (500, 502, 503, 504)
_SERVER_ERROR_BACKOFF = 0.3


def build_workday_api_url(host: str, site_path: str) -> str:
    """Build a Workday CXS jobs API endpoint URL.

    Args:
        host: Workday hostname (for example, ``acme.wd5.myworkdayjobs.com``).
        site_path: Path portion from the careers URL (for example,
            ``/Acme_External_Careers`` or ``/tenant/Acme_External_Careers``).

    Returns:
        ``https://<host>/wday/cxs/<tenant>/<site>/jobs``.

    Raises:
        ValueError: If ``host`` or ``site_path`` is not a non-empty string with
            at least one path segment.
    """
    if not isinstance(host, str):
        raise ValueError("host must be a string")
    if not isinstance(site_path, str):
        raise ValueError("site_path must be a string")

    clean_host = host.strip()
    if not clean_host:
        raise ValueError("host is required")

    path_parts = [part for part in site_path.strip('/').split('/') if part]
    if not path_parts:
        raise ValueError("site_path must include at least one segment")

    host_parts = [part for part in clean_host.split('.') if part]
    if not host_parts:
        raise ValueError("host is required")

    tenant = host_parts[0]
    if re.fullmatch(r"wd\d+", tenant.lower()) and len(path_parts) >= 2:
        # For URLs like wd5.myworkdayjobs.com/<tenant>/<site>, tenant lives in the path.
        # Locale-prefixed variants can be /en-US/<tenant>/<site>.
        if len(path_parts) >= 3 and re.fullmatch(r"[a-z]{2}-[a-z]{2}", path_parts[0].lower()):
            tenant = path_parts[1]
        else:
            tenant = path_parts[0]

    site_id = path_parts[-1]
    return f"https://{clean_host}/wday/cxs/{tenant}/{site_id}/jobs"


def get_workday_csrf_token(host: str, session: requests.Session, timeout: int = DEFAULT_HTTP_TIMEOUT) -> str:
    """Acquire the X-Calypso-CSRF-Token required by the Workday CXS jobs API.

    Since early 2026 the CXS API requires the ``X-Calypso-CSRF-Token`` header.
    The careers homepage issues it (header, or ``CALYPSO_CSRF_TOKEN`` cookie)
    and it must be echoed back on every POST.

    Returns the token, or "" when acquisition fails (callers still attempt the
    POST — graceful degradation).
    """
    try:
        resp = session.get(f"https://{host}/", timeout=timeout, allow_redirects=True)
        token = resp.headers.get("X-Calypso-CSRF-Token", "")
        if not token:
            token = resp.cookies.get("CALYPSO_CSRF_TOKEN", "")
        return token
    except Exception as exc:
        logger.warning("  ⚠️  Could not acquire Workday CSRF token for %s: %s", host, exc)
        return ""


def _extract_error_body(response: requests.Response) -> str:
    """Best-effort extraction of an API error body for diagnostics."""
    try:
        return json.dumps(response.json(), ensure_ascii=False)
    except Exception:
        text = (response.text or "").strip()
        if not text:
            return "<no-body>"
        return text[:500]


def _post_page(
    company_name: str,
    api_url: str,
    payload: Dict[str, Any],
    headers: Dict[str, str],
    max_retries: int,
    timeout: int,
) -> requests.Response:
    """POST one page, retrying 5xx with backoff; a 403 is returned immediately."""
    response = None
    for attempt in range(max_retries + 1):
        response = ngj_http.limited_post(api_url, json=payload, headers=headers, timeout=timeout)
        if response.status_code == 403:
            return response
        if response.status_code in _SERVER_ERROR_STATUSES and attempt < max_retries:
            logger.warning(
                "  ⚠️  Workday API error for %s: HTTP %s. Retrying (%s/%s)...",
                company_name, response.status_code, attempt + 1, max_retries,
            )
            time.sleep(_SERVER_ERROR_BACKOFF * (2 ** attempt))
            continue
        break
    return response


def _to_job(company_name: str, host: str, item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'company': company_name,
        'title': item.get('title', ''),
        'location': item.get('locationsText', 'Remote'),
        'url': f"https://{host}{item.get('externalPath', '')}",
        'posted_at': item.get('postedOn', ''),
        'source': 'Workday',
        'description': '',  # Not fetched: one extra request per job.
    }


def _fetch_workday_company(
    company: Dict[str, str],
    page_limit: int,
    max_total_limit: int,
    max_retries: int,
    timeout: int,
) -> SourceResult:
    """Fetch one Workday company's jobs. Never raises: failures become SourceErrors."""
    company_name = company.get('name')
    workday_url = company.get('workday_url')

    if not company_name or not workday_url:
        return SourceResult.failure(
            company_name or '<unnamed>', SOURCE, KIND_CONFIG, "company entry needs name and workday_url",
        )

    skipped = ngj_http.cooldown_skip(company_name, SOURCE, workday_url)
    if skipped is not None:
        return skipped

    logger.info("Fetching jobs from %s (Workday)...", company_name)

    try:
        parsed = urlparse(workday_url)
        host = parsed.netloc
        api_url = build_workday_api_url(host, parsed.path)

        # CSRF token from the careers homepage, echoed on every POST.
        csrf_token = get_workday_csrf_token(host, ngj_http.get_session(), timeout=timeout)
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': _BROWSER_USER_AGENT,
        }
        if csrf_token:
            headers['X-Calypso-CSRF-Token'] = csrf_token

        jobs: List[Dict[str, Any]] = []
        raw_count = 0
        offset = 0

        while True:
            payload = {
                "appliedFacets": {},
                "limit": page_limit,
                "offset": offset,
                "searchText": "",  # Fetch all, filter locally
            }
            response = _post_page(company_name, api_url, payload, headers, max_retries, timeout)

            if response.status_code == 403:
                return ngj_http.record_forbidden(company_name, SOURCE, api_url, label="Workday ")

            if response.status_code == 422:
                # CSRF token expired mid-run — re-acquire and retry once.
                logger.info("  🔄 %s: 422 received, re-acquiring CSRF token and retrying...", company_name)
                csrf_token = get_workday_csrf_token(host, ngj_http.get_session(), timeout=timeout)
                if csrf_token:
                    headers = {**headers, 'X-Calypso-CSRF-Token': csrf_token}
                response = ngj_http.limited_post(api_url, json=payload, headers=headers, timeout=timeout)
                if response.status_code == 403:
                    # Keep the pages already fetched; this 403 follows a token
                    # refresh, so it is not counted toward the domain cooldown.
                    logger.warning("  ⚠️  %s: Workday 403 Forbidden after CSRF refresh", company_name)
                    return SourceResult(
                        jobs=tuple(jobs),
                        raw_count=raw_count,
                        errors=SourceResult.failure(
                            company_name, SOURCE, KIND_FORBIDDEN, "403 Forbidden after CSRF refresh", status=403,
                        ).errors,
                    )

            if not response.ok:
                error_body = _extract_error_body(response)
                logger.warning(
                    "  ⚠️  Workday API error for %s: HTTP %s — %s", company_name, response.status_code, error_body,
                )
                return SourceResult(
                    jobs=tuple(jobs),
                    raw_count=raw_count,
                    errors=SourceResult.failure(
                        company_name, SOURCE, KIND_HTTP, f"HTTP {response.status_code}: {error_body[:200]}",
                        status=response.status_code,
                    ).errors,
                )

            job_items = response.json().get('jobPostings', [])
            if not job_items:
                break

            raw_count += len(job_items)
            jobs.extend(_to_job(company_name, host, item) for item in job_items)

            offset += page_limit
            if len(jobs) >= max_total_limit:
                logger.info("  ℹ️  %s: Reached safety limit of %s jobs. Truncating.", company_name, max_total_limit)
                jobs = jobs[:max_total_limit]
                break

        logger.info("  ✓ Found %s jobs from %s", len(jobs), company_name)
        return SourceResult(jobs=tuple(jobs), raw_count=raw_count)

    except Exception as exc:
        logger.error("  ❌ Error processing %s: %s", company_name, exc)
        return SourceResult.failure(company_name, SOURCE, KIND_UNEXPECTED, f"{type(exc).__name__}: {exc}")


def _workday_host_key(company: Dict[str, str]) -> str:
    """Group key for companies whose requests must not interleave (same host)."""
    try:
        return urlparse(company.get('workday_url') or '').netloc.lower()
    except (TypeError, ValueError):
        return ''


def fetch_workday_jobs(
    companies: Sequence[Dict[str, str]],
    page_limit: Optional[int] = None,
    max_total_limit: Optional[int] = None,
    max_retries: int = 2,
    timeout: Optional[int] = None,
    max_workers: Optional[int] = None,
) -> SourceResult:
    """Fetch Workday companies in parallel.

    Companies are grouped by host and each host group runs in one worker, so
    tenants that share a host never interleave their CSRF token GET and POSTs
    on the shared session's per-host cookies. Results are merged in config
    order. One company failing never affects the others.

    ``None`` arguments fall back to the module defaults; the pipeline always
    passes the values from :class:`ngj.settings.Settings`.
    """
    page_limit = coerce_positive_int(page_limit, DEFAULT_WORKDAY_PAGE_LIMIT, "page_limit")
    max_total_limit = coerce_positive_int(max_total_limit, DEFAULT_WORKDAY_MAX_JOBS_PER_COMPANY, "max_total_limit")
    max_workers = coerce_positive_int(max_workers, DEFAULT_WORKDAY_MAX_WORKERS, "max_workers")
    timeout = coerce_positive_int(timeout, DEFAULT_WORKDAY_TIMEOUT, "timeout")

    # host -> [(config index, company)], preserving config order within a host.
    host_groups: Dict[str, List[Tuple[int, Dict[str, str]]]] = {}
    for index, company in enumerate(companies):
        host_groups.setdefault(_workday_host_key(company), []).append((index, company))

    def _fetch_group(group: List[Tuple[int, Dict[str, str]]]) -> List[Tuple[int, SourceResult]]:
        return [
            (index, _fetch_workday_company(company, page_limit, max_total_limit, max_retries, timeout))
            for index, company in group
        ]

    results: Dict[int, SourceResult] = {}
    workers = max(1, min(max_workers, len(host_groups)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_fetch_group, group) for group in host_groups.values()]
        for future in as_completed(futures):
            # _fetch_workday_company catches its own errors, so result() only
            # raises on a programming error — surface it rather than hide it.
            for index, result in future.result():
                results[index] = result

    return SourceResult.merge(results[index] for index in sorted(results))

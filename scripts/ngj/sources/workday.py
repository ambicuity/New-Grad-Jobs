"""Workday CXS jobs API adapter (``https://<host>/wday/cxs/<tenant>/<site>/jobs``).

Search strategy
---------------
Big tenants list thousands of jobs, and the unfiltered listing is ordered by
Workday's own relevance, so a plain ``searchText: ""`` crawl capped at a few
hundred jobs silently dropped most new-grad roles (NVIDIA: 2 of ~30 filter
survivors were in the first 200). When ``search_keywords`` are configured
(``apis.workday.search_filters.title_keywords``), each keyword is searched
separately and results are merged by ``externalPath``. Workday ranks keyword
matches by relevance, so paging a keyword stops as soon as a page contains no
title that passes the optional ``title_filter`` (a cheap title-only
pre-check), or the per-keyword cap is hit.

Errors
------
HTTP 422 with an empty message means the tenant/site in ``workday_url`` does
not exist on that ``wdN`` data centre (it is not a CSRF problem: the CXS API
answers without a token). It is reported as a config error so the entry gets
fixed rather than retried.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import requests

from ngj import http as ngj_http
from ngj.models import (
    KIND_CONFIG,
    KIND_HTTP,
    KIND_NETWORK,
    KIND_PARSE,
    KIND_TIMEOUT,
    KIND_UNEXPECTED,
    SourceError,
    SourceResult,
)
from ngj.settings import (
    DEFAULT_HTTP_TIMEOUT,
    DEFAULT_WORKDAY_KEYWORD_WORKERS,
    DEFAULT_WORKDAY_MAX_JOBS_PER_COMPANY,
    DEFAULT_WORKDAY_MAX_JOBS_PER_KEYWORD,
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
_SERVER_ERROR_BACKOFF = 0.5
# The search POST is idempotent but POSTs are excluded from the session's
# urllib3 retry policy, so a 5xx page gets one retry here — the only retry
# on this path.
DEFAULT_POST_RETRIES = 1
# The CXS jobs API rejects any page size above 20 with HTTP 400.
WORKDAY_MAX_PAGE_LIMIT = 20

TitleFilter = Callable[[str], bool]


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


def get_workday_csrf_token(
    careers_url: str,
    session: requests.Session,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> str:
    """Best-effort ``X-Calypso-CSRF-Token`` from the tenant's careers-site page.

    The token is issued by the careers *site* page (``https://<host>/<site>``),
    never by the bare host root, which always answers 406. The CXS jobs API
    currently answers without it; it is echoed when available so a tenant
    that starts enforcing it keeps working. Returns "" on any failure.
    """
    url = careers_url if careers_url.startswith(('http://', 'https://')) else f"https://{careers_url}/"
    try:
        resp = session.get(
            url, timeout=timeout, allow_redirects=True,
            headers={'User-Agent': _BROWSER_USER_AGENT, 'Accept': 'text/html,application/xhtml+xml'},
        )
        token = resp.headers.get("X-Calypso-CSRF-Token", "")
        if not token:
            token = resp.cookies.get("CALYPSO_CSRF_TOKEN", "") or ""
        return token
    except Exception as exc:
        logger.warning("  ⚠️  Could not acquire Workday CSRF token for %s: %s", url, exc)
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
    payload: dict[str, Any],
    headers: dict[str, str],
    max_retries: int,
    timeout: int,
) -> requests.Response:
    """POST one page; a 5xx is retried ``max_retries`` times, anything else returned as-is."""
    response = ngj_http.limited_post(api_url, json=payload, headers=headers, timeout=timeout)
    for attempt in range(max_retries):
        if response.status_code not in _SERVER_ERROR_STATUSES:
            break
        logger.warning(
            "  ⚠️  Workday API error for %s: HTTP %s. Retrying (%s/%s)...",
            company_name, response.status_code, attempt + 1, max_retries,
        )
        time.sleep(_SERVER_ERROR_BACKOFF * (2 ** attempt))
        response = ngj_http.limited_post(api_url, json=payload, headers=headers, timeout=timeout)
    return response


def _to_job(company_name: str, host: str, item: dict[str, Any]) -> dict[str, Any]:
    return {
        'company': company_name,
        'title': item.get('title') or '',
        'location': item.get('locationsText') or '',
        'url': f"https://{host}{item.get('externalPath', '')}",
        'posted_at': item.get('postedOn', ''),
        'source': 'Workday',
        'description': '',  # Not fetched: one extra request per job.
    }


@dataclass(frozen=True)
class _Tenant:
    """Per-company request context shared by every query."""

    company_name: str
    host: str
    api_url: str
    headers: dict[str, str]
    page_limit: int
    max_retries: int
    timeout: int
    # time.monotonic() after which no new page is requested (None: no budget).
    deadline: float | None = None

    def out_of_time(self) -> bool:
        return self.deadline is not None and time.monotonic() >= self.deadline


@dataclass
class _QueryResult:
    """One searchText query's jobs (insertion-ordered, keyed by externalPath)."""

    jobs: dict[str, dict[str, Any]] = field(default_factory=dict)
    raw_count: int = 0
    pages: int = 0
    error: SourceError | None = None
    out_of_time: bool = False


def _page_error(tenant: _Tenant, response: requests.Response) -> SourceError:
    """Turn a non-2xx page into a SourceError (403 also feeds the tenant cooldown)."""
    if response.status_code == 403:
        return ngj_http.record_forbidden(tenant.company_name, SOURCE, tenant.api_url, label="Workday ").errors[0]
    error_body = _extract_error_body(response)
    logger.warning(
        "  ⚠️  Workday API error for %s: HTTP %s — %s", tenant.company_name, response.status_code, error_body,
    )
    if response.status_code == 422:
        return SourceError(
            tenant.company_name, SOURCE, KIND_CONFIG, 422,
            f"HTTP 422: tenant/site not found on this Workday host — check workday_url ({error_body[:120]})",
        )
    return SourceError(
        tenant.company_name, SOURCE, KIND_HTTP, response.status_code,
        f"HTTP {response.status_code}: {error_body[:200]}",
    )


def _job_key(item: dict[str, Any]) -> str:
    return item.get('externalPath') or f"{item.get('title')}|{item.get('locationsText')}"


def _crawl_search(
    tenant: _Tenant,
    search_text: str,
    cap: int,
    title_filter: TitleFilter | None,
) -> _QueryResult:
    """Page one searchText query until it runs out, hits ``cap`` postings, or stops being relevant."""
    result = _QueryResult()
    offset = 0
    while result.raw_count < cap:
        if ngj_http.SOURCE_COOLDOWN.is_tripped(tenant.api_url):
            break  # a sibling query hit the 403 cooldown
        if tenant.out_of_time():
            result.out_of_time = True
            break
        payload = {"appliedFacets": {}, "limit": tenant.page_limit, "offset": offset, "searchText": search_text}
        try:
            response = _post_page(tenant.company_name, tenant.api_url, payload, tenant.headers,
                                  tenant.max_retries, tenant.timeout)
        except requests.exceptions.RequestException as exc:
            # Keep what this query (and the other queries) already collected.
            kind = KIND_TIMEOUT if ngj_http.is_timeout_error(exc) else KIND_NETWORK
            logger.warning("  ⚠️  Workday %s for %s (%r, offset %s): %s",
                           kind, tenant.company_name, search_text, offset, exc)
            result.error = SourceError(tenant.company_name, SOURCE, kind, None, f"{type(exc).__name__}: {exc}")
            break
        result.pages += 1
        if not response.ok:
            result.error = _page_error(tenant, response)
            break

        try:
            items = (response.json() or {}).get('jobPostings') or []
        except ValueError as exc:
            result.error = SourceError(tenant.company_name, SOURCE, KIND_PARSE, response.status_code,
                                       f"invalid JSON: {exc}")
            break
        if not items:
            break
        result.raw_count += len(items)
        for item in items:
            result.jobs.setdefault(_job_key(item), _to_job(tenant.company_name, tenant.host, item))

        if (
            search_text
            and title_filter is not None
            and not any(title_filter(item.get('title') or '') for item in items)
        ):
            break  # keyword results are relevance-ranked: later pages will not do better
        if len(items) < tenant.page_limit:
            break
        offset += tenant.page_limit
    return result


def _run_queries(
    tenant: _Tenant,
    queries: Sequence[tuple[str, int]],
    title_filter: TitleFilter | None,
    workers: int,
) -> list[_QueryResult]:
    """Run the queries (a few at a time for one tenant); results keep query order."""
    if len(queries) == 1 or workers <= 1:
        return [_crawl_search(tenant, text, cap, title_filter) for text, cap in queries]
    with ThreadPoolExecutor(max_workers=min(workers, len(queries))) as executor:
        return list(executor.map(lambda q: _crawl_search(tenant, q[0], q[1], title_filter), queries))


def _fetch_workday_company(
    company: dict[str, str],
    page_limit: int,
    max_total_limit: int,
    max_retries: int,
    timeout: int,
    search_keywords: Sequence[str] = (),
    max_jobs_per_keyword: int = DEFAULT_WORKDAY_MAX_JOBS_PER_KEYWORD,
    title_filter: TitleFilter | None = None,
    keyword_workers: int = DEFAULT_WORKDAY_KEYWORD_WORKERS,
    max_seconds: float | None = None,
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

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': _BROWSER_USER_AGENT,
        }
        csrf_token = get_workday_csrf_token(workday_url, ngj_http.get_session(), timeout=timeout)
        if csrf_token:
            headers['X-Calypso-CSRF-Token'] = csrf_token
        deadline = time.monotonic() + max_seconds if max_seconds else None
        tenant = _Tenant(company_name, host, api_url, headers, page_limit, max_retries, timeout, deadline)

        if search_keywords:
            queries = [(keyword, max_jobs_per_keyword) for keyword in search_keywords]
        else:
            queries = [("", max_total_limit)]  # fetch all, filter locally
        results = _run_queries(tenant, queries, title_filter, keyword_workers)

        merged: dict[str, dict[str, Any]] = {}
        for query in results:
            for key, job in query.jobs.items():
                merged.setdefault(key, job)
        jobs = list(merged.values())
        if len(jobs) >= max_total_limit:
            logger.info("  ℹ️  %s: Reached safety limit of %s jobs. Truncating.", company_name, max_total_limit)
            jobs = jobs[:max_total_limit]

        if any(q.out_of_time for q in results):
            # Slow tenant: keep what the time budget allowed rather than hold up the run.
            logger.info("  ⏱️  %s: %ss Workday time budget used up; keeping %s jobs",
                        company_name, max_seconds, len(jobs))
        raw_count = sum(q.raw_count for q in results)
        errors = tuple(q.error for q in results if q.error is not None)[:1]
        if not errors:
            logger.info(
                "  ✓ Found %s jobs from %s (%s pages, %s queries)",
                len(jobs), company_name, sum(q.pages for q in results), len(queries),
            )
        return SourceResult(jobs=tuple(jobs), raw_count=raw_count, errors=errors)

    except Exception as exc:
        logger.error("  ❌ Error processing %s: %s", company_name, exc)
        return SourceResult.failure(company_name, SOURCE, KIND_UNEXPECTED, f"{type(exc).__name__}: {exc}")


def build_title_prefilter(filtering: dict[str, Any] | None) -> TitleFilter | None:
    """Cheap title-only pre-check mirroring ngj.filters (exclusion + new-grad signal).

    Used only to decide when to stop paging a keyword; the real inclusion gate
    is still ``ngj.filters.filter_jobs`` after deduplication.
    """
    from ngj.filters import (
        DEFAULT_EXCLUSION_SIGNALS,
        DEFAULT_INTERNSHIP_SIGNALS,
        has_new_grad_signal,
        is_title_excluded,
    )

    if not isinstance(filtering, dict):
        return None
    signals = filtering.get('new_grad_signals')
    if not signals:
        return None
    # Internships are treated as exclusions here on purpose: paging Workday for
    # them would cost minutes per run, and near misses are a bonus, not a goal.
    exclusions = (
        list(filtering.get('exclusion_signals', DEFAULT_EXCLUSION_SIGNALS))
        + list(filtering.get('internship_signals', DEFAULT_INTERNSHIP_SIGNALS))
    )

    def passes(title: str) -> bool:
        return not is_title_excluded(title, exclusions) and has_new_grad_signal(title, signals)

    return passes


def _workday_host_key(company: dict[str, str]) -> str:
    """Group key for companies whose requests must not interleave (same host)."""
    try:
        return urlparse(company.get('workday_url') or '').netloc.lower()
    except (TypeError, ValueError):
        return ''


def fetch_workday_jobs(
    companies: Sequence[dict[str, str]],
    page_limit: int | None = None,
    max_total_limit: int | None = None,
    max_retries: int = DEFAULT_POST_RETRIES,
    timeout: int | None = None,
    max_workers: int | None = None,
    search_keywords: Sequence[str] = (),
    max_jobs_per_keyword: int | None = None,
    title_filter: TitleFilter | None = None,
    keyword_workers: int | None = None,
    max_seconds_per_company: float | None = None,
) -> SourceResult:
    """Fetch Workday companies in parallel.

    Companies are grouped by host and each host group runs in one worker, so
    tenants that share a host never interleave their requests on the shared
    session's per-host cookies. Results are merged in config order. One
    company failing never affects the others.

    ``None`` arguments fall back to the module defaults; the pipeline always
    passes the values from :class:`ngj.settings.Settings`.
    """
    page_limit = coerce_positive_int(page_limit, DEFAULT_WORKDAY_PAGE_LIMIT, "page_limit")
    if page_limit > WORKDAY_MAX_PAGE_LIMIT:
        logger.warning("  ⚠️  Workday page_limit=%s exceeds the API maximum; using %s",
                       page_limit, WORKDAY_MAX_PAGE_LIMIT)
        page_limit = WORKDAY_MAX_PAGE_LIMIT
    max_total_limit = coerce_positive_int(max_total_limit, DEFAULT_WORKDAY_MAX_JOBS_PER_COMPANY, "max_total_limit")
    max_workers = coerce_positive_int(max_workers, DEFAULT_WORKDAY_MAX_WORKERS, "max_workers")
    timeout = coerce_positive_int(timeout, DEFAULT_WORKDAY_TIMEOUT, "timeout")
    max_jobs_per_keyword = coerce_positive_int(
        max_jobs_per_keyword, DEFAULT_WORKDAY_MAX_JOBS_PER_KEYWORD, "max_jobs_per_keyword")
    keyword_workers = coerce_positive_int(keyword_workers, DEFAULT_WORKDAY_KEYWORD_WORKERS, "keyword_workers")
    keywords = tuple(dict.fromkeys(k.strip() for k in search_keywords if isinstance(k, str) and k.strip()))

    # host -> [(config index, company)], preserving config order within a host.
    host_groups: dict[str, list[tuple[int, dict[str, str]]]] = {}
    for index, company in enumerate(companies):
        host_groups.setdefault(_workday_host_key(company), []).append((index, company))

    def _fetch_group(group: list[tuple[int, dict[str, str]]]) -> list[tuple[int, SourceResult]]:
        return [
            (index, _fetch_workday_company(
                company, page_limit, max_total_limit, max_retries, timeout,
                keywords, max_jobs_per_keyword, title_filter, keyword_workers, max_seconds_per_company,
            ))
            for index, company in group
        ]

    results: dict[int, SourceResult] = {}
    workers = max(1, min(max_workers, len(host_groups)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_fetch_group, group) for group in host_groups.values()]
        for future in as_completed(futures):
            # _fetch_workday_company catches its own errors, so result() only
            # raises on a programming error — surface it rather than hide it.
            for index, result in future.result():
                results[index] = result

    return SourceResult.merge(results[index] for index in sorted(results))

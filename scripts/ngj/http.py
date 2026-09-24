"""HTTP plumbing shared by every source adapter.

- a pooled ``requests.Session`` created lazily on first use (never at import)
- :class:`DomainConcurrencyLimiter` capping parallel requests per domain
- 403 cooldown glue around ``source_cooldown.SOURCE_COOLDOWN``
- :func:`fetch_json_with_retry`, the one retry loop used by the JSON board
  APIs (Greenhouse, Lever, Ashby)
- :func:`fan_out`, the one thread-pool fan-out used by per-company sources

Adapters call ``limited_get`` / ``limited_post`` through this module
(``ngj_http.limited_get(...)``) so tests can patch ``ngj.http.limited_get``
in one place.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from typing import Any, TypeVar
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ngj.models import (
    KIND_COOLDOWN,
    KIND_FORBIDDEN,
    KIND_HTTP,
    KIND_NETWORK,
    KIND_PARSE,
    KIND_TIMEOUT,
    KIND_UNEXPECTED,
    SourceError,
    SourceResult,
)
from source_cooldown import SOURCE_COOLDOWN, SOURCE_COOLDOWN_THRESHOLD

logger = logging.getLogger(__name__)

T = TypeVar("T")

USER_AGENT = "NewGradJobs-Aggregator/3.0"

# HTTP status codes that should never be retried
NON_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({400, 401, 404, 405, 410, 451})

# HTTP status codes that should be retried
RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({403, 408, 422, 429, 500, 502, 503, 504})

# Seconds to wait before re-trying a failed board-API request.
DEFAULT_RETRY_DELAY = 1.0


def is_retryable_status(status_code: int) -> bool:
    """Classify an HTTP status code as retryable or not."""
    if status_code in RETRYABLE_STATUS_CODES:
        return True
    if status_code in NON_RETRYABLE_STATUS_CODES:
        return False
    return 500 <= status_code < 600


def create_session() -> requests.Session:
    """Create a pooled session with transport-level retries and keep-alive."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.3,  # 0.3s, 0.6s, 1.2s between transport retries
        status_forcelist=[429, 500, 502, 503, 504],  # 422 is handled by source-specific logic.
        allowed_methods=["GET", "POST"],
    )
    # One pool per host; pool_maxsize covers the largest per-host worker pool
    # (Lever/Greenhouse fan-outs) so threads never wait on a free connection.
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=1000,
        pool_maxsize=300,
        pool_block=False,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    # 'br' (Brotli) is intentionally excluded: requests does not decode it
    # natively and some origins (notably Ashby/Cloudflare) prefer it when
    # offered, producing un-parseable bodies.
    session.headers.update({
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Keep-Alive': 'timeout=60, max=2000',
        'User-Agent': USER_AGENT,
    })
    return session


_session: requests.Session | None = None
_session_lock = threading.Lock()


def get_session() -> requests.Session:
    """Return the process-wide session, creating it on first use."""
    global _session
    if _session is None:
        with _session_lock:
            if _session is None:
                _session = create_session()
    return _session


class DomainConcurrencyLimiter:
    """Thread-safe per-domain concurrency limiter.

    Domains with configured limits are guarded by a BoundedSemaphore. Domains
    without explicit limits are left unthrottled.
    """

    def __init__(self, limits: dict[str, int]):
        self._limits = {
            domain.lower(): limit
            for domain, limit in limits.items()
            if isinstance(limit, int) and limit > 0
        }
        self._lock = threading.Lock()
        self._semaphores: dict[str, threading.BoundedSemaphore] = {}

    def _domain_for_url(self, url: str) -> str:
        return (urlparse(url).netloc or "").split(":")[0].lower()

    def _matched_domain(self, domain: str) -> str | None:
        if domain in self._limits:
            return domain
        # Subdomains match their configured parent, e.g. boards-api.greenhouse.io -> greenhouse.io
        for configured_domain in self._limits:
            if domain.endswith(f".{configured_domain}"):
                return configured_domain
        return None

    def _get_semaphore(self, domain: str) -> threading.BoundedSemaphore | None:
        matched_domain = self._matched_domain(domain)
        if matched_domain is None:
            return None
        limit = self._limits[matched_domain]
        with self._lock:
            semaphore = self._semaphores.get(matched_domain)
            if semaphore is None:
                semaphore = threading.BoundedSemaphore(limit)
                self._semaphores[matched_domain] = semaphore
            return semaphore

    @contextmanager
    def acquire(self, url: str) -> Iterator[None]:
        semaphore = self._get_semaphore(self._domain_for_url(url))
        if semaphore is None:
            yield
            return
        semaphore.acquire()
        try:
            yield
        finally:
            semaphore.release()


# Cap Greenhouse API concurrency while leaving other domains unthrottled.
DOMAIN_LIMITER = DomainConcurrencyLimiter({"greenhouse.io": 10})


def limited_get(url: str, **kwargs: Any) -> requests.Response:
    """HTTP GET on the shared session, wrapped with domain concurrency limiting."""
    with DOMAIN_LIMITER.acquire(url):
        return get_session().get(url, **kwargs)


def limited_post(url: str, **kwargs: Any) -> requests.Response:
    """HTTP POST on the shared session, wrapped with domain concurrency limiting."""
    with DOMAIN_LIMITER.acquire(url):
        return get_session().post(url, **kwargs)


# ---------------------------------------------------------------------------
# 403 cooldown glue
# ---------------------------------------------------------------------------

def cooldown_skip(company: str, source: str, url: str) -> SourceResult | None:
    """Return a cooldown SourceResult when ``url``'s domain is tripped, else None."""
    if not SOURCE_COOLDOWN.is_tripped(url):
        return None
    key = SOURCE_COOLDOWN.domain_key(url)
    logger.info("  ⏭️  %s: skipping — source '%s' in cooldown (403 threshold exceeded)", company, key)
    return SourceResult.failure(company, source, KIND_COOLDOWN, f"skipped: '{key}' in 403 cooldown")


def record_forbidden(company: str, source: str, url: str, label: str = "") -> SourceResult:
    """Count a 403 toward the domain cooldown, log it, and return the error result."""
    key = SOURCE_COOLDOWN.domain_key(url)
    if SOURCE_COOLDOWN.try_admit(url):
        count = SOURCE_COOLDOWN.counts().get(key, 0)
        logger.warning("  ⚠️  %s: %s403 Forbidden (%s/%s)", company, label, count, SOURCE_COOLDOWN_THRESHOLD)
    else:
        logger.warning("  🚫 %s: %s403 Forbidden — cooldown now active for '%s'", company, label, key)
    return SourceResult.failure(company, source, KIND_FORBIDDEN, "403 Forbidden", status=403)


# ---------------------------------------------------------------------------
# Shared fetch / retry loop for JSON board APIs
# ---------------------------------------------------------------------------

def fetch_json_with_retry(
    company: str,
    source: str,
    source_label: str,
    url: str,
    parse: Callable[[Any], SourceResult | None],
    *,
    timeout: int,
    max_retries: int = 2,
    retry_delay: float = DEFAULT_RETRY_DELAY,
) -> SourceResult:
    """GET ``url`` and hand the decoded JSON to ``parse`` with retry semantics.

    - Domains in 403 cooldown are skipped without a request.
    - HTTP 403 is counted toward the cooldown and never retried.
    - Non-retryable statuses (see :func:`is_retryable_status`) stop immediately.
    - Timeouts, retryable statuses, transport errors and exceptions raised by
      ``parse`` are retried up to ``max_retries`` times.
    - ``parse`` returning None means "unexpected payload shape" and is retried.

    The final failure is returned as a :class:`SourceError` on the result.
    """
    skipped = cooldown_skip(company, source, url)
    if skipped is not None:
        return skipped

    attempts = max_retries + 1
    last_error: SourceError | None = None

    def error(kind: str, message: str, status: int | None = None) -> SourceError:
        return SourceError(company, source, kind, status, message)

    for attempt in range(attempts):
        try:
            if attempt > 0:
                logger.info("  🔄 Retry %s for %s...", attempt, company)
                time.sleep(retry_delay)

            logger.info("Fetching jobs from %s (%s)...", company, source_label)
            response = limited_get(url, timeout=timeout)

            if response.status_code == 403:
                return record_forbidden(company, source, url)

            response.raise_for_status()
            result = parse(response.json())
            if result is None:
                logger.warning("  ⚠️  %s: Unexpected API response format", company)
                last_error = error(KIND_PARSE, "Unexpected API response format", response.status_code)
                continue

            logger.info("  ✓ Found %s jobs from %s", len(result.jobs), company)
            return result

        except requests.exceptions.Timeout:
            last_error = error(KIND_TIMEOUT, f"timed out after {attempts} attempts (timeout={timeout}s)")
            if attempt < max_retries:
                logger.warning("  ⏱️  %s request timed out, retrying...", company)
                continue
            logger.error("  ❌ %s request timed out after %s attempts", company, attempts)
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            last_error = error(KIND_HTTP, str(exc), status)
            if status is not None and not is_retryable_status(status):
                logger.warning("  ⚠️  %s: HTTP %s (non-retryable)", company, status)
                break
            if attempt < max_retries:
                logger.warning("  ⚠️  Request error for %s: %s, retrying...", company, exc)
                continue
            logger.error("  ❌ Request error for %s after %s attempts: %s", company, attempts, exc)
        except requests.exceptions.RequestException as exc:
            # requests' JSONDecodeError is a RequestException *and* a ValueError.
            kind = KIND_PARSE if isinstance(exc, ValueError) else KIND_NETWORK
            last_error = error(kind, str(exc))
            if attempt < max_retries:
                logger.warning("  ⚠️  Request error for %s: %s, retrying...", company, exc)
                continue
            logger.error("  ❌ Request error for %s after %s attempts: %s", company, attempts, exc)
        except Exception as exc:  # parse() bugs / malformed records: retried, then reported
            last_error = error(KIND_UNEXPECTED, f"{type(exc).__name__}: {exc}")
            if attempt < max_retries:
                logger.warning("  ⚠️  Error fetching from %s: %s, retrying...", company, exc)
                continue
            logger.error("  ❌ Error fetching from %s after %s attempts: %s", company, attempts, exc)

    return SourceResult(errors=(last_error,)) if last_error else SourceResult()


# ---------------------------------------------------------------------------
# Shared thread-pool fan-out
# ---------------------------------------------------------------------------

def fan_out(
    items: Sequence[T],
    fetch_one: Callable[[T], SourceResult],
    *,
    max_workers: int,
    source: str,
    describe: Callable[[T], str],
    label: str,
    noun: str = "companies",
) -> SourceResult:
    """Run ``fetch_one`` over ``items`` in a thread pool and merge the results.

    Results are merged in input order (not completion order) so output is
    deterministic. A worker that raises becomes a ``KIND_UNEXPECTED`` error for
    that item; it never takes the other items down with it.
    """
    total = len(items)
    if total == 0:
        return SourceResult()

    logger.info("\n🚀 Starting PARALLEL %s fetch: %s %s with %s workers", label, total, noun, max_workers)
    results: list[SourceResult | None] = [None] * total
    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
        futures = {executor.submit(fetch_one, item): index for index, item in enumerate(items)}
        for future in as_completed(futures):
            index = futures[future]
            try:
                results[index] = future.result()
            except Exception as exc:
                name = describe(items[index])
                logger.error("  ❌ %s: %s", name, exc)
                results[index] = SourceResult.failure(name, source, KIND_UNEXPECTED, f"{type(exc).__name__}: {exc}")

    merged = SourceResult.merge(r for r in results if r is not None)
    failed = len({e.company for e in merged.errors})
    logger.info(
        "✅ %s parallel fetch complete: %s jobs from %s/%s %s",
        label, len(merged.jobs), total - failed, total, noun,
    )
    return merged

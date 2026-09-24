"""HTTP plumbing shared by every source adapter.

- a pooled ``requests.Session`` created lazily on first use (never at import)
- :class:`DomainConcurrencyLimiter` capping parallel requests per domain
- 403 cooldown glue around ``source_cooldown.SOURCE_COOLDOWN``
- :func:`create_session` with the single retry policy (:class:`CappedRetry`)
- :func:`fetch_json_with_retry`, the shared fetch/parse/error mapping used by
  the JSON board APIs (Greenhouse, Lever, Ashby)
- :func:`fan_out`, the one thread-pool fan-out used by per-company sources

Adapters call ``limited_get`` / ``limited_post`` through this module
(``ngj_http.limited_get(...)``) so tests can patch ``ngj.http.limited_get``
in one place.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from typing import Any, TypeVar
from urllib.parse import urlparse

import requests
import urllib3
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
from source_cooldown import SOURCE_COOLDOWN, SOURCE_COOLDOWN_THRESHOLD  # noqa: F401 (re-exported)

logger = logging.getLogger(__name__)

T = TypeVar("T")

USER_AGENT = "NewGradJobs-Aggregator/3.0"

# ---------------------------------------------------------------------------
# Retry policy — the ONE retry layer for every GET in the scraper.
# ---------------------------------------------------------------------------
# urllib3 retries idempotent GETs on connect/read errors and on these statuses.
# POSTs are never retried here (the Workday adapter gives its idempotent
# search POST a single 5xx retry of its own). Callers must not wrap GET
# requests in their own retry loops: before this was consolidated an adapter
# Retry(total=3) stacked under 3-attempt manual loops sent up to 12 requests
# per URL.
RETRY_TOTAL = 3
RETRY_BACKOFF_FACTOR = 0.5  # sleeps 0s, 1s, 2s between the 4 attempts (urllib3 2.x)
RETRY_STATUS_FORCELIST: tuple[int, ...] = (429, 500, 502, 503, 504)
RETRY_ALLOWED_METHODS: frozenset[str] = frozenset({"GET", "HEAD"})
# A server-sent Retry-After is honoured but never trusted beyond this.
MAX_RETRY_AFTER_SECONDS = 30.0


class CappedRetry(Retry):
    """urllib3 ``Retry`` that clamps ``Retry-After`` to :data:`MAX_RETRY_AFTER_SECONDS`.

    ``Retry.new()`` rebuilds via ``type(self)``, so the clamp survives every
    ``increment()``.
    """

    max_retry_after: float = MAX_RETRY_AFTER_SECONDS

    def get_retry_after(self, response: Any) -> float | None:
        retry_after = super().get_retry_after(response)
        if retry_after is None:
            return None
        return max(0.0, min(float(retry_after), self.max_retry_after))


def build_retry() -> CappedRetry:
    """The shared retry policy (see module constants)."""
    return CappedRetry(
        total=RETRY_TOTAL,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        status_forcelist=RETRY_STATUS_FORCELIST,
        allowed_methods=RETRY_ALLOWED_METHODS,
        respect_retry_after_header=True,
        # Hand the final 429/5xx response back instead of raising RetryError,
        # so callers can report the real status.
        raise_on_status=False,
    )


def create_session() -> requests.Session:
    """Create a pooled session with the single transport-level retry policy."""
    session = requests.Session()
    # One pool per host; pool_maxsize covers the largest per-host worker pool
    # (Lever/Greenhouse fan-outs) so threads never wait on a free connection.
    adapter = HTTPAdapter(
        max_retries=build_retry(),
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
# 25 (was 10) stops the Greenhouse worker pool from queueing on a handful of
# slots — the per-survivor detail fan-out is latency-bound — while staying polite.
GREENHOUSE_CONCURRENCY = 25
DOMAIN_LIMITER = DomainConcurrencyLimiter({"greenhouse.io": GREENHOUSE_CONCURRENCY})


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
    """Return a cooldown SourceResult when ``url``'s tenant/board (or provider) is tripped, else None."""
    key = SOURCE_COOLDOWN.tripped_key(url)
    if key is None:
        return None
    logger.info("  ⏭️  %s: skipping — '%s' in cooldown (403 threshold exceeded)", company, key)
    return SourceResult.failure(company, source, KIND_COOLDOWN, f"skipped: '{key}' in 403 cooldown")


def record_forbidden(company: str, source: str, url: str, label: str = "") -> SourceResult:
    """Count a 403 toward the tenant/board and provider cooldowns, log it, and return the error result."""
    key = SOURCE_COOLDOWN.cooldown_key(url)
    if SOURCE_COOLDOWN.try_admit(url):
        count = SOURCE_COOLDOWN.counts().get(key, 0)
        logger.warning("  ⚠️  %s: %s403 Forbidden (%s/%s)", company, label, count, SOURCE_COOLDOWN.threshold)
    else:
        logger.warning(
            "  🚫 %s: %s403 Forbidden — cooldown now active for '%s'",
            company, label, SOURCE_COOLDOWN.tripped_key(url) or key,
        )
    return SourceResult.failure(company, source, KIND_FORBIDDEN, "403 Forbidden", status=403)


# ---------------------------------------------------------------------------
# Shared fetch for JSON board APIs
# ---------------------------------------------------------------------------

def is_timeout_error(exc: BaseException) -> bool:
    """True for a timeout, including read timeouts that exhausted the urllib3 retries.

    requests maps an exhausted ``MaxRetryError(ReadTimeoutError)`` to a plain
    ``ConnectionError``, so the reason has to be unwrapped.
    """
    if isinstance(exc, requests.exceptions.Timeout):
        return True
    reason = exc.args[0] if exc.args else None
    reason = getattr(reason, "reason", reason)
    # NewConnectionError subclasses ConnectTimeoutError in urllib3 2.x but is
    # a refused/failed connection, not a timeout.
    return isinstance(reason, urllib3.exceptions.TimeoutError) and not isinstance(
        reason, urllib3.exceptions.NewConnectionError)


def fetch_json_with_retry(
    company: str,
    source: str,
    source_label: str,
    url: str,
    parse: Callable[[Any], SourceResult | None],
    *,
    timeout: int,
) -> SourceResult:
    """GET ``url`` once and hand the decoded JSON to ``parse``.

    Transient failures (connect/read errors, 429, 5xx) are retried by the
    session's urllib3 policy (:func:`build_retry`) — this function adds no
    second retry layer. Everything that reaches it is final:

    - a URL whose tenant/board or provider is in 403 cooldown is skipped;
    - HTTP 403 is counted toward the cooldown;
    - any other non-2xx status becomes a ``KIND_HTTP`` error;
    - bad JSON, ``parse`` returning None (unexpected shape) or ``parse``
      raising are deterministic, so they are reported, never retried.

    ``parse`` builds the whole result from one payload and returns it, so a
    failure part-way through cannot leave partial or duplicated jobs behind.
    """
    skipped = cooldown_skip(company, source, url)
    if skipped is not None:
        return skipped

    def failure(kind: str, message: str, status: int | None = None) -> SourceResult:
        return SourceResult(errors=(SourceError(company, source, kind, status, message),))

    logger.info("Fetching jobs from %s (%s)...", company, source_label)
    try:
        response = limited_get(url, timeout=timeout)
    except requests.exceptions.RequestException as exc:
        if is_timeout_error(exc):
            logger.error("  ❌ %s request timed out (timeout=%ss)", company, timeout)
            return failure(KIND_TIMEOUT, f"timed out (timeout={timeout}s, after transport retries)")
        logger.error("  ❌ Request error for %s: %s", company, exc)
        return failure(KIND_NETWORK, str(exc))

    if response.status_code == 403:
        return record_forbidden(company, source, url)
    if not response.ok:
        logger.warning("  ⚠️  %s: HTTP %s", company, response.status_code)
        return failure(KIND_HTTP, f"HTTP {response.status_code} for {url}", response.status_code)

    try:
        data = response.json()
    except ValueError as exc:  # requests' JSONDecodeError is a ValueError
        logger.warning("  ⚠️  %s: response is not JSON: %s", company, exc)
        return failure(KIND_PARSE, f"invalid JSON: {exc}", response.status_code)

    try:
        result = parse(data)
    except Exception as exc:  # malformed records: reported, not retried
        logger.error("  ❌ Error parsing %s: %s", company, exc)
        return failure(KIND_UNEXPECTED, f"{type(exc).__name__}: {exc}", response.status_code)
    if result is None:
        logger.warning("  ⚠️  %s: Unexpected API response format", company)
        return failure(KIND_PARSE, "Unexpected API response format", response.status_code)

    logger.info("  ✓ Found %s jobs from %s", len(result.jobs), company)
    return result


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


TRANSIENT_KINDS = frozenset({KIND_TIMEOUT, KIND_NETWORK})


def retry_transient_failures(
    items: Sequence[T],
    first_pass: SourceResult,
    fetch_one: Callable[[T], SourceResult],
    *,
    describe: Callable[[T], str],
) -> SourceResult:
    """Re-fetch, one at a time, the items whose first attempt timed out or hit a network error.

    Every source fetches concurrently, so the largest boards (Anduril, SpaceX:
    ~2.5 MB lists) can stall past the read timeout under contention even though
    they answer in well under a second on their own. A short sequential second
    pass recovers them. Permanent failures (HTTP 4xx, parse, config) are kept
    as-is and never retried.
    """
    transient = {e.company for e in first_pass.errors if e.kind in TRANSIENT_KINDS}
    retry = [item for item in items if describe(item) in transient]
    if not retry:
        return first_pass

    logger.info("🔁 Retrying %s timed-out item(s) sequentially: %s", len(retry), ", ".join(map(describe, retry)))
    kept = SourceResult(
        jobs=first_pass.jobs,
        errors=tuple(e for e in first_pass.errors if e.company not in transient),
        raw_count=first_pass.raw_count,
    )
    return SourceResult.merge([kept, *(fetch_one(item) for item in retry)])

"""Per-tenant 403 cooldown / circuit-breaker for HTTP fetchers.

Kept as a standalone module (used via ``ngj.http``) so it can be imported
independently and tested in isolation without pulling in the full scraper.

Two breakers run side by side:

- **per tenant/board** (:meth:`SourceCooldownTracker.cooldown_key`) — one
  Workday tenant host, one Greenhouse/Lever/Ashby board. ``threshold`` 403s
  (default 5) from that tenant/board skip it for the rest of the run.
- **per provider** (:meth:`SourceCooldownTracker.domain_key`) — a much higher
  ``provider_threshold`` (default 25) of 403s summed across a provider's
  tenants/boards means the provider itself is blocking us, so every
  tenant/board on it is skipped.

Previously only the provider key existed, so five 403s from five unrelated
Workday tenants disabled all of Workday.

Public API
----------
- :class:`SourceCooldownTracker` — thread-safe 403 counter
- :data:`SOURCE_COOLDOWN_THRESHOLD` — per tenant/board trip threshold (5)
- :data:`SOURCE_COOLDOWN_PROVIDER_THRESHOLD` — provider-wide threshold (25)
- :data:`SOURCE_COOLDOWN` — module-level singleton used by all fetchers
"""

from __future__ import annotations

import logging
import re
import threading
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

__all__ = [
    "SourceCooldownTracker",
    "SOURCE_COOLDOWN_THRESHOLD",
    "SOURCE_COOLDOWN_PROVIDER_THRESHOLD",
    "SOURCE_COOLDOWN",
]

# Second-level labels that form a public suffix together with a two-letter
# country code ("example.co.uk", "example.com.au"). Without this every
# ".co.uk" host would collapse into one "co.uk" provider key.
_SECOND_LEVEL_SUFFIX_LABELS = frozenset({"co", "com", "net", "org", "gov", "ac", "edu", "ne", "or", "go"})

# Multi-tenant hosts where the tenant lives in the URL path, not the hostname:
# (provider domain, regex capturing the board token from the path).
_PATH_TENANT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # boards-api.greenhouse.io/v1/boards/<token>/jobs, api.greenhouse.io/v1/boards/<token>/...
    ("greenhouse.io", re.compile(r"^/v\d+/boards/([^/?#]+)")),
    # boards.greenhouse.io/<token>, job-boards.greenhouse.io/<token>
    ("greenhouse.io", re.compile(r"^/(?!v\d+/)([^/?#]+)")),
    # api.lever.co/v0/postings/<company>
    ("lever.co", re.compile(r"^/v\d+/postings/([^/?#]+)")),
    # jobs.lever.co/<company>
    ("lever.co", re.compile(r"^/(?!v\d+/)([^/?#]+)")),
    # api.ashbyhq.com/posting-api/job-board/<slug>
    ("ashbyhq.com", re.compile(r"^/posting-api/job-board/([^/?#]+)")),
    # jobs.ashbyhq.com/<slug>
    ("ashbyhq.com", re.compile(r"^/(?!posting-api/)([^/?#]+)")),
)


def _split_host_path(url_or_domain: str) -> tuple[str, str]:
    """Return (lower-case host without port, path) for a URL or bare host."""
    s = (url_or_domain or "").strip()
    if s.lower().startswith(("http://", "https://")):
        parsed = urlparse(s)
        return (parsed.netloc or "").split(":")[0].lower(), parsed.path or ""
    host, _, rest = s.partition("/")
    return host.split(":")[0].lower(), ("/" + rest) if rest else ""


class SourceCooldownTracker:
    """Thread-safe per-tenant (+ per-provider) 403 circuit breaker.

    Tracks HTTP 403 responses within a single run. Entirely in-memory; a fresh
    process starts clean. Thread-safe for concurrent fetcher workers.
    Complements :class:`ngj.http.DomainConcurrencyLimiter` (which caps
    parallelism); this class stops fetching from sources actively rejecting us.

    Keys
    ----
    ``cooldown_key`` (tenant/board granularity)::

        https://acme.wd5.myworkdayjobs.com/Careers            → acme.wd5.myworkdayjobs.com
        https://boards-api.greenhouse.io/v1/boards/acme/jobs  → greenhouse.io/acme
        https://api.lever.co/v0/postings/acme                 → lever.co/acme
        https://api.ashbyhq.com/posting-api/job-board/acme    → ashbyhq.com/acme

    ``domain_key`` (provider granularity)::

        goldmansachs.wd5.myworkdayjobs.com → myworkdayjobs.com
        boards-api.greenhouse.io           → greenhouse.io
        careers.example.co.uk              → example.co.uk
    """

    def __init__(self, threshold: int = 5, provider_threshold: int | None = None) -> None:
        if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 1:
            raise ValueError(f"threshold must be a positive integer, got {threshold!r}")
        if provider_threshold is None:
            provider_threshold = threshold * 5
        if (
            isinstance(provider_threshold, bool)
            or not isinstance(provider_threshold, int)
            or provider_threshold < threshold
        ):
            raise ValueError(
                f"provider_threshold must be an integer >= threshold ({threshold}), got {provider_threshold!r}"
            )
        self._threshold = threshold
        self._provider_threshold = provider_threshold
        self._lock = threading.Lock()
        self._counts: dict[str, int] = {}
        self._provider_counts: dict[str, int] = {}
        self._tripped: set[str] = set()

    @property
    def threshold(self) -> int:
        return self._threshold

    @property
    def provider_threshold(self) -> int:
        return self._provider_threshold

    # ------------------------------------------------------------------ keys

    @staticmethod
    def domain_key(url_or_domain: str) -> str:
        """Provider key: the registrable domain of a URL or hostname.

        Keeps the last two labels, or three when the last two form a
        country-code public suffix such as ``co.uk`` / ``com.au``. Returns the
        full host when it has fewer labels than that.
        """
        host, _ = _split_host_path(url_or_domain)
        parts = [p for p in host.split(".") if p]
        if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in _SECOND_LEVEL_SUFFIX_LABELS:
            return ".".join(parts[-3:])
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return host

    @classmethod
    def cooldown_key(cls, url_or_domain: str) -> str:
        """Tenant/board key: the full host, or ``<provider>/<board>`` on shared hosts.

        Greenhouse, Lever and Ashby serve every board from one API host, so
        the board token in the path identifies the tenant there. A bare
        provider URL without a board falls back to the host.
        """
        host, path = _split_host_path(url_or_domain)
        provider = cls.domain_key(host)
        for domain, pattern in _PATH_TENANT_PATTERNS:
            if provider != domain:
                continue
            match = pattern.match(path)
            if match:
                return f"{domain}/{match.group(1).lower()}"
        return host

    # --------------------------------------------------------------- state

    def _tripped_key_locked(self, key: str, provider: str) -> str | None:
        if key in self._tripped:
            return key
        if provider in self._tripped:
            return provider
        return None

    def _record_locked(self, key: str, provider: str) -> bool:
        """Count one 403; return True when this call tripped a breaker."""
        self._counts[key] = self._counts.get(key, 0) + 1
        self._provider_counts[provider] = self._provider_counts.get(provider, 0) + 1
        tripped_now = False
        if self._counts[key] >= self._threshold:
            self._tripped.add(key)
            tripped_now = True
            logger.warning(
                "  🚫 COOLDOWN TRIPPED: '%s' has returned %s 403 responses in this run "
                "— skipping it for remainder of run", key, self._threshold,
            )
        if self._provider_counts[provider] >= self._provider_threshold and provider not in self._tripped:
            self._tripped.add(provider)
            tripped_now = True
            logger.warning(
                "  🚫 COOLDOWN TRIPPED: provider '%s' has returned %s 403 responses across its "
                "tenants — skipping the whole provider for remainder of run", provider, self._provider_threshold,
            )
        return tripped_now

    def try_admit(self, source: str) -> bool:
        """Atomically record a 403 and return whether the source is still admitted.

        Under one lock: an already-tripped tenant/provider returns ``False``
        without counting; otherwise the 403 is counted and ``False`` is
        returned when this call trips either breaker.
        """
        key = self.cooldown_key(source)
        provider = self.domain_key(source)
        with self._lock:
            if self._tripped_key_locked(key, provider) is not None:
                return False
            return not self._record_locked(key, provider)

    def record_403(self, source: str) -> bool:
        """Record one 403; return ``True`` only on the call that trips a breaker.

        .. deprecated:: Prefer :meth:`try_admit` for new call-sites.
        """
        key = self.cooldown_key(source)
        provider = self.domain_key(source)
        with self._lock:
            if self._tripped_key_locked(key, provider) is not None:
                return False
            return self._record_locked(key, provider)

    def tripped_key(self, source: str) -> str | None:
        """The tripped tenant/board or provider key covering ``source``, else None."""
        key = self.cooldown_key(source)
        provider = self.domain_key(source)
        with self._lock:
            return self._tripped_key_locked(key, provider)

    def is_tripped(self, source: str) -> bool:
        """``True`` when ``source``'s tenant/board or its provider is in cooldown."""
        return self.tripped_key(source) is not None

    def counts(self) -> dict[str, int]:
        """Snapshot of 403 counts per tenant/board key (logging and tests only)."""
        with self._lock:
            return dict(self._counts)

    def provider_counts(self) -> dict[str, int]:
        """Snapshot of 403 counts per provider key (logging and tests only)."""
        with self._lock:
            return dict(self._provider_counts)

    def tripped_sources(self) -> set[str]:
        """Snapshot of tripped tenant/board and provider keys (logging and tests only)."""
        with self._lock:
            return set(self._tripped)


# Five 403s from one tenant/board means that tenant is blocking us.
SOURCE_COOLDOWN_THRESHOLD: int = 5
# 25 403s summed across a provider's tenants means the provider is blocking us.
SOURCE_COOLDOWN_PROVIDER_THRESHOLD: int = 25

# Module-level singleton — one tracker per process run, reset on each invocation.
SOURCE_COOLDOWN = SourceCooldownTracker(
    threshold=SOURCE_COOLDOWN_THRESHOLD,
    provider_threshold=SOURCE_COOLDOWN_PROVIDER_THRESHOLD,
)

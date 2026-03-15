"""Per-source 403 cooldown / circuit-breaker for HTTP fetchers.

Extracted from ``update_jobs.py`` so it can be imported independently and
tested in isolation without pulling in the full scraper module.

Public API
----------
- :class:`SourceCooldownTracker` — thread-safe per-domain 403 counter
- :data:`SOURCE_COOLDOWN_THRESHOLD` — default trip threshold (5)
- :data:`SOURCE_COOLDOWN` — module-level singleton used by all fetchers
"""

from __future__ import annotations

import threading
from typing import Dict
from urllib.parse import urlparse

__all__ = ["SourceCooldownTracker", "SOURCE_COOLDOWN_THRESHOLD", "SOURCE_COOLDOWN"]


class SourceCooldownTracker:
    """Thread-safe per-domain 403 circuit breaker for HTTP fetchers.

    Tracks the number of HTTP 403 Forbidden responses received from each domain
    within a single run. Once a domain accumulates ``threshold`` 403 responses it
    is *tripped*: all subsequent requests to any URL sharing that domain are
    skipped for the remainder of the run.

    Design constraints
    ------------------
    - Entirely in-memory and stateless across runs (no files, DB, or external
      cache).  A fresh instance is created at module load; each process run
      starts clean.
    - Thread-safe: safe to call from concurrent fetcher worker threads.
    - Complements :class:`DomainConcurrencyLimiter` (which caps parallelism);
      this class stops fetching when a source is actively rejecting requests.

    Domain key derivation
    ---------------------
    Takes the last two components of the hostname so that subdomains are
    grouped with their parent::

        api.greenhouse.io   → greenhouse.io
        boards-api.greenhouse.io → greenhouse.io
        goldmansachs.wd5.myworkdayjobs.com → myworkdayjobs.com
        careers.google.com  → google.com

    Callers may also pass a plain domain string (``"greenhouse.io"``) or a
    full URL — both are normalised to the same key.
    """

    def __init__(self, threshold: int = 5):
        if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 1:
            raise ValueError(f"threshold must be a positive integer, got {threshold!r}")
        self._threshold = threshold
        self._lock = threading.Lock()
        self._counts: Dict[str, int] = {}
        self._tripped: set = set()

    @staticmethod
    def domain_key(url_or_domain: str) -> str:
        """Derive a stable, normalised domain key from a URL or hostname.

        Maps subdomains to their parent so that counts aggregate correctly
        across the varied sub-hosts used by a single API provider.

        Args:
            url_or_domain: A full URL (``https://api.greenhouse.io/…``) or a
                bare hostname / domain string (``"api.greenhouse.io"``).

        Returns:
            The last two dot-separated components of the host in lower-case,
            e.g. ``"greenhouse.io"``.  Returns the full host if it has fewer
            than two components.
        """
        s = (url_or_domain or "").strip().lower()
        if s.startswith(("http://", "https://")):
            netloc = urlparse(s).netloc or ""
            host = netloc.split(":")[0]
        else:
            host = s.split(":")[0]
        parts = [p for p in host.split(".") if p]
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return host

    def try_admit(self, source: str) -> bool:
        """Atomically record a 403 and return whether the source is still admitted.

        Called when a 403 Forbidden response is received from ``source``.
        Combines :meth:`record_403` and the subsequent :meth:`is_tripped` check
        into a single lock acquisition to eliminate TOCTOU races.

        Under a single lock:
        - If the domain is already tripped → returns ``False`` immediately
          (no state change; no double-count).
        - Otherwise → increments the count.  If the count now reaches the
          threshold, the domain is tripped and ``False`` is returned.
        - Returns ``True`` only if the domain is still below the trip
          threshold after recording this 403 (caller may log a warning and
          continue).

        Args:
            source: URL or domain that returned 403.

        Returns:
            ``True`` if the domain was admitted (count still below threshold);
            ``False`` if the domain is in cooldown (was already tripped, or
            was just tripped by this call).
        """
        key = self.domain_key(source)
        with self._lock:
            if key in self._tripped:
                return False  # already tripped — no state change
            self._counts[key] = self._counts.get(key, 0) + 1
            if self._counts[key] >= self._threshold:
                self._tripped.add(key)
                print(
                    f"  🚫 COOLDOWN TRIPPED: '{key}' has returned {self._threshold} "
                    f"403 responses in this run — skipping for remainder of run"
                )
                return False  # just tripped — not admitted
        return True  # admitted; count still below threshold

    def record_403(self, source: str) -> bool:
        """Record one HTTP 403 response from ``source``.

        Thread-safe.  If this call causes the domain to reach the configured
        threshold, the source is tripped and an explicit log line is emitted.

        .. deprecated::
            Prefer :meth:`try_admit` for new call-sites — it combines the
            record and trip-check in a single lock acquisition.

        Args:
            source: URL or domain that returned 403.

        Returns:
            ``True`` on the exact call that trips the cooldown (threshold just
            reached), ``False`` in all other cases (already tripped, or count
            still below threshold).
        """
        key = self.domain_key(source)
        with self._lock:
            if key in self._tripped:
                return False  # already tripped — no state change
            self._counts[key] = self._counts.get(key, 0) + 1
            if self._counts[key] >= self._threshold:
                self._tripped.add(key)
                print(
                    f"  🚫 COOLDOWN TRIPPED: '{key}' has returned {self._threshold} "
                    f"403 responses in this run — skipping for remainder of run"
                )
                return True
        return False

    def is_tripped(self, source: str) -> bool:
        """Return ``True`` if the source domain is in cooldown for this run.

        Args:
            source: URL or domain to check.

        Returns:
            ``True`` if the cooldown has been tripped for this domain.
        """
        key = self.domain_key(source)
        with self._lock:
            return key in self._tripped

    def counts(self) -> Dict[str, int]:
        """Return a snapshot of the current 403 counts per domain key.

        Intended for logging and test assertions only.
        """
        with self._lock:
            return dict(self._counts)

    def tripped_sources(self) -> set:
        """Return the set of currently tripped domain keys.

        Intended for logging and test assertions only.
        """
        with self._lock:
            return set(self._tripped)


# Default 403 threshold before a source is put into cooldown for the run.
# Five 403s from the same domain indicates the source is actively blocking us,
# not a transient per-company access denial.
SOURCE_COOLDOWN_THRESHOLD: int = 5

# Module-level singleton — one tracker per process run, reset on each invocation.
# Thread-safe; shared across all parallel fetcher workers.
SOURCE_COOLDOWN = SourceCooldownTracker(threshold=SOURCE_COOLDOWN_THRESHOLD)

"""Result types shared by every source adapter.

Each adapter returns a :class:`SourceResult` instead of a bare job list so that
per-company failures (timeouts, 403 cooldowns, bad payloads, ...) travel with
the jobs rather than disappearing into log lines. Health reporting builds on
``SourceResult.errors``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple

# SourceError.kind values. Kept as plain strings so they serialize directly
# into health/report JSON.
KIND_TIMEOUT = "timeout"          # request timed out on every attempt
KIND_HTTP = "http"                # non-2xx status after retries (status set)
KIND_FORBIDDEN = "forbidden"      # HTTP 403; feeds the per-domain cooldown
KIND_COOLDOWN = "cooldown"        # skipped: domain already tripped the 403 cooldown
KIND_NETWORK = "network"          # connection/DNS/other transport error
KIND_PARSE = "parse"              # response body was not the expected shape/JSON
KIND_CONFIG = "config"            # the configured source entry is unusable
KIND_UNAVAILABLE = "unavailable"  # optional dependency missing (e.g. JobSpy)
KIND_UNEXPECTED = "unexpected"    # any other exception

ERROR_KINDS = frozenset({
    KIND_TIMEOUT, KIND_HTTP, KIND_FORBIDDEN, KIND_COOLDOWN, KIND_NETWORK,
    KIND_PARSE, KIND_CONFIG, KIND_UNAVAILABLE, KIND_UNEXPECTED,
})


@dataclass(frozen=True)
class SourceError:
    """One failed fetch for one company (or search task) of one source."""

    company: str
    source: str
    kind: str
    status: Optional[int]
    message: str


@dataclass(frozen=True)
class SourceResult:
    """Jobs fetched from a source plus the per-company errors hit on the way.

    ``raw_count`` is the number of postings the upstream API returned before
    any adapter-side dropping (e.g. JobSpy rows without an http URL).
    """

    jobs: Tuple[Dict[str, Any], ...] = ()
    errors: Tuple[SourceError, ...] = ()
    raw_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors

    @classmethod
    def failure(
        cls,
        company: str,
        source: str,
        kind: str,
        message: str,
        status: Optional[int] = None,
    ) -> "SourceResult":
        return cls(errors=(SourceError(company, source, kind, status, message),))

    @classmethod
    def merge(cls, results: Iterable["SourceResult"]) -> "SourceResult":
        """Concatenate results in iteration order."""
        jobs: list = []
        errors: list = []
        raw_count = 0
        for result in results:
            jobs.extend(result.jobs)
            errors.extend(result.errors)
            raw_count += result.raw_count
        return cls(jobs=tuple(jobs), errors=tuple(errors), raw_count=raw_count)

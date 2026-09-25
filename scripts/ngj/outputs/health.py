"""health.json: run status and count telemetry for monitoring/staleness checks.

Readers: scraper-watchdog.yml (``last_run``), the README badges
(``total_jobs``, ``configured_company_apis``, ``enabled_sources``), the
pipeline's partial-collapse guard (``total_jobs``, ``raw_source_counts``) and
scripts/quality.py. ``source_counts`` is a deprecated alias of
``raw_source_counts`` kept for one release.
"""

from __future__ import annotations

import json
import logging
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ngj.filters import NEAR_MISS_REASONS
from ngj.models import KIND_COOLDOWN, SourceResult
from ngj.registry import configured_company_apis, source_registry

logger = logging.getLogger(__name__)

HEALTH_SCHEMA_VERSION = "1.1"

# A source is "degraded" when more than this share of its configured units
# (companies/boards/queries) failed.
DEGRADED_FAILURE_RATIO = 0.25
MAX_FAILED_COMPANIES_LISTED = 20

REQUIRED_HEALTH_KEYS = frozenset({
    "schema_version", "status", "last_run", "total_jobs", "raw_source_counts", "source_counts",
    "zero_sources", "url_safety_blocked", "run_duration_seconds", "sources",
    "configured_company_apis", "enabled_sources", "active_hiring_companies", "active_sources",
})
HEALTH_STATUSES = frozenset({"ok", "degraded", "failed"})


def compute_display_metrics(
    jobs: Sequence[dict[str, Any]],
    raw_source_counts: Mapping[str, int],
    config: Mapping[str, Any],
) -> dict[str, int]:
    """Canonical count metrics used by the site and README surfaces."""
    registry = source_registry(config)
    active_hiring_companies = len({
        company.strip() for company in (job.get('company') for job in jobs)
        if isinstance(company, str) and company.strip()
    })
    return {
        'configured_company_apis': configured_company_apis(registry),
        'enabled_sources': len(registry),
        'active_hiring_companies': active_hiring_companies,
        'active_sources': sum(1 for count in raw_source_counts.values() if count > 0),
    }


def summarize_source(name: str, result: SourceResult, configured_units: int | None) -> dict[str, Any]:
    """Per-source health: counts, error summary, failure ratio and status."""
    failed = sorted({error.company for error in result.errors if error.company})
    in_cooldown = any(error.kind == KIND_COOLDOWN for error in result.errors)
    if configured_units:
        failure_ratio: float | None = round(min(1.0, len(failed) / configured_units), 3)
    else:
        failure_ratio = None
    degraded = in_cooldown or (failure_ratio is not None and failure_ratio > DEGRADED_FAILURE_RATIO)
    return {
        'jobs': len(result.jobs),
        'raw_count': result.raw_count,
        'configured_units': configured_units,
        'failure_ratio': failure_ratio,
        'in_cooldown': in_cooldown,
        'status': 'degraded' if degraded else 'ok',
        'errors': {
            'count': len(result.errors),
            'by_kind': dict(sorted(Counter(error.kind for error in result.errors).items())),
            'failed_companies': failed[:MAX_FAILED_COMPANIES_LISTED],
            'failed_companies_total': len(failed),
        },
    }


def build_health(
    jobs: Sequence[dict[str, Any]],
    source_results: Mapping[str, SourceResult],
    start_time: float,
    config: Mapping[str, Any],
    url_blocked_count: int = 0,
    now: datetime | None = None,
    near_misses: Sequence[dict[str, Any]] = (),
    corpus_total: int | None = None,
) -> dict[str, Any]:
    """Build the health payload. ``near_misses`` are the jobs-extended.json entries (counted, not judged).

    Status values:
      - failed: total job count is 0
      - degraded: a source returned 0 jobs, a source is in 403 cooldown or had
        more than 25% of its configured units fail, or the publish-time URL
        safety gate blocked one or more jobs
      - ok: otherwise
    """
    registry = source_registry(config)
    raw_source_counts = {name: len(result.jobs) for name, result in source_results.items()}
    sources = {
        name: summarize_source(name, result, registry[name].unit_count if name in registry else None)
        for name, result in source_results.items()
    }
    total_jobs = len(jobs)
    zero_sources = [name for name, count in raw_source_counts.items() if count == 0]
    degraded_sources = [name for name, summary in sources.items() if summary['status'] == 'degraded']
    if total_jobs == 0:
        status = 'failed'
    elif zero_sources or degraded_sources or url_blocked_count:
        status = 'degraded'
    else:
        status = 'ok'

    return {
        'schema_version': HEALTH_SCHEMA_VERSION,
        'status': status,
        'last_run': (now or datetime.now(UTC)).isoformat().replace('+00:00', 'Z'),
        'total_jobs': total_jobs,
        'raw_source_counts': raw_source_counts,
        # Deprecated alias of raw_source_counts; remove after one release.
        'source_counts': dict(raw_source_counts),
        'zero_sources': zero_sources,
        'degraded_sources': degraded_sources,
        'url_safety_blocked': url_blocked_count,
        'run_duration_seconds': round(time.time() - start_time, 1),
        'sources': sources,
        **compute_display_metrics(jobs, raw_source_counts, config),
        'near_miss_jobs': len(near_misses),
        'near_miss_reasons': _near_miss_reason_counts(near_misses),
        # Unique postings seen this run (corpus-index.json), before any rule.
        'corpus_jobs': corpus_total,
    }


def _near_miss_reason_counts(near_misses: Sequence[dict[str, Any]]) -> dict[str, int]:
    counts = dict.fromkeys(NEAR_MISS_REASONS, 0)
    for job in near_misses:
        for reason in (job.get('near_miss') or {}).get('reasons', []):
            if reason in counts:
                counts[reason] += 1
    return counts


def validate_health(payload: Any) -> list[str]:
    """Shape check for health.json (used by scripts/quality.py)."""
    if not isinstance(payload, dict):
        return ["health.json root must be an object"]
    errors = [f"health.json missing key: {key}" for key in sorted(REQUIRED_HEALTH_KEYS - payload.keys())]
    if payload.get('status') not in HEALTH_STATUSES:
        errors.append(f"health.json status must be one of {sorted(HEALTH_STATUSES)}")
    for key in ('total_jobs', 'url_safety_blocked', 'configured_company_apis', 'enabled_sources',
                'active_hiring_companies', 'active_sources'):
        value = payload.get(key)
        if key in payload and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            errors.append(f"health.json {key} must be a non-negative integer")
    counts = payload.get('raw_source_counts')
    if 'raw_source_counts' in payload and not (
        isinstance(counts, dict) and all(isinstance(v, int) and not isinstance(v, bool) for v in counts.values())
    ):
        errors.append("health.json raw_source_counts must map source → integer")
    last_run = payload.get('last_run')
    try:
        datetime.fromisoformat(str(last_run).replace('Z', '+00:00'))
    except ValueError:
        errors.append("health.json last_run must be an ISO 8601 timestamp")
    return errors


def generate_health_json(
    jobs: Sequence[dict[str, Any]],
    source_results: Mapping[str, SourceResult],
    start_time: float,
    config: Mapping[str, Any],
    output_dir: Path,
    url_blocked_count: int = 0,
    near_misses: Sequence[dict[str, Any]] = (),
    corpus_total: int | None = None,
) -> dict[str, Any] | None:
    """Write ``output_dir/health.json``; returns the payload, or None if the write failed.

    ``url_blocked_count`` is the number of jobs dropped by the publish-time URL
    safety gate (scripts/url_safety.py), surfaced so monitoring can alert when
    unsafe links start appearing upstream.
    """
    health = build_health(jobs, source_results, start_time, config, url_blocked_count, near_misses=near_misses,
                          corpus_total=corpus_total)
    health_path = Path(output_dir) / "health.json"
    try:
        health_path.parent.mkdir(parents=True, exist_ok=True)
        health_path.write_text(json.dumps(health, indent=2) + '\n', encoding='utf-8')
    except OSError as exc:
        logger.error("❌ Failed to write health.json: %s", exc)
        return None
    logger.info("🩺 Health report: status=%s, total_jobs=%s", health['status'], health['total_jobs'])
    return health

"""health.json: run status and count telemetry for monitoring/staleness checks."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def compute_display_metrics(
    jobs: Sequence[dict[str, Any]],
    source_counts: Mapping[str, int],
    config: Mapping[str, Any],
) -> dict[str, int]:
    """Canonical count metrics used by the site and README surfaces."""
    apis = config.get('apis', {})
    gh_companies = len(apis.get('greenhouse', {}).get('companies', []))
    lever_companies = len(apis.get('lever', {}).get('companies', []))
    workday_cfg = apis.get('workday', {})
    workday_companies = len(workday_cfg.get('companies', [])) if workday_cfg.get('enabled') else 0
    graphql_cfg = apis.get('graphql', {})
    graphql_sources = len(graphql_cfg.get('sources', [])) if graphql_cfg.get('enabled') else 0

    enabled_sources = sum((
        int(gh_companies > 0),
        int(lever_companies > 0),
        int(bool(workday_cfg.get('enabled')) and len(workday_cfg.get('companies', [])) > 0),
        int(bool(apis.get('google', {}).get('enabled', True)) and len(apis.get('google', {}).get('search_terms', [])) > 0),
        int(bool(apis.get('jobspy', {}).get('enabled', True))),
        int(bool(graphql_cfg.get('enabled')) and len(graphql_cfg.get('sources', [])) > 0),
    ))

    active_hiring_companies = len({
        job.get('company', '').strip()
        for job in jobs
        if isinstance(job.get('company'), str) and job.get('company').strip()
    })

    return {
        'configured_company_apis': gh_companies + lever_companies + workday_companies + graphql_sources,
        'enabled_sources': enabled_sources,
        'active_hiring_companies': active_hiring_companies,
        'active_sources': sum(1 for count in source_counts.values() if count > 0),
    }


def build_health(
    jobs: Sequence[dict[str, Any]],
    source_counts: Mapping[str, int],
    start_time: float,
    config: Mapping[str, Any],
    url_blocked_count: int = 0,
) -> dict[str, Any]:
    """Build the health payload.

    Status values:
      - ok: every source returned jobs and total > 0
      - degraded: at least one source returned 0 jobs, or the publish-time URL
        safety gate blocked one or more jobs
      - failed: total job count is 0
    """
    total_jobs = len(jobs)
    zero_sources = [s for s, c in source_counts.items() if c == 0]
    if total_jobs == 0:
        status = 'failed'
    elif zero_sources or url_blocked_count:
        status = 'degraded'
    else:
        status = 'ok'

    return {
        'status': status,
        'last_run': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
        'total_jobs': total_jobs,
        'source_counts': dict(source_counts),
        'zero_sources': zero_sources,
        'url_safety_blocked': url_blocked_count,
        'run_duration_seconds': round(time.time() - start_time, 1),
        **compute_display_metrics(jobs, source_counts, config),
    }


def generate_health_json(
    jobs: Sequence[dict[str, Any]],
    source_counts: Mapping[str, int],
    start_time: float,
    config: Mapping[str, Any],
    output_dir: Path,
    url_blocked_count: int = 0,
) -> dict[str, Any] | None:
    """Write ``output_dir/health.json``; returns the payload, or None if the write failed.

    ``url_blocked_count`` is the number of jobs dropped by the publish-time URL
    safety gate (scripts/url_safety.py), surfaced so monitoring can alert when
    unsafe links start appearing upstream.
    """
    health = build_health(jobs, source_counts, start_time, config, url_blocked_count)
    health_path = Path(output_dir) / "health.json"
    try:
        health_path.parent.mkdir(parents=True, exist_ok=True)
        health_path.write_text(json.dumps(health, indent=2) + '\n', encoding='utf-8')
    except OSError as exc:
        logger.warning("⚠️  Failed to write health.json: %s", exc)
        return None
    logger.info("🩺 Health report: status=%s, total_jobs=%s", health['status'], health['total_jobs'])
    return health

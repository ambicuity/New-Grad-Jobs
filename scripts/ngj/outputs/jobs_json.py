"""jobs.json payload (public API), jobs-index.json, description shards and the
jobs-extended.json near-miss tier."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from contracts import JOBS_SCHEMA_VERSION, compute_job_id
from ngj.dates import extract_sort_date, get_iso_date
from ngj.filters import NEAR_MISS_REASONS
from ngj.taxonomy import CATEGORY_PATTERNS
from ngj.text import clean_description
from publish import write_extended_artifact, write_site_artifacts

logger = logging.getLogger(__name__)

# Full "About the role" text kept for the lazily loaded description shards.
FULL_DESCRIPTION_CHARS = 50000


def unique_jobs_by_id(jobs: Sequence[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    """(job_id, job) pairs in input order, dropping later jobs whose job_id repeats.

    ngj.dedup keys on the same hash, so a repeat here means a dedup bug; it is
    logged and the first job wins, keeping job_ids unique in the output.
    """
    seen: set[str] = set()
    pairs: list[tuple[str, dict[str, Any]]] = []
    for job in jobs:
        job_id = compute_job_id(job)
        if job_id in seen:
            logger.error("❌ Duplicate job_id %s after dedup (dropped): %s | %s",
                         job_id, job.get('company'), job.get('url'))
            continue
        seen.add(job_id)
        pairs.append((job_id, job))
    return pairs


def sort_jobs_newest_first(jobs: Sequence[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    """Return unique (job_id, job) pairs newest first, ties broken by job_id (ascending).

    Deterministic for identical input; the input sequence is not modified.
    """
    with_ids = sorted(unique_jobs_by_id(jobs), key=lambda pair: pair[0])
    # Stable sort: equal dates keep the job_id order established above.
    return sorted(with_ids, key=lambda pair: extract_sort_date(pair[1]), reverse=True)


def _category_counts(jobs: Sequence[dict[str, Any]]) -> dict[str, int]:
    counts = {category_id: 0 for category_id in CATEGORY_PATTERNS}
    for job in jobs:
        cat_id = (job.get('category') or {}).get('id', 'other')
        counts[cat_id] = counts.get(cat_id, 0) + 1
    return counts


def resolve_first_seen(
    job_id: str,
    job: dict[str, Any],
    previous_first_seen: Mapping[str, str],
    now_iso: str,
) -> str:
    """When this job first appeared on the board.

    Carried forward from the previous run when known. A job the previous run
    did not have is new (``now``) — except when there is no previous
    first-seen data at all (first run, or previous artifacts unavailable),
    where "now" would stamp every job as brand new, so the employer's
    ``posted_at`` (else ``now``) is used instead.
    """
    carried = previous_first_seen.get(job_id)
    if carried:
        return carried
    if previous_first_seen:
        return now_iso
    return get_iso_date(job.get('posted_at')) or now_iso


def _public_job(job_id: str, job: dict[str, Any], first_seen: str) -> dict[str, Any]:
    return {
        'job_id': job_id,
        # Kept for backward compatibility of the public schema; always == job_id.
        'id': job_id,
        'company': job.get('company', ''),
        'title': job.get('title', ''),
        'location': job.get('location', ''),
        'url': job.get('url', ''),
        'posted_at': get_iso_date(job.get('posted_at')),
        'first_seen': first_seen,
        'source': job.get('source', ''),
        'category': job.get('category', {}),
        'company_tier': job.get('company_tier', {}),
        'flags': job.get('flags', {}),
        'is_closed': job.get('is_closed', False),
        'comp': job.get('comp'),
        'description': job.get('description', ''),
    }


def generate_jobs_json(
    jobs: Sequence[dict[str, Any]],
    config: dict[str, Any] | None = None,
    *,
    previous_first_seen: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build the jobs.json payload. ``jobs`` is left untouched (no in-place sort).

    ``meta.categories`` lists every category, zero counts included, so README
    count markers and category sections never go stale. ``config`` is accepted
    for call-site compatibility and currently unused.
    """
    now = now or datetime.now(UTC)
    first_seen_now = get_iso_date(now) or now.isoformat()
    ordered = sort_jobs_newest_first(jobs)
    category_counts = _category_counts([job for _, job in ordered])
    previous_first_seen = previous_first_seen or {}
    return {
        'meta': {
            'schema_version': JOBS_SCHEMA_VERSION,
            'generated_at': now.isoformat(),
            'total_jobs': len(ordered),
            'categories': [
                {
                    'id': cat_id,
                    'name': cat_info['name'],
                    'emoji': cat_info['emoji'],
                    'count': category_counts.get(cat_id, 0),
                }
                for cat_id, cat_info in CATEGORY_PATTERNS.items()
            ],
        },
        'jobs': [
            _public_job(job_id, job, resolve_first_seen(job_id, job, previous_first_seen, first_seen_now))
            for job_id, job in ordered
        ],
    }


def generate_extended_json(
    near_misses: Sequence[dict[str, Any]],
    *,
    previous_first_seen: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build the jobs-extended.json payload: near misses with their reasons, no descriptions.

    Same job shape as jobs.json minus ``description`` (the site loads this file
    only when a "widen scope" toggle is on, so it must stay small), plus
    ``near_miss.reasons``. ``meta.reasons`` counts every reason, zero included.
    """
    now = now or datetime.now(UTC)
    first_seen_now = get_iso_date(now) or now.isoformat()
    ordered = sort_jobs_newest_first(near_misses)
    previous_first_seen = previous_first_seen or {}
    reason_counts = {reason: 0 for reason in NEAR_MISS_REASONS}
    jobs: list[dict[str, Any]] = []
    for job_id, job in ordered:
        reasons = [r for r in (job.get('near_miss') or {}).get('reasons', []) if r in reason_counts]
        for reason in reasons:
            reason_counts[reason] += 1
        public = _public_job(job_id, job, resolve_first_seen(job_id, job, previous_first_seen, first_seen_now))
        del public['description']
        public['near_miss'] = {'reasons': reasons}
        jobs.append(public)
    return {
        'meta': {
            'schema_version': JOBS_SCHEMA_VERSION,
            'tier': 'near_miss',
            'generated_at': now.isoformat(),
            'total_jobs': len(jobs),
            'reasons': reason_counts,
        },
        'jobs': jobs,
    }


def build_full_descriptions(jobs: Sequence[dict[str, Any]]) -> dict[str, str]:
    """Map job_id → full cleaned "About the role" text for the description shards.

    Uses the raw ATS HTML when present, else the published snippet. Kept out of
    jobs.json so the site's first load stays small (see scripts/publish.py).
    """
    texts: dict[str, str] = {}
    for job_id, job in unique_jobs_by_id(jobs):
        desc_html = job.get('description_html') or ''
        text = clean_description(desc_html, max_chars=FULL_DESCRIPTION_CHARS) if desc_html else (
            job.get('description') or '')
        if text:
            texts[job_id] = text
    return texts


def write_jobs_artifacts(
    output_dir: Path,
    jobs_json: dict[str, Any],
    jobs: Sequence[dict[str, Any]],
    extended_json: dict[str, Any] | None = None,
) -> None:
    """Write jobs.json, jobs-index.json, descriptions/<shard>.json and (when given) jobs-extended.json."""
    write_site_artifacts(Path(output_dir), jobs_json, build_full_descriptions(jobs))
    logger.info(
        "jobs.json, jobs-index.json and description shards updated with %s jobs → %s",
        len(jobs_json.get('jobs', [])), output_dir,
    )
    if extended_json is not None:
        write_extended_artifact(Path(output_dir), extended_json)
        logger.info("jobs-extended.json written with %s near misses", extended_json['meta']['total_jobs'])

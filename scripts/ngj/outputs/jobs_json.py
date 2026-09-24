"""jobs.json payload (public API), jobs-index.json and description shards."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from contracts import compute_job_id
from ngj.dates import extract_sort_date, get_iso_date
from ngj.taxonomy import CATEGORY_PATTERNS
from ngj.text import clean_description
from publish import write_site_artifacts

logger = logging.getLogger(__name__)

# Full "About the role" text kept for the lazily loaded description shards.
FULL_DESCRIPTION_CHARS = 50000


def sort_jobs_newest_first(jobs: Sequence[Dict[str, Any]]) -> List[Tuple[str, Dict[str, Any]]]:
    """Return (job_id, job) pairs newest first, ties broken by job_id (ascending).

    Deterministic for identical input; the input sequence is not modified.
    """
    with_ids = sorted(((compute_job_id(job), job) for job in jobs), key=lambda pair: pair[0])
    # Stable sort: equal dates keep the job_id order established above.
    return sorted(with_ids, key=lambda pair: extract_sort_date(pair[1]), reverse=True)


def _category_counts(jobs: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    counts = {category_id: 0 for category_id in CATEGORY_PATTERNS}
    for job in jobs:
        cat_id = job.get('category', {}).get('id', 'other')
        counts[cat_id] = counts.get(cat_id, 0) + 1
    return counts


def _public_job(job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'job_id': job_id,
        'id': job.get('id', ''),
        'company': job.get('company', ''),
        'title': job.get('title', ''),
        'location': job.get('location', ''),
        'url': job.get('url', ''),
        'posted_at': get_iso_date(job.get('posted_at')),
        'source': job.get('source', ''),
        'category': job.get('category', {}),
        'company_tier': job.get('company_tier', {}),
        'flags': job.get('flags', {}),
        'is_closed': job.get('is_closed', False),
        'comp': job.get('comp'),
        'description': job.get('description', ''),
    }


def generate_jobs_json(jobs: Sequence[Dict[str, Any]], config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Build the jobs.json payload. ``jobs`` is left untouched (no in-place sort).

    ``config`` is accepted for call-site compatibility and currently unused.
    """
    category_counts = _category_counts(jobs)
    return {
        'meta': {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'total_jobs': len(jobs),
            'categories': [
                {
                    'id': cat_id,
                    'name': cat_info['name'],
                    'emoji': cat_info['emoji'],
                    'count': category_counts.get(cat_id, 0),
                }
                for cat_id, cat_info in CATEGORY_PATTERNS.items()
                if category_counts.get(cat_id, 0) > 0
            ],
        },
        'jobs': [_public_job(job_id, job) for job_id, job in sort_jobs_newest_first(jobs)],
    }


def build_full_descriptions(jobs: Sequence[Dict[str, Any]]) -> Dict[str, str]:
    """Map job_id → full cleaned "About the role" text for the description shards.

    Uses the raw ATS HTML when present, else the published snippet. Kept out of
    jobs.json so the site's first load stays small (see scripts/publish.py).
    """
    texts: Dict[str, str] = {}
    for job in jobs:
        desc_html = job.get('description_html') or ''
        text = clean_description(desc_html, max_chars=FULL_DESCRIPTION_CHARS) if desc_html else (
            job.get('description') or '')
        if text:
            texts[compute_job_id(job)] = text
    return texts


def write_jobs_artifacts(output_dir: Path, jobs_json: Dict[str, Any], jobs: Sequence[Dict[str, Any]]) -> None:
    """Write jobs.json, jobs-index.json and descriptions/<shard>.json into ``output_dir``."""
    write_site_artifacts(Path(output_dir), jobs_json, build_full_descriptions(jobs))
    logger.info(
        "jobs.json, jobs-index.json and description shards updated with %s jobs → %s",
        len(jobs), output_dir,
    )

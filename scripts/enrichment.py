"""Additive enrichment helpers that do not alter filtering inclusion logic."""

from __future__ import annotations

from typing import Any

try:
    from contracts import compute_job_id
except ModuleNotFoundError:
    from scripts.contracts import compute_job_id


def attach_job_ids(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach stable job_id to each job dictionary (in-place)."""
    for job in jobs:
        if not job.get('job_id'):
            job['job_id'] = compute_job_id(job)
    return jobs

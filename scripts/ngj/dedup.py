"""Duplicate removal across sources."""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def get_job_key(job: Dict[str, Any]) -> str:
    """Generate unique key for job deduplication

    Handles non-string values (NaN, None, float) that may come from JobSpy/pandas.
    """
    def safe_str(value) -> str:
        """Safely convert any value to lowercase string"""
        if value is None:
            return ''
        if isinstance(value, float):
            # Handle NaN and other floats
            if math.isnan(value) or math.isinf(value):
                return ''
            return str(value)
        return str(value).lower().strip()

    company = safe_str(job.get('company', ''))
    title = safe_str(job.get('title', ''))
    url = safe_str(job.get('url', ''))
    return f"{company}|{title}|{url}"


def deduplicate_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate jobs based on company, title, and URL"""
    seen_keys = set()
    unique_jobs = []

    for job in jobs:
        key = get_job_key(job)
        if key not in seen_keys:
            seen_keys.add(key)
            unique_jobs.append(job)

    duplicates_removed = len(jobs) - len(unique_jobs)
    if duplicates_removed > 0:
        logger.info("🔄 Deduplication: Removed %s duplicate jobs", duplicates_removed)

    return unique_jobs

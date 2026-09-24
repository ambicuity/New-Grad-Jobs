"""Contracts and deterministic identifiers for published job artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

JOBS_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class JobPostingContract:
    """Shape contract for jobs.json job entries."""

    schema_version: str
    job_id: str
    id: str
    company: str
    title: str
    location: str
    url: str
    posted_at: str
    source: str
    category: dict[str, Any]
    company_tier: dict[str, Any]
    flags: dict[str, Any]
    is_closed: bool


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _canonical_job_identity(job: dict[str, Any]) -> str:
    canonical_fields = {
        "company": _normalize_text(job.get("company")),
        "title": _normalize_text(job.get("title")),
        "url": _normalize_text(job.get("url")),
        "location": _normalize_text(job.get("location")),
        "source": _normalize_text(job.get("source")),
    }
    return json.dumps(canonical_fields, sort_keys=True, separators=(",", ":"))


def compute_job_id(job: dict[str, Any]) -> str:
    """Compute a stable job identifier from normalized immutable fields."""
    digest = hashlib.sha256(_canonical_job_identity(job).encode("utf-8")).hexdigest()
    return f"job_{digest[:20]}"


def validate_jobs_json_contract(data: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return False, ["jobs artifact root must be an object"]

    meta = data.get("meta")
    jobs = data.get("jobs")
    if not isinstance(meta, dict):
        errors.append("meta must be an object")
    if not isinstance(jobs, list):
        errors.append("jobs must be a list")
        return False, errors

    required_keys = {
        "schema_version",
        "job_id",
        "id",
        "company",
        "title",
        "location",
        "url",
        "posted_at",
        "source",
        "category",
        "company_tier",
        "flags",
        "is_closed",
    }

    for idx, job in enumerate(jobs):
        if not isinstance(job, dict):
            errors.append(f"jobs[{idx}] must be an object")
            continue
        missing = sorted(required_keys - set(job.keys()))
        if missing:
            errors.append(f"jobs[{idx}] missing keys: {', '.join(missing)}")
            continue
        if job.get("schema_version") != JOBS_SCHEMA_VERSION:
            errors.append(f"jobs[{idx}].schema_version must be {JOBS_SCHEMA_VERSION}")
        if not isinstance(job.get("job_id"), str) or not job.get("job_id"):
            errors.append(f"jobs[{idx}].job_id must be a non-empty string")

    if isinstance(meta, dict):
        if meta.get("schema_version") != JOBS_SCHEMA_VERSION:
            errors.append(f"meta.schema_version must be {JOBS_SCHEMA_VERSION}")

    return len(errors) == 0, errors

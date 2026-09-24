"""Contracts and deterministic identifiers for published job artifacts.

``job_id`` is the stable, unique key of a published job. It is derived from
the job's source and its *canonical* posting URL (see :func:`canonical_url`),
so it survives title/location edits and tracking-parameter churn, and it is
the same value the dedup step keys on (ngj.dedup), which is what makes it
unique in the published output. ``id`` is kept in jobs.json for backward
compatibility and always equals ``job_id``.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# 1.1: meta.schema_version added; per-job schema_version dropped; job_id is
# now hash(source, canonical URL) and id == job_id; first_seen added.
JOBS_SCHEMA_VERSION = "1.1"

JOB_ID_PREFIX = "job_"
JOB_ID_HEX_CHARS = 20
JOB_ID_RE = re.compile(rf"^{JOB_ID_PREFIX}[0-9a-f]{{{JOB_ID_HEX_CHARS}}}$")

# Query parameters that identify the posting itself (everything else is
# tracking/UI state and is dropped). Compared case-insensitively.
#   gh_jid        Greenhouse embeds on company career sites (?gh_jid=123)
#   jk / vjk      Indeed view-job key
#   jobid, job_id, jid, id, currentjobid   generic/LinkedIn-style ids
ID_QUERY_PARAMS = frozenset({"gh_jid", "jk", "vjk", "jobid", "job_id", "jid", "id", "currentjobid"})

_DEFAULT_PORTS = {"http": 80, "https": 443}


@dataclass(frozen=True)
class JobPostingContract:
    """Shape contract for jobs.json job entries (required keys)."""

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


REQUIRED_JOB_KEYS = frozenset(JobPostingContract.__dataclass_fields__)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and not math.isfinite(value):  # NaN/inf from pandas/JobSpy
        return ""
    return " ".join(str(value).split()).lower()


def canonical_url(url: Any) -> str:
    """Return a canonical form of a posting URL, or "" when it is not an http(s) URL.

    scheme + lowercased host (default port dropped) + path without a trailing
    slash; the query keeps only posting-id params (:data:`ID_QUERY_PARAMS`,
    sorted); fragment dropped. Path case is preserved (ATS ids are
    case-sensitive).
    """
    if not isinstance(url, str) or not url.strip():
        return ""
    try:
        parts = urlsplit(url.strip())
        port = parts.port
    except ValueError:
        return ""
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").rstrip(".")
    if scheme not in _DEFAULT_PORTS or not host:
        return ""
    netloc = host if port in (None, _DEFAULT_PORTS[scheme]) else f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", parts.path).rstrip("/")
    kept = sorted(
        (key.lower(), value)
        for key, value in parse_qsl(parts.query, keep_blank_values=False)
        if key.lower() in ID_QUERY_PARAMS
    )
    return urlunsplit((scheme, netloc, path, urlencode(kept), ""))


def job_identity(job: dict[str, Any]) -> str:
    """The canonical identity string hashed into ``job_id``.

    ``source`` + canonical URL; when the job has no usable URL, falls back to
    ``source`` + company + title + location.
    """
    source = _normalize_text(job.get("source"))
    url = canonical_url(job.get("url"))
    if url:
        fields: dict[str, str] = {"source": source, "url": url}
    else:
        fields = {
            "source": source,
            "company": _normalize_text(job.get("company")),
            "title": _normalize_text(job.get("title")),
            "location": _normalize_text(job.get("location")),
        }
    return json.dumps(fields, sort_keys=True, separators=(",", ":"))


def compute_job_id(job: dict[str, Any]) -> str:
    """Stable, unique job identifier: ``job_`` + 20 hex chars of sha256(identity)."""
    digest = hashlib.sha256(job_identity(job).encode("utf-8")).hexdigest()
    return f"{JOB_ID_PREFIX}{digest[:JOB_ID_HEX_CHARS]}"


def _validate_job(idx: int, job: Any) -> list[str]:
    if not isinstance(job, dict):
        return [f"jobs[{idx}] must be an object"]
    missing = sorted(REQUIRED_JOB_KEYS - set(job.keys()))
    if missing:
        return [f"jobs[{idx}] missing keys: {', '.join(missing)}"]
    errors: list[str] = []
    job_id = job.get("job_id")
    if not isinstance(job_id, str) or not JOB_ID_RE.match(job_id):
        errors.append(f"jobs[{idx}].job_id must match {JOB_ID_RE.pattern}: {job_id!r}")
    if job.get("id") != job_id:
        errors.append(f"jobs[{idx}].id must equal job_id")
    if not isinstance(job.get("is_closed"), bool):
        errors.append(f"jobs[{idx}].is_closed must be a bool")
    for key in ("category", "company_tier", "flags"):
        if not isinstance(job.get(key), dict):
            errors.append(f"jobs[{idx}].{key} must be an object")
    first_seen = job.get("first_seen")
    if first_seen is not None and not isinstance(first_seen, str):
        errors.append(f"jobs[{idx}].first_seen must be a string or null")
    return errors


def validate_jobs_json_contract(data: Any) -> tuple[bool, list[str]]:
    """Validate a jobs.json payload. Returns ``(ok, errors)``.

    ``meta.schema_version`` carries the schema version (a per-job copy would be
    redundant). Every job needs the :data:`REQUIRED_JOB_KEYS`, a well-formed
    ``job_id`` equal to ``id``, and job_ids must be unique.
    """
    errors: list[str] = []
    if not isinstance(data, dict):
        return False, ["jobs artifact root must be an object"]

    meta = data.get("meta")
    jobs = data.get("jobs")
    if not isinstance(meta, dict):
        errors.append("meta must be an object")
    elif meta.get("schema_version") != JOBS_SCHEMA_VERSION:
        errors.append(f"meta.schema_version must be {JOBS_SCHEMA_VERSION}")
    if not isinstance(jobs, list):
        errors.append("jobs must be a list")
        return False, errors

    for idx, job in enumerate(jobs):
        errors.extend(_validate_job(idx, job))

    counts = Counter(
        job["job_id"] for job in jobs if isinstance(job, dict) and isinstance(job.get("job_id"), str)
    )
    duplicated = sorted(job_id for job_id, n in counts.items() if n > 1)
    if duplicated:
        errors.append(f"duplicate job_id values ({len(duplicated)}): {', '.join(duplicated[:10])}")

    return len(errors) == 0, errors

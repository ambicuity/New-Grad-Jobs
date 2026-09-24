"""Artifact publishing helpers for deterministic pipeline outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Full "About the role" text is split into 16 shards keyed by the first hex
# digit of each job's stable `job_id` (job_<sha256 prefix>). The browser loads
# the slim jobs-index.json up front and fetches one shard only when a job's
# detail pane opens, instead of downloading every description on page load.
DESCRIPTION_SHARD_KEYS: tuple[str, ...] = tuple("0123456789abcdef")
_JOB_ID_PREFIX = "job_"

# Fields left out of jobs-index.json: the list view never renders them.
_INDEX_EXCLUDED_FIELDS = frozenset({"description"})


def write_json_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding='utf-8')


def write_compact_json_artifact(path: Path, payload: dict[str, Any]) -> None:
    """Write minified JSON for browser-fetched payloads (no indentation)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False, sort_keys=False)
    path.write_text(text + "\n", encoding='utf-8')


def description_shard(job_id: str) -> str:
    """Return the shard key ('0'-'f') for a `job_<hex>` identifier."""
    if not isinstance(job_id, str) or not job_id.startswith(_JOB_ID_PREFIX):
        raise ValueError(f"job_id must start with {_JOB_ID_PREFIX!r}: {job_id!r}")
    key = job_id[len(_JOB_ID_PREFIX):len(_JOB_ID_PREFIX) + 1].lower()
    if key not in DESCRIPTION_SHARD_KEYS:
        raise ValueError(f"job_id has no hex digest: {job_id!r}")
    return key


def build_jobs_index(jobs_json: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of jobs.json without fields the list view never shows."""
    return {
        "meta": jobs_json.get("meta", {}),
        "jobs": [
            {k: v for k, v in job.items() if k not in _INDEX_EXCLUDED_FIELDS}
            for job in jobs_json.get("jobs", [])
        ],
    }


def build_description_shards(descriptions: dict[str, str]) -> dict[str, dict[str, str]]:
    """Group job_id → text into every shard (empty shards included, keys sorted)."""
    grouped: dict[str, dict[str, str]] = {key: {} for key in DESCRIPTION_SHARD_KEYS}
    for job_id in sorted(descriptions):
        text = descriptions[job_id]
        if text:
            grouped[description_shard(job_id)][job_id] = text
    return grouped


def write_site_artifacts(
    docs_dir: Path,
    jobs_json: dict[str, Any],
    descriptions: dict[str, str],
) -> None:
    """Write jobs.json (public API), jobs-index.json and descriptions/<shard>.json."""
    docs_dir = Path(docs_dir)
    write_json_artifact(docs_dir / "jobs.json", jobs_json)
    write_compact_json_artifact(docs_dir / "jobs-index.json", build_jobs_index(jobs_json))
    for key, shard in build_description_shards(descriptions).items():
        write_compact_json_artifact(docs_dir / "descriptions" / f"{key}.json", shard)

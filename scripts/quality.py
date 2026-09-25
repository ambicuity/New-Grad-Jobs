"""Integrity checks for the generated publishing artifacts.

:func:`run_integrity_checks` validates one output dir (see
ngj.settings.resolve_output_dir) as a whole:

- jobs.json: parses, passes the contract (contracts.validate_jobs_json_contract:
  meta.schema_version, required keys, id == job_id, unique job_ids) and
  ``meta.total_jobs`` matches the job list;
- jobs-index.json: parses, same count and the same job_ids in the same order,
  no ``description`` field;
- descriptions/<0-f>.json: every shard present; every job with a description
  snippet has full text in the shard its job_id maps to (publish.description_shard);
  no text in the wrong shard or for an unpublished job;
- every published URL passes url_safety.is_safe_url;
- feed.xml and feeds/<slug>.xml: well-formed RSS 2.0 (channel title/link/description, items with
  title/link/guid), item guids are published job_ids;
- health.json: shape (ngj.outputs.health.validate_health) and its total_jobs
  matches jobs.json.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from contracts import JOBS_SCHEMA_VERSION, REQUIRED_JOB_KEYS, validate_jobs_json_contract
from ngj.filters import NEAR_MISS_REASONS
from ngj.outputs.health import validate_health
from ngj.outputs.rss import feed_variants
from publish import DESCRIPTION_SHARD_KEYS, description_shard
from url_safety import is_safe_url

MAX_LISTED = 10


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _load_json(path: Path, errors: list[str]) -> Any:
    """Parsed JSON, or None (with an error recorded) when missing/invalid."""
    if not path.exists():
        errors.append(f"missing {path.name}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"{path.name} invalid JSON: {getattr(exc, 'msg', exc)}")
        return None


def _listed(items: list[str]) -> str:
    extra = f" (+{len(items) - MAX_LISTED} more)" if len(items) > MAX_LISTED else ""
    return ", ".join(items[:MAX_LISTED]) + extra


def _job_ids(jobs: list[Any]) -> list[str]:
    return [job["job_id"] for job in jobs if isinstance(job, dict) and isinstance(job.get("job_id"), str)]


def check_jobs_json(payload: Any) -> list[str]:
    ok, contract_errors = validate_jobs_json_contract(payload)
    errors = [] if ok else [f"jobs contract: {e}" for e in contract_errors]
    if isinstance(payload, dict) and isinstance(payload.get("jobs"), list) and isinstance(payload.get("meta"), dict):
        total = payload["meta"].get("total_jobs")
        if total != len(payload["jobs"]):
            errors.append(f"jobs count mismatch: meta.total_jobs={total} != len(jobs)={len(payload['jobs'])}")
    return errors


def check_jobs_index(index: Any, jobs: list[Any]) -> list[str]:
    if not isinstance(index, dict) or not isinstance(index.get("jobs"), list):
        return ["jobs-index.json must be an object with a jobs list"]
    errors: list[str] = []
    index_jobs = index["jobs"]
    if len(index_jobs) != len(jobs):
        errors.append(f"jobs-index count mismatch: {len(index_jobs)} != jobs.json {len(jobs)}")
    if (index.get("meta") or {}).get("total_jobs") != len(jobs):
        errors.append("jobs-index meta.total_jobs does not match jobs.json")
    if _job_ids(index_jobs) != _job_ids(jobs):
        errors.append("jobs-index job_ids differ from jobs.json (set or order)")
    if any(isinstance(job, dict) and "description" in job for job in index_jobs):
        errors.append("jobs-index.json must not carry description")
    return errors


def check_description_shards(shard_dir: Path, jobs: list[Any]) -> list[str]:
    errors: list[str] = []
    placed: dict[str, str] = {}
    for key in DESCRIPTION_SHARD_KEYS:
        shard = _load_json(shard_dir / f"{key}.json", errors)
        if shard is None:
            continue
        if not isinstance(shard, dict):
            errors.append(f"descriptions/{key}.json must be an object")
            continue
        for job_id in shard:
            placed[job_id] = key
    if errors:
        return [e.replace("missing ", "missing descriptions/") for e in errors]

    published = set(_job_ids(jobs))
    misplaced = sorted(
        job_id for job_id, key in placed.items()
        if job_id in published and description_shard(job_id) != key
    )
    orphans = sorted(job_id for job_id in placed if job_id not in published)
    missing = sorted(
        job["job_id"] for job in jobs
        if isinstance(job, dict) and job.get("description") and job.get("job_id") not in placed
    )
    if misplaced:
        errors.append(f"descriptions in the wrong shard: {_listed(misplaced)}")
    if orphans:
        errors.append(f"descriptions for unpublished job_ids: {_listed(orphans)}")
    if missing:
        errors.append(f"jobs with a description snippet but no shard text: {_listed(missing)}")
    return errors


def check_urls(jobs: list[Any]) -> list[str]:
    unsafe = [
        str(job.get("job_id")) for job in jobs
        if isinstance(job, dict) and not is_safe_url(str(job.get("url") or ""))
    ]
    return [f"unsafe or missing URLs: {_listed(unsafe)}"] if unsafe else []


def _missing_children(element: ET.Element, names: tuple[str, ...]) -> list[str]:
    return [name for name in names if not (element.findtext(name) or "").strip()]


def check_feed(feed_path: Path, jobs: list[Any]) -> list[str]:
    if not feed_path.exists():
        return ["missing feed.xml"]
    try:
        root = ET.parse(feed_path).getroot()
    except ET.ParseError as exc:
        return [f"feed.xml is not well-formed XML: {exc}"]
    if root.tag != "rss" or root.get("version") != "2.0":
        return ["feed.xml root must be <rss version=\"2.0\">"]
    channel = root.find("channel")
    if channel is None:
        return ["feed.xml has no <channel>"]
    errors = [f"feed.xml channel missing <{name}>" for name in _missing_children(channel, ("title", "link", "description"))]
    published = set(_job_ids(jobs))
    guids: list[str] = []
    for index, item in enumerate(channel.findall("item")):
        missing = _missing_children(item, ("title", "link", "guid"))
        if missing:
            errors.append(f"feed.xml item {index} missing {', '.join(missing)}")
        guids.append((item.findtext("guid") or "").strip())
    unknown = sorted({g for g in guids if g and g not in published})
    if unknown:
        errors.append(f"feed.xml guids not in jobs.json: {_listed(unknown)}")
    repeated = sorted(g for g, n in Counter(guids).items() if g and n > 1)
    if repeated:
        errors.append(f"feed.xml duplicate guids: {_listed(repeated)}")
    return errors


def check_extended(path: Path, curated_jobs: list[Any]) -> list[str]:
    """jobs-extended.json (near-miss tier): optional, but when present it must be sound.

    Every entry needs the jobs.json required keys (minus description, which
    must be absent), unique ids that never overlap the curated set, and one or
    more known near-miss reasons.
    """
    if not path.exists():
        return []
    errors: list[str] = []
    payload = _load_json(path, errors)
    if payload is None:
        return errors
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        return ["jobs-extended.json must be an object with a jobs list"]
    jobs = payload["jobs"]
    if (payload.get("meta") or {}).get("total_jobs") != len(jobs):
        errors.append("jobs-extended meta.total_jobs does not match its jobs list")
    curated_ids = set(_job_ids(curated_jobs))
    seen: set[str] = set()
    for index, job in enumerate(jobs):
        if not isinstance(job, dict):
            errors.append(f"jobs-extended job {index} is not an object")
            continue
        missing = sorted((REQUIRED_JOB_KEYS - {"description"}) - job.keys())
        if missing:
            errors.append(f"jobs-extended job {index} missing keys: {', '.join(missing)}")
        if "description" in job:
            errors.append(f"jobs-extended job {index} must not carry description")
        job_id = job.get("job_id")
        if isinstance(job_id, str):
            if job_id in seen:
                errors.append(f"jobs-extended duplicate job_id: {job_id}")
            if job_id in curated_ids:
                errors.append(f"jobs-extended overlap with jobs.json: {job_id}")
            seen.add(job_id)
        reasons = (job.get("near_miss") or {}).get("reasons") if isinstance(job.get("near_miss"), dict) else None
        if not isinstance(reasons, list) or not reasons:
            errors.append(f"jobs-extended job {index} has no near-miss reasons")
        else:
            for reason in reasons:
                if reason not in NEAR_MISS_REASONS:
                    errors.append(f"jobs-extended job {index} unknown near-miss reason: {reason!r}")
        url = job.get("url")
        if isinstance(url, str) and url and not is_safe_url(url):
            errors.append(f"jobs-extended job {index} unsafe url: {url}")
    return errors


def check_feeds_dir(feeds_dir: Path, jobs: list[Any]) -> list[str]:
    """Every sliced feed under ``feeds/`` must pass the same checks as feed.xml, and the slices must exist."""
    errors: list[str] = []
    expected = [feeds_dir / f"{variant.slug}.xml" for variant in feed_variants(jobs)]
    for path in expected:
        for error in check_feed(path, jobs):
            errors.append(error.replace("feed.xml", f"feeds/{path.name}", 1))
    return errors


def check_health(health: Any, jobs: list[Any]) -> list[str]:
    errors = validate_health(health)
    if isinstance(health, dict):
        total = health.get("total_jobs")
        if isinstance(total, int) and total != len(jobs):
            errors.append(f"health total mismatch: health.total_jobs={total} != len(jobs)={len(jobs)}")
    return errors


def run_integrity_checks(artifacts_dir: Path) -> tuple[bool, dict[str, Any]]:
    """Validate every artifact in ``artifacts_dir``. Returns ``(ok, report)``."""
    artifacts_dir = Path(artifacts_dir)
    errors: list[str] = []
    report: dict[str, Any] = {
        "status": "ok",
        "checked_at": _utc_now(),
        "artifacts_dir": str(artifacts_dir),
        "errors": errors,
        "warnings": [],
        "schema_versions": {"jobs": JOBS_SCHEMA_VERSION},
    }

    jobs_payload = _load_json(artifacts_dir / "jobs.json", errors)
    if jobs_payload is not None:
        errors.extend(check_jobs_json(jobs_payload))
    raw_jobs = jobs_payload.get("jobs") if isinstance(jobs_payload, dict) else None
    jobs: list[Any] = raw_jobs if isinstance(raw_jobs, list) else []
    report["total_jobs"] = len(jobs)

    health = _load_json(artifacts_dir / "health.json", errors)
    if health is not None:
        errors.extend(check_health(health, jobs))

    if jobs_payload is not None:
        index = _load_json(artifacts_dir / "jobs-index.json", errors)
        if index is not None:
            errors.extend(check_jobs_index(index, jobs))
        errors.extend(check_description_shards(artifacts_dir / "descriptions", jobs))
        errors.extend(check_urls(jobs))
        errors.extend(check_feed(artifacts_dir / "feed.xml", jobs))
        errors.extend(check_feeds_dir(artifacts_dir / "feeds", jobs))
        errors.extend(check_extended(artifacts_dir / "jobs-extended.json", jobs))

    if errors:
        report["status"] = "failed"
    elif report["warnings"]:
        report["status"] = "degraded"
    return report["status"] != "failed", report

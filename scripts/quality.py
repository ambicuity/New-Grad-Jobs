"""Integrity and liveness quality helpers for publishing artifacts."""

from __future__ import annotations

import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover - exercised via request-free integrity runs
    requests = None

try:
    from contracts import JOBS_SCHEMA_VERSION, EVALUATIONS_SCHEMA_VERSION, validate_evaluations_contract, validate_jobs_json_contract
except ModuleNotFoundError:
    from scripts.contracts import JOBS_SCHEMA_VERSION, EVALUATIONS_SCHEMA_VERSION, validate_evaluations_contract, validate_jobs_json_contract

DEAD_URL_PATTERNS = (
    r"\b(position\s+closed|job\s+closed|no\s+longer\s+accepting|expired)\b",
    r"\b404\b",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_private_or_invalid_host(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return True

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return True
    if hostname in {"localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254"}:
        return True
    return hostname.startswith(("10.", "192.168.", "172."))


def _looks_dead_from_text(text: str) -> bool:
    lowered = (text or "").lower()
    return any(re.search(pattern, lowered) for pattern in DEAD_URL_PATTERNS)


def run_liveness_checks(
    jobs: list[dict[str, Any]],
    sample_pct: float = 0.05,
    max_checks: int = 50,
    timeout: int = 4,
    retries: int = 1,
    session: Any | None = None,
) -> dict[str, Any]:
    """Sample URL liveness checks; always non-blocking and telemetry-only."""
    telemetry = {
        "liveness_state": "ok",
        "sample_size": 0,
        "checked": 0,
        "failed": 0,
        "failure_rate": 0.0,
        "last_checked_at": _utc_now(),
    }

    if not jobs:
        telemetry["liveness_state"] = "unavailable"
        telemetry["reason"] = "no_jobs"
        return telemetry

    sample_size = min(max_checks, max(1, int(len(jobs) * sample_pct)))
    sample = random.sample(jobs, min(sample_size, len(jobs)))
    telemetry["sample_size"] = len(sample)
    if session is not None:
        http = session
    elif requests is not None:
        http = requests.Session()
    else:
        telemetry["liveness_state"] = "unavailable"
        telemetry["reason"] = "requests_not_installed"
        return telemetry

    for job in sample:
        url = str(job.get("url") or "").strip()
        if not url.startswith("http") or _is_private_or_invalid_host(url):
            continue

        telemetry["checked"] += 1
        is_dead = True

        for _ in range(max(retries, 0) + 1):
            try:
                resp = http.get(url, timeout=timeout, allow_redirects=True)
                content_type = (resp.headers.get("Content-Type") or "").lower()
                text_for_heuristics = ""
                if "text/html" in content_type:
                    text_for_heuristics = resp.text[:2000]

                if resp.status_code < 400 and not _looks_dead_from_text(text_for_heuristics):
                    is_dead = False
                    break
            except Exception:
                continue

        job["url_verified"] = not is_dead
        if is_dead:
            telemetry["failed"] += 1

    checked = telemetry["checked"]
    failed = telemetry["failed"]
    telemetry["failure_rate"] = round((failed / checked), 4) if checked else 0.0

    if checked == 0:
        telemetry["liveness_state"] = "unavailable"
        telemetry["reason"] = "no_valid_urls_in_sample"
    elif telemetry["failure_rate"] >= 0.5:
        telemetry["liveness_state"] = "degraded"

    return telemetry


def load_evaluation_telemetry(evaluations_path: Path) -> dict[str, Any]:
    base = {
        "evaluation_state": "unavailable",
        "evaluation_last_checked_at": _utc_now(),
        "evaluation_count": 0,
        "evaluation_reason": "artifact_missing",
    }

    if not evaluations_path.exists():
        return base

    try:
        payload = json.loads(evaluations_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        base["evaluation_state"] = "degraded"
        base["evaluation_reason"] = f"invalid_json: {exc.msg}"
        return base

    ok, errors = validate_evaluations_contract(payload)
    if not ok:
        base["evaluation_state"] = "degraded"
        base["evaluation_reason"] = "; ".join(errors[:3])
        return base

    evaluations = payload.get("evaluations", [])
    base["evaluation_state"] = "ok"
    base["evaluation_reason"] = "ready"
    base["evaluation_count"] = len(evaluations)
    base["evaluation_last_checked_at"] = payload.get("generated_at") or _utc_now()
    return base


def run_integrity_checks(repo_root: Path) -> tuple[bool, dict[str, Any]]:
    """Validate artifact existence, contracts, and cross-artifact consistency."""
    docs_dir = repo_root / "docs"
    jobs_path = docs_dir / "jobs.json"
    health_path = docs_dir / "health.json"
    evaluations_path = docs_dir / "job-evaluations.json"

    report: dict[str, Any] = {
        "status": "ok",
        "checked_at": _utc_now(),
        "errors": [],
        "warnings": [],
        "schema_versions": {
            "jobs": JOBS_SCHEMA_VERSION,
            "evaluations": EVALUATIONS_SCHEMA_VERSION,
        },
    }

    if not jobs_path.exists():
        report["errors"].append("missing docs/jobs.json")
        report["status"] = "failed"
        return False, report
    if not health_path.exists():
        report["errors"].append("missing docs/health.json")
        report["status"] = "failed"
        return False, report

    try:
        jobs_payload = json.loads(jobs_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report["errors"].append(f"docs/jobs.json invalid JSON: {exc.msg}")
        report["status"] = "failed"
        return False, report

    ok_jobs, job_errors = validate_jobs_json_contract(jobs_payload)
    if not ok_jobs:
        report["errors"].extend([f"jobs contract: {e}" for e in job_errors])

    jobs = jobs_payload.get("jobs", []) if isinstance(jobs_payload, dict) else []
    meta = jobs_payload.get("meta", {}) if isinstance(jobs_payload, dict) else {}
    if isinstance(meta, dict):
        total_jobs = meta.get("total_jobs")
        if isinstance(total_jobs, int) and total_jobs != len(jobs):
            report["errors"].append(
                f"jobs count mismatch: meta.total_jobs={total_jobs} != len(jobs)={len(jobs)}"
            )

    try:
        health_payload = json.loads(health_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report["errors"].append(f"docs/health.json invalid JSON: {exc.msg}")
        health_payload = {}

    if isinstance(health_payload, dict):
        health_total = health_payload.get("total_jobs")
        if isinstance(health_total, int) and health_total != len(jobs):
            report["errors"].append(
                f"health total mismatch: health.total_jobs={health_total} != len(jobs)={len(jobs)}"
            )

    if evaluations_path.exists():
        try:
            eval_payload = json.loads(evaluations_path.read_text(encoding="utf-8"))
            ok_eval, eval_errors = validate_evaluations_contract(eval_payload)
            if not ok_eval:
                report["warnings"].extend([f"evaluations contract: {e}" for e in eval_errors])
        except json.JSONDecodeError as exc:
            report["warnings"].append(f"docs/job-evaluations.json invalid JSON: {exc.msg}")

    if report["errors"]:
        report["status"] = "failed"
    elif report["warnings"]:
        report["status"] = "degraded"

    return report["status"] != "failed", report

"""Integrity checks for the generated publishing artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contracts import JOBS_SCHEMA_VERSION, validate_jobs_json_contract


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_integrity_checks(artifacts_dir: Path) -> tuple[bool, dict[str, Any]]:
    """Validate artifact existence, contracts, and cross-artifact consistency.

    ``artifacts_dir`` is the pipeline output dir holding jobs.json and
    health.json (see ngj.settings.resolve_output_dir).
    """
    artifacts_dir = Path(artifacts_dir)
    jobs_path = artifacts_dir / "jobs.json"
    health_path = artifacts_dir / "health.json"

    report: dict[str, Any] = {
        "status": "ok",
        "checked_at": _utc_now(),
        "errors": [],
        "warnings": [],
        "schema_versions": {"jobs": JOBS_SCHEMA_VERSION},
    }

    if not jobs_path.exists():
        report["errors"].append("missing jobs.json")
        report["status"] = "failed"
        return False, report
    if not health_path.exists():
        report["errors"].append("missing health.json")
        report["status"] = "failed"
        return False, report

    try:
        jobs_payload = json.loads(jobs_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report["errors"].append(f"jobs.json invalid JSON: {exc.msg}")
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
        report["errors"].append(f"health.json invalid JSON: {exc.msg}")
        health_payload = {}

    if isinstance(health_payload, dict):
        health_total = health_payload.get("total_jobs")
        if isinstance(health_total, int) and health_total != len(jobs):
            report["errors"].append(
                f"health total mismatch: health.total_jobs={health_total} != len(jobs)={len(jobs)}"
            )

    if report["errors"]:
        report["status"] = "failed"
    elif report["warnings"]:
        report["status"] = "degraded"

    return report["status"] != "failed", report

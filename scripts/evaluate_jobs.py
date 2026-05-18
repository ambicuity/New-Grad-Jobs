#!/usr/bin/env python3
"""Optional non-gating evaluation sidecar for job scoring."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from contracts import (
        EVALUATIONS_SCHEMA_VERSION,
        EVALUATION_PROMPT_VERSION,
        compute_input_hash,
        new_evaluation_id,
        validate_jobs_json_contract,
    )
except ModuleNotFoundError:
    from scripts.contracts import (
        EVALUATIONS_SCHEMA_VERSION,
        EVALUATION_PROMPT_VERSION,
        compute_input_hash,
        new_evaluation_id,
        validate_jobs_json_contract,
    )

MODEL_NAME = "heuristic-ranker-v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_eligible(job: dict[str, Any]) -> bool:
    if job.get("is_closed"):
        return False
    if not str(job.get("job_id") or "").strip():
        return False
    if not str(job.get("url") or "").strip().startswith("http"):
        return False
    return True


def _score_job(job: dict[str, Any]) -> tuple[float, float, list[str]]:
    """Return (score_overall, confidence, reason_codes)."""
    score = 50.0
    confidence = 0.55
    reasons: list[str] = []

    title = str(job.get("title") or "").lower()
    location = str(job.get("location") or "").lower()
    tier = str((job.get("company_tier") or {}).get("tier") or "")
    category = str((job.get("category") or {}).get("id") or "")

    if "new grad" in title or "early career" in title:
        score += 20
        confidence += 0.1
        reasons.append("explicit_new_grad_signal")

    if any(token in title for token in ("software engineer", "machine learning", "data engineer")):
        score += 10
        reasons.append("core_track_signal")

    if tier in {"faang_plus", "unicorn"}:
        score += 8
        reasons.append("high_signal_company_tier")

    if "remote" in location:
        score += 4
        reasons.append("remote_friendly")

    if category in {"software_engineering", "data_ml", "data_engineering", "infrastructure_sre"}:
        score += 6
        reasons.append("target_category")

    score = max(0.0, min(100.0, round(score, 1)))
    confidence = max(0.0, min(1.0, round(confidence, 2)))
    return score, confidence, reasons


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    jobs_path = repo_root / "docs" / "jobs.json"
    output_path = repo_root / "docs" / "job-evaluations.json"

    if not jobs_path.exists():
        raise FileNotFoundError("docs/jobs.json is required before running evaluate_jobs.py")

    payload = json.loads(jobs_path.read_text(encoding="utf-8"))
    ok, errors = validate_jobs_json_contract(payload)
    if not ok:
        raise ValueError("jobs artifact failed contract validation: " + "; ".join(errors[:5]))

    jobs = payload.get("jobs", [])
    now = _utc_now()
    evaluations: list[dict[str, Any]] = []

    for job in jobs:
        if not _is_eligible(job):
            continue

        input_payload = {
            "job_id": job.get("job_id"),
            "title": job.get("title"),
            "company": job.get("company"),
            "location": job.get("location"),
            "category": (job.get("category") or {}).get("id"),
            "company_tier": (job.get("company_tier") or {}).get("tier"),
            "posted_at": job.get("posted_at"),
        }
        input_hash = compute_input_hash(input_payload)
        score, confidence, reasons = _score_job(job)

        scored_at = _utc_now()
        evaluations.append(
            {
                "schema_version": EVALUATIONS_SCHEMA_VERSION,
                "evaluation_id": new_evaluation_id(str(job.get("job_id")), scored_at),
                "job_id": job.get("job_id"),
                "score_overall": score,
                "confidence": confidence,
                "scores": {
                    "relevance": score,
                },
                "model": MODEL_NAME,
                "prompt_version": EVALUATION_PROMPT_VERSION,
                "scored_at": scored_at,
                "input_hash": input_hash,
                "reason_codes": reasons,
            }
        )

    artifact = {
        "schema_version": EVALUATIONS_SCHEMA_VERSION,
        "generated_at": now,
        "model": MODEL_NAME,
        "prompt_version": EVALUATION_PROMPT_VERSION,
        "meta": {
            "total_jobs": len(jobs),
            "eligible_jobs": len([job for job in jobs if _is_eligible(job)]),
            "evaluated_jobs": len(evaluations),
        },
        "evaluations": evaluations,
    }

    output_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output_path} with {len(evaluations)} evaluations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

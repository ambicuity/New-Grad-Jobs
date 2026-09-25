"""corpus-index.json: every unique posting the scraper saw this run, titles only.

The curated board (jobs.json) and the near-miss tier (jobs-extended.json)
are the product. This artifact is the data foundation underneath them: one
compact row per deduplicated posting, tagged with the tier it landed in
(curated / near miss / out), so a reader or an opt-in "explore everything"
mode can apply its own signals client-side without the scraper ever
publishing 50k job pages or descriptions. Rows are arrays (see FIELDS) to
keep the file small; the site's Brotli sibling makes it ~0.9 MB on the wire.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from contracts import compute_job_id
from ngj.dates import get_iso_date
from ngj.taxonomy import categorize_job
from publish import write_compact_json_artifact
from url_safety import is_safe_url

logger = logging.getLogger(__name__)

CORPUS_FILENAME = "corpus-index.json"
CORPUS_SCHEMA_VERSION = "corpus-1"
FIELDS: tuple[str, ...] = ("company", "title", "location", "source", "posted_at", "category", "tier", "url")
TIER_CURATED = 0
TIER_NEAR_MISS = 1
TIER_OUT = 2
TIER_NAMES = {TIER_CURATED: "curated", TIER_NEAR_MISS: "near_miss", TIER_OUT: "out"}
_MAX_TEXT = 300


def _text(value: Any) -> str:
    return " ".join(str(value).split())[:_MAX_TEXT] if isinstance(value, str) else ""


def _job_ids(jobs: Iterable[Mapping[str, Any]]) -> set[str]:
    return {compute_job_id(dict(job)) for job in jobs}


def build_corpus_index(
    unique_jobs: Sequence[Mapping[str, Any]],
    curated: Sequence[Mapping[str, Any]],
    near_misses: Sequence[Mapping[str, Any]],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """One row per unique posting, tier-tagged. Inputs are never mutated.

    ``curated`` / ``near_misses`` are the published lists (after the URL
    gate), so the tier counts here match jobs.json and jobs-extended.json
    exactly. Unsafe or missing apply URLs become "" rather than being
    published.
    """
    now = now or datetime.now(UTC)
    curated_ids = _job_ids(curated)
    near_ids = _job_ids(near_misses)
    rows: list[list[Any]] = []
    counts = {name: 0 for name in TIER_NAMES.values()}
    seen: set[str] = set()
    for job in unique_jobs:
        job_id = compute_job_id(dict(job))
        if job_id in seen:
            continue
        seen.add(job_id)
        tier = TIER_CURATED if job_id in curated_ids else TIER_NEAR_MISS if job_id in near_ids else TIER_OUT
        counts[TIER_NAMES[tier]] += 1
        url = job.get("url")
        title = _text(job.get("title"))
        rows.append([
            _text(job.get("company")),
            title,
            _text(job.get("location")),
            _text(job.get("source")),
            (get_iso_date(job.get("posted_at")) or "")[:10],
            categorize_job(title)["id"],
            tier,
            url if isinstance(url, str) and is_safe_url(url) else "",
        ])
    # Tier first, then newest first (undated rows last), then company / title.
    rows.sort(key=lambda r: (r[6], -int(r[4].replace("-", "")) if r[4] else 0, r[0], r[1]))
    return {
        "meta": {
            "schema_version": CORPUS_SCHEMA_VERSION,
            "generated_at": now.isoformat(),
            "total": len(rows),
            "tiers": counts,
            "fields": list(FIELDS),
        },
        "rows": rows,
    }


def write_corpus_index(output_dir: Path, payload: dict[str, Any]) -> Path | None:
    """Write ``output_dir/corpus-index.json`` (minified). Returns the path, or None if the write failed."""
    path = Path(output_dir) / CORPUS_FILENAME
    try:
        write_compact_json_artifact(path, payload)
    except OSError as exc:
        logger.error("❌ Failed to write %s: %s", CORPUS_FILENAME, exc)
        return None
    logger.info("🗂️  %s written with %s rows (%s)", CORPUS_FILENAME, payload["meta"]["total"], payload["meta"]["tiers"])
    return path


def validate_corpus(payload: Any, curated_total: int | None = None, near_miss_total: int | None = None) -> list[str]:
    """Shape check for corpus-index.json (used by scripts/quality.py)."""
    if not isinstance(payload, dict) or not isinstance(payload.get("rows"), list):
        return ["corpus-index.json must be an object with a rows list"]
    errors: list[str] = []
    meta = payload.get("meta") or {}
    rows = payload["rows"]
    if meta.get("fields") != list(FIELDS):
        errors.append("corpus-index meta.fields does not match FIELDS")
    if meta.get("total") != len(rows):
        errors.append("corpus-index meta.total does not match its rows")
    counts = {name: 0 for name in TIER_NAMES.values()}
    for index, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != len(FIELDS):
            errors.append(f"corpus-index row {index} has {len(row) if isinstance(row, list) else 'no'} fields, expected {len(FIELDS)}")
            continue
        tier = row[6]
        if tier not in TIER_NAMES:
            errors.append(f"corpus-index row {index} has unknown tier {tier!r}")
            continue
        counts[TIER_NAMES[tier]] += 1
        if row[7] and not is_safe_url(row[7]):
            errors.append(f"corpus-index row {index} unsafe url: {row[7]}")
    if meta.get("tiers") != counts:
        errors.append(f"corpus-index meta.tiers {meta.get('tiers')} does not match the rows {counts}")
    if curated_total is not None and counts["curated"] != curated_total:
        errors.append(f"corpus-index curated rows {counts['curated']} != jobs.json {curated_total}")
    if near_miss_total is not None and counts["near_miss"] != near_miss_total:
        errors.append(f"corpus-index near-miss rows {counts['near_miss']} != jobs-extended.json {near_miss_total}")
    return errors

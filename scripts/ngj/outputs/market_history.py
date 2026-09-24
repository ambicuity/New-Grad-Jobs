"""Daily market snapshots (data/market-history.json, 90-day retention).

Unlike the generated public artifacts this file is persistent state: it is
committed and each run appends/replaces today's snapshot.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ngj.taxonomy import iter_category_ids

logger = logging.getLogger(__name__)

RETENTION_DAYS = 90
TOP_COMPANIES = 10


class MarketHistoryError(RuntimeError):
    """The market history file exists but is unreadable or malformed."""


def load_market_history(history_path: Path) -> list[dict[str, Any]]:
    """Load existing snapshots; a missing file means an empty history.

    A file that exists but cannot be parsed or validated raises
    MarketHistoryError instead of returning [] — falling back to an empty list
    used to overwrite up to 90 days of history with a single snapshot.
    """
    if not os.path.exists(history_path):
        return []
    try:
        with open(history_path, encoding='utf-8') as f:
            history_data = json.load(f)
    except (OSError, ValueError) as e:
        raise MarketHistoryError(
            f"Could not load market history at {history_path}: {e}. "
            "Refusing to overwrite it; fix or remove the file and re-run."
        ) from e

    snapshots = history_data.get('snapshots') if isinstance(history_data, dict) else None
    if not isinstance(snapshots, list) or not all(
        isinstance(entry, dict) and isinstance(entry.get('date'), str) for entry in snapshots
    ):
        raise MarketHistoryError(
            f"Invalid market history at {history_path}: expected an object with a "
            "'snapshots' list of objects that each carry a 'date' string. "
            "Refusing to overwrite it; fix or remove the file and re-run."
        )
    return snapshots


def build_snapshot(jobs: Sequence[dict[str, Any]], now: datetime) -> dict[str, Any]:
    """Aggregate today's counts by category, tier and company."""
    category_counts: Counter = Counter()
    tier_counts: Counter = Counter()
    for job in jobs:
        for category_id in iter_category_ids(job):
            category_counts[category_id] += 1
        tier_counts[job.get('company_tier', {}).get('tier', 'other')] += 1

    company_counts = Counter(job.get('company', 'Unknown') for job in jobs)
    unique_companies = len(company_counts)
    return {
        'date': now.strftime('%Y-%m-%d'),
        'total_jobs': len(jobs),
        'categories': dict(category_counts),
        'tiers': dict(tier_counts),
        'top_companies': [
            {'company': company, 'jobs': count}
            for company, count in company_counts.most_common(TOP_COMPANIES)
        ],
        'unique_companies': unique_companies,
        'avg_jobs_per_company': round(len(jobs) / unique_companies, 2) if unique_companies > 0 else 0,
        'timestamp': now.isoformat(),
    }


def merge_snapshot(
    history: Sequence[dict[str, Any]],
    snapshot: dict[str, Any],
    now: datetime,
) -> list[dict[str, Any]]:
    """Return a new history: today's snapshot replaced/added, 90-day window, sorted."""
    today = snapshot['date']
    merged = [entry for entry in history if entry['date'] != today] + [snapshot]
    cutoff_date = (now - timedelta(days=RETENTION_DAYS)).strftime('%Y-%m-%d')
    return sorted((entry for entry in merged if entry['date'] >= cutoff_date), key=lambda x: x['date'])


def _write_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Write via a sibling temp file + os.replace so a crash never truncates the file."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=directory, prefix='.market-history.', suffix='.tmp')
    tmp_path: str | None = tmp_name
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        os.replace(tmp_name, path)
        tmp_path = None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def save_market_history(
    jobs: Sequence[dict[str, Any]],
    history_path: Path,
    now: datetime | None = None,
) -> bool:
    """Add/replace today's snapshot in ``history_path``. Returns True when written.

    Raises MarketHistoryError when the existing file is corrupt (it is left
    untouched). A failed write is logged and returns False.
    """
    now = now or datetime.now(UTC)
    snapshot = build_snapshot(jobs, now)
    existing = load_market_history(history_path)
    replaced = any(entry['date'] == snapshot['date'] for entry in existing)
    history = merge_snapshot(existing, snapshot, now)
    logger.info(
        "  ✓ %s market snapshot for %s: %s jobs",
        'Updated' if replaced else 'Added', snapshot['date'], len(jobs),
    )

    history_data = {
        'meta': {
            'last_updated': now.isoformat(),
            'total_snapshots': len(history),
            'date_range': {
                'start': history[0]['date'] if history else None,
                'end': history[-1]['date'] if history else None,
            },
        },
        'snapshots': history,
    }
    try:
        _write_atomic(Path(history_path), history_data)
    except OSError as exc:
        logger.error("  ❌ Failed to save market history: %s", exc)
        return False
    logger.info("  ✓ Saved market history: %s snapshots (last %s days)", len(history), RETENTION_DAYS)
    return True

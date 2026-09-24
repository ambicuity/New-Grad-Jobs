"""Posted-date normalization, parsing and formatting.

Sources hand us epoch milliseconds (Lever), ISO strings (Greenhouse/Ashby),
``date``/``datetime`` objects (JobSpy) and human phrases ("Posted 3 Days Ago",
Workday). Everything is normalized to UTC-naive datetimes internally and
published as ISO 8601 with an explicit "Z".
"""

from __future__ import annotations

import logging
import math
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from dateutil import parser as date_parser  # type: ignore[import-untyped]
from dateutil.relativedelta import relativedelta  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

DAYS_PER_WEEK: int = 7


def utc_now() -> datetime:
    """The module clock (timezone-aware UTC). Tests monkeypatch this."""
    return datetime.now(UTC)


def normalize_date_string(
    posted_at: Any,
    reference_date: datetime | None = None,
    *,
    now_utc: datetime | None = None,
) -> str:
    """Normalize human-readable date phrases to strings ``date_parser`` handles.

    ``reference_date`` is the "current time" used to resolve relative phrases
    ("today", "2 days ago"); it defaults to ``datetime.now(timezone.utc)``.
    ``now_utc`` is a backward-compatible keyword alias.

    Handles "Posted Today", "Yesterday", "Posted 2 Days Ago", "30+ Days Ago",
    "Just posted"/"Recently", "2 Weeks Ago", "3 Months Ago", "Active 5 Days
    Ago", "5 hours ago". ``date``/``datetime`` objects become their ISO string.
    Unrecognized strings are returned unchanged.
    """
    if posted_at is None:
        return ''
    if isinstance(posted_at, float) and math.isnan(posted_at):
        return ''

    if not isinstance(posted_at, str):
        if hasattr(posted_at, 'isoformat'):
            return posted_at.isoformat()
        return str(posted_at)

    posted_at_lower = posted_at.lower().strip()
    reference = reference_date if reference_date is not None else now_utc
    if reference is None:
        reference = utc_now()
    now = as_utc_naive(reference)

    if 'today' in posted_at_lower:
        return now.strftime('%Y-%m-%d')

    if 'yesterday' in posted_at_lower:
        return (now - timedelta(days=1)).strftime('%Y-%m-%d')

    days_match = re.search(r'(\d+)\s*days?\s+ago', posted_at_lower)
    if days_match:
        return (now - timedelta(days=int(days_match.group(1)))).strftime('%Y-%m-%d')

    days_plus_match = re.search(r'(\d+)\+\s*days?\s+ago', posted_at_lower)
    if days_plus_match:
        return (now - timedelta(days=int(days_plus_match.group(1)))).strftime('%Y-%m-%d')

    if re.search(r'\d+\s*(?:hours?|minutes?)\s+ago', posted_at_lower):
        return now.strftime('%Y-%m-%d')

    if re.search(r'\b(?:just\s+(?:posted|now)|recently)\b', posted_at_lower):
        return now.strftime('%Y-%m-%d')

    weeks_match = re.search(r'(\d+)\s*(?:weeks?|wks?)\s+ago', posted_at_lower)
    if weeks_match:
        return (now - timedelta(days=int(weeks_match.group(1)) * DAYS_PER_WEEK)).strftime('%Y-%m-%d')

    months_match = re.search(r'(\d+)\s*(?:months?|mos?)\s+ago', posted_at_lower)
    if months_match:
        return (now - relativedelta(months=int(months_match.group(1)))).strftime('%Y-%m-%d')

    return posted_at


def as_utc_naive(dt: datetime) -> datetime:
    """Normalize datetime to UTC, then return a timezone-naive value.

    Naive inputs are treated as already UTC to keep comparisons deterministic.
    """
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(UTC).replace(tzinfo=None)


def parse_posted_at(posted_at: Any, now_utc: datetime | None = None) -> datetime:
    """Parse any supported posted_at value to a UTC-naive datetime.

    Numbers are epoch milliseconds (Lever). Raises on unparseable input.
    """
    if isinstance(posted_at, (int, float)):
        parsed = datetime.fromtimestamp(posted_at / 1000, tz=UTC)
    else:
        now_utc = now_utc or utc_now()
        parsed = date_parser.parse(normalize_date_string(posted_at, now_utc))
    return as_utc_naive(parsed)


def is_recent_job(posted_at: Any, max_age_days: int, *, now: datetime | None = None) -> bool:
    """Check if a job was posted within the last ``max_age_days`` days.

    ``now`` is the reference instant (defaults to :func:`utc_now`); naive values
    are taken as UTC, aware ones are converted. The cutoff is inclusive and all
    comparisons happen in UTC, so the host's local date never matters: a bare
    ``date`` means midnight UTC of that day.
    """
    if posted_at is None:
        return False
    if isinstance(posted_at, float) and math.isnan(posted_at):
        return False

    try:
        now_utc = now if now is not None else utc_now()
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)
        if isinstance(posted_at, (datetime, date)):
            posted_date = posted_at
            if not isinstance(posted_date, datetime):
                posted_date = datetime.combine(posted_date, datetime.min.time())
            posted_date = as_utc_naive(posted_date)
        else:
            posted_date = parse_posted_at(posted_at, now_utc)
        cutoff_date = as_utc_naive(now_utc) - timedelta(days=max_age_days)
        return posted_date >= cutoff_date
    except Exception as exc:
        logger.warning("Error parsing date %s: %s", posted_at, exc)
        return False


def format_posted_date(posted_at: Any, now_utc: datetime | None = None) -> str:
    """Relative display string: "Today", "1 day ago", "N days ago", else YYYY-MM-DD."""
    try:
        now_utc = now_utc or utc_now()
        posted_date = parse_posted_at(posted_at, now_utc)
        diff = now_utc.replace(tzinfo=None) - posted_date
        if diff.days == 0:
            return "Today"
        if diff.days == 1:
            return "1 day ago"
        if diff.days < 7:
            return f"{diff.days} days ago"
        return posted_date.strftime("%Y-%m-%d")
    except Exception as exc:
        logger.warning("Warning: could not format date '%s': %s", posted_at, exc)
        return "Unknown"


def format_utc_iso(dt_utc_naive: datetime) -> str:
    """Format a UTC-naive datetime as ISO 8601 with an explicit "Z" designator.

    Without the designator browsers parse the string as local time. Fractions
    are clipped to milliseconds, the precision ECMAScript date-time defines.
    """
    timespec = 'milliseconds' if dt_utc_naive.microsecond else 'seconds'
    return dt_utc_naive.isoformat(timespec=timespec) + 'Z'


def get_iso_date(posted_at: Any) -> str:
    """ISO 8601 UTC date string (e.g. "2026-09-24T14:50:21Z"), or "" if unparseable."""
    try:
        return format_utc_iso(parse_posted_at(posted_at))
    except Exception as exc:
        logger.warning("Warning: could not parse ISO date '%s': %s", posted_at, exc)
        return ""


def extract_sort_date(job: dict[str, Any]) -> datetime:
    """posted_at as a UTC-naive datetime for sorting; ``datetime.min`` if absent/bad."""
    posted_at = job.get('posted_at')
    if not posted_at:
        return datetime.min
    try:
        return parse_posted_at(posted_at)
    except Exception:
        return datetime.min

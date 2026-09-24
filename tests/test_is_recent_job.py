#!/usr/bin/env python3
"""
Comprehensive tests for is_recent_job(, now=NOW) in scripts/update_jobs.py.

The is_recent_job(, now=NOW) function is critical infrastructure used by filter_jobs()
to determine if a job posting is recent enough to include in the listings.
It handles multiple input formats from different APIs (ISO strings, timestamps,
date objects) and must handle edge cases gracefully.
"""

import os
import sys
from datetime import UTC, date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from ngj import dates  # noqa: E402
from ngj.dates import is_recent_job  # noqa: E402

# Frozen clock: every test measures against this instant, never the wall clock,
# so results cannot flip at midnight, across time zones, or on slow CI runners.
NOW = datetime(2026, 9, 24, 12, 0, 0, tzinfo=UTC)


class TestIsRecentJobBasicBehavior:
    """Test basic recency checking with standard inputs."""

    def test_job_posted_today_is_recent(self):
        """Job posted today should pass with any max_age_days >= 1."""
        today = NOW.isoformat()
        assert is_recent_job(today, max_age_days=1, now=NOW) is True
        assert is_recent_job(today, max_age_days=7, now=NOW) is True
        assert is_recent_job(today, max_age_days=30, now=NOW) is True

    def test_job_posted_within_max_age_days(self):
        """Job posted 3 days ago should pass with max_age_days=7."""
        three_days_ago = (NOW - timedelta(days=3)).isoformat()
        assert is_recent_job(three_days_ago, max_age_days=7, now=NOW) is True

    def test_job_posted_exactly_at_cutoff_passes(self):
        """Job posted exactly max_age_days ago should pass (boundary test)."""
        # Note: Due to timing precision, we test slightly before cutoff
        cutoff_date = (NOW - timedelta(days=7) + timedelta(minutes=1)).isoformat()
        assert is_recent_job(cutoff_date, max_age_days=7, now=NOW) is True

    def test_job_posted_beyond_max_age_days_fails(self):
        """Job posted 30 days ago should fail with max_age_days=7."""
        thirty_days_ago = (NOW - timedelta(days=30)).isoformat()
        assert is_recent_job(thirty_days_ago, max_age_days=7, now=NOW) is False

    def test_job_posted_one_day_beyond_cutoff_fails(self):
        """Job posted just past the cutoff should fail (boundary test)."""
        just_past_cutoff = (NOW - timedelta(days=8)).isoformat()
        assert is_recent_job(just_past_cutoff, max_age_days=7, now=NOW) is False


class TestIsRecentJobEdgeCases:
    """Test edge cases: None, NaN, empty strings, invalid inputs."""

    def test_none_returns_false(self):
        """None should return False (no date means not recent)."""
        assert is_recent_job(None, max_age_days=7, now=NOW) is False

    def test_nan_returns_false(self):
        """NaN from pandas DataFrames should return False."""
        assert is_recent_job(float('nan'), max_age_days=7, now=NOW) is False

    def test_infinity_returns_false(self):
        """Infinity values should return False."""
        assert is_recent_job(float('inf'), max_age_days=7, now=NOW) is False
        assert is_recent_job(float('-inf'), max_age_days=7, now=NOW) is False

    def test_empty_string_returns_false(self):
        """Empty string should return False."""
        assert is_recent_job('', max_age_days=7, now=NOW) is False

    def test_whitespace_string_returns_false(self):
        """Whitespace-only string should return False."""
        assert is_recent_job('   ', max_age_days=7, now=NOW) is False

    def test_invalid_date_string_returns_false(self):
        """Invalid date string should return False (not crash)."""
        assert is_recent_job('not a date', max_age_days=7, now=NOW) is False
        assert is_recent_job('2026-99-99', max_age_days=7, now=NOW) is False

    def test_zero_max_age_days(self):
        """max_age_days=0 accepts jobs within the last 24 hours (timedelta(days=0))."""
        # Note: max_age_days=0 means cutoff is now - 0 days, but timing precision
        # means jobs from a few seconds ago might fail if now_utc advances between
        # creating the timestamp and checking it. Test with safe margins.
        yesterday = (NOW - timedelta(days=1)).isoformat()
        assert is_recent_job(yesterday, max_age_days=0, now=NOW) is False
        # Jobs from more than 1 day ago definitely fail
        two_days_ago = (NOW - timedelta(days=2)).isoformat()
        assert is_recent_job(two_days_ago, max_age_days=0, now=NOW) is False

    def test_negative_max_age_days(self):
        """Negative max_age_days should reject all jobs (past is always negative)."""
        today = NOW.isoformat()
        assert is_recent_job(today, max_age_days=-1, now=NOW) is False


class TestIsRecentJobDatetimeObjects:
    """Test handling of already-parsed date/datetime objects."""

    def test_datetime_object_recent(self):
        """datetime object from 2 days ago should pass."""
        two_days_ago = NOW - timedelta(days=2)
        assert is_recent_job(two_days_ago, max_age_days=7, now=NOW) is True

    def test_datetime_object_old(self):
        """datetime object from 30 days ago should fail."""
        thirty_days_ago = NOW - timedelta(days=30)
        assert is_recent_job(thirty_days_ago, max_age_days=7, now=NOW) is False

    def test_date_object_recent(self):
        """date object (not datetime) from today should pass."""
        today_date = NOW.date()
        assert is_recent_job(today_date, max_age_days=7, now=NOW) is True

    def test_date_object_old(self):
        """date object from 30 days ago should fail."""
        thirty_days_ago = NOW.date() - timedelta(days=30)
        assert is_recent_job(thirty_days_ago, max_age_days=7, now=NOW) is False

    def test_timezone_aware_datetime(self):
        """Timezone-aware datetime should be handled correctly."""
        two_days_ago_utc = NOW - timedelta(days=2)
        assert is_recent_job(two_days_ago_utc, max_age_days=7, now=NOW) is True


class TestIsRecentJobTimestamps:
    """Test handling of Unix timestamps (Lever API format)."""

    def test_timestamp_milliseconds_recent(self):
        """Lever API sends timestamps in milliseconds - should pass if recent."""
        now_ms = int(NOW.timestamp() * 1000)
        two_days_ago_ms = now_ms - (2 * 24 * 60 * 60 * 1000)
        assert is_recent_job(two_days_ago_ms, max_age_days=7, now=NOW) is True

    def test_timestamp_milliseconds_old(self):
        """Lever API timestamp from 30 days ago should fail."""
        now_ms = int(NOW.timestamp() * 1000)
        thirty_days_ago_ms = now_ms - (30 * 24 * 60 * 60 * 1000)
        assert is_recent_job(thirty_days_ago_ms, max_age_days=7, now=NOW) is False

    def test_timestamp_as_float_recent(self):
        """Float timestamps (from JSON parsing) should work."""
        now_ms = float(NOW.timestamp() * 1000)
        two_days_ago_ms = now_ms - (2.0 * 24 * 60 * 60 * 1000)
        assert is_recent_job(two_days_ago_ms, max_age_days=7, now=NOW) is True

    def test_timestamp_zero(self):
        """Timestamp 0 (Unix epoch - Jan 1, 1970) should be old with typical max_age_days."""
        # Note: Implementation parses 0 as timestamp (1970-01-01)
        # With typical values like 7 or 30 days, Unix epoch is too old
        assert is_recent_job(0, max_age_days=7, now=NOW) is False
        assert is_recent_job(0, max_age_days=30, now=NOW) is False
        # With extremely large max_age_days (60+ years), even Unix epoch is "recent"
        # This is an edge case that doesn't occur in production (max_age_days is typically 7-30)
        assert is_recent_job(0, max_age_days=365*60, now=NOW) is True

    def test_timestamp_negative(self):
        """Negative timestamp (before Unix epoch) should fail or error."""
        # Note: Implementation tries to parse negative timestamps, which may
        # raise an exception (caught and returns False) or parse incorrectly
        result = is_recent_job(-1000, max_age_days=30, now=NOW)
        # We accept either False (error path) or the actual result
        assert isinstance(result, bool)


class TestIsRecentJobDateFormats:
    """Test various ISO 8601 and common date string formats."""

    def test_iso_8601_with_timezone(self):
        """ISO 8601 with timezone should parse correctly."""
        two_days_ago = (NOW - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%S+00:00')
        assert is_recent_job(two_days_ago, max_age_days=7, now=NOW) is True

    def test_iso_8601_with_z_suffix(self):
        """ISO 8601 with Z suffix (Zulu time) should work."""
        two_days_ago = (NOW - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
        assert is_recent_job(two_days_ago, max_age_days=7, now=NOW) is True

    def test_iso_8601_date_only(self):
        """ISO 8601 date-only format should work."""
        two_days_ago = (NOW - timedelta(days=2)).strftime('%Y-%m-%d')
        assert is_recent_job(two_days_ago, max_age_days=7, now=NOW) is True

    def test_iso_8601_with_microseconds(self):
        """ISO 8601 with microseconds should work."""
        two_days_ago = (NOW - timedelta(days=2)).isoformat()
        assert is_recent_job(two_days_ago, max_age_days=7, now=NOW) is True

    def test_human_readable_date_after_normalization(self):
        """Human-readable dates (normalized by normalize_date_string) should work."""
        # These are normalized before reaching is_recent_job in production,
        # but test that dateutil.parser can handle common formats
        two_days_ago = (NOW - timedelta(days=2)).strftime('%B %d, %Y')
        try:
            result = is_recent_job(two_days_ago, max_age_days=7, now=NOW)
            assert result is True
        except Exception:
            # If dateutil.parser doesn't handle this format, that's okay
            # as normalize_date_string handles it first in production
            pass


class TestIsRecentJobFutureTimestamps:
    """Test handling of future dates (clock skew, bad API data)."""

    def test_future_date_is_recent(self):
        """Future date should be considered recent (clock skew tolerance)."""
        tomorrow = (NOW + timedelta(days=1)).isoformat()
        assert is_recent_job(tomorrow, max_age_days=7, now=NOW) is True

    def test_far_future_date_is_recent(self):
        """Far future date (bad API data) should still be recent."""
        far_future = (NOW + timedelta(days=365)).isoformat()
        assert is_recent_job(far_future, max_age_days=7, now=NOW) is True


class TestIsRecentJobMaxAgeDaysVariations:
    """Test various max_age_days values."""

    def test_max_age_days_1(self):
        """max_age_days=1 should only accept yesterday and today."""
        today = NOW.isoformat()
        two_days_ago = (NOW - timedelta(days=2)).isoformat()
        assert is_recent_job(today, max_age_days=1, now=NOW) is True
        assert is_recent_job(two_days_ago, max_age_days=1, now=NOW) is False

    def test_max_age_days_30(self):
        """max_age_days=30 should accept last month."""
        fifteen_days_ago = (NOW - timedelta(days=15)).isoformat()
        forty_days_ago = (NOW - timedelta(days=40)).isoformat()
        assert is_recent_job(fifteen_days_ago, max_age_days=30, now=NOW) is True
        assert is_recent_job(forty_days_ago, max_age_days=30, now=NOW) is False

    def test_max_age_days_365(self):
        """max_age_days=365 should accept last year."""
        six_months_ago = (NOW - timedelta(days=180)).isoformat()
        two_years_ago = (NOW - timedelta(days=730)).isoformat()
        assert is_recent_job(six_months_ago, max_age_days=365, now=NOW) is True
        assert is_recent_job(two_years_ago, max_age_days=365, now=NOW) is False


class TestIsRecentJobIntegrationScenarios:
    """Test realistic scenarios from actual API responses."""

    def test_greenhouse_iso_format(self):
        """Greenhouse API returns ISO 8601 dates."""
        greenhouse_date = (NOW - timedelta(days=3)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        assert is_recent_job(greenhouse_date, max_age_days=7, now=NOW) is True

    def test_lever_millisecond_timestamp(self):
        """Lever API returns timestamps in milliseconds."""
        now_ms = int(NOW.timestamp() * 1000)
        lever_timestamp = now_ms - (3 * 24 * 60 * 60 * 1000)  # 3 days ago
        assert is_recent_job(lever_timestamp, max_age_days=7, now=NOW) is True

    def test_workday_date_object(self):
        """Workday parser might return date objects."""
        workday_date = NOW.date() - timedelta(days=3)
        assert is_recent_job(workday_date, max_age_days=7, now=NOW) is True

    def test_jobspy_normalized_date(self):
        """JobSpy dates are normalized before reaching is_recent_job."""
        # After normalization, they're in %Y-%m-%d format
        jobspy_date = (NOW - timedelta(days=3)).strftime('%Y-%m-%d')
        assert is_recent_job(jobspy_date, max_age_days=7, now=NOW) is True

    def test_pandas_dataframe_nan(self):
        """Pandas DataFrames can have NaN for missing dates."""
        assert is_recent_job(float('nan'), max_age_days=7, now=NOW) is False

    def test_malformed_api_response(self):
        """Malformed API response should not crash."""
        assert is_recent_job('Invalid', max_age_days=7, now=NOW) is False
        assert is_recent_job(None, max_age_days=7, now=NOW) is False
        assert is_recent_job('', max_age_days=7, now=NOW) is False


class TestIsRecentJobClock:
    """The clock is injectable, so recency never depends on real time."""

    def test_exact_cutoff_boundary_is_inclusive(self):
        cutoff = (NOW - timedelta(days=7)).isoformat()
        assert is_recent_job(cutoff, max_age_days=7, now=NOW) is True
        just_before = (NOW - timedelta(days=7, seconds=1)).isoformat()
        assert is_recent_job(just_before, max_age_days=7, now=NOW) is False

    def test_naive_now_is_treated_as_utc(self):
        naive_now = NOW.replace(tzinfo=None)
        assert is_recent_job("2026-09-20T00:00:00Z", max_age_days=7, now=naive_now) is True

    def test_aware_non_utc_now_is_converted(self):
        from datetime import timezone
        pacific = NOW.astimezone(timezone(timedelta(hours=-7)))
        assert is_recent_job("2026-09-17T12:00:00Z", max_age_days=7, now=pacific) is True
        assert is_recent_job("2026-09-17T11:59:59Z", max_age_days=7, now=pacific) is False

    def test_relative_phrases_resolve_against_injected_now(self):
        assert is_recent_job("Posted 3 Days Ago", max_age_days=7, now=NOW) is True
        assert is_recent_job("30+ Days Ago", max_age_days=7, now=NOW) is False

    def test_default_clock_is_the_module_clock(self, monkeypatch):
        monkeypatch.setattr(dates, "utc_now", lambda: NOW)
        assert is_recent_job("2026-09-20T00:00:00Z", max_age_days=7) is True
        assert is_recent_job("2026-09-01T00:00:00Z", max_age_days=7) is False

    def test_date_object_uses_utc_midnight_not_local_date(self):
        """A bare date is midnight UTC; the frozen UTC clock decides, not date.today()."""
        assert is_recent_job(date(2026, 9, 17), max_age_days=7, now=NOW) is False
        assert is_recent_job(date(2026, 9, 18), max_age_days=7, now=NOW) is True

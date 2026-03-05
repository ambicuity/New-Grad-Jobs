#!/usr/bin/env python3
"""Tests for timezone-aware date normalization in scripts/update_jobs.py."""

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import is_recent_job, normalize_date_string


FIXED_NOW_UTC = datetime(2026, 3, 4, 12, 0, 0, tzinfo=timezone.utc)


def test_is_recent_job_rejects_none_and_nan():
    assert is_recent_job(None, 7) is False
    assert is_recent_job(float('nan'), 7) is False


def test_is_recent_job_empty_string_returns_false():
    assert is_recent_job('', 7) is False


from datetime import date


def test_normalize_date_string_jobspy_human_readable_variants():
    now = FIXED_NOW_UTC.replace(tzinfo=None)
    assert normalize_date_string('Posted Today', FIXED_NOW_UTC) == now.strftime('%Y-%m-%d')
    assert normalize_date_string('Yesterday', FIXED_NOW_UTC) == (now - timedelta(days=1)).strftime('%Y-%m-%d')
    assert normalize_date_string('Posted 2 Days Ago', FIXED_NOW_UTC) == (now - timedelta(days=2)).strftime('%Y-%m-%d')
    assert normalize_date_string('30+ Days Ago', FIXED_NOW_UTC) == (now - timedelta(days=30)).strftime('%Y-%m-%d')


def test_normalize_date_string_native_date_object_returns_iso_string():
    """Regression: native date/datetime objects must be coerced to ISO string.

    Workday and JobSpy API clients can return already-parsed date/datetime
    objects.  Previously the function returned them unchanged, causing
    dateparser to emit hundreds of 'Parser must be a string or character
    stream, not date' warnings during CI runs.
    """
    d = date(2026, 3, 5)
    result = normalize_date_string(d)
    assert isinstance(result, str), "Expected ISO string, got non-string type"
    assert result == '2026-03-05'

    dt = datetime(2026, 3, 5, 12, 30, 0)
    result_dt = normalize_date_string(dt)
    assert isinstance(result_dt, str), "Expected ISO string, got non-string type"
    assert result_dt.startswith('2026-03-05')




def test_normalize_date_string_preserves_utc_offset_strings():
    value = '2026-03-01T12:34:56+05:30'
    assert normalize_date_string(value, FIXED_NOW_UTC) == value


def test_is_recent_job_handles_utc_offset_string_by_normalizing_to_utc(monkeypatch):
    monkeypatch.setattr('update_jobs.datetime', _fixed_datetime_class(FIXED_NOW_UTC))

    old_instant_utc = FIXED_NOW_UTC - timedelta(days=7, hours=1)
    plus14 = timezone(timedelta(hours=14))
    old_plus14_str = old_instant_utc.astimezone(plus14).isoformat()

    assert is_recent_job(old_plus14_str, 7) is False


def test_is_recent_job_handles_timezone_aware_datetime_object(monkeypatch):
    monkeypatch.setattr('update_jobs.datetime', _fixed_datetime_class(FIXED_NOW_UTC))

    fresh_instant_utc = FIXED_NOW_UTC - timedelta(days=1)
    minus8 = timezone(timedelta(hours=-8))
    fresh_minus8_dt = fresh_instant_utc.astimezone(minus8)

    assert is_recent_job(fresh_minus8_dt, 7) is True


def test_is_recent_job_handles_unix_millis(monkeypatch):
    monkeypatch.setattr('update_jobs.datetime', _fixed_datetime_class(FIXED_NOW_UTC))

    recent_ms = int((FIXED_NOW_UTC - timedelta(days=1)).timestamp() * 1000)
    old_ms = int((FIXED_NOW_UTC - timedelta(days=8)).timestamp() * 1000)

    assert is_recent_job(recent_ms, 7) is True
    assert is_recent_job(old_ms, 7) is False


def test_is_recent_job_handles_naive_datetime(monkeypatch):
    monkeypatch.setattr('update_jobs.datetime', _fixed_datetime_class(FIXED_NOW_UTC))

    naive_recent = (FIXED_NOW_UTC - timedelta(days=1)).replace(tzinfo=None)
    assert is_recent_job(naive_recent, 7) is True


def test_is_recent_job_boundary_behavior_for_recent_window(monkeypatch):
    monkeypatch.setattr('update_jobs.datetime', _fixed_datetime_class(FIXED_NOW_UTC))

    just_inside = (FIXED_NOW_UTC - timedelta(days=7) + timedelta(minutes=1)).isoformat()
    just_outside = (FIXED_NOW_UTC - timedelta(days=7) - timedelta(minutes=1)).isoformat()

    assert is_recent_job(just_inside, 7) is True
    assert is_recent_job(just_outside, 7) is False


def _fixed_datetime_class(fixed_now: datetime):
    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_now.replace(tzinfo=None)
            return fixed_now.astimezone(tz)

        @classmethod
        def fromtimestamp(cls, ts, tz=None):
            return datetime.fromtimestamp(ts, tz=tz)

        @classmethod
        def combine(cls, date_obj, time_obj):
            return datetime.combine(date_obj, time_obj)

    return _FixedDateTime

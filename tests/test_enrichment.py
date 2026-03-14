#!/usr/bin/env python3
"""
Unit tests for job enrichment functions in scripts/update_jobs.py.

Tests cover:
- detect_sponsorship_flags(): visa/citizenship keyword detection
- is_job_closed(): closed-job indicator detection
- get_company_tier(): FAANG+/Unicorn/sector classification
- enrich_jobs(): full enrichment pipeline
- format_posted_date(): human-readable date display
- get_iso_date(): ISO date string extraction
"""

import sys
import os
import math
from datetime import datetime, timedelta, timezone, date
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import (
    detect_sponsorship_flags,
    is_job_closed,
    get_company_tier,
    enrich_jobs,
    format_posted_date,
    get_iso_date,
)

FIXED_NOW = datetime(2026, 3, 11, 12, 0, 0)


# ---------------------------------------------------------------------------
# detect_sponsorship_flags
# ---------------------------------------------------------------------------

class TestDetectSponsorshipFlags:
    """Keyword-based sponsorship and citizenship detection."""

    def test_clean_job_has_no_flags(self):
        result = detect_sponsorship_flags("Software Engineer", "Work on backend systems.")
        assert result['no_sponsorship'] is False
        assert result['us_citizenship_required'] is False

    def test_no_sponsorship_detected_in_description(self):
        result = detect_sponsorship_flags(
            "Software Engineer",
            "We will not sponsor visas for this position."
        )
        assert result['no_sponsorship'] is True

    def test_no_sponsorship_detected_in_title(self):
        result = detect_sponsorship_flags("SWE - U.S. Citizens Only", "")
        assert result['no_sponsorship'] is True

    def test_us_citizenship_required_security_clearance(self):
        result = detect_sponsorship_flags(
            "Software Engineer",
            "Applicant must hold an active security clearance."
        )
        assert result['us_citizenship_required'] is True

    def test_us_citizenship_required_ts_sci(self):
        result = detect_sponsorship_flags("TS/SCI Required - Backend Engineer", "")
        assert result['us_citizenship_required'] is True

    def test_case_insensitive_matching(self):
        result = detect_sponsorship_flags(
            "Engineer",
            "MUST BE AUTHORIZED TO WORK IN THE US."
        )
        assert result['no_sponsorship'] is True

    def test_empty_description(self):
        result = detect_sponsorship_flags("Software Engineer")
        assert result['no_sponsorship'] is False
        assert result['us_citizenship_required'] is False

    def test_both_flags_can_be_true(self):
        result = detect_sponsorship_flags(
            "Engineer - No Sponsorship, TS/SCI Clearance Required",
            ""
        )
        assert result['no_sponsorship'] is True
        assert result['us_citizenship_required'] is True

    def test_returns_dict_with_expected_keys(self):
        result = detect_sponsorship_flags("Software Engineer", "Great benefits.")
        assert 'no_sponsorship' in result
        assert 'us_citizenship_required' in result


# ---------------------------------------------------------------------------
# is_job_closed
# ---------------------------------------------------------------------------

class TestIsJobClosed:
    """Closed-job indicator detection."""

    def test_open_job_returns_false(self):
        assert is_job_closed("Software Engineer", "Exciting opportunity at our startup.") is False

    def test_closed_in_title(self):
        assert is_job_closed("Software Engineer [Closed]", "") is True

    def test_no_longer_accepting_in_description(self):
        assert is_job_closed("SWE", "We are no longer accepting applications.") is True

    def test_position_filled_in_description(self):
        assert is_job_closed("SWE", "Position filled - no longer reviewing applications.") is True

    def test_expired_in_description(self):
        assert is_job_closed("SWE", "This posting has expired.") is True

    def test_empty_description_defaults_to_open(self):
        assert is_job_closed("Software Engineer") is False

    def test_case_insensitive(self):
        assert is_job_closed("CLOSED POSITION - DO NOT APPLY", "") is True


# ---------------------------------------------------------------------------
# get_company_tier
# ---------------------------------------------------------------------------

class TestGetCompanyTier:
    """Company tier and sector classification."""

    def test_faang_plus_company(self):
        result = get_company_tier("Google")
        assert result['tier'] == 'faang_plus'
        assert result['emoji'] == '🔥'

    def test_unicorn_company(self):
        # Find a unicorn that's in the set
        from update_jobs import UNICORNS
        if UNICORNS:
            company = next(iter(UNICORNS))
            result = get_company_tier(company)
            assert result['tier'] == 'unicorn'

    def test_unknown_company_returns_other(self):
        result = get_company_tier("Obscure Startup XYZ")
        assert result['tier'] == 'other'
        assert result['emoji'] == ''

    def test_finance_sector_detected(self):
        from update_jobs import FINANCE
        if FINANCE:
            company = next(iter(FINANCE))
            result = get_company_tier(company)
            assert 'finance' in result['sectors']

    def test_defense_sector_detected(self):
        from update_jobs import DEFENSE
        if DEFENSE:
            company = next(iter(DEFENSE))
            result = get_company_tier(company)
            assert 'defense' in result['sectors']

    def test_result_always_has_sectors_key(self):
        result = get_company_tier("Nonexistent Corp")
        assert 'sectors' in result
        assert isinstance(result['sectors'], list)

    def test_company_can_overlap_tier_and_sector(self):
        """A FAANG+ company that's also in FINANCE should have both."""
        from update_jobs import FAANG_PLUS, FINANCE
        overlap = FAANG_PLUS & FINANCE
        if overlap:
            company = next(iter(overlap))
            result = get_company_tier(company)
            assert result['tier'] == 'faang_plus'
            assert 'finance' in result['sectors']


# ---------------------------------------------------------------------------
# enrich_jobs
# ---------------------------------------------------------------------------

def _make_job(**kwargs):
    """Minimal valid job dict factory."""
    defaults = {
        'title': 'Software Engineer, New Grad',
        'company': 'Acme Corp',
        'location': 'San Francisco, CA',
        'url': 'https://example.com/job/1',
        'posted_at': datetime(2026, 3, 10).isoformat(),
        'description': '',
        'source': 'Greenhouse',
    }
    defaults.update(kwargs)
    return defaults


class TestEnrichJobs:
    """Full enrichment pipeline: category, tier, flags, closed status, id."""

    def test_enriched_job_has_category(self):
        jobs = [_make_job()]
        result = enrich_jobs(jobs)
        assert len(result) == 1
        assert 'category' in result[0]
        assert isinstance(result[0]['category'], dict)

    def test_enriched_job_has_company_tier(self):
        jobs = [_make_job()]
        result = enrich_jobs(jobs)
        assert 'company_tier' in result[0]
        assert 'tier' in result[0]['company_tier']

    def test_enriched_job_has_flags(self):
        jobs = [_make_job()]
        result = enrich_jobs(jobs)
        assert 'flags' in result[0]
        assert 'no_sponsorship' in result[0]['flags']

    def test_enriched_job_has_is_closed(self):
        jobs = [_make_job()]
        result = enrich_jobs(jobs)
        assert 'is_closed' in result[0]
        assert result[0]['is_closed'] is False

    def test_enriched_job_has_id(self):
        jobs = [_make_job()]
        result = enrich_jobs(jobs)
        assert 'id' in result[0]
        assert isinstance(result[0]['id'], str)
        assert len(result[0]['id']) > 0

    def test_id_max_length_100(self):
        long_title = "A" * 200
        jobs = [_make_job(title=long_title)]
        result = enrich_jobs(jobs)
        assert len(result[0]['id']) <= 100

    def test_empty_input_returns_empty(self):
        assert enrich_jobs([]) == []

    def test_multiple_jobs_all_enriched(self):
        jobs = [_make_job(url=f"https://example.com/{i}") for i in range(3)]
        result = enrich_jobs(jobs)
        assert len(result) == 3
        for job in result:
            assert 'category' in job
            assert 'company_tier' in job

    def test_faang_company_gets_faang_tier(self):
        jobs = [_make_job(company='Google')]
        result = enrich_jobs(jobs)
        assert result[0]['company_tier']['tier'] == 'faang_plus'

    def test_closed_job_flagged(self):
        jobs = [_make_job(title="Software Engineer [Closed]")]
        result = enrich_jobs(jobs)
        assert result[0]['is_closed'] is True

    def test_sponsorship_flag_propagated(self):
        jobs = [_make_job(description="We will not sponsor visas.")]
        result = enrich_jobs(jobs)
        assert result[0]['flags']['no_sponsorship'] is True


# ---------------------------------------------------------------------------
# format_posted_date
# ---------------------------------------------------------------------------

class TestFormatPostedDate:
    """Human-readable date display formatting."""

    def test_recent_date_shows_today(self):
        now = datetime.now()
        result = format_posted_date(now.isoformat())
        assert result == "Today"

    def test_yesterday_shows_1_day_ago(self):
        yesterday = datetime.now() - timedelta(days=1)
        result = format_posted_date(yesterday.isoformat())
        assert result == "1 day ago"

    def test_days_ago_format(self):
        three_days_ago = datetime.now() - timedelta(days=3)
        result = format_posted_date(three_days_ago.isoformat())
        assert result == "3 days ago"

    def test_old_date_shows_iso_format(self):
        two_weeks_ago = datetime.now() - timedelta(days=14)
        result = format_posted_date(two_weeks_ago.isoformat())
        # Should return YYYY-MM-DD formatted date
        assert result == two_weeks_ago.strftime("%Y-%m-%d")

    def test_lever_timestamp_int(self):
        """Lever API returns timestamps in milliseconds."""
        ts_ms = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
        result = format_posted_date(ts_ms)
        assert result == "1 day ago"

    def test_lever_timestamp_float(self):
        """Float millisecond timestamps should also work."""
        ts_ms = float(int((datetime.now() - timedelta(days=2)).timestamp() * 1000))
        result = format_posted_date(ts_ms)
        assert result == "2 days ago"

    def test_invalid_date_returns_unknown(self):
        result = format_posted_date("not-a-date")
        assert result == "Unknown"

    def test_human_readable_posted_today(self):
        result = format_posted_date("Posted Today")
        assert result == "Today"

    def test_human_readable_posted_2_days_ago(self):
        result = format_posted_date("Posted 2 Days Ago")
        assert result == "2 days ago"


# ---------------------------------------------------------------------------
# get_iso_date
# ---------------------------------------------------------------------------

class TestGetIsoDate:
    """ISO date string extraction for JSON output."""

    def test_iso_string_passthrough(self):
        result = get_iso_date("2026-03-10T00:00:00")
        assert result.startswith("2026-03-10")

    def test_lever_timestamp_ms_converted(self):
        """Lever API millisecond timestamps must produce ISO strings."""
        dt = datetime(2026, 3, 10, 12, 0, 0)
        ts_ms = int(dt.timestamp() * 1000)
        result = get_iso_date(ts_ms)
        assert result.startswith("2026-03-10")

    def test_float_timestamp_converted(self):
        dt = datetime(2026, 3, 10, 12, 0, 0)
        ts_ms = float(dt.timestamp() * 1000)
        result = get_iso_date(ts_ms)
        assert result.startswith("2026-03-10")

    def test_human_readable_string_converted(self):
        result = get_iso_date("2026-03-10")
        assert result.startswith("2026-03-10")

    def test_invalid_input_returns_empty_string(self):
        result = get_iso_date("not-a-date-at-all!!!")
        assert result == ""

    def test_result_is_string(self):
        result = get_iso_date("2026-03-10T00:00:00")
        assert isinstance(result, str)

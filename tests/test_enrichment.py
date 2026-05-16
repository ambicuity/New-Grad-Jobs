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
    extract_compensation,
    fetch_greenhouse_jobs,
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


# ---------------------------------------------------------------------------
# extract_compensation
# ---------------------------------------------------------------------------

class TestExtractCompensation:
    """Regex-based salary range extraction from job description bodies."""

    def test_ca_law_style_range(self):
        text = 'The base salary range for this position is $120,000 - $180,000.'
        r = extract_compensation(text)
        assert r == {'min': 120000, 'max': 180000, 'currency': 'USD', 'source': 'posting'}

    def test_em_dash_range(self):
        r = extract_compensation('Pay range: $85,000 – $115,000 per year.')
        assert r['min'] == 85000 and r['max'] == 115000

    def test_k_suffix_range(self):
        r = extract_compensation('Annual compensation: $90K – $130K')
        assert r == {'min': 90000, 'max': 130000, 'currency': 'USD', 'source': 'posting'}

    def test_lowercase_k_suffix(self):
        r = extract_compensation('Salary $110k - $145k')
        assert r['min'] == 110000 and r['max'] == 145000

    def test_usd_prefix(self):
        r = extract_compensation('USD 75,000 to 95,000 plus equity')
        assert r['min'] == 75000 and r['max'] == 95000

    def test_single_value_band(self):
        r = extract_compensation('Compensation: $200,000/year + RSUs')
        assert r is not None
        assert r['min'] == 180000 and r['max'] == 220000

    def test_single_value_k(self):
        r = extract_compensation('Base $150k annually, plus bonus')
        assert r is not None
        assert r['min'] == 135000 and r['max'] == 165000

    def test_rejects_series_funding(self):
        text = 'We just closed our Series B and raised $120M from top VCs.'
        assert extract_compensation(text) is None

    def test_rejects_signon_bonus_below_floor(self):
        # "$5,000 sign-on" — under 30k sanity floor
        assert extract_compensation('Sign-on bonus up to $5,000') is None

    def test_rejects_product_budget(self):
        # "$1.2M product budget" — far above 600k sanity ceiling
        assert extract_compensation('We have a $1.2M product budget this year.') is None

    def test_rejects_stock_price(self):
        assert extract_compensation('Stock price closed at $124.50 yesterday') is None

    def test_rejects_valuation_phrase(self):
        text = 'Valued at $5 billion after our latest round, we are looking for engineers.'
        assert extract_compensation(text) is None

    def test_rejects_too_wide_range(self):
        # $50k–$400k span > 250k cap, likely false positive
        assert extract_compensation('Range is anywhere from $50,000 to $400,000.') is None

    def test_empty_text(self):
        assert extract_compensation('') is None

    def test_none_text(self):
        assert extract_compensation(None) is None

    def test_no_salary_mention(self):
        text = 'We are hiring a software engineer to work on our distributed systems.'
        assert extract_compensation(text) is None

    def test_funding_then_real_salary(self):
        # Common in startup descriptions: funding context followed by real comp.
        # Blocklist should strip the funding span, leaving the salary to match.
        text = ('We raised $50M Series C last year. The base salary range '
                'for this role is $140,000 - $190,000 plus equity.')
        r = extract_compensation(text)
        assert r is not None
        assert r['min'] == 140000 and r['max'] == 190000

    def test_inverted_range_is_rejected(self):
        # If hi < lo the sanity check fails.
        assert extract_compensation('Pay: $180,000 - $120,000') is None

    def test_result_shape(self):
        r = extract_compensation('Range: $100,000 - $150,000')
        assert set(r.keys()) == {'min', 'max', 'currency', 'source'}
        assert r['currency'] == 'USD'
        assert r['source'] == 'posting'
        assert isinstance(r['min'], int) and isinstance(r['max'], int)

    def test_and_up_to_connector(self):
        # Chime / older listings use this construction.
        text = 'The base salary offered for this role will begin at $65,000 and up to $90,000.'
        r = extract_compensation(text)
        assert r is not None
        assert r['min'] == 65000 and r['max'] == 90000

    def test_decimal_cents(self):
        # Some listings include .00 on the dollar amounts.
        r = extract_compensation('Base salary $140,000.00 and up to $165,000.00')
        assert r is not None
        assert r['min'] == 140000 and r['max'] == 165000

    def test_through_connector(self):
        r = extract_compensation('Pay range: $110,000 through $140,000 per year.')
        assert r is not None
        assert r['min'] == 110000 and r['max'] == 140000

    def test_html_wrapped_range(self):
        # Greenhouse/Lever return HTML; salary may be split across tags.
        text = '<p>Base salary range: <strong>$120,000</strong> &ndash; <strong>$180,000</strong></p>'
        r = extract_compensation(text)
        assert r is not None
        assert r['min'] == 120000 and r['max'] == 180000

    def test_html_entities(self):
        # &#36; is the HTML entity for $.
        text = 'Salary: &#36;100,000 to &#36;140,000'
        r = extract_compensation(text)
        assert r is not None
        assert r['min'] == 100000 and r['max'] == 140000


# ---------------------------------------------------------------------------
# fetch_greenhouse_jobs: regression — must request ?content=true so descriptions
# (and therefore comp / closed-flag detection) are populated.
# ---------------------------------------------------------------------------

class TestGreenhouseFetcherContentFlag:
    """Without ?content=true the GH API omits descriptions — silently zeros
    out comp extraction. Lock in the auto-append behavior."""

    def _mock_response(self, status=200, json_body=None):
        m = type('R', (), {})()
        m.status_code = status
        m.ok = 200 <= status < 300
        m.json = lambda: (json_body or {'jobs': []})
        m.raise_for_status = lambda: None
        m.text = ''
        return m

    def test_appends_content_true_when_missing(self):
        captured = {}
        def fake_get(url, *a, **kw):
            captured['url'] = url
            return self._mock_response(json_body={'jobs': []})
        with patch('update_jobs.limited_get', side_effect=fake_get):
            fetch_greenhouse_jobs('Affirm',
                                  'https://boards-api.greenhouse.io/v1/boards/affirm/jobs')
        assert 'content=true' in captured['url']

    def test_preserves_existing_query_params(self):
        captured = {}
        def fake_get(url, *a, **kw):
            captured['url'] = url
            return self._mock_response(json_body={'jobs': []})
        with patch('update_jobs.limited_get', side_effect=fake_get):
            fetch_greenhouse_jobs('Stripe',
                                  'https://boards-api.greenhouse.io/v1/boards/stripe/jobs?foo=bar')
        assert 'foo=bar' in captured['url']
        assert 'content=true' in captured['url']

    def test_does_not_double_append(self):
        captured = {}
        def fake_get(url, *a, **kw):
            captured['url'] = url
            return self._mock_response(json_body={'jobs': []})
        with patch('update_jobs.limited_get', side_effect=fake_get):
            fetch_greenhouse_jobs('Lever',
                                  'https://boards-api.greenhouse.io/v1/boards/lever/jobs?content=true')
        # exactly one occurrence
        assert captured['url'].count('content=true') == 1

    def test_extracts_comp_from_returned_content(self):
        # End-to-end: when GH returns content, comp shows up in the result dict.
        body = {'jobs': [{
            'id': 1, 'title': 'Software Engineer, New Grad',
            'location': {'name': 'San Francisco, CA'},
            'absolute_url': 'https://example.com/job/1',
            'updated_at': '2026-05-16T10:00:00Z',
            'content': 'The base salary range for this role is $120,000 - $180,000.',
        }]}
        def fake_get(url, *a, **kw):
            return self._mock_response(json_body=body)
        with patch('update_jobs.limited_get', side_effect=fake_get):
            jobs = fetch_greenhouse_jobs('TestCo',
                                         'https://boards-api.greenhouse.io/v1/boards/testco/jobs')
        assert len(jobs) == 1
        assert jobs[0]['comp'] == {'min': 120000, 'max': 180000,
                                   'currency': 'USD', 'source': 'posting'}

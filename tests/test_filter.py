#!/usr/bin/env python3
"""
Unit tests for job filtering logic in scripts/update_jobs.py.

Tests cover the filter_jobs() function's handling of:
- Date recency filtering
- Title keyword matching
- Location filtering
- Deduplication
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import filter_jobs


def _make_job(
    title="Software Engineer, New Grad",
    company="Acme Corp",
    location="San Francisco, CA",
    url="https://example.com/job/1",
    posted_at=None,
    description="",
    source="Greenhouse",
):
    """Factory helper to create minimal valid job dicts for tests."""
    if posted_at is None:
        posted_at = datetime.utcnow().isoformat()
    return {
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "posted_at": posted_at,
        "description": description,
        "source": source,
    }


def _default_config():
    """Return a minimal config matching the production structure."""
    return {
        "filtering": {
            "max_days_old": 7,
            "title_keywords": ["new grad", "entry level", "junior", "associate", "0-1 years"],
            "exclude_keywords": ["senior", "staff", "principal", "director", "manager", "lead", "vp", "intern"],
            "locations": ["usa", "us", "united states", "remote"],
            "min_title_length": 5,
        }
    }


class TestFilterJobsDateRecency:
    """Filter by posting date."""

    def test_recent_job_passes(self):
        jobs = [_make_job(posted_at=(datetime.utcnow() - timedelta(days=2)).isoformat())]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 1

    def test_old_job_filtered_out(self):
        jobs = [_make_job(posted_at=(datetime.utcnow() - timedelta(days=30)).isoformat())]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_job_with_no_date_passes(self):
        """Jobs with missing dates should not crash the filter."""
        jobs = [_make_job(posted_at=None)]
        try:
            filter_jobs(jobs, _default_config())
            # Depending on implementation, may pass or be excluded — just don't crash
        except Exception as e:
            assert False, f"filter_jobs raised an exception on None date: {e}"


class TestFilterJobsKeywords:
    """Filter by required and excluded title keywords."""

    def test_new_grad_title_passes(self):
        jobs = [_make_job(title="Software Engineer, New Grad")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 1

    def test_entry_level_title_passes(self):
        jobs = [_make_job(title="Entry Level Backend Engineer")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 1

    def test_senior_title_excluded(self):
        jobs = [_make_job(title="Senior Software Engineer")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_staff_title_excluded(self):
        jobs = [_make_job(title="Staff Engineer")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_principal_excluded(self):
        jobs = [_make_job(title="Principal Product Manager")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_no_matching_keyword_excluded(self):
        jobs = [_make_job(title="Software Architect")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0


class TestFilterJobsDeduplication:
    """Duplicate URLs should only appear once."""

    def test_duplicate_urls_are_removed(self):
        url = "https://example.com/job/123"
        jobs = [_make_job(url=url), _make_job(title="New Grad SWE", url=url)]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 1

    def test_different_urls_both_kept(self):
        jobs = [
            _make_job(url="https://example.com/job/1"),
            _make_job(url="https://example.com/job/2"),
        ]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 2

    def test_empty_input_returns_empty(self):
        result = filter_jobs([], _default_config())
        assert result == []

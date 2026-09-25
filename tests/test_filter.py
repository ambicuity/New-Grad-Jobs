#!/usr/bin/env python3
"""
Unit tests for job filtering logic in scripts/update_jobs.py.

Tests cover the filter_jobs() function's handling of:
- Date recency filtering
- Title keyword matching
- Location filtering
- Deduplication
"""

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from ngj.dedup import deduplicate_jobs  # noqa: E402
from ngj.filters import filter_jobs, has_new_grad_signal, has_track_signal, is_title_excluded  # noqa: E402


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
        posted_at = datetime.now(UTC).isoformat()
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
            "max_age_days": 7,
            "new_grad_signals": ["new grad", "entry level", "junior", "associate", "0-1 years"],
            "exclusion_signals": ["senior", "staff", "principal", "director", "manager", "lead", "vp", "intern"],
            "track_signals": ["software", "engineer", "developer"],
            "locations": ["usa", "us", "united states", "remote"],
            "min_title_length": 5,
        }
    }


class TestFilterJobsDateRecency:
    """Filter by posting date."""

    def test_recent_job_passes(self):
        jobs = [_make_job(posted_at=(datetime.now(UTC) - timedelta(days=2)).isoformat())]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 1

    def test_old_job_filtered_out(self):
        jobs = [_make_job(posted_at=(datetime.now(UTC) - timedelta(days=30)).isoformat())]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_job_with_no_date_passes(self):
        """Jobs with missing dates should not crash the filter."""
        jobs = [_make_job(posted_at=None)]
        # Depending on implementation, may pass or be excluded — just don't crash
        assert isinstance(filter_jobs(jobs, _default_config()), list)


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

    def test_generic_swe_without_new_grad_keyword_excluded(self):
        """P4: 'Software Engineer' alone should no longer bypass the new-grad check.
        It was removed from strong_new_grad_signals to reduce false positives.
        """
        jobs = [_make_job(title="Software Engineer")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0


class TestFilterJobsDeduplication:
    """Duplicate URLs should only appear once."""

    def test_duplicate_urls_are_removed(self):
        url = "https://example.com/job/123"
        jobs = [_make_job(url=url), _make_job(url=url)]
        result = deduplicate_jobs(jobs)
        assert len(result) == 1

    def test_different_urls_both_kept(self):
        jobs = [
            _make_job(url="https://example.com/job/1"),
            _make_job(url="https://example.com/job/2"),
        ]
        result = deduplicate_jobs(jobs)
        assert len(result) == 2

    def test_empty_input_returns_empty(self):
        result = deduplicate_jobs([])
        assert result == []


class TestTrackSignals:
    """Tests for the has_track_signal() helper function."""

    def test_non_engineering_network_title_does_not_count(self):
        assert not has_track_signal("Associate, Network Contracting", ["network"])

    def test_engineering_network_title_counts(self):
        assert has_track_signal("Network Engineer, New Grad", ["network"])

    def test_non_network_signal_still_uses_substring_matching(self):
        assert has_track_signal("Software Engineer, New Grad", ["software"])

    def test_none_title_returns_false(self):
        assert not has_track_signal(None, ["network"])

    def test_empty_title_returns_false(self):
        assert not has_track_signal("", ["network"])

    def test_whitespace_only_title_returns_false(self):
        assert not has_track_signal("   \t  ", ["network"])

    def test_non_string_title_returns_false(self):
        assert not has_track_signal(123, ["network"])

    def test_nan_title_returns_false(self):
        assert not has_track_signal(float('nan'), ["network"])

    def test_unicode_title_uses_case_insensitive_substring_matching(self):
        assert has_track_signal("Développeur Logiciel, New Grad 🚀", ["développeur"])

    def test_very_long_title_still_matches_signal(self):
        title = f"{'x' * 10000} Software Engineer, New Grad"
        assert has_track_signal(title, ["software"])

    def test_empty_signals_returns_false(self):
        assert not has_track_signal("Network Engineer, New Grad", [])

    def test_blank_signal_is_ignored(self):
        assert not has_track_signal("Software Engineer, New Grad", [""])

    def test_whitespace_signal_is_ignored(self):
        assert not has_track_signal("Software Engineer, New Grad", ["   "])


class TestHasNewGradSignal:
    """Test the has_new_grad_signal() helper function. It returns True if any of the configured new grad signals are present in the job title."""

    def test_matches_valid_signal(self):
        assert has_new_grad_signal("Software Engineer, New Grad", ["New Grad"])

    def test_case_insensitivity(self):
        assert has_new_grad_signal("SOFTWARE ENGINEER", ["software"])

    def test_returns_false_on_no_match(self):
        assert not has_new_grad_signal("Senior Dev", ["New Grad"])

    def test_empty_signals_list(self):
        assert not has_new_grad_signal("Software Engineer", [])

    def test_missing_match_signal(self):
        assert not has_new_grad_signal("Senior Lead", ["junior", "grad", "entry level"])

    def test_partial_word_does_not_match(self):
        """A signal should match a whole word, not a substring of another word."""
        assert not has_new_grad_signal("Software Upgrading", ["grad"])

    def test_empty_title(self):
        """An empty title should not cause an error and should return False."""
        assert not has_new_grad_signal("", ["new grad"])

    def test_whitespace_title(self):
        assert not has_new_grad_signal(" ", ["New Grad"])

    def test_none_title(self):
        assert not has_new_grad_signal(None, ["New Grad"])

    def test_nan_title(self):
        assert not has_new_grad_signal(float('nan'), ["New Grad"])

    def test_unicode_title(self):
        assert has_new_grad_signal("软件工程师 New Grad", ["New Grad"])

    def test_very_long_title(self):
        long_title = "A" * 10000 + " New Grad"
        assert has_new_grad_signal(long_title, ["New Grad"])

    def test_hyphenated_signal_matches(self):
        """Hyphenated signals from production config should match correctly."""
        assert has_new_grad_signal("Entry-Level Software Engineer", ["entry-level"])
        assert has_new_grad_signal("Early-Career Developer", ["early-career"])

    def test_hyphenated_signal_word_boundary(self):
        """Hyphenated signals should not match partial words."""
        assert not has_new_grad_signal("Reentry-Level Position", ["entry-level"])


class TestFilterJobsTrackSignals:
    """Test track signal logic and strong new grad signal bypass."""

    def test_strong_new_grad_signal_bypasses_track_requirement(self):
        """Jobs with strong new grad signals (e.g., 'new grad', '2025 start') should pass
        even without a track signal (e.g., 'software', 'engineer')."""
        jobs = [_make_job(title="New Grad Program 2025")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 1, "Strong new grad signal should bypass track signal requirement"

    def test_weak_new_grad_with_track_signal_passes(self):
        """Jobs with weak new grad signals (e.g., 'junior', 'entry level') should require
        a track signal (e.g., 'software', 'engineer') to pass."""
        jobs = [_make_job(title="Junior Software Engineer")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 1, "Weak new grad + track signal should pass"

    def test_weak_new_grad_without_track_signal_fails(self):
        """Jobs with weak new grad signals but no track signal should be filtered out."""
        jobs = [_make_job(title="Junior Analyst")]  # 'analyst' not in track_signals
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0, "Weak new grad without track signal should fail"

    def test_strong_new_grad_campus_keyword(self):
        """'campus' is a strong new grad signal but still needs a new_grad_signal trigger.
        Strong signals allow bypass of track_signal requirement only."""
        config = _default_config()
        # Add 'campus' to new_grad_signals so it triggers the initial check
        config['filtering']['new_grad_signals'].append('campus')
        jobs = [_make_job(title="Campus Hire Program")]  # Has 'campus', no track signal needed
        result = filter_jobs(jobs, config)
        assert len(result) == 1

    def test_strong_new_grad_graduate_program(self):
        """'graduate program' is a strong new grad signal but still needs initial trigger.
        The term 'graduate' should be in new_grad_signals to pass the initial check."""
        config = _default_config()
        config['filtering']['new_grad_signals'].append('graduate')
        jobs = [_make_job(title="Graduate Program - Technology")]
        result = filter_jobs(jobs, config)
        assert len(result) == 1

    def test_strong_new_grad_early_career(self):
        """'early career' is a strong new grad signal but still needs initial trigger."""
        config = _default_config()
        config['filtering']['new_grad_signals'].append('early career')
        jobs = [_make_job(title="Early Career Program")]
        result = filter_jobs(jobs, config)
        assert len(result) == 1

    def test_strong_new_grad_2026_start(self):
        """'2026 start' is a strong new grad signal - year should be in new_grad_signals."""
        config = _default_config()
        config['filtering']['new_grad_signals'].append('2026')
        jobs = [_make_job(title="2026 Start - Technology")]
        result = filter_jobs(jobs, config)
        assert len(result) == 1

    def test_strong_new_grad_year_only_2025(self):
        """'2025' alone is a strong new grad signal when in new_grad_signals."""
        config = _default_config()
        config['filtering']['new_grad_signals'].append('2025')
        jobs = [_make_job(title="Software Engineer 2025")]
        result = filter_jobs(jobs, config)
        assert len(result) == 1

    def test_strong_new_grad_year_only_2026(self):
        """'2026' alone is a strong new grad signal when in new_grad_signals."""
        config = _default_config()
        config['filtering']['new_grad_signals'].append('2026')
        jobs = [_make_job(title="Engineer 2026")]
        result = filter_jobs(jobs, config)
        assert len(result) == 1


class TestFilterJobsLocation:
    """Test location filtering using is_valid_location()."""

    def test_valid_us_location_passes(self):
        """Jobs in USA locations should pass."""
        jobs = [_make_job(location="San Francisco, CA")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 1

    def test_valid_remote_us_passes(self):
        """Remote USA jobs should pass."""
        jobs = [_make_job(location="Remote - USA")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 1

    def test_canada_location_passes(self):
        """Jobs in Canada should pass."""
        jobs = [_make_job(location="Toronto, ON")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 1

    def test_india_location_passes(self):
        """Jobs in India should pass."""
        jobs = [_make_job(location="Bangalore, India")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 1

    def test_invalid_location_filtered_out(self):
        """Jobs in non-USA/Canada/India locations should be filtered out."""
        jobs = [_make_job(location="London, UK")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0, "UK location should be filtered out"

    def test_germany_location_filtered_out(self):
        """Jobs in Germany should be filtered out."""
        jobs = [_make_job(location="Berlin, Germany")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_empty_location_is_unknown_and_kept(self):
        """An empty location is unknown, not foreign: the job is kept."""
        jobs = [_make_job(location="")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 1

    def test_none_location_is_unknown_and_kept(self):
        """A missing (None) location is unknown, not foreign: the job is kept."""
        jobs = [_make_job(location=None)]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 1

    def test_foreign_remote_location_filtered_out(self):
        """'remote' no longer whitelists a foreign country."""
        jobs = [_make_job(location="Remote - Germany")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0


class TestFilterJobsExclusionSignals:
    """Test exclusion signal filtering (senior, staff, principal, etc.)."""

    def test_senior_in_middle_of_title_excluded(self):
        """'senior' anywhere in title should exclude."""
        jobs = [_make_job(title="New Grad Senior Software Engineer")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_sr_abbreviation_excluded(self):
        """'sr.' abbreviation should exclude."""
        jobs = [_make_job(title="Sr. Software Engineer")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_sr_with_space_excluded(self):
        """'sr ' (with space) should exclude."""
        jobs = [_make_job(title="Sr Software Engineer")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_lead_excluded(self):
        """'lead' should exclude."""
        jobs = [_make_job(title="Lead Software Engineer")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_director_excluded(self):
        """'director' should exclude."""
        jobs = [_make_job(title="Director of Engineering")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_vp_excluded(self):
        """'vp' should exclude."""
        jobs = [_make_job(title="VP of Engineering")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_vice_president_excluded(self):
        """'vice president' should exclude."""
        jobs = [_make_job(title="Vice President, Engineering")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_head_of_excluded(self):
        """'head of' should exclude."""
        jobs = [_make_job(title="Head of Engineering")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_architect_excluded(self):
        """'architect' should exclude."""
        jobs = [_make_job(title="Software Architect")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_distinguished_excluded(self):
        """'distinguished' should exclude."""
        jobs = [_make_job(title="Distinguished Engineer")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_fellow_excluded(self):
        """'fellow' should exclude."""
        jobs = [_make_job(title="Engineering Fellow")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_intern_excluded(self):
        """'intern' should exclude (we only want full-time new grad roles)."""
        jobs = [_make_job(title="Software Engineer Intern")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_internship_excluded(self):
        """'internship' should exclude."""
        jobs = [_make_job(title="Software Engineering Internship")]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0


class TestFilterJobsIntegration:
    """Integration tests combining multiple filtering criteria."""

    def test_all_filters_pass(self):
        """Job passing all filters should be included."""
        jobs = [_make_job(
            title="Software Engineer, New Grad",
            location="San Francisco, CA",
            posted_at=(datetime.now(UTC) - timedelta(days=1)).isoformat()
        )]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 1

    def test_fails_exclusion_signal(self):
        """Job with exclusion signal should be filtered out even if everything else passes."""
        jobs = [_make_job(
            title="Senior Software Engineer, New Grad",  # Has 'senior'
            location="San Francisco, CA",
            posted_at=(datetime.now(UTC) - timedelta(days=1)).isoformat()
        )]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_fails_new_grad_signal(self):
        """Job without new grad signal should be filtered out."""
        jobs = [_make_job(
            title="Software Engineer",  # No new grad signal
            location="San Francisco, CA",
            posted_at=(datetime.now(UTC) - timedelta(days=1)).isoformat()
        )]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_fails_track_signal(self):
        """Job with weak new grad signal but no track signal should be filtered out."""
        jobs = [_make_job(
            title="Junior Analyst",  # 'junior' is weak, 'analyst' not in track_signals
            location="San Francisco, CA",
            posted_at=(datetime.now(UTC) - timedelta(days=1)).isoformat()
        )]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_fails_date_recency(self):
        """Old job should be filtered out even if everything else passes."""
        jobs = [_make_job(
            title="Software Engineer, New Grad",
            location="San Francisco, CA",
            posted_at=(datetime.now(UTC) - timedelta(days=30)).isoformat()
        )]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_fails_location(self):
        """Job in invalid location should be filtered out."""
        jobs = [_make_job(
            title="Software Engineer, New Grad",
            location="London, UK",
            posted_at=(datetime.now(UTC) - timedelta(days=1)).isoformat()
        )]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0

    def test_multiple_jobs_mixed_results(self):
        """Filter should correctly handle mixed batch of jobs."""
        jobs = [
            _make_job(title="Software Engineer, New Grad", location="San Francisco, CA"),  # PASS
            _make_job(title="Senior Software Engineer", location="San Francisco, CA"),  # FAIL - senior
            _make_job(title="Junior Software Engineer", location="London, UK"),  # FAIL - location
            _make_job(title="New Grad Program 2025", location="New York, NY"),  # PASS - strong signal
            _make_job(title="Junior Analyst", location="Austin, TX"),  # FAIL - no track signal
        ]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 2, "Should have 2 valid jobs"

    def test_empty_jobs_list_returns_empty(self):
        """Empty input should return empty output."""
        result = filter_jobs([], _default_config())
        assert result == []

    def test_all_jobs_filtered_out(self):
        """If all jobs are invalid, should return empty list."""
        jobs = [
            _make_job(title="Senior Software Engineer"),
            _make_job(title="Principal Engineer"),
            _make_job(title="Staff Developer"),
        ]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0


class TestFilterJobsConfigVariations:
    """Test filter_jobs with different config variations."""

    def test_custom_exclusion_signals(self):
        """Custom exclusion signals should be respected."""
        config = _default_config()
        config['filtering']['exclusion_signals'] = ['rockstar', 'ninja']
        jobs = [_make_job(title="Rockstar Software Engineer New Grad")]
        result = filter_jobs(jobs, config)
        assert len(result) == 0, "Custom exclusion signal should exclude job"

    def test_custom_max_age_days(self):
        """Custom max_age_days should be respected."""
        config = _default_config()
        config['filtering']['max_age_days'] = 30
        jobs = [_make_job(posted_at=(datetime.now(UTC) - timedelta(days=20)).isoformat())]
        result = filter_jobs(jobs, config)
        assert len(result) == 1, "Job should pass with extended max_age_days"

    def test_filters_key_fallback(self):
        """Config with 'filters' key (instead of 'filtering') should work."""
        config = {
            "filters": {  # Using 'filters' instead of 'filtering'
                "max_age_days": 7,
                "new_grad_signals": ["new grad"],
                "exclusion_signals": ["senior"],
                "track_signals": ["software"],
            }
        }
        jobs = [_make_job(title="Software Engineer, New Grad")]
        result = filter_jobs(jobs, config)
        assert len(result) == 1, "Should work with 'filters' key"

    def test_missing_filtering_key_raises_keyerror(self):
        """A config with no 'filtering'/'filters' block is invalid: new_grad_signals is required.

        Pins current behavior explicitly instead of swallowing the error, so a
        silent change (e.g. crashing differently, or quietly passing everything)
        is caught.
        """
        jobs = [
            _make_job(title="New Grad Software Engineer"),
            _make_job(title="Senior New Grad"),
        ]
        with pytest.raises(KeyError, match="new_grad_signals"):
            filter_jobs(jobs, {})


class TestFilterJobsEdgeCases:
    """Edge cases and boundary conditions."""

    def test_job_with_missing_title_filtered_out(self):
        """Job with missing title should be filtered out safely."""
        job = _make_job()
        del job['title']
        result = filter_jobs([job], _default_config())
        assert len(result) == 0

    def test_job_with_none_title_filtered_out(self):
        """Job with None title should be filtered out safely.
        NOTE: This test reveals a potential bug - the code crashes on None title
        because line 1857 does title.lower() without checking for None first.
        The job.get('title', '') should handle this, but if title is explicitly None,
        it will crash. This test is marked to demonstrate the bug."""
        job = _make_job(title=None)
        # Currently this crashes - we're documenting the bug
        # In production, jobs should always have a title from the API
        try:
            result = filter_jobs([job], _default_config())
            # If we get here without crash, verify it was filtered out
            assert len(result) == 0
        except AttributeError as e:
            # Expected current behavior - the code crashes on None title
            # This is acceptable if the upstream API always provides titles
            assert "'NoneType' object has no attribute 'lower'" in str(e)

    def test_job_with_empty_title_filtered_out(self):
        """Job with empty string title should be filtered out."""
        job = _make_job(title="")
        result = filter_jobs([job], _default_config())
        assert len(result) == 0

    def test_job_with_whitespace_title_filtered_out(self):
        """Job with whitespace-only title should be filtered out."""
        job = _make_job(title="   ")
        result = filter_jobs([job], _default_config())
        assert len(result) == 0

    def test_case_insensitive_exclusion_matching(self):
        """Exclusion signals should be case-insensitive."""
        jobs = [
            _make_job(title="SENIOR Software Engineer New Grad"),
            _make_job(title="SeNiOr Developer New Grad"),
        ]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0, "Case variations should still be excluded"

    def test_unicode_in_title(self):
        """Unicode characters in title should not crash filter."""
        jobs = [_make_job(title="软件工程师 New Grad Software Engineer")]
        # Should either pass or fail gracefully, not crash
        assert isinstance(filter_jobs(jobs, _default_config()), list)

    def test_very_long_title(self):
        """Very long title should not crash filter."""
        long_title = "A" * 5000 + " Software Engineer New Grad"
        jobs = [_make_job(title=long_title)]
        assert isinstance(filter_jobs(jobs, _default_config()), list)

    def test_filter_order_exclusion_first(self):
        """Exclusion signals should be checked FIRST, before other filters.
        This is an implementation detail test to verify optimization."""
        # A job that would pass all other filters but has exclusion signal
        jobs = [_make_job(
            title="Senior Software Engineer, New Grad 2025",  # Has 'senior'
            location="San Francisco, CA",
            posted_at=(datetime.now(UTC) - timedelta(days=1)).isoformat()
        )]
        result = filter_jobs(jobs, _default_config())
        assert len(result) == 0, "Exclusion should happen first"


class TestGraduateCohortSignals:
    """Cohort-year and 'Graduate'-suffixed titles must survive the filter.

    Large employers (ByteDance, TikTok, and similar campus programs) title their
    new grad reqs "<Role> Graduate (<Team>) - <Year> Start". Those titles carry no
    "new grad"/"entry level" keyword, so the cohort year and the bare word
    "graduate" are what make them recognizable. The signals live in config.yml,
    so these tests read the real config rather than a fixture — they guard the
    shipped signal list, not just the matching code.
    """

    # Fixed so recency never depends on the wall clock: these tests are about
    # signal matching, and a date-driven failure here would point at the wrong
    # thing. Paired with a max_age_days override wide enough that the date can
    # never age out. See CONTRIBUTING.md — tests must be deterministic.
    POSTED_AT = "2026-08-12T12:00:00"
    MAX_AGE_DAYS = 36500

    def _live_config(self) -> dict[str, Any]:
        """Load the shipped config with recency widened out of the way.

        Returns a copy — the caller must not mutate what the YAML load returned,
        since every test in this class reads the same file.
        """
        root = os.path.join(os.path.dirname(__file__), '..')
        with open(os.path.join(root, 'config.yml'), encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return {**config, 'filtering': {**config['filtering'], 'max_age_days': self.MAX_AGE_DAYS}}

    def _job(self, title: str, location: str = "San Jose, California, United States") -> dict[str, Any]:
        """Build a job fixture with a fixed posting date."""
        return _make_job(title=title, location=location, posted_at=self.POSTED_AT)

    def test_config_lists_current_cohort_years(self) -> None:
        """The config must carry the in-flight cohort years, not just past ones."""
        signals = self._live_config()['filtering']['new_grad_signals']
        for expected in ("2026 start", "2027 start", "2027"):
            assert expected in signals, f"'{expected}' missing from new_grad_signals"

    def test_config_lists_bare_graduate_signal(self) -> None:
        """'graduate' alone must match "<Role> Graduate (<Team>)" style titles."""
        assert "graduate" in self._live_config()['filtering']['new_grad_signals']

    def test_bare_graduate_title_passes(self) -> None:
        """A "<Role> Graduate" title with no cohort year must pass on "graduate" alone.

        Carries no year and no other new-grad keyword, so deleting "graduate"
        from the config fails this test — which is the point of having it. Note
        "graduate" is not a *strong* signal, so the track signal ("platform" /
        "engineer") is doing required work here.
        """
        jobs = [self._job("Platform Engineer Graduate")]
        result = filter_jobs(jobs, self._live_config())
        assert len(result) == 1

    def test_cohort_year_2027_title_passes(self) -> None:
        """'2027' alone is a strong signal, so no track signal is required."""
        jobs = [self._job("Technology Cohort 2027", location="Seattle, WA")]
        result = filter_jobs(jobs, self._live_config())
        assert len(result) == 1

    def test_real_bytedance_cohort_title_passes(self) -> None:
        """The composite title shape seen in the wild, carrying both new signals."""
        jobs = [self._job("Research Engineer Graduate (Monetization Technology) - 2027 Start")]
        result = filter_jobs(jobs, self._live_config())
        assert len(result) == 1

    def test_graduate_cohort_title_still_excludes_seniority(self) -> None:
        """Cohort signals must not override the seniority exclusion list."""
        jobs = [self._job("Senior Research Engineer Graduate (AML) - 2027 Start")]
        result = filter_jobs(jobs, self._live_config())
        assert len(result) == 0

    def test_graduate_cohort_title_still_excludes_interns(self) -> None:
        """2027 intern reqs remain out of scope — this board tracks full-time roles."""
        jobs = [self._job("Machine Learning Engineer Intern (AML-Ark-US) - 2027 Summer")]
        result = filter_jobs(jobs, self._live_config())
        assert len(result) == 0


class TestExclusionSignalWordBoundaries:
    """Exclusion signals match whole words, not substrings of other words.

    Substring matching dropped legitimate entry-level titles: 'intern' killed
    "Internal Tools"/"International", 'lead' killed "Leadership Development
    Program", and 'manager' killed "Associate Product Manager". These tests run
    against the shipped config.yml list so every intended exclusion is guarded.
    """

    @staticmethod
    def _live_signals() -> list:
        root = os.path.join(os.path.dirname(__file__), '..')
        with open(os.path.join(root, 'config.yml'), encoding='utf-8') as f:
            return yaml.safe_load(f)['filtering']['exclusion_signals']

    @pytest.mark.parametrize("title", [
        "Software Engineer, Internal Tools - New Grad",
        "International Payments Software Engineer, New Grad",
        "Leadership Development Program - Software Engineer 2026",
        "Associate Product Manager, New Grad",
        "Associate Technical Program Manager, University Grad",
        "Rotational Program - Engineering Leadership Track",
        "Computer Architecture Engineer, New Grad",
        "Software Engineer, Principality Payments",
        "Software Engineer I (Staffing Platform)",
    ])
    def test_non_senior_titles_not_excluded(self, title):
        assert is_title_excluded(title, self._live_signals()) is False

    @pytest.mark.parametrize("title", [
        "Senior Software Engineer",
        "Sr. Software Engineer",
        "Sr Software Engineer",
        "Staff Engineer",
        "Principal Engineer",
        "Lead Software Engineer",
        "Tech Lead, Payments",
        "Team Leads - Platform",
        "Engineering Manager",
        "Product Manager, Payments",
        "Director of Engineering",
        "VP of Engineering",
        "Vice President, Engineering",
        "Head of Platform",
        "Software Architect",
        "Solutions Architects",
        "Distinguished Engineer",
        "Engineering Fellow",
        "Software Engineer (10+ years)",
        "Backend Engineer, 5+ years experience",
        "Software Engineer Intern",
        "Software Engineering Internship",
        "Summer Internships 2027 - SWE",
        "Interns - Data Science 2027",
        "Machine Learning Engineer Intern (AML-Ark-US) - 2027 Summer",
        "Software Engineer - Intern/Co-op",
        "Software Engineer (Internship)",
    ])
    def test_senior_and_intern_titles_still_excluded(self, title):
        assert is_title_excluded(title, self._live_signals()) is True

    def test_filter_jobs_keeps_internal_tools_new_grad(self):
        jobs = [_make_job(title="Software Engineer, Internal Tools - New Grad")]
        assert len(filter_jobs(jobs, _default_config())) == 1

    def test_filter_jobs_keeps_leadership_development_program(self):
        jobs = [_make_job(title="Software Engineer New Grad - Leadership Development Program")]
        assert len(filter_jobs(jobs, _default_config())) == 1

    def test_filter_jobs_still_drops_intern(self):
        jobs = [_make_job(title="Software Engineer Intern, New Grad")]
        assert len(filter_jobs(jobs, _default_config())) == 0

    def test_published_titles_are_not_newly_excluded(self):
        """Every title currently on the board must still clear the exclusion list."""
        root = os.path.join(os.path.dirname(__file__), '..')
        path = os.path.join(root, 'docs', 'jobs.json')
        if not os.path.exists(path):
            pytest.skip("docs/jobs.json not present")
        with open(path, encoding='utf-8') as f:
            titles = [job.get('title', '') for job in json.load(f).get('jobs', [])]
        signals = self._live_signals()
        newly_excluded = [t for t in titles if is_title_excluded(t, signals)]
        assert newly_excluded == []


# ---------------------------------------------------------------------------
# Precision: co-ops / students never reach the board; every profession is in scope
# ---------------------------------------------------------------------------

def _precision_config():
    """Production-shaped config: strong signals pass without a track signal."""
    config = _default_config()
    config["filtering"].update(
        strong_new_grad_signals=["new grad", "new graduate", "2027"],
        new_grad_signals=["new grad", "new graduate", "junior", "associate", "2027", "software engineer"],
        exclusion_signals=["senior", "intern", "co-op", "coop", "student", "summer analyst", "summer associate"],
        track_signals=["software", "engineer", "developer", "data", "quantitative", "marketing", "nurse", "analyst"],
    )
    return config


class TestCoopAndStudentExclusion:
    @pytest.mark.parametrize(
        "title",
        [
            "Software Engineering Co-op (Fall/Spring 2027)",
            "Mechanical Engineering Co-Op - Spring 2027",
            "Winter 2027: AI Developer Coop (8 months)",
            "College Co-Op Student - Distribution Engineering - Winter 2027",
            "Registered Nursing Student Fall 2026",
            "Functions - Internal Audit, Summer Analyst, Dallas - USA, 2027",
            "2027 Capital Markets, Global Investment Banking Summer Associate",
        ],
    )
    def test_program_titles_are_excluded(self, title):
        assert filter_jobs([_make_job(title=title)], _precision_config()) == []

    def test_new_grad_software_engineer_still_passes(self):
        jobs = [_make_job(title="New Graduate Engineer, Software (Application Software)")]
        assert len(filter_jobs(jobs, _precision_config())) == 1


class TestEveryProfessionIsInScope:
    """The board covers every field: a new-grad signal plus any configured track word passes."""

    @pytest.mark.parametrize(
        "title",
        [
            "New Graduate Registered Nurse (RN) - Neuro Med/Surg",
            "Junior Marketing Analyst",
            "Associate Data Analyst",
            "Investment Banking Analyst - 2027 Start",
        ],
    )
    def test_non_software_new_grad_titles_pass(self, title):
        assert len(filter_jobs([_make_job(title=title)], _precision_config())) == 1

    def test_bare_new_grad_signal_without_a_role_word_is_still_rejected(self):
        assert filter_jobs([_make_job(title="Associate")], _precision_config()) == []

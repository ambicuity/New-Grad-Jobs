#!/usr/bin/env python3
"""Tests for job deduplication logic in scripts/update_jobs.py."""

import os
import sys
from typing import Dict, Any, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import deduplicate_jobs, get_job_key


def _make_job(**kwargs) -> Dict[str, Any]:
    """Helper to create minimal valid job dict"""
    defaults = {
        'company': 'Test Corp',
        'title': 'Engineer',
        'url': 'https://example.com/job',
        'posted_at': '2026-03-01',
    }
    defaults.update(kwargs)
    return defaults


class TestGetJobKey:
    """Tests for the get_job_key() function"""

    def test_basic_key_generation(self):
        """Test basic key generation with string fields"""
        job = _make_job(company='ACME Inc', title='Software Engineer', url='https://acme.com/job')
        key = get_job_key(job)
        assert key == "acme inc|software engineer|https://acme.com/job"

    def test_key_is_case_insensitive(self):
        """Test that company and title are lowercased in key"""
        job1 = _make_job(company='ACME', title='ENGINEER', url='https://example.com/job')
        job2 = _make_job(company='acme', title='engineer', url='https://example.com/job')
        assert get_job_key(job1) == get_job_key(job2)

    def test_key_strips_whitespace(self):
        """Test that whitespace is stripped"""
        job1 = _make_job(company='  ACME  ', title='  Engineer  ', url='https://example.com/job')
        job2 = _make_job(company='ACME', title='Engineer', url='https://example.com/job')
        assert get_job_key(job1) == get_job_key(job2)

    def test_key_with_none_values(self):
        """Test key generation with None values"""
        job = _make_job(company=None, title='Engineer', url=None)
        key = get_job_key(job)
        assert key == "|engineer|"

    def test_key_with_missing_fields(self):
        """Test key generation when fields are missing from dict"""
        job = {'url': 'https://example.com/job'}  # Missing company and title
        key = get_job_key(job)
        assert key == "||https://example.com/job"

    def test_key_with_nan_values(self):
        """Test that NaN values are converted to empty strings"""
        job = _make_job(company=float('nan'), title='Engineer', url='https://example.com/job')
        key = get_job_key(job)
        assert key == "|engineer|https://example.com/job"
        assert 'nan' not in key.lower()

    def test_key_with_inf_values(self):
        """Test that Inf values are converted to empty strings"""
        job = _make_job(company=float('inf'), title='Engineer', url='https://example.com/job')
        key = get_job_key(job)
        assert key == "|engineer|https://example.com/job"
        assert 'inf' not in key.lower()

    def test_key_with_numeric_values(self):
        """Test key generation with numeric values (e.g., from malformed API responses)"""
        job = _make_job(company=123, title=456, url=789)
        key = get_job_key(job)
        assert key == "123|456|789"

    def test_key_with_unicode_characters(self):
        """Test key generation preserves Unicode characters"""
        job = _make_job(company='Société Générale', title='Ingénieur Logiciel', url='https://example.com/job')
        key = get_job_key(job)
        # Unicode should be preserved
        assert 'société générale' in key
        assert 'ingénieur logiciel' in key

    def test_key_with_empty_strings(self):
        """Test key generation with empty string values"""
        job = _make_job(company='', title='', url='')
        key = get_job_key(job)
        assert key == "||"


class TestDeduplicateJobs:
    """Tests for the deduplicate_jobs() function"""

    def test_deduplicate_no_duplicates(self):
        """Test that unique jobs are preserved"""
        jobs = [
            _make_job(company='ACME', title='SWE', url='https://acme.com/swe'),
            _make_job(company='ACME', title='DevOps', url='https://acme.com/devops'),
            _make_job(company='TechCorp', title='SWE', url='https://tech.com/swe'),
        ]
        result = deduplicate_jobs(jobs)
        assert len(result) == 3
        assert result == jobs

    def test_deduplicate_removes_exact_duplicates(self, capsys):
        """Test that exact duplicate jobs are removed"""
        job = _make_job(company='ACME', title='SWE', url='https://acme.com/swe')
        jobs = [job, job, job]
        result = deduplicate_jobs(jobs)
        assert len(result) == 1
        assert result[0] == job
        # Check that deduplication message is printed
        captured = capsys.readouterr()
        assert "Removed 2 duplicate jobs" in captured.out

    def test_deduplicate_case_insensitive_matching(self, capsys):
        """Test that deduplication is case-insensitive for company/title"""
        job1 = _make_job(company='ACME', title='SOFTWARE ENGINEER', url='https://acme.com/swe')
        job2 = _make_job(company='acme', title='software engineer', url='https://acme.com/swe')
        jobs = [job1, job2]
        result = deduplicate_jobs(jobs)
        assert len(result) == 1
        assert result[0] == job1  # First occurrence is kept

    def test_deduplicate_preserves_order(self):
        """Test that deduplication preserves the order of first occurrence"""
        jobs = [
            _make_job(company='Company1', title='Title1', url='https://example.com/1'),
            _make_job(company='Company2', title='Title2', url='https://example.com/2'),
            _make_job(company='Company1', title='Title1', url='https://example.com/1'),  # Duplicate of first
            _make_job(company='Company3', title='Title3', url='https://example.com/3'),
        ]
        result = deduplicate_jobs(jobs)
        assert len(result) == 3
        assert result[0]['company'] == 'Company1'
        assert result[1]['company'] == 'Company2'
        assert result[2]['company'] == 'Company3'

    def test_deduplicate_handles_nan_values(self, capsys):
        """Test that jobs with NaN are deduplicated correctly"""
        job1 = _make_job(company='ACME', title=float('nan'), url='https://acme.com/job')
        job2 = _make_job(company='ACME', title=float('nan'), url='https://acme.com/job')
        jobs = [job1, job2]
        result = deduplicate_jobs(jobs)
        assert len(result) == 1

    def test_deduplicate_empty_list(self, capsys):
        """Test deduplication with empty list"""
        result = deduplicate_jobs([])
        assert len(result) == 0
        captured = capsys.readouterr()
        assert "Removed" not in captured.out  # No message for 0 removals

    def test_deduplicate_single_job(self):
        """Test deduplication with single job"""
        job = _make_job(company='ACME', title='SWE', url='https://acme.com/swe')
        result = deduplicate_jobs([job])
        assert len(result) == 1
        assert result[0] == job

    def test_deduplicate_url_field_critical(self):
        """Test that URL is part of the deduplication key"""
        # Same company and title, but different URLs should be kept separate
        job1 = _make_job(company='ACME', title='SWE', url='https://acme.com/job1')
        job2 = _make_job(company='ACME', title='SWE', url='https://acme.com/job2')
        jobs = [job1, job2]
        result = deduplicate_jobs(jobs)
        assert len(result) == 2

    def test_deduplicate_company_field_critical(self):
        """Test that company is part of the deduplication key"""
        # Same title and URL, but different companies should be kept separate
        job1 = _make_job(company='ACME', title='SWE', url='https://careers.example.com/swe')
        job2 = _make_job(company='TechCorp', title='SWE', url='https://careers.example.com/swe')
        jobs = [job1, job2]
        result = deduplicate_jobs(jobs)
        assert len(result) == 2

    def test_deduplicate_title_field_critical(self):
        """Test that title is part of the deduplication key"""
        # Same company and URL, but different titles should be kept separate
        job1 = _make_job(company='ACME', title='Software Engineer', url='https://acme.com/careers')
        job2 = _make_job(company='ACME', title='DevOps Engineer', url='https://acme.com/careers')
        jobs = [job1, job2]
        result = deduplicate_jobs(jobs)
        assert len(result) == 2

    def test_deduplicate_mixed_duplicates(self, capsys):
        """Test deduplication with various duplicate patterns"""
        jobs = [
            _make_job(company='ACME', title='SWE', url='https://acme.com/1'),
            _make_job(company='ACME', title='SWE', url='https://acme.com/1'),  # Exact duplicate
            _make_job(company='ACME', title='SWE', url='https://acme.com/2'),  # Different URL
            _make_job(company='ACME', title='SWE', url='https://acme.com/1'),  # Duplicate again
            _make_job(company='TechCorp', title='SWE', url='https://acme.com/1'),  # Different company
        ]
        result = deduplicate_jobs(jobs)
        assert len(result) == 3
        captured = capsys.readouterr()
        assert "Removed 2 duplicate jobs" in captured.out

    def test_deduplicate_whitespace_normalization(self, capsys):
        """Test that whitespace differences don't affect deduplication"""
        job1 = _make_job(company='  ACME  ', title='  SWE  ', url='https://acme.com/job')
        job2 = _make_job(company='ACME', title='SWE', url='https://acme.com/job')
        jobs = [job1, job2]
        result = deduplicate_jobs(jobs)
        assert len(result) == 1
        captured = capsys.readouterr()
        assert "Removed 1 duplicate jobs" in captured.out

    def test_deduplicate_preserves_job_data(self):
        """Test that deduplication preserves all job fields"""
        job = _make_job(
            company='ACME',
            title='SWE',
            url='https://acme.com/job',
            posted_at='2026-03-01',
            salary='150k',
            location='New York'
        )
        duplicate_job = {**job}  # Create an exact copy
        jobs = [job, duplicate_job]
        result = deduplicate_jobs(jobs)
        assert len(result) == 1
        # Verify all fields are preserved in the kept job
        assert result[0]['company'] == 'ACME'
        assert result[0]['title'] == 'SWE'
        assert result[0]['salary'] == '150k'
        assert result[0]['location'] == 'New York'

    def test_deduplicate_large_list(self):
        """Test deduplication with a large list to ensure no performance issues"""
        # Create 1000 jobs with 500 duplicates
        base_job = _make_job(company='ACME', title='SWE', url='https://acme.com/job')
        jobs = [base_job] * 500
        # Add 500 unique jobs
        for i in range(500):
            jobs.append(_make_job(company=f'Company{i}', title=f'Title{i}', url=f'https://example.com/{i}'))
        result = deduplicate_jobs(jobs)
        assert len(result) == 501

    def test_deduplicate_no_message_for_no_removals(self, capsys):
        """Test that no deduplication message is printed when no duplicates are removed"""
        jobs = [
            _make_job(company='ACME', title='SWE', url='https://acme.com/1'),
            _make_job(company='TechCorp', title='DevOps', url='https://tech.com/2'),
        ]
        result = deduplicate_jobs(jobs)
        assert len(result) == 2
        captured = capsys.readouterr()
        assert "Removed" not in captured.out

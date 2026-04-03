#!/usr/bin/env python3
"""Comprehensive tests for generate_jobs_json() in scripts/update_jobs.py.

Tests cover JSON structure generation, metadata calculation, category counting,
job sorting, and all edge cases for the main JSON output function.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import generate_jobs_json, CATEGORY_PATTERNS


class TestGenerateJobsJsonStructure:
    """Test JSON structure and metadata generation."""

    def test_empty_jobs_list_generates_valid_structure(self):
        """Empty job list should generate valid JSON with zero counts."""
        config = {}
        result = generate_jobs_json([], config)

        assert 'meta' in result
        assert 'jobs' in result
        assert result['meta']['total_jobs'] == 0
        assert result['jobs'] == []
        assert result['meta']['categories'] == []

    def test_meta_includes_generated_timestamp(self):
        """Meta section should include ISO timestamp of generation."""
        config = {}
        before = datetime.now()
        result = generate_jobs_json([], config)
        after = datetime.now()

        generated_at = result['meta']['generated_at']
        assert isinstance(generated_at, str)
        # Parse and verify it's between before/after
        generated_time = datetime.fromisoformat(generated_at)
        assert before <= generated_time <= after

    def test_meta_total_jobs_matches_job_count(self):
        """Meta total_jobs should match actual number of jobs in array."""
        jobs = [
            {'company': 'A', 'title': 'Job 1', 'url': 'http://a.com/1', 'posted_at': '2026-03-01'},
            {'company': 'B', 'title': 'Job 2', 'url': 'http://b.com/2', 'posted_at': '2026-03-02'},
            {'company': 'C', 'title': 'Job 3', 'url': 'http://c.com/3', 'posted_at': '2026-03-03'},
        ]
        config = {}
        result = generate_jobs_json(jobs, config)

        assert result['meta']['total_jobs'] == 3
        assert len(result['jobs']) == 3

    def test_job_objects_include_all_required_fields(self):
        """Each job object should have all required fields."""
        jobs = [{
            'id': 'test-123',
            'company': 'TestCo',
            'title': 'Software Engineer',
            'location': 'San Francisco, CA',
            'url': 'http://testco.com/job',
            'posted_at': '2026-03-15T10:00:00',
            'source': 'Greenhouse',
            'category': {'id': 'software_engineering', 'name': 'Software Engineering', 'emoji': '💻'},
            'company_tier': {'id': 'faang_plus', 'name': 'FAANG+', 'emoji': '🔥'},
            'flags': {'no_sponsorship': False, 'us_citizenship': False},
            'is_closed': False
        }]
        config = {}
        result = generate_jobs_json(jobs, config)

        job = result['jobs'][0]
        assert job['id'] == 'test-123'
        assert job['company'] == 'TestCo'
        assert job['title'] == 'Software Engineer'
        assert job['location'] == 'San Francisco, CA'
        assert job['url'] == 'http://testco.com/job'
        assert 'posted_at' in job
        assert 'posted_display' in job
        assert job['source'] == 'Greenhouse'
        assert job['category'] == {'id': 'software_engineering', 'name': 'Software Engineering', 'emoji': '💻'}
        assert job['company_tier'] == {'id': 'faang_plus', 'name': 'FAANG+', 'emoji': '🔥'}
        assert job['flags'] == {'no_sponsorship': False, 'us_citizenship': False}
        assert job['is_closed'] is False

    def test_missing_optional_fields_use_defaults(self):
        """Missing optional fields should use empty strings or default values."""
        jobs = [{'company': 'MinimalCo'}]  # Only company field
        config = {}
        result = generate_jobs_json(jobs, config)

        job = result['jobs'][0]
        assert job['id'] == ''
        assert job['company'] == 'MinimalCo'
        assert job['title'] == ''
        assert job['location'] == ''
        assert job['url'] == ''
        assert job['source'] == ''
        assert job['category'] == {}
        assert job['company_tier'] == {}
        assert job['flags'] == {}
        assert job['is_closed'] is False


class TestCategoryCountCalculation:
    """Test category count calculation in metadata."""

    def test_categories_counted_correctly(self):
        """Categories should be counted from job category IDs."""
        jobs = [
            {'company': 'A', 'category': {'id': 'software_engineering'}},
            {'company': 'B', 'category': {'id': 'software_engineering'}},
            {'company': 'C', 'category': {'id': 'data_ml'}},
            {'company': 'D', 'category': {'id': 'hardware'}},
            {'company': 'E', 'category': {'id': 'hardware'}},
            {'company': 'F', 'category': {'id': 'hardware'}},
        ]
        config = {}
        result = generate_jobs_json(jobs, config)

        categories = {cat['id']: cat['count'] for cat in result['meta']['categories']}
        assert categories['software_engineering'] == 2
        assert categories['data_ml'] == 1
        assert categories['hardware'] == 3

    def test_zero_count_categories_excluded_from_metadata(self):
        """Categories with zero jobs should not appear in metadata."""
        jobs = [
            {'company': 'A', 'category': {'id': 'software_engineering'}},
            {'company': 'B', 'category': {'id': 'data_ml'}},
        ]
        config = {}
        result = generate_jobs_json(jobs, config)

        category_ids = [cat['id'] for cat in result['meta']['categories']]
        assert 'software_engineering' in category_ids
        assert 'data_ml' in category_ids
        # These should not appear (zero count)
        assert 'hardware' not in category_ids
        assert 'quant_finance' not in category_ids
        assert 'product_management' not in category_ids

    def test_category_metadata_includes_name_and_emoji(self):
        """Category metadata should include name and emoji from CATEGORY_PATTERNS."""
        jobs = [
            {'company': 'A', 'category': {'id': 'software_engineering'}},
            {'company': 'B', 'category': {'id': 'data_ml'}},
        ]
        config = {}
        result = generate_jobs_json(jobs, config)

        categories = {cat['id']: cat for cat in result['meta']['categories']}

        swe = categories['software_engineering']
        assert swe['name'] == CATEGORY_PATTERNS['software_engineering']['name']
        assert swe['emoji'] == CATEGORY_PATTERNS['software_engineering']['emoji']

        ml = categories['data_ml']
        assert ml['name'] == CATEGORY_PATTERNS['data_ml']['name']
        assert ml['emoji'] == CATEGORY_PATTERNS['data_ml']['emoji']

    def test_missing_category_defaults_to_other(self):
        """Jobs without category should be counted as 'other'."""
        jobs = [
            {'company': 'A', 'category': {}},
            {'company': 'B'},  # No category field
            {'company': 'C', 'category': {'id': 'software_engineering'}},
        ]
        config = {}
        result = generate_jobs_json(jobs, config)

        categories = {cat['id']: cat['count'] for cat in result['meta']['categories']}
        # Jobs with missing/empty category default to 'other'
        assert categories.get('other', 0) == 2
        assert categories.get('software_engineering', 0) == 1

    def test_unknown_category_id_counted_separately(self):
        """Unknown category IDs should be counted but may not be in final metadata."""
        jobs = [
            {'company': 'A', 'category': {'id': 'software_engineering'}},
            {'company': 'B', 'category': {'id': 'unknown_category'}},
        ]
        config = {}
        result = generate_jobs_json(jobs, config)

        # Unknown categories are counted but not included in metadata
        # (only categories in CATEGORY_PATTERNS appear in metadata)
        category_ids = [cat['id'] for cat in result['meta']['categories']]
        assert 'software_engineering' in category_ids
        assert 'unknown_category' not in category_ids


class TestJobSorting:
    """Test job sorting by date."""

    def test_jobs_sorted_by_date_descending(self):
        """Jobs should be sorted by posted_at date in descending order (newest first)."""
        jobs = [
            {'company': 'A', 'posted_at': '2026-03-10'},
            {'company': 'B', 'posted_at': '2026-03-15'},  # Newest
            {'company': 'C', 'posted_at': '2026-03-01'},  # Oldest
            {'company': 'D', 'posted_at': '2026-03-12'},
        ]
        config = {}
        result = generate_jobs_json(jobs, config)

        companies = [job['company'] for job in result['jobs']]
        assert companies == ['B', 'D', 'A', 'C']

    def test_jobs_with_datetime_objects_sort_correctly(self):
        """Jobs with datetime objects should sort by datetime descending."""
        jobs = [
            {'company': 'A', 'posted_at': datetime(2026, 3, 10, 12, 0, 0)},
            {'company': 'B', 'posted_at': datetime(2026, 3, 15, 8, 30, 0)},
            {'company': 'C', 'posted_at': datetime(2026, 3, 15, 14, 45, 0)},
        ]
        config = {}
        result = generate_jobs_json(jobs, config)

        companies = [job['company'] for job in result['jobs']]
        assert companies == ['C', 'B', 'A']

    def test_jobs_with_missing_dates_sorted_to_end(self):
        """Jobs with missing/None posted_at should appear at the end."""
        jobs = [
            {'company': 'A', 'posted_at': '2026-03-15'},
            {'company': 'B', 'posted_at': None},
            {'company': 'C', 'posted_at': '2026-03-10'},
            {'company': 'D'},  # Missing posted_at
        ]
        config = {}
        result = generate_jobs_json(jobs, config)

        companies = [job['company'] for job in result['jobs']]
        # A and C sorted by date, B and D at the end
        assert companies[:2] == ['A', 'C']
        assert set(companies[2:]) == {'B', 'D'}

    def test_jobs_with_unix_timestamps_sorted_correctly(self):
        """Jobs with Unix timestamps (milliseconds) should sort correctly."""
        base_time = datetime(2026, 3, 15, 0, 0, 0, tzinfo=timezone.utc)
        jobs = [
            {'company': 'A', 'posted_at': int(base_time.timestamp() * 1000)},  # Now
            {'company': 'B', 'posted_at': int((base_time - timedelta(days=5)).timestamp() * 1000)},  # 5 days ago
            {'company': 'C', 'posted_at': int((base_time + timedelta(hours=2)).timestamp() * 1000)},  # 2 hours future
        ]
        config = {}
        result = generate_jobs_json(jobs, config)

        companies = [job['company'] for job in result['jobs']]
        assert companies == ['C', 'A', 'B']


class TestDateFormatting:
    """Test date formatting in job output."""

    def test_posted_at_converted_to_iso_format(self):
        """posted_at should be converted to ISO format string."""
        jobs = [{'company': 'A', 'posted_at': datetime(2026, 3, 15, 14, 30, 0)}]
        config = {}
        result = generate_jobs_json(jobs, config)

        posted_at = result['jobs'][0]['posted_at']
        assert isinstance(posted_at, str)
        assert '2026-03-15' in posted_at

    def test_posted_display_human_readable(self):
        """posted_display should be human-readable format."""
        jobs = [{'company': 'A', 'posted_at': '2026-03-15T10:00:00'}]
        config = {}
        result = generate_jobs_json(jobs, config)

        posted_display = result['jobs'][0]['posted_display']
        assert isinstance(posted_display, str)
        # Should be something like "3 days ago" or similar human format
        assert posted_display != ''

    def test_none_posted_at_handled_gracefully(self):
        """None posted_at should not cause errors."""
        jobs = [{'company': 'A', 'posted_at': None}]
        config = {}
        result = generate_jobs_json(jobs, config)

        # Should not crash, should have some default value
        assert 'posted_at' in result['jobs'][0]
        assert 'posted_display' in result['jobs'][0]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_large_job_list_processed_correctly(self):
        """Large job lists should be processed without errors."""
        jobs = [
            {
                'company': f'Company{i}',
                'title': f'Job {i}',
                'url': f'http://company{i}.com/job',
                'posted_at': f'2026-03-{(i % 28) + 1:02d}',
                'category': {'id': 'software_engineering'}
            }
            for i in range(1000)
        ]
        config = {}
        result = generate_jobs_json(jobs, config)

        assert result['meta']['total_jobs'] == 1000
        assert len(result['jobs']) == 1000

    def test_special_characters_in_job_fields(self):
        """Special characters in job fields should be preserved."""
        jobs = [{
            'company': 'Test & Co. <Company>',
            'title': 'Engineer "Senior" (L4)',
            'location': "San Francisco's Bay Area",
            'url': 'http://test.com/job?id=123&dept=eng',
        }]
        config = {}
        result = generate_jobs_json(jobs, config)

        job = result['jobs'][0]
        assert job['company'] == 'Test & Co. <Company>'
        assert job['title'] == 'Engineer "Senior" (L4)'
        assert job['location'] == "San Francisco's Bay Area"
        assert job['url'] == 'http://test.com/job?id=123&dept=eng'

    def test_unicode_characters_handled_correctly(self):
        """Unicode characters should be handled correctly."""
        jobs = [{
            'company': 'Café Résumé™',
            'title': '软件工程师 Software Engineer',
            'location': 'München, Deutschland 🇩🇪',
        }]
        config = {}
        result = generate_jobs_json(jobs, config)

        job = result['jobs'][0]
        assert job['company'] == 'Café Résumé™'
        assert job['title'] == '软件工程师 Software Engineer'
        assert job['location'] == 'München, Deutschland 🇩🇪'

    def test_all_categories_represented_correctly(self):
        """All CATEGORY_PATTERNS categories should be represented when present."""
        jobs = [
            {'company': 'A', 'category': {'id': 'software_engineering'}},
            {'company': 'B', 'category': {'id': 'data_ml'}},
            {'company': 'C', 'category': {'id': 'data_engineering'}},
            {'company': 'D', 'category': {'id': 'infrastructure_sre'}},
            {'company': 'E', 'category': {'id': 'product_management'}},
            {'company': 'F', 'category': {'id': 'quant_finance'}},
            {'company': 'G', 'category': {'id': 'hardware'}},
            {'company': 'H', 'category': {'id': 'other'}},
        ]
        config = {}
        result = generate_jobs_json(jobs, config)

        category_ids = {cat['id'] for cat in result['meta']['categories']}
        assert category_ids == {
            'software_engineering', 'data_ml', 'data_engineering',
            'infrastructure_sre', 'product_management', 'quant_finance',
            'hardware', 'other'
        }

    def test_duplicate_jobs_not_deduplicated(self):
        """generate_jobs_json should not deduplicate - that's done earlier."""
        jobs = [
            {'company': 'A', 'title': 'Engineer', 'url': 'http://a.com/1'},
            {'company': 'A', 'title': 'Engineer', 'url': 'http://a.com/1'},  # Exact duplicate
        ]
        config = {}
        result = generate_jobs_json(jobs, config)

        # Both should be present (deduplication happens in filter_jobs)
        assert len(result['jobs']) == 2
        assert result['meta']['total_jobs'] == 2

    def test_config_parameter_not_used(self):
        """Config parameter exists but is not currently used by the function."""
        jobs = [{'company': 'A', 'title': 'Job 1'}]
        config_1 = {'some': 'config'}
        config_2 = {}

        result_1 = generate_jobs_json(jobs, config_1)
        result_2 = generate_jobs_json(jobs, config_2)

        # Results should be identical regardless of config
        assert result_1['meta']['total_jobs'] == result_2['meta']['total_jobs']
        assert len(result_1['jobs']) == len(result_2['jobs'])

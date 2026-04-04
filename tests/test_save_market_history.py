"""
Tests for save_market_history() function.

Tests the market history snapshot generation and persistence function that:
- Creates daily market snapshots with job statistics
- Manages 90-day rolling history retention
- Handles file I/O with error recovery
"""

import sys
import os
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import update_jobs


class TestSaveMarketHistoryStructure:
    """Test snapshot structure and metadata generation."""

    def setup_method(self):
        """Create temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.history_path = os.path.join(self.temp_dir, 'market-history.json')
        # Temporarily replace the history path construction
        self.original_join = os.path.join

        def mock_join(*args):
            if 'market-history.json' in args:
                return self.history_path
            return self.original_join(*args)

        os.path.join = mock_join

    def teardown_method(self):
        """Clean up temporary directory."""
        os.path.join = self.original_join
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_creates_valid_snapshot_structure(self):
        """Snapshot has all required fields with correct types."""
        jobs = [
            {
                'company': 'Google',
                'categories': ['swe'],
                'company_tier': {'tier': 'faang-plus'}
            }
        ]

        update_jobs.save_market_history(jobs)

        assert os.path.exists(self.history_path)
        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert 'meta' in data
        assert 'snapshots' in data
        assert len(data['snapshots']) == 1

        snapshot = data['snapshots'][0]
        assert 'date' in snapshot
        assert 'total_jobs' in snapshot
        assert 'categories' in snapshot
        assert 'tiers' in snapshot
        assert 'top_companies' in snapshot
        assert 'unique_companies' in snapshot
        assert 'avg_jobs_per_company' in snapshot
        assert 'timestamp' in snapshot

    def test_metadata_includes_date_range(self):
        """Meta section includes last_updated, total_snapshots, and date_range."""
        jobs = [{'company': 'Stripe', 'categories': ['swe'], 'company_tier': {'tier': 'unicorn'}}]
        update_jobs.save_market_history(jobs)

        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        meta = data['meta']
        assert 'last_updated' in meta
        assert 'total_snapshots' in meta
        assert meta['total_snapshots'] == 1
        assert 'date_range' in meta
        assert 'start' in meta['date_range']
        assert 'end' in meta['date_range']

    def test_snapshot_date_format(self):
        """Snapshot date uses YYYY-MM-DD format."""
        jobs = [{'company': 'Meta', 'categories': ['ml'], 'company_tier': {'tier': 'faang-plus'}}]
        update_jobs.save_market_history(jobs)

        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        snapshot_date = data['snapshots'][0]['date']
        # Should match YYYY-MM-DD format
        assert len(snapshot_date) == 10
        assert snapshot_date.count('-') == 2
        datetime.strptime(snapshot_date, '%Y-%m-%d')  # Should not raise


class TestCategoryAndTierCounting:
    """Test category and tier aggregation logic."""

    def setup_method(self):
        """Create temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.history_path = os.path.join(self.temp_dir, 'market-history.json')
        self.original_join = os.path.join

        def mock_join(*args):
            if 'market-history.json' in args:
                return self.history_path
            return self.original_join(*args)

        os.path.join = mock_join

    def teardown_method(self):
        """Clean up temporary directory."""
        os.path.join = self.original_join
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_counts_categories_correctly(self):
        """Categories are counted across all jobs."""
        jobs = [
            {'company': 'Google', 'categories': ['swe', 'ml'], 'company_tier': {'tier': 'faang-plus'}},
            {'company': 'Meta', 'categories': ['swe'], 'company_tier': {'tier': 'faang-plus'}},
            {'company': 'Stripe', 'categories': ['data'], 'company_tier': {'tier': 'unicorn'}},
        ]

        update_jobs.save_market_history(jobs)

        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        categories = data['snapshots'][0]['categories']
        assert categories['swe'] == 2
        assert categories['ml'] == 1
        assert categories['data'] == 1

    def test_counts_tiers_correctly(self):
        """Company tiers are counted correctly."""
        jobs = [
            {'company': 'Google', 'categories': ['swe'], 'company_tier': {'tier': 'faang-plus'}},
            {'company': 'Meta', 'categories': ['swe'], 'company_tier': {'tier': 'faang-plus'}},
            {'company': 'Stripe', 'categories': ['swe'], 'company_tier': {'tier': 'unicorn'}},
            {'company': 'Unknown Startup', 'categories': ['swe'], 'company_tier': {'tier': 'other'}},
        ]

        update_jobs.save_market_history(jobs)

        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        tiers = data['snapshots'][0]['tiers']
        assert tiers['faang-plus'] == 2
        assert tiers['unicorn'] == 1
        assert tiers['other'] == 1

    def test_missing_categories_empty(self):
        """Jobs without categories field result in empty category counts."""
        jobs = [
            {'company': 'Google', 'company_tier': {'tier': 'faang-plus'}},  # no categories
        ]

        update_jobs.save_market_history(jobs)

        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        categories = data['snapshots'][0]['categories']
        assert categories == {}

    def test_missing_tier_defaults_to_other(self):
        """Jobs without tier default to 'other'."""
        jobs = [
            {'company': 'Google', 'categories': ['swe']},  # no company_tier
            {'company': 'Meta', 'categories': ['swe'], 'company_tier': {}},  # empty tier
        ]

        update_jobs.save_market_history(jobs)

        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        tiers = data['snapshots'][0]['tiers']
        assert tiers['other'] == 2


class TestTopCompanies:
    """Test top companies ranking and statistics."""

    def setup_method(self):
        """Create temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.history_path = os.path.join(self.temp_dir, 'market-history.json')
        self.original_join = os.path.join

        def mock_join(*args):
            if 'market-history.json' in args:
                return self.history_path
            return self.original_join(*args)

        os.path.join = mock_join

    def teardown_method(self):
        """Clean up temporary directory."""
        os.path.join = self.original_join
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_top_companies_limited_to_10(self):
        """Top companies list is capped at 10 entries."""
        jobs = [
            {'company': f'Company{i}', 'categories': ['swe'], 'company_tier': {'tier': 'other'}}
            for i in range(15)
        ]

        update_jobs.save_market_history(jobs)

        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        top_companies = data['snapshots'][0]['top_companies']
        assert len(top_companies) == 10

    def test_top_companies_sorted_by_count(self):
        """Top companies are sorted by job count descending."""
        jobs = [
            {'company': 'Google', 'categories': ['swe'], 'company_tier': {'tier': 'faang-plus'}},
            {'company': 'Google', 'categories': ['ml'], 'company_tier': {'tier': 'faang-plus'}},
            {'company': 'Google', 'categories': ['data'], 'company_tier': {'tier': 'faang-plus'}},
            {'company': 'Meta', 'categories': ['swe'], 'company_tier': {'tier': 'faang-plus'}},
            {'company': 'Meta', 'categories': ['ml'], 'company_tier': {'tier': 'faang-plus'}},
            {'company': 'Stripe', 'categories': ['swe'], 'company_tier': {'tier': 'unicorn'}},
        ]

        update_jobs.save_market_history(jobs)

        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        top_companies = data['snapshots'][0]['top_companies']
        assert len(top_companies) == 3
        assert top_companies[0] == {'company': 'Google', 'jobs': 3}
        assert top_companies[1] == {'company': 'Meta', 'jobs': 2}
        assert top_companies[2] == {'company': 'Stripe', 'jobs': 1}

    def test_unique_companies_count(self):
        """Unique companies count is accurate."""
        jobs = [
            {'company': 'Google', 'categories': ['swe'], 'company_tier': {'tier': 'faang-plus'}},
            {'company': 'Google', 'categories': ['ml'], 'company_tier': {'tier': 'faang-plus'}},
            {'company': 'Meta', 'categories': ['swe'], 'company_tier': {'tier': 'faang-plus'}},
            {'company': 'Stripe', 'categories': ['data'], 'company_tier': {'tier': 'unicorn'}},
        ]

        update_jobs.save_market_history(jobs)

        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        unique_companies = data['snapshots'][0]['unique_companies']
        assert unique_companies == 3

    def test_avg_jobs_per_company_calculation(self):
        """Average jobs per company is calculated correctly."""
        jobs = [
            {'company': 'Google', 'categories': ['swe'], 'company_tier': {'tier': 'faang-plus'}},
            {'company': 'Google', 'categories': ['ml'], 'company_tier': {'tier': 'faang-plus'}},
            {'company': 'Meta', 'categories': ['swe'], 'company_tier': {'tier': 'faang-plus'}},
            {'company': 'Stripe', 'categories': ['data'], 'company_tier': {'tier': 'unicorn'}},
        ]

        update_jobs.save_market_history(jobs)

        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        avg_jobs = data['snapshots'][0]['avg_jobs_per_company']
        # 4 jobs / 3 companies = 1.33
        assert avg_jobs == 1.33


class TestHistoryRetention:
    """Test 90-day retention and snapshot management."""

    def setup_method(self):
        """Create temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.history_path = os.path.join(self.temp_dir, 'market-history.json')
        self.original_join = os.path.join

        def mock_join(*args):
            if 'market-history.json' in args:
                return self.history_path
            return self.original_join(*args)

        os.path.join = mock_join

    def teardown_method(self):
        """Clean up temporary directory."""
        os.path.join = self.original_join
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_keeps_only_90_days(self):
        """Snapshots older than 90 days are removed."""
        # Create old history with snapshots from 100 days ago
        old_date = (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d')
        recent_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        old_history = {
            'meta': {'last_updated': datetime.now().isoformat(), 'total_snapshots': 2, 'date_range': {'start': old_date, 'end': recent_date}},
            'snapshots': [
                {
                    'date': old_date,
                    'total_jobs': 100,
                    'categories': {},
                    'tiers': {},
                    'top_companies': [],
                    'unique_companies': 10,
                    'avg_jobs_per_company': 10,
                    'timestamp': datetime.now().isoformat()
                },
                {
                    'date': recent_date,
                    'total_jobs': 200,
                    'categories': {},
                    'tiers': {},
                    'top_companies': [],
                    'unique_companies': 20,
                    'avg_jobs_per_company': 10,
                    'timestamp': datetime.now().isoformat()
                }
            ]
        }

        with open(self.history_path, 'w', encoding='utf-8') as f:
            json.dump(old_history, f)

        jobs = [{'company': 'Google', 'categories': ['swe'], 'company_tier': {'tier': 'faang-plus'}}]
        update_jobs.save_market_history(jobs)

        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Should have removed the 100-day-old snapshot
        snapshot_dates = [s['date'] for s in data['snapshots']]
        assert old_date not in snapshot_dates
        assert recent_date in snapshot_dates

    def test_updates_existing_snapshot_for_today(self):
        """If today's snapshot exists, it is updated rather than duplicated."""
        # First call
        jobs_v1 = [{'company': 'Google', 'categories': ['swe'], 'company_tier': {'tier': 'faang-plus'}}]
        update_jobs.save_market_history(jobs_v1)

        # Second call on same day with different data
        jobs_v2 = [
            {'company': 'Google', 'categories': ['swe'], 'company_tier': {'tier': 'faang-plus'}},
            {'company': 'Meta', 'categories': ['ml'], 'company_tier': {'tier': 'faang-plus'}},
        ]
        update_jobs.save_market_history(jobs_v2)

        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Should have only one snapshot with updated data
        assert len(data['snapshots']) == 1
        assert data['snapshots'][0]['total_jobs'] == 2

    def test_snapshots_sorted_by_date(self):
        """Snapshots are sorted chronologically (oldest to newest)."""
        # Create history with unsorted dates
        date1 = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        date2 = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
        date3 = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')

        old_history = {
            'meta': {'last_updated': datetime.now().isoformat(), 'total_snapshots': 3, 'date_range': {'start': date2, 'end': date1}},
            'snapshots': [
                {
                    'date': date1,
                    'total_jobs': 100,
                    'categories': {},
                    'tiers': {},
                    'top_companies': [],
                    'unique_companies': 10,
                    'avg_jobs_per_company': 10,
                    'timestamp': datetime.now().isoformat()
                },
                {
                    'date': date2,
                    'total_jobs': 150,
                    'categories': {},
                    'tiers': {},
                    'top_companies': [],
                    'unique_companies': 15,
                    'avg_jobs_per_company': 10,
                    'timestamp': datetime.now().isoformat()
                },
                {
                    'date': date3,
                    'total_jobs': 200,
                    'categories': {},
                    'tiers': {},
                    'top_companies': [],
                    'unique_companies': 20,
                    'avg_jobs_per_company': 10,
                    'timestamp': datetime.now().isoformat()
                }
            ]
        }

        with open(self.history_path, 'w', encoding='utf-8') as f:
            json.dump(old_history, f)

        jobs = [{'company': 'Google', 'categories': ['swe'], 'company_tier': {'tier': 'faang-plus'}}]
        update_jobs.save_market_history(jobs)

        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        dates = [s['date'] for s in data['snapshots']]
        assert dates == sorted(dates)  # Should be in chronological order


class TestFileHandling:
    """Test file I/O, error handling, and edge cases."""

    def setup_method(self):
        """Create temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.history_path = os.path.join(self.temp_dir, 'market-history.json')
        self.original_join = os.path.join

        def mock_join(*args):
            if 'market-history.json' in args:
                return self.history_path
            return self.original_join(*args)

        os.path.join = mock_join

    def teardown_method(self):
        """Clean up temporary directory."""
        os.path.join = self.original_join
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_creates_directory_if_not_exists(self):
        """Creates directory if it doesn't exist."""
        # Remove temp dir to test creation
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        jobs = [{'company': 'Google', 'categories': ['swe'], 'company_tier': {'tier': 'faang-plus'}}]
        update_jobs.save_market_history(jobs)

        assert os.path.exists(self.history_path)

    def test_handles_corrupted_json(self, capsys):
        """Gracefully handles corrupted JSON file."""
        # Write corrupted JSON
        with open(self.history_path, 'w', encoding='utf-8') as f:
            f.write("{invalid json")

        jobs = [{'company': 'Google', 'categories': ['swe'], 'company_tier': {'tier': 'faang-plus'}}]
        update_jobs.save_market_history(jobs)

        # Should recover and create new history
        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert len(data['snapshots']) == 1
        captured = capsys.readouterr()
        assert "Could not load market history" in captured.out

    def test_empty_jobs_list(self):
        """Handles empty jobs list gracefully."""
        jobs = []
        update_jobs.save_market_history(jobs)

        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        snapshot = data['snapshots'][0]
        assert snapshot['total_jobs'] == 0
        assert snapshot['unique_companies'] == 0
        assert snapshot['avg_jobs_per_company'] == 0
        assert snapshot['categories'] == {}
        assert snapshot['tiers'] == {}
        assert snapshot['top_companies'] == []

    def test_missing_company_field_uses_unknown(self):
        """Jobs without company field default to 'Unknown'."""
        jobs = [
            {'categories': ['swe'], 'company_tier': {'tier': 'other'}},  # no company
        ]

        update_jobs.save_market_history(jobs)

        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        top_companies = data['snapshots'][0]['top_companies']
        assert len(top_companies) == 1
        assert top_companies[0]['company'] == 'Unknown'

    def test_large_job_list_performance(self):
        """Handles large job lists efficiently (1000+ jobs)."""
        jobs = [
            {
                'company': f'Company{i % 50}',
                'categories': ['swe'],
                'company_tier': {'tier': 'other'}
            }
            for i in range(1000)
        ]

        update_jobs.save_market_history(jobs)

        with open(self.history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        snapshot = data['snapshots'][0]
        assert snapshot['total_jobs'] == 1000
        assert snapshot['unique_companies'] == 50
        assert len(snapshot['top_companies']) == 10  # Still capped at 10


class TestSaveMarketHistoryDeterminism:
    """Deterministic tests for retention boundaries and snapshot contracts."""

    FIXED_NOW = datetime(2026, 4, 3, 12, 0, 0)

    @staticmethod
    def _fixed_datetime_class(fixed_now: datetime):
        class _FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                if tz is None:
                    return fixed_now.replace(tzinfo=None)
                return fixed_now.astimezone(tz)

        return _FixedDateTime

    def test_retention_boundary_drops_day_91_keeps_day_90(self, tmp_path, monkeypatch):
        history_path = str(tmp_path / "market-history.json")
        original_join = os.path.join
        monkeypatch.setattr(update_jobs, "datetime", self._fixed_datetime_class(self.FIXED_NOW))

        day_91 = (self.FIXED_NOW - timedelta(days=91)).strftime("%Y-%m-%d")
        day_90 = (self.FIXED_NOW - timedelta(days=90)).strftime("%Y-%m-%d")

        existing = {
            "meta": {
                "last_updated": self.FIXED_NOW.isoformat(),
                "total_snapshots": 2,
                "date_range": {"start": day_91, "end": day_90},
            },
            "snapshots": [
                {
                    "date": day_91,
                    "total_jobs": 10,
                    "categories": {},
                    "tiers": {},
                    "top_companies": [],
                    "unique_companies": 1,
                    "avg_jobs_per_company": 10.0,
                    "timestamp": self.FIXED_NOW.isoformat(),
                },
                {
                    "date": day_90,
                    "total_jobs": 20,
                    "categories": {},
                    "tiers": {},
                    "top_companies": [],
                    "unique_companies": 2,
                    "avg_jobs_per_company": 10.0,
                    "timestamp": self.FIXED_NOW.isoformat(),
                },
            ],
        }
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(existing, f)

        def patched_join(*args):
            if args and args[-1] == "market-history.json":
                return history_path
            return original_join(*args)

        with patch("update_jobs.os.path.join", side_effect=patched_join):
            update_jobs.save_market_history(
                [{"company": "Google", "categories": ["swe"], "company_tier": {"tier": "faang-plus"}}]
            )

        with open(history_path, "r", encoding="utf-8") as f:
            output = json.load(f)
        dates = [snap["date"] for snap in output["snapshots"]]
        assert day_91 not in dates
        assert day_90 in dates
        assert self.FIXED_NOW.strftime("%Y-%m-%d") in dates

    def test_snapshot_schema_and_aggregation_are_deterministic(self, tmp_path, monkeypatch):
        history_path = str(tmp_path / "market-history.json")
        original_join = os.path.join
        monkeypatch.setattr(update_jobs, "datetime", self._fixed_datetime_class(self.FIXED_NOW))

        jobs = [
            {"company": "Google", "categories": ["swe", "ml"], "company_tier": {"tier": "faang-plus"}},
            {"company": "Meta", "categories": ["swe"], "company_tier": {"tier": "faang-plus"}},
            {"company": "Stripe", "categories": ["data"], "company_tier": {"tier": "unicorn"}},
        ]

        def patched_join(*args):
            if args and args[-1] == "market-history.json":
                return history_path
            return original_join(*args)

        with patch("update_jobs.os.path.join", side_effect=patched_join):
            update_jobs.save_market_history(jobs)

        with open(history_path, "r", encoding="utf-8") as f:
            output = json.load(f)
        snapshot = output["snapshots"][0]
        assert set(snapshot.keys()) == {
            "date",
            "total_jobs",
            "categories",
            "tiers",
            "top_companies",
            "unique_companies",
            "avg_jobs_per_company",
            "timestamp",
        }
        assert snapshot["date"] == "2026-04-03"
        assert snapshot["timestamp"] == self.FIXED_NOW.isoformat()
        assert snapshot["categories"] == {"swe": 2, "ml": 1, "data": 1}
        assert snapshot["tiers"] == {"faang-plus": 2, "unicorn": 1}

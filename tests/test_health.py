#!/usr/bin/env python3
"""
Unit tests for generate_health_json() in scripts/update_jobs.py.

Covers:
  - Status determination: ok, degraded, failed
  - Output structure validation
"""

import sys
import os
import json
import time
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import generate_health_json


class TestHealthJsonStatus:
    """Tests for health status determination."""

    BASE_CONFIG = {
        'apis': {
            'greenhouse': {'companies': [{'name': 'A'}, {'name': 'B'}]},
            'lever': {'companies': [{'name': 'C'}]},
            'workday': {'enabled': True, 'companies': [{'name': 'D'}]},
            'google': {'enabled': True, 'search_terms': ['new grad software engineer']},
            'jobspy': {'enabled': True},
            'graphql': {'enabled': True, 'sources': [{'company': 'E'}]},
        }
    }

    def _run_health(self, jobs, source_counts, tmpdir):
        """Helper to generate health.json in a temp directory and return the result."""
        health_path = os.path.join(tmpdir, 'health.json')
        with patch('update_jobs.os.path.join', return_value=health_path):
            with patch('update_jobs.os.makedirs'):
                generate_health_json(jobs, source_counts, time.time() - 10, self.BASE_CONFIG)
        with open(health_path) as f:
            return json.load(f)

    def test_ok_status(self):
        """All sources returned jobs → status ok."""
        with tempfile.TemporaryDirectory() as tmpdir:
            jobs = [{'title': 'SWE'}] * 5
            counts = {'greenhouse': 3, 'lever': 2}
            result = self._run_health(jobs, counts, tmpdir)
            assert result['status'] == 'ok'
            assert result['total_jobs'] == 5
            assert result['zero_sources'] == []

    def test_degraded_status(self):
        """One source returned 0 → status degraded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            jobs = [{'title': 'SWE'}] * 3
            counts = {'greenhouse': 3, 'lever': 0}
            result = self._run_health(jobs, counts, tmpdir)
            assert result['status'] == 'degraded'
            assert 'lever' in result['zero_sources']

    def test_failed_status(self):
        """Zero total jobs → status failed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            jobs = []
            counts = {'greenhouse': 0, 'lever': 0}
            result = self._run_health(jobs, counts, tmpdir)
            assert result['status'] == 'failed'
            assert result['total_jobs'] == 0

    def test_output_structure(self):
        """Health JSON must have all required keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            jobs = [{'title': 'SWE'}]
            counts = {'greenhouse': 1}
            result = self._run_health(jobs, counts, tmpdir)
            required_keys = {'status', 'last_run', 'total_jobs',
                             'source_counts', 'zero_sources', 'run_duration_seconds',
                             'configured_company_apis', 'enabled_sources',
                             'active_hiring_companies', 'active_sources'}
            assert required_keys.issubset(set(result.keys()))

    def test_display_metrics_are_derived_from_data_and_config(self):
        """Configured/source/company metrics should be computed from true sources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            jobs = [
                {'company': 'Acme', 'title': 'SWE'},
                {'company': 'Acme', 'title': 'SWE II'},
                {'company': 'Beta', 'title': 'ML Engineer'},
                {'company': '', 'title': 'Unknown'},
            ]
            counts = {'greenhouse': 2, 'jobspy': 1}
            result = self._run_health(jobs, counts, tmpdir)
            assert result['configured_company_apis'] == 5
            assert result['enabled_sources'] == 6
            assert result['active_hiring_companies'] == 2
            assert result['active_sources'] == 2

#!/usr/bin/env python3
'''
Unit tests for utility functions in scripts/update_jobs.py.
Tests cover importing get_job_key from update_jobs.py and its behavior in generating consistent keys for job deduplication.

'''

import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import get_job_key

def test_get_job_key_handles_nan():
    """Test that get_job_key handles NaN values correctly."""
    job_with_nan = {
        'company': 'Tech Corp',
        'title': float('nan'),  #simulating a pandas NaN, eq to a math.nan
        'url': 'https://example.com'
    }
    nan_value = float('nan')
    assert math.isnan(nan_value), "Test setup error: value is not NaN"

    result = get_job_key(job_with_nan)
    assert result == "tech corp||https://example.com"
    assert "|" in result
    assert "nan" not in result.lower()

def test_get_job_key_all_missing():
    """Test when all fields are either None/NaN."""
    job_empty = {
        'company': None,
        'title': float('nan'),
        'url': None
    }
    result = get_job_key(job_empty)
    assert result == "||", "Expected empty key for all missing values"

def test_get_job_key_normalizes_strings():
    """Test that it strips whitespace and handles casing."""
    job = {
        'company': '  ACME CORP',
        'title': 'DevOps Engineer',
        'url': 'HTTP://LINK.COM'
    }
    result = get_job_key(job)
    assert result == "acme corp|devops engineer|http://link.com"
#

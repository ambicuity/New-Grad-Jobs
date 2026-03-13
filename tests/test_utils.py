#!/usr/bin/env python3
'''
Unit tests for utility functions in scripts/update_jobs.py.
Tests cover importing get_job_key from update_jobs.py and its behavior in generating consistent keys for job deduplication.

'''
import pytest
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import get_job_key

def test_get_job_key_handles_nan()->None:
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

def test_get_job_key_handles_inf()->None:
    """Test that get_job_key handles Inf values correctly."""
    job_with_inf = {
        'company': float('inf'),
        'title': 'Engineer',
        'url': 'https://example.com'
    }
    inf_value = float('inf')
    assert math.isinf(inf_value), "Test setup error: value is not Inf"

    result = get_job_key(job_with_inf)
    assert result == "|engineer|https://example.com"
    assert "inf" not in result.lower()

def test_get_job_key_all_missing()->None:
    """Test when all fields are either None/NaN."""
    job_empty = {
        'company': None,
        'title': float('nan'),
        'url': None
    }
    result = get_job_key(job_empty)
    assert result == "||", "Expected empty key for all missing values"

def test_get_job_key_normalizes_strings()->None:
    """Test that it strips whitespace and handles casing."""
    job = {
        'company': '  ACME CORP',
        'title': 'DevOps Engineer',
        'url': 'HTTP://LINK.COM'
    }
    result = get_job_key(job)
    assert result == "acme corp|devops engineer|http://link.com"

@pytest.mark.parametrize("job_input, expected_key", [
    # Test case: Missing key
    ({'title': 'SWE', 'url': 'http://a.com'}, '|swe|http://a.com'),
    # Test case: Empty string value
    ({'company': '', 'title': 'SWE', 'url': 'http://a.com'}, '|swe|http://a.com'),
    # Test case: Unicode characters
    ({'company': 'Stripe™', 'title': 'Ingénieur Logiciel', 'url': 'http://a.com'}, 'stripe™|ingénieur logiciel|http://a.com'),
    # Test case: Integer value (should be converted to string)
    ({'company': 'Company', 'title': 123, 'url': 'http://a.com'}, 'company|123|http://a.com'),
    # Test case: float value (should be converted to string)
    ({'company': 'Company', 'title': 123.45, 'url': 'http://a.com'}, 'company|123.45|http://a.com'),
])
def test_get_job_key_edge_cases(job_input: dict, expected_key: str) -> None:
    """Test get_job_key with various edge cases based on style guide recommendations."""
    assert get_job_key(job_input) == expected_key

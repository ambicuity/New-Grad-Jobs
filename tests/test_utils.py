#!/usr/bin/env python3
'''
Unit tests for utility functions in scripts/update_jobs.py.
Tests cover importing get_job_key from update_jobs.py and its behavior in generating consistent keys for job deduplication.

'''
import pytest
import sys
import os
import math
import json
import re
import requests
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import get_job_key, fetch_google_jobs

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


# Testing for update_jobs.py - fetch_google_jobs function

def create_mock_google_html(jobs_array) -> None:
    # This data structure is exactly what find_jobs_array expects to see
    # after json.loads() is called on the regex match.
    # It must be a list containing a list, where the first element is your job list.
    data_to_encode = [jobs_array]

    json_data = json.dumps(data_to_encode)

    # We must match the regex: AF_initDataCallback({key: 'ds:1', hash: '[^']+', data:([^<]+)});</script>
    # Note: No space between 'data:' and the JSON string to be safe.
    return f"AF_initDataCallback({{key: 'ds:1', hash: 'xyz', data:{json_data}}});</script>"

def test_fetch_google_jobs_success2() -> None:
    mock_jobs = [["12345", "early Software Engineer", "https://google.com/job1", None, None, None, None, "Google", None, [["Mountain View, CA"]], [None, "Description 1"], None, [1679212800]]]

    # Ensure this matches the scraper's expected script format EXACTLY
    mock_html = f"<script>AF_initDataCallback({{key: 'ds:1', hash: '1', data:{json.dumps([mock_jobs])}}});</script>"

    with patch('update_jobs.limited_get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html
        mock_get.return_value = mock_response

        # IMPORTANT: Check if the case sensitivity of the search term matters
        results = fetch_google_jobs(["early software engineer"], max_pages=1)
        assert len(results) == 1
        assert results[0]['title'] == "early Software Engineer"
        assert results[0]['company'] == "Google"
        assert "Mountain View, CA" in results[0]['location']
        assert results[0]['url'] == "https://google.com/job1"
        assert "Description 1" in results[0]['description']
        assert "2023-03-19" in results[0]['posted_at']


def test_fetch_google_jobs_rate_limited() -> None:
    """Test that it handles rate limiting (403, 429) correctly."""
    with patch('update_jobs.limited_get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)

        results = fetch_google_jobs(["software engineer"], max_pages=1, max_retries=0)
        assert len(results) == 0

def test_fetch_google_jobs_403_result() -> None:
    """Test that it handles rate limiting (403) correctly."""
    with patch('update_jobs.limited_get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)

        results = fetch_google_jobs(["software engineer"], max_pages=1, max_retries=0)
        assert len(results) == 0

def test_fetch_google_jobs_empty_results() -> None:
    """Test handling of no jobs found."""
    mock_html = "<html><body><script>AF_initDataCallback({key: 'ds:1', hash: '123', data:[None, None, [[]]]});</script></body></html>"

    with patch('update_jobs.limited_get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html
        mock_get.return_value = mock_response

        results = fetch_google_jobs(["nonexistent job"], max_pages=1)
        assert len(results) == 0

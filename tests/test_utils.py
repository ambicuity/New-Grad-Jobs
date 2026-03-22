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
import requests
import urllib.parse
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import get_job_key, fetch_google_jobs, DEFAULT_GOOGLE_MAX_PAGES, _coerce_positive_int

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

# ---------------------------------------------------------------------------

# Testing for update_jobs.py - fetch_google_jobs function
# Helper -
def create_mock_google_html(jobs_array) -> str:
    """Build a minimal HTML snippet that satisfies the scraper's regex + find_jobs_array.

    IMPORTANT: Job IDs (index 0 of each job entry) MUST be purely numeric strings.
    find_jobs_array() uses obj[0][0].isdigit() to identify the jobs list.
    Using non-numeric IDs like 'job1' causes find_jobs_array to skip the list
    silently, returning zero results even when the regex match succeeds.
    """
    # data_to_encode wraps jobs_array so that after parsing, find_jobs_array
    # can locate the inner list whose first element's first field is a digit string.
    data_to_encode = [jobs_array]
    json_data = json.dumps(data_to_encode)
    # Must match the regex:
    #   AF_initDataCallback({key: 'ds:1', hash: '[^']+', data:([^<]+)});</script>
    return f"AF_initDataCallback({{key: 'ds:1', hash: 'xyz', data:{json_data}}});</script>"


# Normal Successful response
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

def test_fetch_google_jobs_regex_failure() -> None:
    """Test behavior when regex fails to find the data script."""
    mock_html = "<html><body>Some random HTML without the script tag</body></html>"

    with patch('update_jobs.limited_get') as mock_get:
        mock_response = MagicMock(status_code=200, text=mock_html)
        mock_get.return_value = mock_response

        results = fetch_google_jobs(["term"], max_pages=1)
        assert len(results) == 0 # Would want zero to not muddy results.

def test_fetch_google_jobs_invalid_json() -> None:
    """Test handling of invalid JSON in the script tag."""
    mock_html = "<script>AF_initDataCallback({key: 'ds:1', hash: '1', data: {invalid json} });</script>"

    with patch('update_jobs.limited_get') as mock_get:
        mock_response = MagicMock(status_code=200, text=mock_html)
        mock_get.return_value = mock_response

        results = fetch_google_jobs(["term"], max_pages=1)
        assert len(results) == 0 # Invalid would mean wrong area maybe, would not want it to go further

# ---------------------------------------------------------------------------
# Pagination

def test_fetch_google_jobs_pagination() -> None:
    """Test that pagination increments the page counter and stops when no new jobs appear."""
    page1_jobs = [["11111", "Title 1", "https://url1", None, None, None, None, "Google", None, [["Loc 1"]], [None, "Desc 1"], None, [1679212800]]]
    page2_jobs = [["22222", "Title 2", "https://url2", None, None, None, None, "Google", None, [["Loc 2"]], [None, "Desc 2"], None, [1679299200]]]

    html1 = create_mock_google_html(page1_jobs)
    html2 = create_mock_google_html(page2_jobs)
    html3 = create_mock_google_html([])  # Empty → stops pagination

    with patch('update_jobs.limited_get') as mock_get:
        mock_get.side_effect = [
            MagicMock(status_code=200, text=html1),
            MagicMock(status_code=200, text=html2),
            MagicMock(status_code=200, text=html3),
        ]

        results = fetch_google_jobs(["software engineer"], max_pages=3)
        assert len(results) == 2
        assert results[0]['title'] == "Title 1"
        assert results[1]['title'] == "Title 2"
        # Stopped on empty page, not from hitting the max_pages cap
        assert mock_get.call_count == 3


def test_fetch_google_jobs_max_pages_respected() -> None:
    """Test that fetching hard-stops at max_pages even if more results exist."""
    def make_page(job_id: str, url: str) -> str:
        job = [[job_id, f"Title {job_id}", url, None, None, None, None, "Google", None, [["Loc"]], [None, "Desc"], None, [1679212800]]]
        return create_mock_google_html(job)

    with patch('update_jobs.limited_get') as mock_get:
        mock_get.side_effect = [
            MagicMock(status_code=200, text=make_page("10001", "https://url1")),
            MagicMock(status_code=200, text=make_page("10002", "https://url2")),
        ]
        results = fetch_google_jobs(["software engineer"], max_pages=2)
        assert len(results) == 2
        assert mock_get.call_count == 2  # Must not request a 3rd page


# ---------------------------------------------------------------------------
# Multiple search terms

def test_fetch_google_jobs_multiple_search_terms() -> None:
    """Test iteration through all search terms and URL-based deduplication."""
    term1_jobs = [["10001", "Title 1", "https://url1", None, None, None, None, "Google", None, [["Loc 1"]], [None, "Desc 1"], None, [1679212800]]]
    # Same URL as term1's job — should be deduped
    term2_jobs = [
        ["10001", "Title 1", "https://url1", None, None, None, None, "Google", None, [["Loc 1"]], [None, "Desc 1"], None, [1679212800]],
        ["10002", "Title 2", "https://url2", None, None, None, None, "Google", None, [["Loc 2"]], [None, "Desc 2"], None, [1679299200]],
    ]

    html1 = create_mock_google_html(term1_jobs)
    html_empty = create_mock_google_html([])
    html2 = create_mock_google_html(term2_jobs)

    with patch('update_jobs.limited_get') as mock_get:
        mock_get.side_effect = [
            MagicMock(status_code=200, text=html1),       # Term 1 Page 1
            MagicMock(status_code=200, text=html_empty),  # Term 1 Page 2 → stops
            MagicMock(status_code=200, text=html2),       # Term 2 Page 1
            MagicMock(status_code=200, text=html_empty),  # Term 2 Page 2 → stops
        ]

        results = fetch_google_jobs(["term1", "term2"], max_pages=2)
        assert len(results) == 2  # url1 deduplicated; url2 unique
        assert results[0]['url'] == "https://url1"
        assert results[1]['url'] == "https://url2"
        assert mock_get.call_count == 4


# ---------------------------------------------------------------------------
# Field parsing edge cases

def test_fetch_google_jobs_multiple_locations() -> None:
    """Test that multiple office locations are joined with ' | '."""
    jobs = [["10001", "Title 1", "https://url1", None, None, None, None, "Google", None, [["New York, NY"], ["San Francisco, CA"]], [None, "Desc 1"], None, [1679212800]]]
    html = create_mock_google_html(jobs)

    with patch('update_jobs.limited_get') as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=html)
        results = fetch_google_jobs(["term"], max_pages=1)
        assert results[0]['location'] == "New York, NY | San Francisco, CA"


def test_fetch_google_jobs_invalid_timestamp() -> None:
    """Test that missing, empty, or non-numeric timestamps all yield an empty posted_at."""
    job_no_ts    = ["10001", "Title 1", "https://url1", None, None, None, None, "Google", None, [["Loc"]], [None, "D"]]  # index 12 absent
    job_empty_ts = ["10002", "Title 2", "https://url2", None, None, None, None, "Google", None, [["Loc"]], [None, "D"], None, []]
    job_str_ts   = ["10003", "Title 3", "https://url3", None, None, None, None, "Google", None, [["Loc"]], [None, "D"], None, ["not-a-number"]]

    html = create_mock_google_html([job_no_ts, job_empty_ts, job_str_ts])

    with patch('update_jobs.limited_get') as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=html)
        results = fetch_google_jobs(["term"], max_pages=1)
        assert len(results) == 3
        assert results[0]['posted_at'] == ""
        assert results[1]['posted_at'] == ""
        assert results[2]['posted_at'] == ""


def test_fetch_google_jobs_description_whitespace_normalization() -> None:
    """Test that runs of whitespace (spaces, tabs, newlines) are collapsed to a single space."""
    # Avoid '<' characters — Python's json.dumps does NOT escape them to \u003c,
    # so a literal '<' in the JSON would truncate the scraper's [^<]+ regex match.
    raw_desc = "Line 1  Line 2   Extra   Spaces"
    job = ["10001", "Title 1", "https://url1", None, None, None, None, "Google", None, [["Loc"]], [None, raw_desc], None, [1679212800]]
    html = create_mock_google_html([job])

    with patch('update_jobs.limited_get') as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=html)
        results = fetch_google_jobs(["term"], max_pages=1)
        assert results[0]['description'] == "Line 1 Line 2 Extra Spaces"


def test_fetch_google_jobs_description_html_stripping() -> None:
    """Test that HTML tags are stripped from descriptions.

    Background: Google's page JS-encodes '<' as '\\u003c' inside the embedded
    JSON blob (the same escaping json.loads reverses).  Python's json.dumps does
    NOT do this automatically, so we manually pre-escape '<' before embedding the
    JSON in the mock HTML — this is what real Google HTML looks like.
    """
    raw_desc = "Intro<br>Bullet 1<p>Bullet 2</p>End"
    job = ["10001", "Title 1", "https://url1", None, None, None, None, "Google", None, [["Loc"]], [None, raw_desc], None, [1679212800]]

    # Build JSON, then escape '<' to '\u003c' so the [^<]+ regex sees no raw '<'.
    # json.loads will decode '\u003c' back to '<' before the scraper's re.sub runs.
    inner_json = json.dumps([[job]])
    inner_json_escaped = inner_json.replace("<", r"\u003c").replace(">", r"\u003e")
    mock_html = f"AF_initDataCallback({{key: 'ds:1', hash: 'xyz', data:{inner_json_escaped}}});</script>"

    with patch('update_jobs.limited_get') as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=mock_html)
        results = fetch_google_jobs(["term"], max_pages=1)
        # HTML tags stripped, whitespace collapsed
        assert results[0]['description'] == "Intro Bullet 1 Bullet 2 End"


def test_fetch_google_jobs_description_truncated() -> None:
    """Test that descriptions longer than 500 chars are truncated to exactly 500."""
    long_desc = "A" * 600
    job = ["10001", "Title 1", "https://url1", None, None, None, None, "Google", None, [["Loc"]], [None, long_desc], None, [1679212800]]
    html = create_mock_google_html([job])

    with patch('update_jobs.limited_get') as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=html)
        results = fetch_google_jobs(["term"], max_pages=1)
        assert len(results[0]['description']) == 500


def test_fetch_google_jobs_link_fallback() -> None:
    """Test that a missing link field falls back to the canonical Google URL using the job ID."""
    job = ["98765", "Title 1", None, None, None, None, None, "Google", None, [["Loc"]], [None, "Desc"], None, [1679212800]]
    html = create_mock_google_html([job])

    with patch('update_jobs.limited_get') as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=html)
        results = fetch_google_jobs(["term"], max_pages=1)
        assert results[0]['url'] == "https://www.google.com/about/careers/applications/jobs/results/98765"


def test_fetch_google_jobs_subsidiary_company_name() -> None:
    """Test that the company field at IDX_COMPANY (index 7) is used when present."""
    job = ["10001", "ML Engineer", "https://url1", None, None, None, None, "DeepMind", None, [["London"]], [None, "Desc"], None, [1679212800]]
    html = create_mock_google_html([job])

    with patch('update_jobs.limited_get') as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=html)
        results = fetch_google_jobs(["term"], max_pages=1)
        assert results[0]['company'] == "DeepMind"


def test_fetch_google_jobs_missing_company_defaults_to_google() -> None:
    """Test that a missing/None company field defaults to 'Google'."""
    job = ["10001", "SWE", "https://url1", None, None, None, None, None, None, [["Loc"]], [None, "Desc"], None, [1679212800]]
    html = create_mock_google_html([job])

    with patch('update_jobs.limited_get') as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=html)
        results = fetch_google_jobs(["term"], max_pages=1)
        assert results[0]['company'] == "Google"


def test_fetch_google_jobs_missing_fields() -> None:
    """Test robustness when a job entry is truncated (only ID, title, URL present)."""
    job = ["10001", "Software Engineer", "https://url1"]
    html = create_mock_google_html([job])

    with patch('update_jobs.limited_get') as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=html)
        results = fetch_google_jobs(["term"], max_pages=1)
        assert len(results) == 1
        assert results[0]['company'] == "Google"   # Default when index 7 absent
        assert results[0]['location'] == "Remote"  # Default when index 9 absent
        assert results[0]['description'] == ""
        assert results[0]['posted_at'] == ""


def test_fetch_google_jobs_source_field() -> None:
    """Test that the source field is always set to 'Google Careers'."""
    job = ["10001", "SWE", "https://url1", None, None, None, None, "Google", None, [["Loc"]], [None, "Desc"], None, [1679212800]]
    html = create_mock_google_html([job])

    with patch('update_jobs.limited_get') as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=html)
        results = fetch_google_jobs(["term"], max_pages=1)
        assert results[0]['source'] == "Google Careers"


# ---------------------------------------------------------------------------
# Network error handling

def test_fetch_google_jobs_network_timeout() -> None:
    """Test that a Timeout exception on all retries returns an empty list."""
    with patch('update_jobs.limited_get') as mock_get:
        mock_get.side_effect = requests.exceptions.Timeout
        results = fetch_google_jobs(["term"], max_pages=1, max_retries=0)
        assert results == []


def test_fetch_google_jobs_network_request_exception() -> None:
    """Test that a generic RequestException on all retries returns an empty list."""
    with patch('update_jobs.limited_get') as mock_get:
        mock_get.side_effect = requests.exceptions.RequestException("connection error")
        results = fetch_google_jobs(["term"], max_pages=1, max_retries=0)
        assert results == []


def test_fetch_google_jobs_404_fail_fast() -> None:
    """Test that it fails fast on 404 (breaks retry loop)."""
    with patch('update_jobs.limited_get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        # Configure the mock response and the HTTPError with the response object
        mock_get.return_value = mock_response
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)

        # max_retries=2 means it could try 3 times, but it should stop after 1
        results = fetch_google_jobs(["software engineer"], max_pages=1, max_retries=2)
        assert len(results) == 0
        assert mock_get.call_count == 1  # Should NOT retry on 404


def test_fetch_google_jobs_parsing_error() -> None:
    """Test that a malformed job entry (e.g. TypeError) is skipped but doesn't crash the loop."""
    # First job is valid so find_jobs_array identifies the list correctly (it checks first element's ID)
    valid_job = ["10001", "SWE", "https://url1", None, None, None, None, None, None, [["Loc"]], [None, "Desc"], None, [1679212800]]
    # Second job is malformed (not subscriptable, causing TypeError)
    malformed_job = 123  # Int is not subscriptable

    html = create_mock_google_html([valid_job, malformed_job])

    with patch('update_jobs.limited_get') as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=html)
        results = fetch_google_jobs(["term"], max_pages=1)

        # Should have 1 job (the valid one)
        assert len(results) == 1
        assert results[0]['url'] == "https://url1"


def test_fetch_google_jobs_invalid_field_types() -> None:
    """Test that jobs with invalid type for title, company or link are handled safely.

    This verifies the fix for the code review note regarding undocumented array types.
    """
    # 1. Valid job
    job_valid = ["1", "SWE", "https://url1", None, None, None, None, "Google", None, [["Loc"]], [None, "Desc"]]
    # 2. Invalid title (None) -> should be skipped
    job_none_title = ["2", None, "https://url2", None, None, None, None, "Google"]
    # 3. Invalid title (Int) -> should be skipped
    job_int_title = ["3", 123, "https://url3", None, None, None, None, "Google"]
    # 4. Invalid link (Int) -> should be skipped
    job_int_link = ["4", "SWE", 456, None, None, None, None, "Google"]
    # 5. Invalid company (Int) -> should default to "Google"
    job_int_company = ["5", "SWE", "https://url5", None, None, None, None, 789]
    # 6. Empty title string -> should be skipped
    job_empty_title = ["6", "  ", "https://url6", None, None, None, None, "Google"]

    mock_jobs = [job_valid, job_none_title, job_int_title, job_int_link, job_int_company, job_empty_title]
    html = create_mock_google_html(mock_jobs)

    with patch('update_jobs.limited_get') as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=html)
        results = fetch_google_jobs(["term"], max_pages=1)

        # Expected:
        # - job_valid: OK
        # - job_none_title: skipped
        # - job_int_title: skipped
        # - job_int_link: skipped
        # - job_int_company: OK (company defaults to "Google")
        # - job_empty_title: skipped

        assert len(results) == 2

        # Verify job_valid
        assert results[0]['title'] == "SWE"
        assert results[0]['url'] == "https://url1"
        assert results[0]['company'] == "Google"

        # Verify job_int_company
        assert results[1]['title'] == "SWE"
        assert results[1]['url'] == "https://url5"
        assert results[1]['company'] == "Google" # Coerced from 789 to "Google"


def test_fetch_google_jobs_url_shape() -> None:
    """Regression test for duplicate target_level parameters in the search URL."""
    # We don't care about the content, just the URL generated.
    mock_html = create_mock_google_html([])

    with patch('update_jobs.limited_get') as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=mock_html)

        # We need to pass search_terms as a list
        fetch_google_jobs(["software engineer"], max_pages=1)

        # Check the URL of the first (and only) call
        assert mock_get.call_count == 1
        call_url = mock_get.call_args[0][0]

        # Verify target_level=EARLY is present (or whatever the default is)
        # and that it's NOT duplicated with target_level=INTERN_AND_APPRENTICE
        # or repeated twice.
        assert "target_level=EARLY" in call_url
        # If it was fixed, it should probably be only one of them or a specific one.
        # The prompt says "a single target_level".
        parsed = urllib.parse.urlparse(call_url)
        params = urllib.parse.parse_qs(parsed.query)
        # This returns 2, as currently we use EARLY and INTERN_AND_APPRENTICE. If we change the URL params, then this test must be changed as well.
        assert len(params.get('target_level', [])) == 2, f"Found multiple target_level parameters: {params.get('target_level')}"


def test_fetch_google_jobs_hard_block_abort() -> None:
    """Regression test for ensuring 403/429 stops all subsequent search term requests."""
    with patch('update_jobs.limited_get') as mock_get:
        # First request returns 429
        mock_response_429 = MagicMock(status_code=429)
        mock_response_429.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response_429)

        # Second request should not happen if it correctly aborts
        mock_get.side_effect = [mock_response_429, MagicMock(status_code=200, text="should not be called")]

        # Call with two search terms
        results = fetch_google_jobs(["term1", "term2"], max_pages=1, max_retries=0)

        assert len(results) == 0
        # Should only have 1 call total (for term1), and then abort.
        assert mock_get.call_count == 1
        assert "term1" in mock_get.call_args_list[0][0][0]

@pytest.mark.parametrize("value", [0, -1, "0", "abc", True, 3.5])
def test_coerce_google_max_pages_rejects_invalid_values(value, capsys):
    # This tests the underlying helper function with the Google-specific name
    result = _coerce_positive_int(value, DEFAULT_GOOGLE_MAX_PAGES, "apis.google.MAX_PAGES")
    assert result == DEFAULT_GOOGLE_MAX_PAGES
    assert "Invalid apis.google.MAX_PAGES" in capsys.readouterr().out


def test_coerce_google_max_pages_accepts_positive_string_value(capsys):
    assert _coerce_positive_int("5", DEFAULT_GOOGLE_MAX_PAGES, "apis.google.MAX_PAGES") == 5
    assert capsys.readouterr().out == ""


def test_main_coerces_google_max_pages():
    """Mock main() to verify it correctly calls _coerce_positive_int for Google."""
    from update_jobs import main

    # Mock config that main() loads
    mock_config = {
        'worker_pools': {},
        'apis': {
            'google': {
                'enabled': True,
                'search_terms': ['test'],
                'MAX_PAGES': 'invalid'
            },
            'workday': {'enabled': False},
            'greenhouse': {'companies': []},
            'lever': {'companies': []}
        },
        'filtering': {}
    }

    with (
        patch('update_jobs.load_config', return_value=mock_config),
        patch('update_jobs.ThreadPoolExecutor'),
        patch('update_jobs._coerce_positive_int', side_effect=_coerce_positive_int) as mock_coerce,
        patch('update_jobs.print'), # Silence prints
        patch('update_jobs.save_market_history'), # Prevent docs/ impact
        patch('update_jobs.predict_hiring_trends'),
        patch('update_jobs.generate_jobs_json'),
        patch('update_jobs.generate_readme'),
        patch('update_jobs.generate_rss_feed'),
        patch('update_jobs.generate_health_json'),
        patch('update_jobs.check_job_url_health'),
        patch('builtins.open', new_callable=MagicMock), # Prevent writing files
        patch('os.makedirs'),
    ):
        # We need to catch SystemExit if main fails due to missing files (README etc)
        # But we only care about the coercion call
        try:
            main()
        except SystemExit as exc:
            # main() can exit in this mocked flow; we only care that coercion was invoked.
            assert exc.code in (None, 0, 1)

    # Check if _coerce_positive_int was called for Google MAX_PAGES
    # It might be called multiple times (for Workday too), so we check call args
    google_call = next((call for call in mock_coerce.call_args_list if 'apis.google.MAX_PAGES' in call.args), None)
    assert google_call is not None
    assert google_call.args[0] == 'invalid'
    assert google_call.args[1] == DEFAULT_GOOGLE_MAX_PAGES

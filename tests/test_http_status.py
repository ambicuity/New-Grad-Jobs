import os
import sys

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from update_jobs import (
    is_retryable_status,
    fetch_greenhouse_jobs,
    fetch_lever_jobs,
)


class TestIsRetryableStatus:
    """Tests for the is_retryable_status() shared helper."""

    @pytest.mark.parametrize(
        ("status_code", "expected"),
        [
            # Explicitly non-retryable
            (400, False),
            (401, False),
            (404, False),
            (405, False),
            (410, False),
            (451, False),
            # Explicitly retryable
            (403, True),
            (408, True),
            (422, True),
            (429, True),
            (500, True),
            (502, True),
            (503, True),
            (504, True),
            # Default behavior for unknown codes
            (418, False),  # Unknown 4xx
            (599, True),   # Unknown 5xx
            # Success codes
            (200, False),
            (201, False),
            # Redirects
            (302, False),
        ],
    )
    def test_is_retryable_status(self, status_code: int, expected: bool):
        """Verify is_retryable_status classifies status codes correctly."""
        assert is_retryable_status(status_code) is expected


# ---------------------------------------------------------------------------
# Helpers for integration tests
# ---------------------------------------------------------------------------

def _make_http_error(status_code: int) -> requests.exceptions.HTTPError:
    """Build a requests.HTTPError with a fake Response attached."""
    resp = requests.models.Response()
    resp.status_code = status_code
    resp._content = b"{}"
    error = requests.exceptions.HTTPError(response=resp)
    return error


# ---------------------------------------------------------------------------
# Integration: fetch_greenhouse_jobs
# ---------------------------------------------------------------------------

class TestGreenhouseHttpStatus:
    """Verify fetch_greenhouse_jobs uses is_retryable_status correctly."""

    def test_404_stops_immediately(self, monkeypatch):
        """404 is non-retryable — should return [] without retrying."""
        call_count = 0

        def fake_limited_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            raise _make_http_error(404)

        monkeypatch.setattr("update_jobs.limited_get", fake_limited_get)
        jobs = fetch_greenhouse_jobs("TestCo", "https://api.greenhouse.io/v1/boards/test/jobs")
        assert jobs == []
        assert call_count == 1  # No retries

    def test_429_retries_then_gives_up(self, monkeypatch):
        """429 is retryable — should retry max_retries times then give up."""
        call_count = 0

        def fake_limited_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            raise _make_http_error(429)

        monkeypatch.setattr("update_jobs.limited_get", fake_limited_get)
        jobs = fetch_greenhouse_jobs(
            "TestCo", "https://api.greenhouse.io/v1/boards/test/jobs", max_retries=2
        )
        assert jobs == []
        assert call_count == 3  # 1 initial + 2 retries

    def test_500_retries_then_gives_up(self, monkeypatch):
        """500 is retryable — should exhaust all retries."""
        call_count = 0

        def fake_limited_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            raise _make_http_error(500)

        monkeypatch.setattr("update_jobs.limited_get", fake_limited_get)
        jobs = fetch_greenhouse_jobs(
            "TestCo", "https://api.greenhouse.io/v1/boards/test/jobs", max_retries=1
        )
        assert jobs == []
        assert call_count == 2  # 1 initial + 1 retry


# ---------------------------------------------------------------------------
# Integration: fetch_lever_jobs
# ---------------------------------------------------------------------------

class TestLeverHttpStatus:
    """Verify fetch_lever_jobs uses is_retryable_status correctly."""

    def test_404_stops_immediately(self, monkeypatch):
        """404 is non-retryable — should return [] without retrying."""
        call_count = 0

        def fake_limited_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            raise _make_http_error(404)

        monkeypatch.setattr("update_jobs.limited_get", fake_limited_get)
        jobs = fetch_lever_jobs("TestCo", "https://api.lever.co/v0/postings/test")
        assert jobs == []
        assert call_count == 1  # No retries

    def test_429_retries_then_gives_up(self, monkeypatch):
        """429 is retryable — should retry max_retries times then give up."""
        call_count = 0

        def fake_limited_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            raise _make_http_error(429)

        monkeypatch.setattr("update_jobs.limited_get", fake_limited_get)
        jobs = fetch_lever_jobs(
            "TestCo", "https://api.lever.co/v0/postings/test", max_retries=2
        )
        assert jobs == []
        assert call_count == 3  # 1 initial + 2 retries
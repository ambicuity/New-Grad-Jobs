#!/usr/bin/env python3
"""
Tests for Workday 422 response-body capture (issue #100 instrumentation).

Verifies that when limited_post returns a non-2xx response, fetch_workday_jobs:
  - captures the JSON body (response.json()) when available, OR
  - falls back to response.text[:500] when .json() raises
  - prints the full error body in the warning line (not just the status code)
  - does NOT alter behaviour on successful (2xx) responses

All network calls are mocked — no live requests.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import fetch_workday_jobs  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_company(name="Goldman Sachs", url="https://goldmansachs.wd5.myworkdayjobs.com/GS_Careers"):
    return {"name": name, "workday_url": url}


def _make_response(status_code: int, json_data=None, text: str = ""):
    """Return a mock response object mimicking requests.Response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.ok = (200 <= status_code < 300)
    if json_data is not None:
        mock.json.return_value = json_data
    else:
        mock.json.side_effect = Exception("no JSON body")
    mock.text = text
    return mock


# ---------------------------------------------------------------------------
# 422 logging — JSON body captured
# ---------------------------------------------------------------------------

class TestWorkday422LoggingWithJsonBody:
    """When .json() succeeds, the full JSON body must appear in the warning."""

    def test_422_json_error_body_is_printed(self, capsys):
        error_payload = {
            "errorCode": "CSRF_VALIDATION_FAILED",
            "message": "CSRF token missing or invalid",
        }
        mock_response = _make_response(422, json_data=error_payload)

        with (
            patch("update_jobs.limited_post", return_value=mock_response),
            patch("update_jobs.get_workday_csrf_token", return_value=""),
            patch("update_jobs.HTTP_SESSION", MagicMock()),
        ):
            fetch_workday_jobs([_make_company()])

        out = capsys.readouterr().out
        assert "422" in out
        assert "CSRF_VALIDATION_FAILED" in out
        assert "Goldman Sachs" in out

    def test_422_warning_includes_http_status_label(self, capsys):
        """Output line must contain 'HTTP 422' to distinguish from other noise."""
        mock_response = _make_response(422, json_data={"errorCode": "VALIDATION_ERROR"})

        with (
            patch("update_jobs.limited_post", return_value=mock_response),
            patch("update_jobs.get_workday_csrf_token", return_value=""),
            patch("update_jobs.HTTP_SESSION", MagicMock()),
        ):
            fetch_workday_jobs([_make_company()])

        out = capsys.readouterr().out
        assert "HTTP 422" in out

    def test_422_warning_does_not_suppress_error_body(self, capsys):
        """Old behaviour only printed the status code; new must include body."""
        error_payload = {"errorCode": "MISSING_REQUIRED_FIELD", "expectedFields": ["locale"]}
        mock_response = _make_response(422, json_data=error_payload)

        with (
            patch("update_jobs.limited_post", return_value=mock_response),
            patch("update_jobs.get_workday_csrf_token", return_value=""),
            patch("update_jobs.HTTP_SESSION", MagicMock()),
        ):
            fetch_workday_jobs([_make_company()])

        out = capsys.readouterr().out
        # Both errorCode and the field name must surface
        assert "MISSING_REQUIRED_FIELD" in out
        assert "locale" in out


# ---------------------------------------------------------------------------
# 422 logging — fallback to text[:500]
# ---------------------------------------------------------------------------

class TestWorkday422LoggingWithTextFallback:
    """When .json() raises, response.text[:500] must appear in the warning."""

    def test_422_text_fallback_used_when_json_raises(self, capsys):
        raw_text = "<html><body>Workday error page</body></html>"
        mock_response = _make_response(422, text=raw_text)  # .json() raises by default

        with (
            patch("update_jobs.limited_post", return_value=mock_response),
            patch("update_jobs.get_workday_csrf_token", return_value=""),
            patch("update_jobs.HTTP_SESSION", MagicMock()),
        ):
            fetch_workday_jobs([_make_company()])

        out = capsys.readouterr().out
        assert "Workday error page" in out
        assert "422" in out

    def test_422_text_fallback_truncates_at_500_chars(self, capsys):
        long_text = "X" * 1000
        mock_response = _make_response(422, text=long_text)

        with (
            patch("update_jobs.limited_post", return_value=mock_response),
            patch("update_jobs.get_workday_csrf_token", return_value=""),
            patch("update_jobs.HTTP_SESSION", MagicMock()),
        ):
            fetch_workday_jobs([_make_company()])

        out = capsys.readouterr().out
        # The printed error_body should not contain more than 500 'X' chars
        x_count = out.count("X")
        assert x_count <= 500, f"Text fallback should cap at 500 chars; got {x_count} 'X' chars"

    def test_422_text_fallback_still_prints_status_code(self, capsys):
        mock_response = _make_response(422, text="plain error text")

        with (
            patch("update_jobs.limited_post", return_value=mock_response),
            patch("update_jobs.get_workday_csrf_token", return_value=""),
            patch("update_jobs.HTTP_SESSION", MagicMock()),
        ):
            fetch_workday_jobs([_make_company()])

        out = capsys.readouterr().out
        assert "HTTP 422" in out
        assert "plain error text" in out


# ---------------------------------------------------------------------------
# Non-422 error codes also use the new format
# ---------------------------------------------------------------------------

class TestWorkdayNon422ErrorLogging:
    """Other non-2xx codes (403, 500) should also capture the body."""

    @pytest.mark.parametrize("status_code", [403, 500, 503])
    def test_non_422_errors_also_log_body(self, status_code, capsys):
        error_payload = {"errorCode": "INTERNAL_ERROR", "message": "server exploded"}
        mock_response = _make_response(status_code, json_data=error_payload)

        with (
            patch("update_jobs.limited_post", return_value=mock_response),
            patch("update_jobs.get_workday_csrf_token", return_value=""),
            patch("update_jobs.HTTP_SESSION", MagicMock()),
        ):
            fetch_workday_jobs([_make_company()])

        out = capsys.readouterr().out
        assert str(status_code) in out
        assert "INTERNAL_ERROR" in out


# ---------------------------------------------------------------------------
# Successful responses — behaviour unchanged
# ---------------------------------------------------------------------------

class TestWorkday200SuccessPathUnchanged:
    """On 2xx, fetch_workday_jobs should continue collecting jobs normally."""

    def test_success_response_jobs_are_collected(self):
        page1 = {
            "jobPostings": [
                {
                    "title": "Software Engineer",
                    "externalPath": "/job/123",
                    "locationsText": "New York, NY",
                    "postedOn": "2026-03-01",
                }
            ]
        }
        # Second call returns empty to stop pagination
        empty_page = {"jobPostings": []}

        ok_response_1 = _make_response(200, json_data=page1)
        ok_response_2 = _make_response(200, json_data=empty_page)

        call_count = {"n": 0}

        def fake_limited_post(*args, **kwargs):
            call_count["n"] += 1
            return ok_response_1 if call_count["n"] == 1 else ok_response_2

        with (
            patch("update_jobs.limited_post", side_effect=fake_limited_post),
            patch("update_jobs.get_workday_csrf_token", return_value="tok"),
            patch("update_jobs.HTTP_SESSION", MagicMock()),
        ):
            jobs = fetch_workday_jobs([_make_company()])

        assert len(jobs) == 1
        assert jobs[0]["title"] == "Software Engineer"
        assert jobs[0]["source"] == "Workday"

    def test_success_response_does_not_print_error_warning(self, capsys):
        ok_response = _make_response(200, json_data={"jobPostings": []})

        with (
            patch("update_jobs.limited_post", return_value=ok_response),
            patch("update_jobs.get_workday_csrf_token", return_value="tok"),
            patch("update_jobs.HTTP_SESSION", MagicMock()),
        ):
            fetch_workday_jobs([_make_company()])

        out = capsys.readouterr().out
        assert "⚠️" not in out
        assert "HTTP 4" not in out
        assert "HTTP 5" not in out

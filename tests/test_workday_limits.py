#!/usr/bin/env python3
"""Regression tests for Workday runtime limit handling."""

import logging
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from ngj.settings import DEFAULT_WORKDAY_PAGE_LIMIT  # noqa: E402
from ngj.sources.workday import fetch_workday_jobs  # noqa: E402
from ngj.util import coerce_positive_int as _coerce_positive_int  # noqa: E402


@pytest.fixture(autouse=True)
def _capture_info_logs(caplog):
    """The scraper logs via `logging` (INFO and up); capture it for assertions."""
    caplog.set_level(logging.INFO)



def _make_company() -> dict[str, str]:
    return {
        "name": "Goldman Sachs",
        "workday_url": "https://goldmansachs.wd5.myworkdayjobs.com/GS_Careers",
    }


def _make_response(job_items: list[dict[str, str]]) -> MagicMock:
    mock = MagicMock()
    mock.status_code = 200
    mock.ok = True
    mock.json.return_value = {"jobPostings": job_items}
    return mock


def _make_job_items(start: int, count: int) -> list[dict[str, str]]:
    return [
        {
            "title": f"Software Engineer {index}",
            "externalPath": f"/job/{index}",
            "locationsText": "New York, NY",
            "postedOn": "2026-03-01",
        }
        for index in range(start, start + count)
    ]


@pytest.mark.parametrize("value", [0, -1, "0", "abc", True, 3.5])
def test_coerce_positive_int_rejects_invalid_values(value, caplog):
    result = _coerce_positive_int(value, 20, "apis.workday.page_limit")
    assert result == 20
    assert "Invalid apis.workday.page_limit" in caplog.text


def test_coerce_positive_int_accepts_positive_string_value(caplog):
    assert _coerce_positive_int("25", 20, "apis.workday.page_limit") == 25
    assert caplog.text == ""


def test_fetch_workday_jobs_honors_max_total_limit_exactly(caplog):
    first_page = _make_response(_make_job_items(0, 20))
    second_page = _make_response(_make_job_items(20, 20))

    with (
        patch("ngj.http.limited_post", side_effect=[first_page, second_page]) as mock_post,
        patch("ngj.sources.workday.get_workday_csrf_token", return_value="tok"),
        patch("ngj.http.get_session", return_value=MagicMock()),
    ):
        jobs = list(fetch_workday_jobs([_make_company()], page_limit=20, max_total_limit=25).jobs)

    assert len(jobs) == 25
    assert jobs[-1]["title"] == "Software Engineer 24"
    assert mock_post.call_count == 2
    assert "Reached safety limit of 25 jobs" in caplog.text


def test_fetch_workday_jobs_uses_default_page_limit_when_override_invalid(caplog):
    captured_payloads: list[dict[str, int]] = []

    def fake_limited_post(*_args, **kwargs):
        captured_payloads.append(dict(kwargs["json"]))
        return _make_response([])

    with (
        patch("ngj.http.limited_post", side_effect=fake_limited_post),
        patch("ngj.sources.workday.get_workday_csrf_token", return_value="tok"),
        patch("ngj.http.get_session", return_value=MagicMock()),
    ):
        fetch_workday_jobs([_make_company()], page_limit=0, max_total_limit=5)

    assert captured_payloads[0]["limit"] == DEFAULT_WORKDAY_PAGE_LIMIT
    assert "Invalid page_limit=0" in caplog.text

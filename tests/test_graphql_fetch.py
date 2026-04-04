#!/usr/bin/env python3
"""Unit tests for reusable GraphQL ingestion in scripts/update_jobs.py."""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import (  # noqa: E402
    fetch_all_graphql_jobs_parallel,
    fetch_graphql_jobs,
    get_nested_value,
)


def _make_company_config():
    return {
        "name": "Acme",
        "endpoint": "https://careers.acme.com/graphql",
        "query": "query Careers($after: String) { jobs(first: 2, after: $after) { edges { node { title applyUrl postedAt description locations { name } } } pageInfo { hasNextPage endCursor } } }",
        "variables": {},
        "data_path": "data.jobs.edges",
        "page_info_path": "data.jobs.pageInfo",
        "field_mappings": {
            "title": "title",
            "location": "locations.0.name",
            "url": "applyUrl",
            "posted_at": "postedAt",
            "description": "description",
        },
    }


def _make_graphql_response(jobs_data, has_next_page=False, end_cursor=None):
    return {
        "data": {
            "jobs": {
                "edges": jobs_data,
                "pageInfo": {
                    "hasNextPage": has_next_page,
                    "endCursor": end_cursor,
                },
            }
        }
    }


def _make_mock_response(json_data, status_code=200, raise_json=False):
    response = MagicMock()
    response.status_code = status_code
    response.raise_for_status.return_value = None
    if status_code >= 400:
        response.raise_for_status.side_effect = RuntimeError(f"status={status_code}")
    if raise_json:
        response.json.side_effect = ValueError("invalid json")
    else:
        response.json.return_value = json_data
    return response


def test_get_nested_value_resolves_paths():
    assert get_nested_value({"a": 1}, "a") == 1
    assert get_nested_value({"a": {"b": 2}}, "a.b") == 2
    assert get_nested_value({"a": [{"b": 3}]}, "a.0.b") == 3
    assert get_nested_value({"a": [{"b": 1}, {"b": 2}]}, "a.b") == [1, 2]
    assert get_nested_value({"a": 1}, "a.b") is None
    assert get_nested_value({"a": 1}, "") is None
    assert get_nested_value(["a"], "0") is None


def test_fetch_graphql_jobs_maps_fields_and_defaults_location():
    config = _make_company_config()
    long_description = "x" * 700
    response_payload = _make_graphql_response(
        [
            {"node": {
                "title": "Software Engineer, New Grad",
                "applyUrl": "https://careers.acme.com/jobs/1",
                "postedAt": "2026-03-01T00:00:00Z",
                "description": long_description,
                "locations": [],
            }}
        ]
    )

    with patch("update_jobs.limited_post", return_value=_make_mock_response(response_payload)):
        jobs = fetch_graphql_jobs(config)

    assert len(jobs) == 1
    job = jobs[0]
    assert job["company"] == "Acme"
    assert job["title"] == "Software Engineer, New Grad"
    assert job["location"] == "Remote"
    assert job["url"] == "https://careers.acme.com/jobs/1"
    assert job["posted_at"] == "2026-03-01T00:00:00Z"
    assert job["source"] == "GraphQL"
    assert len(job["description"]) == 500


def test_fetch_graphql_jobs_paginates_with_cursor():
    config = _make_company_config()
    captured_payloads = []

    page_one = _make_graphql_response(
        [{"node": {"title": "Role 1", "applyUrl": "https://x/1", "postedAt": "2026-01-01", "description": "d1", "locations": [{"name": "Remote"}]}}],
        has_next_page=True,
        end_cursor="cursor-1",
    )
    page_two = _make_graphql_response(
        [{"node": {"title": "Role 2", "applyUrl": "https://x/2", "postedAt": "2026-01-02", "description": "d2", "locations": [{"name": "Austin, TX"}]}}],
        has_next_page=False,
        end_cursor=None,
    )

    def _side_effect(*args, **kwargs):
        captured_payloads.append(kwargs.get("json", {}))
        if len(captured_payloads) == 1:
            return _make_mock_response(page_one)
        return _make_mock_response(page_two)

    with patch("update_jobs.limited_post", side_effect=_side_effect):
        jobs = fetch_graphql_jobs(config)

    assert len(jobs) == 2
    first_variables = captured_payloads[0]["variables"]
    second_variables = captured_payloads[1]["variables"]
    assert "after" not in first_variables
    assert second_variables["after"] == "cursor-1"


def test_fetch_graphql_jobs_respects_max_jobs():
    config = _make_company_config()
    page_payload = _make_graphql_response(
        [{"node": {"title": "Role 1", "applyUrl": "https://x/1", "postedAt": "2026-01-01", "description": "", "locations": [{"name": "Remote"}]}}],
        has_next_page=True,
        end_cursor="cursor-1",
    )

    with patch("update_jobs.limited_post", return_value=_make_mock_response(page_payload)) as mocked_post:
        jobs = fetch_graphql_jobs(config, max_jobs=1)

    assert len(jobs) == 1
    assert mocked_post.call_count == 1


def test_fetch_graphql_jobs_returns_empty_on_graphql_errors():
    config = _make_company_config()
    with patch("update_jobs.limited_post", return_value=_make_mock_response({"errors": [{"message": "boom"}]})):
        jobs = fetch_graphql_jobs(config)
    assert jobs == []


def test_fetch_graphql_jobs_handles_http_error():
    config = _make_company_config()
    with patch("update_jobs.limited_post", return_value=_make_mock_response({}, status_code=500)):
        jobs = fetch_graphql_jobs(config)
    assert jobs == []


def test_fetch_graphql_jobs_handles_invalid_json():
    config = _make_company_config()
    with patch("update_jobs.limited_post", return_value=_make_mock_response({}, raise_json=True)):
        jobs = fetch_graphql_jobs(config)
    assert jobs == []


def test_fetch_graphql_jobs_returns_empty_when_data_path_missing():
    config = _make_company_config()
    with patch("update_jobs.limited_post", return_value=_make_mock_response({"data": {}})):
        jobs = fetch_graphql_jobs(config)
    assert jobs == []


def test_fetch_all_graphql_jobs_parallel_aggregates_and_skips_failures(monkeypatch):
    sources = [
        {"name": "Acme"},
        {"name": "Beta"},
        {"name": "Gamma"},
    ]

    def fake_fetch(source_config, max_jobs=200):
        name = source_config["name"]
        if name == "Beta":
            raise RuntimeError("source failed")
        return [{"company": name, "title": "Role", "location": "Remote", "url": f"https://{name}.com", "posted_at": "2026-01-01", "source": "GraphQL", "description": ""}]

    monkeypatch.setattr("update_jobs.fetch_graphql_jobs", fake_fetch)

    jobs = fetch_all_graphql_jobs_parallel(sources, max_jobs_per_source=10, max_workers=2)
    companies = {job["company"] for job in jobs}
    assert companies == {"Acme", "Gamma"}
    assert len(jobs) == 2

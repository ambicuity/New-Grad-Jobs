#!/usr/bin/env python3
"""Unit tests for reusable GraphQL ingestion (scripts/ngj/sources/graphql.py)."""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from pathlib import Path  # noqa: E402

from ngj.models import KIND_CONFIG, KIND_NETWORK, KIND_PARSE, KIND_UNEXPECTED, SourceResult  # noqa: E402
from ngj.settings import Settings  # noqa: E402
from ngj.sources.graphql import fetch_all_graphql_jobs, fetch_graphql_jobs  # noqa: E402
from ngj.util import get_nested_value  # noqa: E402


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
    # 700 chars is below the 3000-char clean_description() ceiling, so it
    # passes through unchanged. Use a >3000-char input to assert clipping.
    long_description = "x" * 4000
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

    with patch("ngj.http.limited_post", return_value=_make_mock_response(response_payload)):
        result = fetch_graphql_jobs(config)
    jobs = list(result.jobs)

    assert len(jobs) == 1
    job = jobs[0]
    assert job["company"] == "Acme"
    assert job["title"] == "Software Engineer, New Grad"
    assert job["location"] == "Remote"
    assert job["url"] == "https://careers.acme.com/jobs/1"
    assert job["posted_at"] == "2026-03-01T00:00:00Z"
    assert job["source"] == "GraphQL"
    # clean_description() clips at 3000 chars on a word boundary and appends "…"
    assert len(job["description"]) <= 3001
    assert job["description"].endswith("…")


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

    with patch("ngj.http.limited_post", side_effect=_side_effect):
        result = fetch_graphql_jobs(config)
    jobs = list(result.jobs)

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

    with patch("ngj.http.limited_post", return_value=_make_mock_response(page_payload)) as mocked_post:
        result = fetch_graphql_jobs(config, max_jobs=1)
    jobs = list(result.jobs)

    assert len(jobs) == 1
    assert mocked_post.call_count == 1


def test_fetch_graphql_jobs_returns_empty_on_graphql_errors():
    config = _make_company_config()
    with patch("ngj.http.limited_post", return_value=_make_mock_response({"errors": [{"message": "boom"}]})):
        result = fetch_graphql_jobs(config)
    jobs = list(result.jobs)
    assert jobs == []
    assert [(e.company, e.source, e.kind) for e in result.errors] == [("Acme", "graphql", KIND_PARSE)]


def test_fetch_graphql_jobs_handles_http_error():
    config = _make_company_config()
    with patch("ngj.http.limited_post", return_value=_make_mock_response({}, status_code=500)):
        result = fetch_graphql_jobs(config)
    jobs = list(result.jobs)
    assert jobs == []
    assert [e.kind for e in result.errors] == [KIND_UNEXPECTED]


def test_fetch_graphql_jobs_handles_invalid_json():
    config = _make_company_config()
    with patch("ngj.http.limited_post", return_value=_make_mock_response({}, raise_json=True)):
        result = fetch_graphql_jobs(config)
    jobs = list(result.jobs)
    assert jobs == []
    assert [e.kind for e in result.errors] == [KIND_PARSE]


def test_fetch_graphql_jobs_returns_empty_when_data_path_missing():
    config = _make_company_config()
    with patch("ngj.http.limited_post", return_value=_make_mock_response({"data": {}})):
        result = fetch_graphql_jobs(config)
    jobs = list(result.jobs)
    assert jobs == []
    assert result.errors == ()


def test_fetch_graphql_jobs_reports_config_error_for_incomplete_source():
    result = fetch_graphql_jobs({"name": "Broken"})
    assert result.jobs == ()
    assert [(e.company, e.kind) for e in result.errors] == [("Broken", KIND_CONFIG)]


def test_fetch_graphql_jobs_reports_network_error():
    import requests

    config = _make_company_config()
    with patch("ngj.http.limited_post", side_effect=requests.exceptions.ConnectionError("down")):
        result = fetch_graphql_jobs(config)
    assert result.jobs == ()
    assert [e.kind for e in result.errors] == [KIND_NETWORK]


def test_fetch_all_graphql_jobs_aggregates_and_records_failures(monkeypatch, tmp_path):
    sources = [
        {"name": "Acme"},
        {"name": "Beta"},
        {"name": "Gamma"},
    ]
    calls = []

    def fake_fetch(source_config, max_jobs=200, timeout=6):
        calls.append((source_config["name"], max_jobs, timeout))
        name = source_config["name"]
        if name == "Beta":
            raise RuntimeError("source failed")
        job = {"company": name, "title": "Role", "location": "Remote", "url": f"https://{name}.com",
               "posted_at": "2026-01-01", "source": "GraphQL", "description": ""}
        return SourceResult(jobs=(job,), raw_count=1)

    monkeypatch.setattr("ngj.sources.graphql.fetch_graphql_jobs", fake_fetch)
    settings = Settings(
        repo_root=tmp_path, output_dir=tmp_path, history_path=Path(tmp_path) / "h.json",
        graphql_max_jobs_per_source=10, graphql_timeout=17, graphql_min_workers=1, graphql_max_workers=2,
    )

    result = fetch_all_graphql_jobs(sources, settings)

    # Merged in config order, independent of completion order.
    assert [job["company"] for job in result.jobs] == ["Acme", "Gamma"]
    assert [(e.company, e.kind) for e in result.errors] == [("Beta", KIND_UNEXPECTED)]
    # Settings values reach every per-source call.
    assert sorted(calls) == [("Acme", 10, 17), ("Beta", 10, 17), ("Gamma", 10, 17)]

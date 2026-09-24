#!/usr/bin/env python3
"""Settings are built once from config.yml + env and actually reach the fetchers."""

import dataclasses
import logging
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from ngj import pipeline  # noqa: E402
from ngj.settings import (  # noqa: E402
    DEFAULT_GOOGLE_MAX_PAGES,
    DEFAULT_GRAPHQL_TIMEOUT,
    DEFAULT_WORKDAY_MAX_WORKERS,
    DEFAULT_WORKDAY_PAGE_LIMIT,
    DEFAULT_WORKDAY_TIMEOUT,
    OUTPUT_DIR_ENV,
    REPO_ROOT,
    Settings,
    build_settings,
    load_config,
    resolve_output_dir,
)

WORKDAY_COMPANY = {"name": "Acme", "workday_url": "https://acme.wd5.myworkdayjobs.com/Acme_Careers"}


def _config(**apis):
    return {"filtering": {}, "apis": apis}


def _empty_page():
    response = MagicMock()
    response.status_code = 200
    response.ok = True
    response.json.return_value = {"jobPostings": []}
    return response


# ---------------------------------------------------------------------------
# build_settings
# ---------------------------------------------------------------------------

def test_settings_is_frozen(tmp_path):
    settings = build_settings(_config(), env={}, repo_root=tmp_path)
    with pytest.raises(dataclasses.FrozenInstanceError):
        settings.workday_timeout = 99


def test_defaults_when_config_is_empty(tmp_path):
    settings = build_settings(_config(), env={}, repo_root=tmp_path)
    assert settings.output_dir == tmp_path / "site" / "public"
    assert settings.history_path == tmp_path / "data" / "market-history.json"
    assert settings.jobs_json_path == tmp_path / "site" / "public" / "jobs.json"
    assert settings.workday_timeout == DEFAULT_WORKDAY_TIMEOUT
    assert settings.workday_page_limit == DEFAULT_WORKDAY_PAGE_LIMIT
    assert settings.workday_max_workers == DEFAULT_WORKDAY_MAX_WORKERS
    assert settings.google_max_pages == DEFAULT_GOOGLE_MAX_PAGES
    assert settings.graphql_timeout == DEFAULT_GRAPHQL_TIMEOUT
    assert settings.workday_enabled is False
    assert settings.graphql_enabled is False


def test_config_values_are_read(tmp_path):
    config = {
        "worker_pools": {"greenhouse_min_workers": 3, "orchestrator_workers": "4", "jobspy_workers": 2},
        "apis": {
            "workday": {"enabled": True, "timeout": 17, "page_limit": 5, "max_jobs_per_company": 9, "max_workers": 3},
            "google": {"enabled": True, "max_pages": 7},
            "graphql": {"enabled": True, "timeout": 11, "max_jobs_per_source": 13},
            "jobspy": {"enabled": True},
        },
    }
    settings = build_settings(config, env={}, repo_root=tmp_path)
    assert (settings.workday_timeout, settings.workday_page_limit) == (17, 5)
    assert (settings.workday_max_jobs_per_company, settings.workday_max_workers) == (9, 3)
    assert settings.google_enabled and settings.google_max_pages == 7
    assert (settings.graphql_timeout, settings.graphql_max_jobs_per_source) == (11, 13)
    assert settings.greenhouse_min_workers == 3
    assert settings.orchestrator_workers == 4
    assert settings.jobspy_workers == 2
    assert settings.workday_enabled and settings.graphql_enabled and settings.jobspy_enabled


def test_google_uppercase_max_pages_key_still_supported(tmp_path):
    settings = build_settings(_config(google={"MAX_PAGES": "5"}), env={}, repo_root=tmp_path)
    assert settings.google_max_pages == 5


@pytest.mark.parametrize("bad", [0, -2, "abc", True, 2.5])
def test_invalid_values_fall_back_to_defaults_with_warning(tmp_path, caplog, bad):
    config = _config(workday={"timeout": bad}, google={"max_pages": bad})
    with caplog.at_level(logging.WARNING):
        settings = build_settings(config, env={}, repo_root=tmp_path)
    assert settings.workday_timeout == DEFAULT_WORKDAY_TIMEOUT
    assert settings.google_max_pages == DEFAULT_GOOGLE_MAX_PAGES
    assert "Invalid apis.workday.timeout" in caplog.text
    assert "Invalid apis.google.max_pages" in caplog.text


def test_output_dir_env_override(tmp_path):
    settings = build_settings(_config(), env={OUTPUT_DIR_ENV: str(tmp_path / "out")}, repo_root=tmp_path)
    assert settings.output_dir == (tmp_path / "out").resolve()
    # history is persistent state and never follows the output dir
    assert settings.history_path == tmp_path / "data" / "market-history.json"


def test_resolve_output_dir_ignores_blank_env(tmp_path):
    assert resolve_output_dir(tmp_path, {OUTPUT_DIR_ENV: "  "}) == tmp_path / "site" / "public"


def test_repo_config_loads_and_builds(tmp_path):
    config = load_config()
    settings = build_settings(config, env={}, repo_root=REPO_ROOT)
    assert settings.workday_enabled is True
    assert "scraper_apis" not in config["apis"]
    assert "readme" not in config


# ---------------------------------------------------------------------------
# Values reach the actual calls (regression: default args bound at import time)
# ---------------------------------------------------------------------------

def _settings(tmp_path, **overrides):
    return Settings(repo_root=tmp_path, output_dir=tmp_path / "out", history_path=tmp_path / "h.json", **overrides)


def test_workday_timeout_from_config_reaches_post_and_csrf_calls(tmp_path):
    config = _config(workday={"enabled": True, "timeout": 17, "page_limit": 7, "companies": [WORKDAY_COMPANY]})
    settings = build_settings(config, env={}, repo_root=tmp_path)
    plan = pipeline.plan_sources(config, settings)

    with (
        patch("ngj.http.limited_post", return_value=_empty_page()) as post,
        patch("ngj.sources.workday.get_workday_csrf_token", return_value="tok") as csrf,
        patch("ngj.http.get_session", return_value=MagicMock()),
    ):
        plan["workday"]()

    assert post.call_args.kwargs["timeout"] == 17
    assert post.call_args.kwargs["json"]["limit"] == 7
    assert csrf.call_args.kwargs["timeout"] == 17


def test_workday_max_jobs_per_company_from_settings_is_enforced(tmp_path):
    settings = _settings(tmp_path, workday_enabled=True, workday_max_jobs_per_company=3, workday_page_limit=2)
    config = _config(workday={"enabled": True, "companies": [WORKDAY_COMPANY]})
    page = MagicMock(status_code=200, ok=True)
    page.json.return_value = {"jobPostings": [
        {"title": f"T{i}", "externalPath": f"/job/{i}", "postedOn": "Posted Today"} for i in range(2)
    ]}
    with (
        patch("ngj.http.limited_post", return_value=page),
        patch("ngj.sources.workday.get_workday_csrf_token", return_value=""),
        patch("ngj.http.get_session", return_value=MagicMock()),
    ):
        result = pipeline.plan_sources(config, settings)["workday"]()
    assert len(result.jobs) == 3


def test_google_max_pages_and_timeout_reach_fetcher(tmp_path):
    settings = _settings(tmp_path, google_enabled=True, google_max_pages=4, http_timeout=9)
    config = _config(google={"enabled": True, "search_terms": ["new grad"]})
    with patch("ngj.pipeline.fetch_google_jobs") as fetch:
        pipeline.plan_sources(config, settings)["google"]()
    fetch.assert_called_once_with(["new grad"], max_pages=4, timeout=9)


def test_google_is_not_planned_when_disabled(tmp_path):
    settings = _settings(tmp_path, google_enabled=False)
    plan = pipeline.plan_sources(_config(google={"enabled": False, "search_terms": ["x"]}), settings)
    assert "google" not in plan


def test_http_timeout_reaches_greenhouse_requests(tmp_path):
    settings = _settings(tmp_path, http_timeout=13, greenhouse_min_workers=1, greenhouse_max_workers=1)
    config = _config(greenhouse={"companies": [{"name": "Acme", "url": "https://boards-api.greenhouse.io/v1/boards/acme/jobs"}]})
    response = MagicMock(status_code=200)
    response.json.return_value = {"jobs": []}
    with patch("ngj.http.limited_get", return_value=response) as get:
        pipeline.plan_sources(config, settings)["greenhouse"]()
    assert get.call_args.kwargs["timeout"] == 13


def test_jobspy_workers_reach_fetcher(tmp_path):
    settings = _settings(tmp_path, jobspy_workers=3)
    config = _config(jobspy={"enabled": True})
    with patch("ngj.pipeline.fetch_jobspy_jobs") as fetch:
        pipeline.plan_sources(config, settings)["jobspy"]()
    fetch.assert_called_once_with({"enabled": True}, workers=3)


def test_disabled_jobspy_is_not_planned(tmp_path):
    assert "jobspy" not in pipeline.plan_sources(_config(jobspy={"enabled": False}), _settings(tmp_path))


def test_plan_sources_skips_empty_and_disabled_sources(tmp_path):
    settings = _settings(tmp_path)
    config = _config(greenhouse={"companies": []}, workday={"enabled": False, "companies": [WORKDAY_COMPANY]},
                     graphql={"enabled": False, "sources": [{"name": "x"}]})
    assert pipeline.plan_sources(config, settings) == {}


def test_settings_paths_are_paths(tmp_path):
    settings = build_settings(_config(), env={}, repo_root=str(tmp_path))
    assert isinstance(settings.repo_root, Path)
    assert isinstance(settings.output_dir, Path)

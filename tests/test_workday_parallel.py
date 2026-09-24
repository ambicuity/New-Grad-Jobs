#!/usr/bin/env python3
"""Tests for the parallel (per-company) Workday fetch path."""

import os
import sys
import threading
import time
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import update_jobs  # noqa: E402
from update_jobs import DEFAULT_WORKDAY_MAX_WORKERS, fetch_workday_jobs  # noqa: E402


def _company(name: str, host: str, site: str = "Careers") -> dict[str, str]:
    return {"name": name, "workday_url": f"https://{host}/{site}"}


def _response(items: list[dict[str, str]]) -> MagicMock:
    mock = MagicMock()
    mock.status_code = 200
    mock.ok = True
    mock.json.return_value = {"jobPostings": items}
    return mock


def _items(tag: str, count: int = 2) -> list[dict[str, str]]:
    return [
        {
            "title": f"{tag} Software Engineer {i}",
            "externalPath": f"/job/{tag}-{i}",
            "locationsText": "Austin, TX",
            "postedOn": "Posted Today",
        }
        for i in range(count)
    ]


def _router(behaviour):
    """Build a limited_post side effect: first page per host from behaviour, then empty."""
    def _post(url, json=None, **_kwargs):
        host = url.split("/")[2]
        if json and json.get("offset", 0) > 0:
            return _response([])
        return behaviour(host)
    return _post


def _no_cooldown():
    return patch.object(update_jobs.SOURCE_COOLDOWN, "is_tripped", return_value=False)


def test_one_company_failing_does_not_drop_the_others(capsys):
    companies = [
        _company("Broken", "broken.wd1.myworkdayjobs.com"),
        _company("Healthy", "healthy.wd1.myworkdayjobs.com"),
    ]

    def behaviour(host):
        if host.startswith("broken"):
            raise RuntimeError("connection reset")
        return _response(_items("healthy"))

    with (
        patch("update_jobs.limited_post", side_effect=_router(behaviour)),
        patch("update_jobs.get_workday_csrf_token", return_value="tok"),
        _no_cooldown(),
    ):
        jobs = fetch_workday_jobs(companies, max_workers=2)

    assert [job["company"] for job in jobs] == ["Healthy", "Healthy"]
    assert "Error processing Broken" in capsys.readouterr().out


def test_companies_are_fetched_concurrently():
    # Both first-page requests must be in flight at once to pass the barrier.
    # A sequential implementation times out here and loses both companies.
    barrier = threading.Barrier(2, timeout=5)
    companies = [
        _company("Alpha", "alpha.wd1.myworkdayjobs.com"),
        _company("Beta", "beta.wd1.myworkdayjobs.com"),
    ]

    def behaviour(host):
        barrier.wait()
        return _response(_items(host.split(".")[0]))

    with (
        patch("update_jobs.limited_post", side_effect=_router(behaviour)),
        patch("update_jobs.get_workday_csrf_token", return_value="tok"),
        _no_cooldown(),
    ):
        jobs = fetch_workday_jobs(companies, max_workers=2)

    assert len(jobs) == 4


def test_results_keep_config_order_regardless_of_completion_order():
    companies = [
        _company("Slow", "slow.wd1.myworkdayjobs.com"),
        _company("Fast", "fast.wd1.myworkdayjobs.com"),
    ]

    def behaviour(host):
        if host.startswith("slow"):
            time.sleep(0.2)
        return _response(_items(host.split(".")[0], count=1))

    with (
        patch("update_jobs.limited_post", side_effect=_router(behaviour)),
        patch("update_jobs.get_workday_csrf_token", return_value="tok"),
        _no_cooldown(),
    ):
        jobs = fetch_workday_jobs(companies, max_workers=2)

    assert [job["company"] for job in jobs] == ["Slow", "Fast"]


def test_companies_sharing_a_host_are_fetched_serially():
    # Workday CSRF cookies are per host on the shared session, so two tenants
    # on one host must not interleave their token GET + POST.
    host = "shared.wd3.myworkdayjobs.com"
    companies = [
        _company("Tenant A", host, "A_Careers"),
        _company("Tenant B", host, "B_Careers"),
        _company("Other", "other.wd3.myworkdayjobs.com"),
    ]
    lock = threading.Lock()
    in_flight = {"shared": 0, "max_shared": 0}

    def behaviour(request_host):
        if request_host == host:
            with lock:
                in_flight["shared"] += 1
                in_flight["max_shared"] = max(in_flight["max_shared"], in_flight["shared"])
            time.sleep(0.05)
            with lock:
                in_flight["shared"] -= 1
        return _response(_items(request_host.split(".")[0], count=1))

    with (
        patch("update_jobs.limited_post", side_effect=_router(behaviour)),
        patch("update_jobs.get_workday_csrf_token", return_value="tok"),
        _no_cooldown(),
    ):
        jobs = fetch_workday_jobs(companies, max_workers=4)

    assert in_flight["max_shared"] == 1
    assert [job["company"] for job in jobs] == ["Tenant A", "Tenant B", "Other"]


def test_cooldown_tripped_company_is_skipped():
    companies = [_company("Skipped", "skipped.wd1.myworkdayjobs.com")]
    with (
        patch("update_jobs.limited_post") as mock_post,
        patch("update_jobs.get_workday_csrf_token", return_value="tok"),
        patch.object(update_jobs.SOURCE_COOLDOWN, "is_tripped", return_value=True),
    ):
        jobs = fetch_workday_jobs(companies, max_workers=2)

    assert jobs == []
    mock_post.assert_not_called()


def test_invalid_max_workers_falls_back_to_default(capsys):
    companies = [_company("Solo", "solo.wd1.myworkdayjobs.com")]
    with (
        patch("update_jobs.limited_post", side_effect=_router(lambda host: _response(_items("solo", 1)))),
        patch("update_jobs.get_workday_csrf_token", return_value="tok"),
        _no_cooldown(),
    ):
        jobs = fetch_workday_jobs(companies, max_workers=0)

    assert len(jobs) == 1
    assert f"using default {DEFAULT_WORKDAY_MAX_WORKERS}" in capsys.readouterr().out


def test_default_max_workers_is_eight():
    assert DEFAULT_WORKDAY_MAX_WORKERS == 8

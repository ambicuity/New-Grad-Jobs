#!/usr/bin/env python3
"""Tests for domain-aware concurrency limiting in scripts/update_jobs.py."""

import os
import sys
import threading
import time
from urllib.parse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import (  # noqa: E402
    DOMAIN_LIMITER,
    DomainConcurrencyLimiter,
    fetch_google_jobs_parallel,
    fetch_greenhouse_jobs,
    fetch_lever_jobs,
    fetch_workday_jobs,
)


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"status={self.status_code}")

    def json(self):
        return self._payload


def test_domain_limiter_caps_greenhouse_concurrency():
    limiter = DomainConcurrencyLimiter({"api.greenhouse.io": 2})
    active = 0
    max_active = 0
    lock = threading.Lock()

    def worker():
        nonlocal active, max_active
        with limiter.acquire("https://api.greenhouse.io/v1/boards/acme/jobs"):
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.05)
            with lock:
                active -= 1

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert max_active <= 2
    assert max_active >= 2


def test_domain_limiter_leaves_other_domains_unthrottled():
    limiter = DomainConcurrencyLimiter({"api.greenhouse.io": 1})
    barrier = threading.Barrier(5)
    failures = []

    def worker():
        try:
            with limiter.acquire("https://jobs.lever.co/postings"):
                barrier.wait(timeout=1)
        except Exception as exc:  # pragma: no cover - assertion below checks empty
            failures.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not failures


def test_repo_domain_limiter_matches_real_greenhouse_hosts() -> None:
    """Verifies the repo-level limiter covers the real Greenhouse host patterns."""
    assert DOMAIN_LIMITER._matched_domain("boards-api.greenhouse.io") == "greenhouse.io"
    assert DOMAIN_LIMITER._matched_domain("foo.api.greenhouse.io") == "greenhouse.io"
    assert DOMAIN_LIMITER._matched_domain("api.lever.co") is None


def test_limiter_integrates_with_greenhouse_lever_and_google_paths(monkeypatch):
    called_urls = []

    def fake_limited_get(url, **kwargs):
        called_urls.append(url)
        host = urlparse(url).netloc

        if host == "api.greenhouse.io":
            return _FakeResponse(
                {
                    "jobs": [
                        {
                            "title": "Software Engineer, New Grad",
                            "location": {"name": "San Francisco, CA"},
                            "absolute_url": "https://example.com/gh/1",
                            "created_at": "2026-03-01T00:00:00Z",
                            "content": "new grad role",
                        }
                    ]
                }
            )

        if host == "api.lever.co":
            return _FakeResponse(
                [
                    {
                        "text": "Backend Engineer, New Grad",
                        "categories": {"location": "Remote"},
                        "hostedUrl": "https://example.com/lever/1",
                        "createdAt": 1700000000000,
                        "description": "entry level",
                    }
                ]
            )

        if host == "careers.google.com":
            return _FakeResponse(
                {
                    "jobs": [
                        {
                            "title": "Software Engineer",
                            "locations": [{"country_code": "US", "display": "Mountain View, CA"}],
                            "apply_url": "https://example.com/google/1",
                            "created": "2026-03-01T00:00:00Z",
                            "description": "new grad",
                        }
                    ]
                }
            )

        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("update_jobs.limited_get", fake_limited_get)

    gh_jobs = fetch_greenhouse_jobs("Acme", "https://api.greenhouse.io/v1/boards/acme/jobs")
    lever_jobs = fetch_lever_jobs("Beta", "https://api.lever.co/v0/postings/beta")
    google_jobs = fetch_google_jobs_parallel(["software engineer"], max_workers=2)

    assert len(gh_jobs) == 1
    assert len(lever_jobs) == 1
    assert len(google_jobs) == 1

    called_hosts = {urlparse(url).netloc for url in called_urls}
    expected_hosts = {"api.greenhouse.io", "api.lever.co", "careers.google.com"}
    assert expected_hosts.issubset(called_hosts)


def test_limiter_integrates_with_workday_post_path(monkeypatch):
    called_urls = []

    class _WorkdayResponse:
        def __init__(self, payload, status_code=200):
            self._payload = payload
            self.status_code = status_code

        @property
        def ok(self):
            return 200 <= self.status_code < 300

        def json(self):
            return self._payload

    def fake_limited_post(url, **kwargs):
        called_urls.append(url)
        payload = kwargs.get("json", {})
        offset = payload.get("offset", 0)
        if offset == 0:
            return _WorkdayResponse(
                {
                    "jobPostings": [
                        {
                            "title": "Software Engineer, New Grad",
                            "externalPath": "/en-US/recruiting/acme/Acme/job/123",
                            "postedOn": "Posted Today",
                            "locationsText": "Remote",
                        }
                    ]
                }
            )
        return _WorkdayResponse({"jobPostings": []})

    monkeypatch.setattr("update_jobs.limited_post", fake_limited_post)

    jobs = fetch_workday_jobs(
        [
            {
                "name": "Acme",
                "workday_url": "https://acme.wd5.myworkdayjobs.com/Acme_External_Careers",
            }
        ]
    )

    assert len(jobs) == 1
    assert jobs[0]["company"] == "Acme"
    assert any("wday/cxs" in url for url in called_urls)


def test_workday_404_retry_uses_path_tenant(monkeypatch):
    called_urls = []

    class _WorkdayResponse:
        def __init__(self, payload, status_code=200):
            self._payload = payload
            self.status_code = status_code

        @property
        def ok(self):
            return 200 <= self.status_code < 300

        def json(self):
            return self._payload

    def fake_limited_post(url, **kwargs):
        called_urls.append(url)
        payload = kwargs.get("json", {})
        offset = payload.get("offset", 0)

        if len(called_urls) == 1:
            return _WorkdayResponse({}, status_code=404)

        if offset == 0:
            return _WorkdayResponse(
                {
                    "jobPostings": [
                        {
                            "title": "Software Engineer, New Grad",
                            "externalPath": "/en-US/recruiting/acme/Acme/job/123",
                            "postedOn": "Posted Today",
                            "locationsText": "Remote",
                        }
                    ]
                }
            )

        return _WorkdayResponse({"jobPostings": []})

    monkeypatch.setattr("update_jobs.limited_post", fake_limited_post)

    jobs = fetch_workday_jobs(
        [
            {
                "name": "Acme",
                "workday_url": "https://foo.wd5.myworkdayjobs.com/acme/Acme_External_Careers",
            }
        ]
    )

    assert len(jobs) == 1
    assert called_urls[0] == "https://foo.wd5.myworkdayjobs.com/wday/cxs/foo/Acme_External_Careers/jobs"
    assert called_urls[1] == "https://foo.wd5.myworkdayjobs.com/wday/cxs/acme/Acme_External_Careers/jobs"


def test_domain_limiter_throttles_greenhouse_subdomains() -> None:
    """Verifies that the limiter correctly throttles Greenhouse subdomains."""
    limiter = DomainConcurrencyLimiter({"greenhouse.io": 1})
    active = 0
    max_active = 0
    lock = threading.Lock()
    start_barrier = threading.Barrier(2)

    def worker(url: str) -> None:
        nonlocal active, max_active
        start_barrier.wait()
        with limiter.acquire(url):
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.05)
            with lock:
                active -= 1

    threads = [
        threading.Thread(target=worker, args=("https://boards-api.greenhouse.io/v1/jobs",)),
        threading.Thread(target=worker, args=("https://foo.api.greenhouse.io/v1/jobs",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert max_active == 1


def test_domain_limiter_throttles_workday_subdomains() -> None:
    """Verifies that the limiter correctly throttles Workday suffixes."""
    limiter = DomainConcurrencyLimiter({"myworkdayjobs.com": 1})
    active = 0
    max_active = 0
    lock = threading.Lock()
    start_barrier = threading.Barrier(2)

    def worker(url: str) -> None:
        nonlocal active, max_active
        start_barrier.wait()
        with limiter.acquire(url):
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.05)
            with lock:
                active -= 1

    threads = [
        threading.Thread(target=worker, args=("https://wd5.myworkdayjobs.com/Acme",)),
        threading.Thread(target=worker, args=("https://wd5.myworkdayjobs.com/Beta",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert max_active == 1


def test_domain_limiter_does_not_throttle_unrelated_domains() -> None:
    """Verifies that unrelated domains remain unthrottled."""
    limiter = DomainConcurrencyLimiter({"greenhouse.io": 1})
    unthrottled_barrier = threading.Barrier(5)
    failures = []

    def unthrottled_worker() -> None:
        try:
            with limiter.acquire("https://unrelated-domain.com/jobs"):
                unthrottled_barrier.wait(timeout=1)
        except Exception as exc:
            failures.append(exc)

    unthrottled_threads = [threading.Thread(target=unthrottled_worker) for _ in range(5)]
    for t in unthrottled_threads:
        t.start()
    for t in unthrottled_threads:
        t.join()

    assert not failures

#!/usr/bin/env python3
"""Tests for domain-aware concurrency limiting in scripts/update_jobs.py."""

import os
import sys
import threading
import time
from urllib.parse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import (  # noqa: E402
    DomainConcurrencyLimiter,
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

        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("update_jobs.limited_get", fake_limited_get)

    gh_jobs = fetch_greenhouse_jobs("Acme", "https://api.greenhouse.io/v1/boards/acme/jobs")
    lever_jobs = fetch_lever_jobs("Beta", "https://api.lever.co/v0/postings/beta")

    assert len(gh_jobs) == 1
    assert len(lever_jobs) == 1

    called_hosts = {urlparse(url).netloc for url in called_urls}
    expected_hosts = {"api.greenhouse.io", "api.lever.co"}
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

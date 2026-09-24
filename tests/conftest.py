#!/usr/bin/env python3
"""
Shared test fixtures and utilities for New Grad Jobs test suite.

This module provides common test infrastructure including:
- Path setup for importing scripts
- Mock factories for common data structures
- Shared constants and test data
"""
import os
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

# Add scripts directory to path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


# ============================================================================
# Mock Data Factories
# ============================================================================

@pytest.fixture
def sample_job() -> dict[str, Any]:
    """Factory for creating a standard job dictionary for testing.

    Returns a job with all common fields populated with realistic test data.
    Use this as a base and modify specific fields for edge case testing.
    """
    return {
        'company': 'Tech Corp',
        'title': 'Software Engineer - New Grad',
        'location': 'San Francisco, CA',
        'url': 'https://example.com/jobs/123',
        'posted_at': datetime.now(UTC).isoformat(),
        'description': 'Join our team as a new grad software engineer.',
        'source': 'Test Source'
    }


@pytest.fixture
def sample_config() -> dict[str, Any]:
    """Factory for creating a minimal valid config structure.

    Returns a config dict with essential fields for testing filter/fetch functions.
    Modify specific sections as needed for individual tests.
    """
    return {
        'filters': {
            'min_days_old': 60,
            'us_only': False,
            'exclude_keywords': ['senior', 'manager'],
            'required_keywords': []
        },
        'greenhouse': {
            'enabled': True,
            'companies': []
        },
        'lever': {
            'enabled': True,
            'companies': []
        },
        'google_careers': {
            'enabled': True,
            'search_terms': ['new grad software engineer']
        }
    }


@pytest.fixture
def greenhouse_company() -> dict[str, str]:
    """Factory for creating a Greenhouse company config entry."""
    return {
        'name': 'Example Corp',
        'url': 'https://boards.greenhouse.io/examplecorp'
    }


@pytest.fixture
def lever_company() -> dict[str, str]:
    """Factory for creating a Lever company config entry."""
    return {
        'name': 'Example Startup',
        'url': 'https://jobs.lever.co/examplestartup'
    }


# ============================================================================
# Test Data Constants
# ============================================================================

# Common location strings for testing location validation
VALID_US_LOCATIONS = [
    'San Francisco, CA',
    'New York, NY',
    'Seattle, WA',
    'Remote - USA',
    'Austin, Texas',
    'United States'
]

VALID_CANADA_LOCATIONS = [
    'Toronto, ON',
    'Vancouver, BC',
    'Montreal, QC',
    'Remote - Canada',
    'Toronto, Ontario'
]

INVALID_LOCATIONS = [
    'London, UK',
    'Berlin, Germany',
    'Tokyo, Japan',
    'Paris, France',
    'Remote - Europe'
]

# Common new grad signal keywords
NEW_GRAD_SIGNALS = [
    'new grad',
    'new graduate',
    'university grad',
    'recent graduate',
    'entry level',
    'entry-level',
    '2026 grad',
    '2027 new grad'
]

# Common exclude keywords
EXCLUDE_KEYWORDS = [
    'senior',
    'staff',
    'principal',
    'lead',
    'manager',
    'director',
    '5+ years',
    '10 years experience'
]


# ============================================================================
# Helper Functions
# ============================================================================

def create_job(
    company: str = 'Test Company',
    title: str = 'Software Engineer',
    location: str = 'San Francisco, CA',
    url: str = 'https://example.com/job',
    posted_at: str = None,
    description: str = '',
    source: str = 'Test',
    **kwargs
) -> dict[str, Any]:
    """Helper to create a job dict with custom fields.

    Args:
        company: Company name
        title: Job title
        location: Job location
        url: Application URL
        posted_at: ISO timestamp (defaults to now if None)
        description: Job description
        source: Data source name
        **kwargs: Additional custom fields

    Returns:
        Dict with job data
    """
    job = {
        'company': company,
        'title': title,
        'location': location,
        'url': url,
        'posted_at': posted_at or datetime.now(UTC).isoformat(),
        'description': description,
        'source': source
    }
    job.update(kwargs)
    return job


def create_jobs_batch(count: int, base_date: datetime = None) -> list[dict[str, Any]]:
    """Helper to create a batch of jobs for bulk testing.

    Args:
        count: Number of jobs to create
        base_date: Starting date (jobs will have dates going backwards from here)

    Returns:
        List of job dicts with varied dates
    """
    if base_date is None:
        base_date = datetime.now(UTC)

    jobs = []
    for i in range(count):
        posted_date = base_date - timedelta(days=i)
        jobs.append(create_job(
            company=f'Company {i}',
            title=f'Engineer {i}',
            url=f'https://example.com/job/{i}',
            posted_at=posted_date.isoformat()
        ))
    return jobs


# ============================================================================
# Test hygiene: no real network, no real (long) sleeps
# ============================================================================
# Kept self-contained at the bottom of this module so it survives refactors
# of the fixtures above. Markers are registered in pyproject.toml.
import socket  # noqa: E402
import time  # noqa: E402

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0", ""})

# Sleeps at or below this many seconds stay real: concurrency tests use tiny
# sleeps (e.g. 0.05s) to force thread interleaving. Anything longer is retry /
# backoff / rate-limit waiting and becomes a no-op so the suite stays fast.
_REAL_SLEEP_MAX_SECONDS = 0.1


class NetworkAccessBlocked(RuntimeError):
    """Raised when a test tries to open a real network connection."""


def _host_of(address: Any) -> str:
    if isinstance(address, tuple) and address:
        return str(address[0])
    return str(address)


@pytest.fixture(autouse=True)
def _block_network(request, monkeypatch):
    """Fail any test that reaches for the real network.

    Patches ``socket.getaddrinfo`` and ``socket.socket.connect``/``connect_ex``.
    Loopback and AF_UNIX connections are allowed. Opt out with
    ``@pytest.mark.network``. Because scraper code often swallows exceptions,
    every blocked attempt is also recorded and the test fails at teardown,
    so hidden network access cannot pass silently.
    """
    if request.node.get_closest_marker("network"):
        yield
        return

    attempts: list[str] = []
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    af_unix = getattr(socket, "AF_UNIX", None)

    def _deny(target: str) -> NetworkAccessBlocked:
        attempts.append(target)
        return NetworkAccessBlocked(
            f"Real network access to {target!r} is blocked in tests. "
            "Mock the HTTP call (e.g. patch requests.get/Session.post) "
            "or mark the test with @pytest.mark.network."
        )

    def _is_allowed(sock: socket.socket, address: Any) -> bool:
        return (af_unix is not None and sock.family == af_unix) or _host_of(address) in _LOCAL_HOSTS

    def guarded_getaddrinfo(host, *args, **kwargs):
        if host is None or str(host) in _LOCAL_HOSTS:
            return real_getaddrinfo(host, *args, **kwargs)
        raise _deny(str(host))

    def guarded_connect(self, address):
        if _is_allowed(self, address):
            return real_connect(self, address)
        raise _deny(_host_of(address))

    def guarded_connect_ex(self, address):
        if _is_allowed(self, address):
            return real_connect_ex(self, address)
        raise _deny(_host_of(address))

    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    yield
    if attempts:
        pytest.fail(f"Test attempted real network access (blocked): {sorted(set(attempts))}", pytrace=False)


@pytest.fixture(autouse=True)
def _fast_sleep(request, monkeypatch):
    """Make ``time.sleep`` a no-op for waits longer than 100ms.

    Code under test calls ``time.sleep`` for retry backoff; there is no value in
    really waiting. Tests that assert on sleep calls keep working: their own
    ``patch('...time.sleep')`` / ``monkeypatch`` is applied after this fixture
    and takes precedence. Opt out with ``@pytest.mark.real_sleep``.
    """
    if request.node.get_closest_marker("real_sleep"):
        return
    real_sleep = time.sleep

    def fast_sleep(seconds: float = 0) -> None:
        if 0 < seconds <= _REAL_SLEEP_MAX_SECONDS:
            real_sleep(seconds)

    monkeypatch.setattr(time, "sleep", fast_sleep)

#!/usr/bin/env python3
"""
Tests for the per-source 403 cooldown/circuit-breaker (issue #184).

Coverage targets:
- SourceCooldownTracker unit tests (all public methods, edge cases, thread safety)
- Integration: fetch_greenhouse_jobs, fetch_lever_jobs and fetch_workday_jobs
  respect the cooldown and report it as a SourceError
- Negative paths: non-403 errors must NOT record counts
- Regression: successful (2xx) paths continue to work correctly
- Architecture: SOURCE_COOLDOWN does not replace DOMAIN_LIMITER

All network calls are mocked — no live requests.
"""

import logging
import os
import sys
import threading
from typing import Any
from unittest.mock import MagicMock

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from ngj import http as ngj_http  # noqa: E402 — module whose globals the adapters look up
from ngj.http import DOMAIN_LIMITER  # noqa: E402
from ngj.models import KIND_COOLDOWN, KIND_FORBIDDEN  # noqa: E402
from ngj.sources import workday as workday_mod  # noqa: E402
from ngj.sources.greenhouse import fetch_greenhouse_jobs  # noqa: E402
from ngj.sources.lever import fetch_lever_jobs  # noqa: E402
from ngj.sources.workday import fetch_workday_jobs  # noqa: E402
from source_cooldown import (  # noqa: E402
    SOURCE_COOLDOWN,
    SOURCE_COOLDOWN_THRESHOLD,
    SourceCooldownTracker,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _capture_info_logs(caplog):
    """Adapters log progress at INFO; capture it so log assertions see it."""
    caplog.set_level(logging.INFO)


def _make_response(status_code: int, json_data: Any = None, text: str = "") -> MagicMock:
    """Return a minimal mock mimicking requests.Response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.ok = (200 <= status_code < 300)
    if json_data is not None:
        mock.json.return_value = json_data
    else:
        mock.json.return_value = {}
    mock.text = text
    # raise_for_status raises only for non-2xx
    if not mock.ok:
        mock.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    else:
        mock.raise_for_status.return_value = None
    return mock


def _fresh_tracker(threshold: int = 3) -> SourceCooldownTracker:
    """Return a new SourceCooldownTracker isolated from module-level state."""
    return SourceCooldownTracker(threshold=threshold)


GH_URL = "https://api.greenhouse.io/v1/boards/acme/jobs"
LEVER_URL = "https://api.lever.co/v0/postings/acme"
WORKDAY_URL = "https://acme.wd5.myworkdayjobs.com/Acme_External_Careers"


# ===========================================================================
# SourceCooldownTracker — unit tests
# ===========================================================================

class TestSourceCooldownTrackerInit:
    """Validates constructor and threshold guard."""

    def test_default_threshold_is_positive(self):
        tracker = SourceCooldownTracker()
        assert tracker._threshold >= 1

    def test_custom_threshold_stored(self):
        tracker = SourceCooldownTracker(threshold=7)
        assert tracker._threshold == 7

    def test_threshold_one_is_valid(self):
        tracker = SourceCooldownTracker(threshold=1)
        assert tracker._threshold == 1

    def test_threshold_zero_raises(self):
        with pytest.raises(ValueError, match=r"threshold must be a positive integer"):
            SourceCooldownTracker(threshold=0)

    def test_threshold_negative_raises(self):
        with pytest.raises(ValueError, match=r"threshold must be a positive integer"):
            SourceCooldownTracker(threshold=-3)

    def test_threshold_bool_true_raises(self):
        # bool is a subclass of int; True == 1 but should still be rejected
        with pytest.raises(ValueError, match=r"threshold must be a positive integer"):
            SourceCooldownTracker(threshold=True)

    def test_threshold_string_raises(self):
        with pytest.raises((ValueError, TypeError)):
            SourceCooldownTracker(threshold="5")  # type: ignore[arg-type]

    def test_fresh_tracker_has_no_tripped_sources(self):
        tracker = _fresh_tracker()
        assert tracker.tripped_sources() == set()

    def test_fresh_tracker_has_no_counts(self):
        tracker = _fresh_tracker()
        assert tracker.counts() == {}


class TestSourceCooldownTrackerDomainKey:
    """Validates domain key derivation."""

    def test_full_url_extracts_base_domain(self):
        assert SourceCooldownTracker.domain_key("https://api.greenhouse.io/v1/jobs") == "greenhouse.io"

    def test_subdomain_stripped(self):
        assert SourceCooldownTracker.domain_key("boards-api.greenhouse.io") == "greenhouse.io"

    def test_lever_url(self):
        assert SourceCooldownTracker.domain_key("https://api.lever.co/v0/postings/acme") == "lever.co"

    def test_workday_url(self):
        assert SourceCooldownTracker.domain_key(
            "https://goldmansachs.wd5.myworkdayjobs.com/GS_Careers"
        ) == "myworkdayjobs.com"

    def test_google_url(self):
        assert SourceCooldownTracker.domain_key(
            "https://careers.google.com/api/v3/search/"
        ) == "google.com"

    def test_plain_domain_no_change(self):
        assert SourceCooldownTracker.domain_key("greenhouse.io") == "greenhouse.io"

    def test_empty_string_returns_empty(self):
        assert SourceCooldownTracker.domain_key("") == ""

    def test_case_normalised_to_lower(self):
        assert SourceCooldownTracker.domain_key("API.Greenhouse.IO") == "greenhouse.io"

    def test_port_stripped(self):
        assert SourceCooldownTracker.domain_key("https://api.greenhouse.io:443/jobs") == "greenhouse.io"

    def test_single_component_host_returned_as_is(self):
        assert SourceCooldownTracker.domain_key("localhost") == "localhost"


class TestSourceCooldownTrackerRecordAndTrip:
    """Validates the core record_403/is_tripped contract."""

    def test_not_tripped_below_threshold(self):
        tracker = _fresh_tracker(threshold=3)
        tracker.record_403(GH_URL)
        tracker.record_403(GH_URL)
        assert not tracker.is_tripped(GH_URL)

    def test_tripped_at_threshold(self):
        tracker = _fresh_tracker(threshold=3)
        for _ in range(3):
            tracker.record_403(GH_URL)
        assert tracker.is_tripped(GH_URL)

    def test_record_returns_true_exactly_on_trip(self):
        tracker = _fresh_tracker(threshold=2)
        result_before = tracker.record_403(GH_URL)  # count=1, below threshold
        result_trip = tracker.record_403(GH_URL)    # count=2, trips
        assert result_before is False
        assert result_trip is True

    def test_record_returns_false_after_already_tripped(self):
        tracker = _fresh_tracker(threshold=1)
        tracker.record_403(GH_URL)  # trips
        result = tracker.record_403(GH_URL)  # already tripped
        assert result is False

    def test_counts_increment_before_trip(self):
        tracker = _fresh_tracker(threshold=5)
        for _ in range(3):
            tracker.record_403(GH_URL)
        key = SourceCooldownTracker.cooldown_key(GH_URL)
        assert tracker.counts()[key] == 3

    def test_counts_not_incremented_after_trip(self):
        tracker = _fresh_tracker(threshold=2)
        tracker.record_403(GH_URL)
        tracker.record_403(GH_URL)  # trips, count=2
        tracker.record_403(GH_URL)  # already tripped — count must NOT go to 3
        key = SourceCooldownTracker.cooldown_key(GH_URL)
        assert tracker.counts()[key] == 2

    def test_different_domains_tracked_independently(self):
        tracker = _fresh_tracker(threshold=2)
        tracker.record_403(GH_URL)
        tracker.record_403(GH_URL)    # greenhouse.io trips
        tracker.record_403(LEVER_URL)  # lever.co only has 1
        assert tracker.is_tripped(GH_URL)
        assert not tracker.is_tripped(LEVER_URL)

    def test_same_board_on_different_subdomains_aggregates(self):
        tracker = _fresh_tracker(threshold=2)
        # The acme board via two Greenhouse API hosts is one tenant.
        tracker.record_403("https://boards-api.greenhouse.io/v1/boards/acme/jobs")
        tracker.record_403("https://api.greenhouse.io/v1/boards/acme/jobs/123")
        assert tracker.is_tripped(GH_URL)

    def test_other_boards_on_the_same_provider_are_not_tripped(self):
        tracker = _fresh_tracker(threshold=2)
        tracker.record_403("https://boards-api.greenhouse.io/v1/boards/beta/jobs")
        tracker.record_403("https://boards-api.greenhouse.io/v1/boards/beta/jobs")
        assert tracker.is_tripped("https://boards-api.greenhouse.io/v1/boards/beta/jobs")
        assert not tracker.is_tripped(GH_URL)

    def test_is_tripped_false_before_any_records(self):
        tracker = _fresh_tracker(threshold=3)
        assert not tracker.is_tripped(GH_URL)
        assert not tracker.is_tripped(LEVER_URL)

    def test_tripped_sources_contains_tripped_domain(self):
        tracker = _fresh_tracker(threshold=1)
        tracker.record_403(GH_URL)
        assert tracker.tripped_sources() == {SourceCooldownTracker.cooldown_key(GH_URL)}

    def test_tripped_sources_does_not_contain_untripped_domain(self):
        tracker = _fresh_tracker(threshold=5)
        tracker.record_403(GH_URL)
        assert "lever.co" not in tracker.tripped_sources()

    def test_counts_snapshot_is_independent_copy(self):
        """Mutating the returned dict must not affect the tracker's internal state."""
        tracker = _fresh_tracker(threshold=5)
        tracker.record_403(GH_URL)
        snapshot = tracker.counts()
        snapshot["greenhouse.io/acme"] = 999
        assert tracker.counts()["greenhouse.io/acme"] == 1

    def test_tripped_sources_snapshot_is_independent_copy(self):
        tracker = _fresh_tracker(threshold=1)
        tracker.record_403(GH_URL)
        snapshot = tracker.tripped_sources()
        snapshot.add("fake.domain")
        assert "fake.domain" not in tracker.tripped_sources()


class TestSourceCooldownTrackerLogging:
    """Validates that the cooldown trip is logged explicitly."""

    def test_trip_emits_explicit_log_line(self, caplog):
        tracker = _fresh_tracker(threshold=2)
        tracker.record_403(GH_URL)
        tracker.record_403(GH_URL)
        out = caplog.text
        assert "COOLDOWN TRIPPED" in out

    def test_no_log_before_threshold(self, caplog):
        tracker = _fresh_tracker(threshold=5)
        tracker.record_403(GH_URL)
        tracker.record_403(GH_URL)
        out = caplog.text
        assert "COOLDOWN TRIPPED" not in out

    def test_trip_logged_only_once(self, caplog):
        tracker = _fresh_tracker(threshold=2)
        for _ in range(5):
            tracker.record_403(GH_URL)
        out = caplog.text
        assert out.count("COOLDOWN TRIPPED") == 1


class TestSourceCooldownTrackerThreadSafety:
    """Validates thread-safe state under concurrent load."""

    def test_concurrent_record_403_correct_trip_count(self):
        """Only the threshold-th call should return True; all others False."""
        threshold = 10
        tracker = _fresh_tracker(threshold=threshold)
        trip_events = []
        lock = threading.Lock()

        def worker():
            result = tracker.record_403(GH_URL)
            if result:
                with lock:
                    trip_events.append(True)

        threads = [threading.Thread(target=worker) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly one trip event should have been recorded
        assert len(trip_events) == 1
        assert tracker.is_tripped(GH_URL)

    def test_concurrent_is_tripped_consistent(self):
        """is_tripped must return consistent values under concurrent access."""
        threshold = 5
        tracker = _fresh_tracker(threshold=threshold)
        # Trip the tracker first
        for _ in range(threshold):
            tracker.record_403(GH_URL)

        results = []
        lock = threading.Lock()

        def reader():
            val = tracker.is_tripped(GH_URL)
            with lock:
                results.append(val)

        threads = [threading.Thread(target=reader) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(results), "All concurrent readers should see is_tripped=True"

    def test_concurrent_try_admit_no_overshoot(self):
        """Concurrent try_admit() calls must never allow more than threshold admissions."""
        threshold = 5
        tracker = _fresh_tracker(threshold=threshold)
        url = "https://api.greenhouse.io/v1/boards/acme/jobs"
        admitted = []
        lock = threading.Lock()

        def worker():
            result = tracker.try_admit(url)
            with lock:
                admitted.append(result)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        admitted_count = sum(admitted)
        assert admitted_count == threshold - 1, (
            f"try_admit() admitted {admitted_count} callers — expected exactly {threshold - 1} "
            f"(threshold-1). TOCTOU race condition detected or admission count incorrect."
        )
        assert tracker.is_tripped(url), "Tracker must be tripped after threshold admissions."


class TestTryAdmitUnit:
    """Direct unit tests for the try_admit() atomic method."""

    def test_returns_true_below_threshold(self):
        tracker = _fresh_tracker(threshold=3)
        url = "https://api.greenhouse.io/v1/boards/acme/jobs"
        assert tracker.try_admit(url) is True, "First call below threshold must return True"
        assert tracker.try_admit(url) is True, "Second call below threshold must return True"

    def test_returns_false_and_trips_at_threshold(self):
        threshold = 3
        tracker = _fresh_tracker(threshold=threshold)
        url = "https://api.greenhouse.io/v1/boards/acme/jobs"
        for _ in range(threshold - 1):
            tracker.try_admit(url)
        # threshold-th call must trip and return False
        result = tracker.try_admit(url)
        assert result is False, "threshold-th call must return False"
        assert tracker.is_tripped(url), "Domain must be tripped after threshold-th call"

    def test_returns_false_without_incrementing_when_already_tripped(self):
        threshold = 2
        tracker = _fresh_tracker(threshold=threshold)
        url = "https://api.greenhouse.io/v1/boards/acme/jobs"
        # Trip it
        for _ in range(threshold):
            tracker.try_admit(url)
        count_after_trip = tracker.counts().get(tracker.cooldown_key(url), 0)
        # Call again — must not increment
        tracker.try_admit(url)
        assert tracker.counts().get(tracker.cooldown_key(url), 0) == count_after_trip, (
            "try_admit() must not increment count when already tripped"
        )

    def test_different_domains_are_independent(self):
        tracker = _fresh_tracker(threshold=2)
        url_a = "https://api.greenhouse.io/v1/boards/acme/jobs"
        url_b = "https://jobs.lever.co/acme/jobs"
        # Trip domain A
        for _ in range(2):
            tracker.try_admit(url_a)
        assert tracker.is_tripped(url_a)
        # Domain B must still admit
        assert tracker.try_admit(url_b) is True, "Separate domain must still be admitted"

    def test_try_admit_consistent_with_counts(self):
        threshold = 4
        tracker = _fresh_tracker(threshold=threshold)
        url = "https://api.greenhouse.io/v1/boards/acme/jobs"
        admitted = sum(1 for _ in range(10) if tracker.try_admit(url))
        # Exactly threshold-1 calls should be admitted (True), threshold-th trips (False)
        assert admitted == threshold - 1, (
            f"Expected {threshold - 1} admitted calls before trip, got {admitted}"
        )


# ===========================================================================
# Module-level constant / singleton verification
# ===========================================================================

class TestModuleLevelConstants:
    """Verifies module-level exports match requirements."""

    def test_source_cooldown_threshold_is_positive_int(self):
        assert isinstance(SOURCE_COOLDOWN_THRESHOLD, int)
        assert SOURCE_COOLDOWN_THRESHOLD >= 1

    def test_source_cooldown_is_tracker_instance(self):
        assert isinstance(SOURCE_COOLDOWN, SourceCooldownTracker)

    def test_source_cooldown_threshold_matches_constant(self):
        assert SOURCE_COOLDOWN._threshold == SOURCE_COOLDOWN_THRESHOLD

    def test_domain_limiter_still_exists(self):
        """DomainConcurrencyLimiter must not have been replaced by cooldown."""
        assert isinstance(DOMAIN_LIMITER, ngj_http.DomainConcurrencyLimiter)

    def test_cooldown_and_limiter_are_distinct_objects(self):
        assert SOURCE_COOLDOWN is not DOMAIN_LIMITER


# ===========================================================================
# fetch_greenhouse_jobs integration
# ===========================================================================

class TestGreenhouseCooldownIntegration:
    """Validates fetch_greenhouse_jobs respects the cooldown."""

    def _success_response(self):
        return _make_response(
            200,
            json_data={
                "jobs": [
                    {
                        "title": "Software Engineer, New Grad 2026",
                        "location": {"name": "San Francisco, CA"},
                        "absolute_url": "https://example.com/job/1",
                        "updated_at": "2026-03-01T00:00:00Z",
                        "content": "entry level",
                    }
                ]
            },
        )

    def _403_response(self):
        return _make_response(403)

    def test_success_path_unaffected_by_cooldown(self, monkeypatch):
        """A fresh tracker must not interfere with successful fetches."""
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(ngj_http, "limited_get", lambda url, **kw: self._success_response())

        jobs = list(fetch_greenhouse_jobs("Acme", GH_URL).jobs)
        assert len(jobs) == 1

    def test_403_records_cooldown(self, monkeypatch, caplog):
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN_THRESHOLD", 5)
        monkeypatch.setattr(ngj_http, "limited_get", lambda url, **kw: self._403_response())

        result = fetch_greenhouse_jobs("Acme", GH_URL)

        key = SourceCooldownTracker.cooldown_key(GH_URL)
        assert tracker.counts().get(key, 0) == 1
        assert [(e.kind, e.status) for e in result.errors] == [(KIND_FORBIDDEN, 403)]

    def test_403_logs_warning(self, monkeypatch, caplog):
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN_THRESHOLD", 5)
        monkeypatch.setattr(ngj_http, "limited_get", lambda url, **kw: self._403_response())

        fetch_greenhouse_jobs("Acme", GH_URL)
        out = caplog.text
        assert "403" in out
        assert "Acme" in out

    def test_403_does_not_retry(self, monkeypatch):
        """403 responses must not trigger the max_retries retry loop."""
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN_THRESHOLD", 5)
        call_count = 0

        def counting_get(url, **kw):
            nonlocal call_count
            call_count += 1
            return self._403_response()

        monkeypatch.setattr(ngj_http, "limited_get", counting_get)
        fetch_greenhouse_jobs("Acme", GH_URL)
        assert call_count == 1, "403 must be handled without retrying"

    def test_skips_when_cooldown_pre_tripped(self, monkeypatch, caplog):
        """If SOURCE_COOLDOWN is already tripped, no HTTP call should be made."""
        tracker = _fresh_tracker(threshold=1)
        tracker.record_403(GH_URL)  # trips immediately (threshold=1)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        caplog.clear()

        call_count = 0

        def should_not_be_called(url, **kw):
            nonlocal call_count
            call_count += 1
            return self._success_response()

        monkeypatch.setattr(ngj_http, "limited_get", should_not_be_called)
        result = fetch_greenhouse_jobs("Acme", GH_URL)
        jobs = list(result.jobs)

        assert jobs == []
        assert call_count == 0, "No HTTP call should be made when cooldown is tripped"
        assert [(e.company, e.source, e.kind) for e in result.errors] == [("Acme", "greenhouse", KIND_COOLDOWN)]
        out = caplog.text
        assert "cooldown" in out.lower() and "⏭️" in out

    def test_403_trips_after_threshold_across_companies(self, monkeypatch, caplog):
        """N companies all returning 403 → trips after threshold-th."""
        threshold = 3
        tracker = _fresh_tracker(threshold=threshold)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN_THRESHOLD", threshold)
        monkeypatch.setattr(ngj_http, "limited_get", lambda url, **kw: self._403_response())

        companies = [f"Company{i}" for i in range(threshold + 2)]
        for name in companies:
            fetch_greenhouse_jobs(name, GH_URL)

        assert tracker.is_tripped(GH_URL)
        out = caplog.text
        assert "COOLDOWN TRIPPED" in out

    def test_non_403_error_does_not_record(self, monkeypatch):
        """A 500 error must NOT increment the 403 counter."""
        tracker = _fresh_tracker(threshold=3)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN_THRESHOLD", 3)
        monkeypatch.setattr(ngj_http, "limited_get", lambda url, **kw: _make_response(500))

        for _ in range(5):
            fetch_greenhouse_jobs("Acme", GH_URL)

        key = SourceCooldownTracker.cooldown_key(GH_URL)
        assert tracker.counts().get(key, 0) == 0
        assert not tracker.is_tripped(GH_URL)

    def test_timeout_does_not_record(self, monkeypatch):
        """A requests.exceptions.Timeout must not increment the 403 counter."""
        tracker = _fresh_tracker(threshold=3)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)

        def raise_timeout(url, **kw):
            raise requests.exceptions.Timeout("timeout")

        monkeypatch.setattr(ngj_http, "limited_get", raise_timeout)
        for _ in range(5):
            fetch_greenhouse_jobs("Acme", GH_URL)

        key = SourceCooldownTracker.cooldown_key(GH_URL)
        assert tracker.counts().get(key, 0) == 0


# ===========================================================================
# fetch_lever_jobs integration
# ===========================================================================

class TestLeverCooldownIntegration:
    """Validates fetch_lever_jobs respects the cooldown."""

    def _success_response(self):
        return _make_response(
            200,
            json_data=[
                {
                    "text": "Backend Engineer, New Grad 2026",
                    "categories": {"location": "Remote"},
                    "hostedUrl": "https://example.com/lever/1",
                    "createdAt": 1700000000000,
                    "description": "entry level",
                }
            ],
        )

    def _403_response(self):
        return _make_response(403)

    def test_success_path_unaffected(self, monkeypatch):
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(ngj_http, "limited_get", lambda url, **kw: self._success_response())
        jobs = list(fetch_lever_jobs("Acme", LEVER_URL).jobs)
        assert len(jobs) == 1

    def test_403_records_count(self, monkeypatch):
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN_THRESHOLD", 5)
        monkeypatch.setattr(ngj_http, "limited_get", lambda url, **kw: self._403_response())

        fetch_lever_jobs("Acme", LEVER_URL)
        key = SourceCooldownTracker.cooldown_key(LEVER_URL)
        assert tracker.counts().get(key, 0) == 1

    def test_skips_when_pre_tripped(self, monkeypatch):
        tracker = _fresh_tracker(threshold=1)
        tracker.record_403(LEVER_URL)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)

        call_count = 0

        def forbidden(url, **kw):
            nonlocal call_count
            call_count += 1
            return self._success_response()

        monkeypatch.setattr(ngj_http, "limited_get", forbidden)
        jobs = list(fetch_lever_jobs("Acme", LEVER_URL).jobs)
        assert jobs == []
        assert call_count == 0

    def test_403_does_not_retry(self, monkeypatch):
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN_THRESHOLD", 5)
        call_count = 0

        def counting_get(url, **kw):
            nonlocal call_count
            call_count += 1
            return self._403_response()

        monkeypatch.setattr(ngj_http, "limited_get", counting_get)
        fetch_lever_jobs("Acme", LEVER_URL)
        assert call_count == 1

    def test_non_403_does_not_record(self, monkeypatch):
        tracker = _fresh_tracker(threshold=3)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN_THRESHOLD", 3)
        monkeypatch.setattr(ngj_http, "limited_get", lambda url, **kw: _make_response(500))

        for _ in range(5):
            fetch_lever_jobs("Acme", LEVER_URL)

        key = SourceCooldownTracker.cooldown_key(LEVER_URL)
        assert tracker.counts().get(key, 0) == 0


# ===========================================================================
# fetch_workday_jobs integration
# ===========================================================================

class TestWorkdayCooldownIntegration:
    """Validates fetch_workday_jobs respects the cooldown."""

    @staticmethod
    def _company() -> dict[str, str]:
        return {"name": "Acme", "workday_url": WORKDAY_URL}

    def _page_response(self, offset=0):
        if offset == 0:
            return _make_response(
                200,
                json_data={
                    "jobPostings": [
                        {
                            "title": "Software Engineer, New Grad",
                            "externalPath": "/en-US/job/123",
                            "postedOn": "Posted Today",
                            "locationsText": "Remote",
                        }
                    ]
                },
            )
        return _make_response(200, json_data={"jobPostings": []})

    def test_success_path_unaffected(self, monkeypatch):
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(workday_mod, "get_workday_csrf_token", lambda host, session, timeout=None: "token")

        def fake_post(url, **kw):
            payload = kw.get("json", {})
            return self._page_response(offset=payload.get("offset", 0))

        monkeypatch.setattr(ngj_http, "limited_post", fake_post)
        jobs = list(fetch_workday_jobs([self._company()]).jobs)
        assert len(jobs) == 1

    def test_403_does_not_retry(self, monkeypatch):
        """A single 403 from Workday must not trigger a retry — call_count must be 1."""
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN_THRESHOLD", 5)
        monkeypatch.setattr(workday_mod, "get_workday_csrf_token", lambda host, session, timeout=None: "token")

        call_count = 0

        def counting_post(url, **kw):
            nonlocal call_count
            call_count += 1
            return _make_response(403)

        monkeypatch.setattr(ngj_http, "limited_post", counting_post)
        fetch_workday_jobs([self._company()])
        assert call_count == 1, (
            f"Expected exactly 1 HTTP call on 403 (no retry), got {call_count}"
        )

    def test_403_records_count(self, monkeypatch):
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN_THRESHOLD", 5)
        monkeypatch.setattr(workday_mod, "get_workday_csrf_token", lambda host, session, timeout=None: "token")
        monkeypatch.setattr(ngj_http, "limited_post", lambda url, **kw: _make_response(403))

        fetch_workday_jobs([self._company()])
        # domain key from the Workday API URL built internally will be myworkdayjobs.com
        workday_key = SourceCooldownTracker.cooldown_key(WORKDAY_URL)
        assert tracker.counts().get(workday_key, 0) >= 1

    def test_403_logs_warning(self, monkeypatch, caplog):
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN_THRESHOLD", 5)
        monkeypatch.setattr(workday_mod, "get_workday_csrf_token", lambda host, session, timeout=None: "token")
        monkeypatch.setattr(ngj_http, "limited_post", lambda url, **kw: _make_response(403))

        fetch_workday_jobs([self._company()])
        out = caplog.text
        assert "403" in out
        assert "Acme" in out

    def test_skips_company_when_pre_tripped(self, monkeypatch):
        tracker = _fresh_tracker(threshold=1)
        # Trip on the Workday domain key
        tracker.record_403(WORKDAY_URL)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(workday_mod, "get_workday_csrf_token", lambda host, session, timeout=None: "token")

        call_count = 0

        def counting_post(url, **kw):
            nonlocal call_count
            call_count += 1
            return self._page_response()

        monkeypatch.setattr(ngj_http, "limited_post", counting_post)
        jobs = list(fetch_workday_jobs([self._company()]).jobs)
        assert jobs == []
        assert call_count == 0

    def test_403s_from_other_tenants_do_not_disable_this_tenant(self, monkeypatch, caplog):
        """Per-tenant keys: 403s from unrelated Workday tenants never trip another tenant."""
        threshold = 3
        tracker = SourceCooldownTracker(threshold=threshold, provider_threshold=100)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(workday_mod, "get_workday_csrf_token", lambda host, session, timeout=None: "tok")
        monkeypatch.setattr(ngj_http, "limited_post", lambda url, **kw: _make_response(403))

        companies = [
            {"name": f"Co{i}", "workday_url": f"https://co{i}.wd5.myworkdayjobs.com/Careers"}
            for i in range(threshold + 1)
        ]
        fetch_workday_jobs(companies)
        assert not tracker.is_tripped(WORKDAY_URL)
        assert "COOLDOWN TRIPPED" not in caplog.text

    def test_provider_breaker_trips_after_provider_threshold(self, monkeypatch, caplog):
        tracker = SourceCooldownTracker(threshold=3, provider_threshold=4)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(workday_mod, "get_workday_csrf_token", lambda host, session, timeout=None: "tok")
        monkeypatch.setattr(ngj_http, "limited_post", lambda url, **kw: _make_response(403))

        companies = [
            {"name": f"Co{i}", "workday_url": f"https://co{i}.wd5.myworkdayjobs.com/Careers"}
            for i in range(4)
        ]
        fetch_workday_jobs(companies)
        assert tracker.is_tripped(WORKDAY_URL)
        assert tracker.tripped_key(WORKDAY_URL) == "myworkdayjobs.com"
        assert "provider 'myworkdayjobs.com'" in caplog.text

        result = fetch_workday_jobs([self._company()])
        assert [e.kind for e in result.errors] == [KIND_COOLDOWN]

    def test_non_403_error_does_not_record(self, monkeypatch):
        tracker = _fresh_tracker(threshold=3)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN_THRESHOLD", 3)
        monkeypatch.setattr(workday_mod, "get_workday_csrf_token", lambda host, session, timeout=None: "tok")
        monkeypatch.setattr(ngj_http, "limited_post", lambda url, **kw: _make_response(500))

        for _ in range(5):
            fetch_workday_jobs([self._company()])

        assert "myworkdayjobs.com" not in tracker.counts()


# ===========================================================================
# Architecture regression: cooldown complements, not replaces, limiter
# ===========================================================================

class TestCooldownArchitecture:
    """Regression suite ensuring architectural constraints are preserved."""

    def test_domain_limiter_still_throttles_greenhouse(self):
        """DOMAIN_LIMITER must still exist and guard greenhouse.io."""
        assert DOMAIN_LIMITER._matched_domain("boards-api.greenhouse.io") == "greenhouse.io"

    def test_adapters_share_the_module_singleton(self):
        """ngj.http (which every adapter goes through) uses the process-wide tracker."""
        assert ngj_http.SOURCE_COOLDOWN is SOURCE_COOLDOWN
        assert ngj_http.SOURCE_COOLDOWN_THRESHOLD == SOURCE_COOLDOWN_THRESHOLD
        assert isinstance(SOURCE_COOLDOWN_THRESHOLD, int) and SOURCE_COOLDOWN_THRESHOLD >= 1

    def test_cooldown_tracker_does_not_inherit_from_domain_limiter(self):
        """SourceCooldownTracker is a distinct type from DomainConcurrencyLimiter."""
        assert not issubclass(SourceCooldownTracker, ngj_http.DomainConcurrencyLimiter)

    def test_cooldown_is_in_memory_only(self):
        """A fresh SourceCooldownTracker must start with empty state (no persistence)."""
        fresh = SourceCooldownTracker(threshold=3)
        assert fresh.counts() == {}
        assert fresh.tripped_sources() == set()

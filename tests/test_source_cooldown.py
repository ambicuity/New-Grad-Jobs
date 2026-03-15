#!/usr/bin/env python3
"""
Tests for the per-source 403 cooldown/circuit-breaker (issue #184).

Coverage targets:
- SourceCooldownTracker unit tests (all public methods, edge cases, thread safety)
- Integration: fetch_greenhouse_jobs, fetch_lever_jobs, fetch_workday_jobs,
  and the Google parallel fetcher respect the cooldown
- Negative paths: non-403 errors must NOT record counts
- Regression: successful (2xx) paths continue to work correctly
- Architecture: SOURCE_COOLDOWN does not replace DOMAIN_LIMITER

All network calls are mocked — no live requests.
"""

import os
import sys
import threading
from typing import Any
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import update_jobs  # noqa: E402 — must import module so we can patch its globals
from source_cooldown import (  # noqa: E402
    SOURCE_COOLDOWN,
    SOURCE_COOLDOWN_THRESHOLD,
    SourceCooldownTracker,
)
from update_jobs import (  # noqa: E402
    DOMAIN_LIMITER,
    fetch_greenhouse_jobs,
    fetch_lever_jobs,
    fetch_workday_jobs,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
        with pytest.raises(ValueError):
            SourceCooldownTracker(threshold=0)

    def test_threshold_negative_raises(self):
        with pytest.raises(ValueError):
            SourceCooldownTracker(threshold=-3)

    def test_threshold_bool_true_raises(self):
        # bool is a subclass of int; True == 1 but should still be rejected
        with pytest.raises(ValueError):
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
        for i in range(3):
            tracker.record_403(GH_URL)
        key = SourceCooldownTracker.domain_key(GH_URL)
        assert tracker.counts()[key] == 3

    def test_counts_not_incremented_after_trip(self):
        tracker = _fresh_tracker(threshold=2)
        tracker.record_403(GH_URL)
        tracker.record_403(GH_URL)  # trips, count=2
        tracker.record_403(GH_URL)  # already tripped — count must NOT go to 3
        key = SourceCooldownTracker.domain_key(GH_URL)
        assert tracker.counts()[key] == 2

    def test_different_domains_tracked_independently(self):
        tracker = _fresh_tracker(threshold=2)
        tracker.record_403(GH_URL)
        tracker.record_403(GH_URL)    # greenhouse.io trips
        tracker.record_403(LEVER_URL)  # lever.co only has 1
        assert tracker.is_tripped(GH_URL)
        assert not tracker.is_tripped(LEVER_URL)

    def test_subdomain_urls_aggregate_to_same_key(self):
        tracker = _fresh_tracker(threshold=2)
        # Two different greenhouse subdomains — both map to greenhouse.io
        tracker.record_403("https://boards-api.greenhouse.io/v1/boards/acme/jobs")
        tracker.record_403("https://api.greenhouse.io/v1/boards/beta/jobs")
        assert tracker.is_tripped(GH_URL)

    def test_is_tripped_false_before_any_records(self):
        tracker = _fresh_tracker(threshold=3)
        assert not tracker.is_tripped(GH_URL)
        assert not tracker.is_tripped(LEVER_URL)

    def test_tripped_sources_contains_tripped_domain(self):
        tracker = _fresh_tracker(threshold=1)
        tracker.record_403(GH_URL)
        assert "greenhouse.io" in tracker.tripped_sources()

    def test_tripped_sources_does_not_contain_untripped_domain(self):
        tracker = _fresh_tracker(threshold=5)
        tracker.record_403(GH_URL)
        assert "lever.co" not in tracker.tripped_sources()

    def test_counts_snapshot_is_independent_copy(self):
        """Mutating the returned dict must not affect the tracker's internal state."""
        tracker = _fresh_tracker(threshold=5)
        tracker.record_403(GH_URL)
        snapshot = tracker.counts()
        snapshot["greenhouse.io"] = 999
        assert tracker.counts()["greenhouse.io"] == 1

    def test_tripped_sources_snapshot_is_independent_copy(self):
        tracker = _fresh_tracker(threshold=1)
        tracker.record_403(GH_URL)
        snapshot = tracker.tripped_sources()
        snapshot.add("fake.domain")
        assert "fake.domain" not in tracker.tripped_sources()


class TestSourceCooldownTrackerLogging:
    """Validates that the cooldown trip is logged explicitly."""

    def test_trip_emits_explicit_log_line(self, capsys):
        tracker = _fresh_tracker(threshold=2)
        tracker.record_403(GH_URL)
        tracker.record_403(GH_URL)
        out = capsys.readouterr().out
        assert "COOLDOWN TRIPPED" in out
        assert "greenhouse.io" in out

    def test_no_log_before_threshold(self, capsys):
        tracker = _fresh_tracker(threshold=5)
        tracker.record_403(GH_URL)
        tracker.record_403(GH_URL)
        out = capsys.readouterr().out
        assert "COOLDOWN TRIPPED" not in out

    def test_trip_logged_only_once(self, capsys):
        tracker = _fresh_tracker(threshold=2)
        for _ in range(5):
            tracker.record_403(GH_URL)
        out = capsys.readouterr().out
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
        assert admitted_count <= threshold, (
            f"try_admit() admitted {admitted_count} callers — exceeds threshold {threshold}. "
            "TOCTOU race condition detected."
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
        count_after_trip = tracker.counts().get(tracker.domain_key(url), 0)
        # Call again — must not increment
        tracker.try_admit(url)
        assert tracker.counts().get(tracker.domain_key(url), 0) == count_after_trip, (
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
        from update_jobs import DomainConcurrencyLimiter
        assert isinstance(DOMAIN_LIMITER, DomainConcurrencyLimiter)

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
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(update_jobs, "limited_get", lambda url, **kw: self._success_response())

        jobs = fetch_greenhouse_jobs("Acme", GH_URL)
        assert len(jobs) == 1

    def test_403_records_cooldown(self, monkeypatch, capsys):
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN_THRESHOLD", 5)
        monkeypatch.setattr(update_jobs, "limited_get", lambda url, **kw: self._403_response())

        fetch_greenhouse_jobs("Acme", GH_URL)

        key = SourceCooldownTracker.domain_key(GH_URL)
        assert tracker.counts().get(key, 0) == 1

    def test_403_logs_warning(self, monkeypatch, capsys):
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN_THRESHOLD", 5)
        monkeypatch.setattr(update_jobs, "limited_get", lambda url, **kw: self._403_response())

        fetch_greenhouse_jobs("Acme", GH_URL)
        out = capsys.readouterr().out
        assert "403" in out
        assert "Acme" in out

    def test_403_does_not_retry(self, monkeypatch):
        """403 responses must not trigger the max_retries retry loop."""
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN_THRESHOLD", 5)
        call_count = 0

        def counting_get(url, **kw):
            nonlocal call_count
            call_count += 1
            return self._403_response()

        monkeypatch.setattr(update_jobs, "limited_get", counting_get)
        fetch_greenhouse_jobs("Acme", GH_URL, max_retries=2)
        assert call_count == 1, "403 must be handled without retrying"

    def test_skips_when_cooldown_pre_tripped(self, monkeypatch, capsys):
        """If SOURCE_COOLDOWN is already tripped, no HTTP call should be made."""
        tracker = _fresh_tracker(threshold=1)
        tracker.record_403(GH_URL)  # trips immediately (threshold=1)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)

        call_count = 0

        def should_not_be_called(url, **kw):
            nonlocal call_count
            call_count += 1
            return self._success_response()

        monkeypatch.setattr(update_jobs, "limited_get", should_not_be_called)
        jobs = fetch_greenhouse_jobs("Acme", GH_URL)

        assert jobs == []
        assert call_count == 0, "No HTTP call should be made when cooldown is tripped"
        out = capsys.readouterr().out
        assert "cooldown" in out.lower() or "⏭️" in out

    def test_403_trips_after_threshold_across_companies(self, monkeypatch, capsys):
        """N companies all returning 403 → trips after threshold-th."""
        threshold = 3
        tracker = _fresh_tracker(threshold=threshold)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN_THRESHOLD", threshold)
        monkeypatch.setattr(update_jobs, "limited_get", lambda url, **kw: self._403_response())

        companies = [f"Company{i}" for i in range(threshold + 2)]
        for name in companies:
            fetch_greenhouse_jobs(name, GH_URL)

        assert tracker.is_tripped(GH_URL)
        out = capsys.readouterr().out
        assert "COOLDOWN TRIPPED" in out

    def test_non_403_error_does_not_record(self, monkeypatch):
        """A 500 error must NOT increment the 403 counter."""
        tracker = _fresh_tracker(threshold=3)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN_THRESHOLD", 3)
        monkeypatch.setattr(update_jobs, "limited_get", lambda url, **kw: _make_response(500))

        for _ in range(5):
            fetch_greenhouse_jobs("Acme", GH_URL, max_retries=0)

        key = SourceCooldownTracker.domain_key(GH_URL)
        assert tracker.counts().get(key, 0) == 0
        assert not tracker.is_tripped(GH_URL)

    def test_timeout_does_not_record(self, monkeypatch):
        """A requests.exceptions.Timeout must not increment the 403 counter."""
        import requests
        tracker = _fresh_tracker(threshold=3)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)

        def raise_timeout(url, **kw):
            raise requests.exceptions.Timeout("timeout")

        monkeypatch.setattr(update_jobs, "limited_get", raise_timeout)
        for _ in range(5):
            fetch_greenhouse_jobs("Acme", GH_URL, max_retries=0)

        key = SourceCooldownTracker.domain_key(GH_URL)
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
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(update_jobs, "limited_get", lambda url, **kw: self._success_response())
        jobs = fetch_lever_jobs("Acme", LEVER_URL)
        assert len(jobs) == 1

    def test_403_records_count(self, monkeypatch):
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN_THRESHOLD", 5)
        monkeypatch.setattr(update_jobs, "limited_get", lambda url, **kw: self._403_response())

        fetch_lever_jobs("Acme", LEVER_URL)
        key = SourceCooldownTracker.domain_key(LEVER_URL)
        assert tracker.counts().get(key, 0) == 1

    def test_skips_when_pre_tripped(self, monkeypatch):
        tracker = _fresh_tracker(threshold=1)
        tracker.record_403(LEVER_URL)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)

        call_count = 0

        def forbidden(url, **kw):
            nonlocal call_count
            call_count += 1
            return self._success_response()

        monkeypatch.setattr(update_jobs, "limited_get", forbidden)
        jobs = fetch_lever_jobs("Acme", LEVER_URL)
        assert jobs == []
        assert call_count == 0

    def test_403_does_not_retry(self, monkeypatch):
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN_THRESHOLD", 5)
        call_count = 0

        def counting_get(url, **kw):
            nonlocal call_count
            call_count += 1
            return self._403_response()

        monkeypatch.setattr(update_jobs, "limited_get", counting_get)
        fetch_lever_jobs("Acme", LEVER_URL, max_retries=2)
        assert call_count == 1

    def test_non_403_does_not_record(self, monkeypatch):
        tracker = _fresh_tracker(threshold=3)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN_THRESHOLD", 3)
        monkeypatch.setattr(update_jobs, "limited_get", lambda url, **kw: _make_response(500))

        for _ in range(5):
            fetch_lever_jobs("Acme", LEVER_URL, max_retries=0)

        key = SourceCooldownTracker.domain_key(LEVER_URL)
        assert tracker.counts().get(key, 0) == 0


# ===========================================================================
# fetch_workday_jobs integration
# ===========================================================================

class TestWorkdayCooldownIntegration:
    """Validates fetch_workday_jobs respects the cooldown."""

    _company = {"name": "Acme", "workday_url": WORKDAY_URL}

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
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(update_jobs, "get_workday_csrf_token", lambda host, session: "token")

        def fake_post(url, **kw):
            payload = kw.get("json", {})
            return self._page_response(offset=payload.get("offset", 0))

        monkeypatch.setattr(update_jobs, "limited_post", fake_post)
        jobs = fetch_workday_jobs([self._company])
        assert len(jobs) == 1

    def test_403_does_not_retry(self, monkeypatch):
        """A single 403 from Workday must not trigger a retry — call_count must be 1."""
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN_THRESHOLD", 5)
        monkeypatch.setattr(update_jobs, "get_workday_csrf_token", lambda host, session: "token")

        call_count = 0

        def counting_post(url, **kw):
            nonlocal call_count
            call_count += 1
            return _make_response(403)

        monkeypatch.setattr(update_jobs, "limited_post", counting_post)
        fetch_workday_jobs([self._company])
        assert call_count == 1, (
            f"Expected exactly 1 HTTP call on 403 (no retry), got {call_count}"
        )

    def test_403_records_count(self, monkeypatch):
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN_THRESHOLD", 5)
        monkeypatch.setattr(update_jobs, "get_workday_csrf_token", lambda host, session: "token")
        monkeypatch.setattr(update_jobs, "limited_post", lambda url, **kw: _make_response(403))

        fetch_workday_jobs([self._company])
        # domain key from the Workday API URL built internally will be myworkdayjobs.com
        assert "myworkdayjobs.com" in tracker.counts()
        assert tracker.counts()["myworkdayjobs.com"] >= 1

    def test_403_logs_warning(self, monkeypatch, capsys):
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN_THRESHOLD", 5)
        monkeypatch.setattr(update_jobs, "get_workday_csrf_token", lambda host, session: "token")
        monkeypatch.setattr(update_jobs, "limited_post", lambda url, **kw: _make_response(403))

        fetch_workday_jobs([self._company])
        out = capsys.readouterr().out
        assert "403" in out
        assert "Acme" in out

    def test_skips_company_when_pre_tripped(self, monkeypatch):
        tracker = _fresh_tracker(threshold=1)
        # Trip on the Workday domain key
        tracker.record_403(WORKDAY_URL)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(update_jobs, "get_workday_csrf_token", lambda host, session: "token")

        call_count = 0

        def counting_post(url, **kw):
            nonlocal call_count
            call_count += 1
            return self._page_response()

        monkeypatch.setattr(update_jobs, "limited_post", counting_post)
        jobs = fetch_workday_jobs([self._company])
        assert jobs == []
        assert call_count == 0

    def test_403_trips_after_threshold_companies(self, monkeypatch, capsys):
        threshold = 3
        tracker = _fresh_tracker(threshold=threshold)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN_THRESHOLD", threshold)
        monkeypatch.setattr(update_jobs, "get_workday_csrf_token", lambda host, session: "tok")
        monkeypatch.setattr(update_jobs, "limited_post", lambda url, **kw: _make_response(403))

        companies = [
            {"name": f"Co{i}", "workday_url": f"https://co{i}.wd5.myworkdayjobs.com/Careers"}
            for i in range(threshold + 1)
        ]
        fetch_workday_jobs(companies)
        assert tracker.is_tripped(WORKDAY_URL)
        out = capsys.readouterr().out
        assert "COOLDOWN TRIPPED" in out

    def test_non_403_error_does_not_record(self, monkeypatch):
        tracker = _fresh_tracker(threshold=3)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN_THRESHOLD", 3)
        monkeypatch.setattr(update_jobs, "get_workday_csrf_token", lambda host, session: "tok")
        monkeypatch.setattr(update_jobs, "limited_post", lambda url, **kw: _make_response(500))

        for _ in range(5):
            fetch_workday_jobs([self._company], max_retries=0)

        assert "myworkdayjobs.com" not in tracker.counts()


# ===========================================================================
# Google parallel fetcher integration
# ===========================================================================

class TestGoogleCooldownIntegration:
    """Validates the Google parallel single-term fetcher respects cooldown."""

    def test_google_403_records_count(self, monkeypatch, capsys):
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN_THRESHOLD", 5)
        monkeypatch.setattr(update_jobs, "limited_get", lambda url, **kw: _make_response(403))

        from update_jobs import fetch_google_jobs_parallel
        fetch_google_jobs_parallel(["software engineer new grad"], max_workers=1)

        assert "google.com" in tracker.counts()

    def test_google_skips_when_pre_tripped(self, monkeypatch):
        tracker = _fresh_tracker(threshold=1)
        tracker.record_403("https://careers.google.com/api/v3/search/")
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)

        call_count = 0

        def counting_get(url, **kw):
            nonlocal call_count
            call_count += 1
            return _make_response(200, json_data={"jobs": []})

        monkeypatch.setattr(update_jobs, "limited_get", counting_get)

        from update_jobs import fetch_google_jobs_parallel
        fetch_google_jobs_parallel(["new grad software engineer"], max_workers=1)

        assert call_count == 0, "No GET should fire when Google is in cooldown"

    def test_google_success_path_unaffected(self, monkeypatch):
        tracker = _fresh_tracker(threshold=5)
        monkeypatch.setattr(update_jobs, "SOURCE_COOLDOWN", tracker)

        def success(url, **kw):
            return _make_response(
                200,
                json_data={
                    "jobs": [
                        {
                            "title": "Software Engineer New Grad",
                            "locations": [{"country_code": "US", "display": "Mountain View, CA"}],
                            "apply_url": "https://example.com/google/1",
                            "created": "2026-03-01T00:00:00Z",
                            "description": "new grad",
                        }
                    ]
                },
            )

        monkeypatch.setattr(update_jobs, "limited_get", success)

        from update_jobs import fetch_google_jobs_parallel
        jobs = fetch_google_jobs_parallel(["software engineer new grad"], max_workers=1)
        assert len(jobs) == 1


# ===========================================================================
# Architecture regression: cooldown complements, not replaces, limiter
# ===========================================================================

class TestCooldownArchitecture:
    """Regression suite ensuring architectural constraints are preserved."""

    def test_domain_limiter_still_throttles_greenhouse(self):
        """DOMAIN_LIMITER must still exist and guard greenhouse.io."""
        assert DOMAIN_LIMITER._matched_domain("boards-api.greenhouse.io") == "greenhouse.io"

    def test_source_cooldown_exported_from_module(self):
        """SOURCE_COOLDOWN must be importable from update_jobs."""
        from update_jobs import SOURCE_COOLDOWN as sc
        assert sc is not None

    def test_source_cooldown_tracker_exported_from_module(self):
        """SourceCooldownTracker class must be importable from update_jobs."""
        from update_jobs import SourceCooldownTracker as sct
        assert sct is not None

    def test_source_cooldown_threshold_exported_from_module(self):
        """SOURCE_COOLDOWN_THRESHOLD constant must be importable."""
        from update_jobs import SOURCE_COOLDOWN_THRESHOLD as t
        assert isinstance(t, int) and t >= 1

    def test_cooldown_tracker_does_not_inherit_from_domain_limiter(self):
        """SourceCooldownTracker is a distinct type from DomainConcurrencyLimiter."""
        from update_jobs import DomainConcurrencyLimiter
        assert not issubclass(SourceCooldownTracker, DomainConcurrencyLimiter)

    def test_cooldown_is_in_memory_only(self):
        """A fresh SourceCooldownTracker must start with empty state (no persistence)."""
        fresh = SourceCooldownTracker(threshold=3)
        assert fresh.counts() == {}
        assert fresh.tripped_sources() == set()

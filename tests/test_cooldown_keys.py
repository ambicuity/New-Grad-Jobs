"""Tenant/board cooldown keys and the provider-wide 403 breaker (source_cooldown)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ngj import http as ngj_http  # noqa: E402
from ngj.models import KIND_COOLDOWN  # noqa: E402
from source_cooldown import (  # noqa: E402
    SOURCE_COOLDOWN,
    SOURCE_COOLDOWN_PROVIDER_THRESHOLD,
    SourceCooldownTracker,
)

GH_URL = "https://boards-api.greenhouse.io/v1/boards/acme/jobs"
LEVER_URL = "https://api.lever.co/v0/postings/acme"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://goldmansachs.wd5.myworkdayjobs.com/GS_Careers", "goldmansachs.wd5.myworkdayjobs.com"),
        ("https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/Site/jobs", "nvidia.wd5.myworkdayjobs.com"),
        ("https://boards-api.greenhouse.io/v1/boards/Stripe/jobs?content=true", "greenhouse.io/stripe"),
        ("https://boards-api.greenhouse.io/v1/boards/stripe/jobs/123", "greenhouse.io/stripe"),
        ("https://boards.greenhouse.io/stripe", "greenhouse.io/stripe"),
        ("https://api.lever.co/v0/postings/acme?mode=json", "lever.co/acme"),
        ("https://jobs.lever.co/acme", "lever.co/acme"),
        ("https://api.ashbyhq.com/posting-api/job-board/openai?includeCompensation=true", "ashbyhq.com/openai"),
        ("https://boards-api.greenhouse.io/", "boards-api.greenhouse.io"),
        ("https://careers.example.co.uk/jobs", "careers.example.co.uk"),
        ("greenhouse.io", "greenhouse.io"),
        ("", ""),
    ],
)
def test_cooldown_key_is_tenant_or_board(url, expected):
    assert SourceCooldownTracker.cooldown_key(url) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://careers.example.co.uk/jobs", "example.co.uk"),
        ("https://jobs.other.co.uk/jobs", "other.co.uk"),
        ("https://jobs.example.com.au/x", "example.com.au"),
        ("https://co.uk", "co.uk"),
    ],
)
def test_domain_key_keeps_country_code_second_level_suffixes_apart(url, expected):
    assert SourceCooldownTracker.domain_key(url) == expected


def test_co_uk_hosts_do_not_share_a_provider_breaker():
    tracker = SourceCooldownTracker(threshold=1, provider_threshold=1)
    tracker.record_403("https://careers.example.co.uk/jobs")
    assert not tracker.is_tripped("https://jobs.other.co.uk/jobs")


def test_provider_threshold_defaults_to_five_times_threshold():
    assert SourceCooldownTracker(threshold=5).provider_threshold == 25


def test_module_singleton_uses_provider_threshold_25():
    assert SOURCE_COOLDOWN_PROVIDER_THRESHOLD == 25
    assert SOURCE_COOLDOWN.provider_threshold == 25
    assert SOURCE_COOLDOWN.threshold == 5


@pytest.mark.parametrize("bad", [0, 2, True, "25"])
def test_provider_threshold_must_be_int_at_least_threshold(bad):
    with pytest.raises(ValueError):
        SourceCooldownTracker(threshold=3, provider_threshold=bad)


def test_provider_breaker_counts_across_boards():
    tracker = SourceCooldownTracker(threshold=3, provider_threshold=3)
    for board in ("a", "b", "c"):
        tracker.try_admit(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs")
    assert tracker.provider_counts() == {"greenhouse.io": 3}
    assert tracker.tripped_key("https://boards-api.greenhouse.io/v1/boards/zzz/jobs") == "greenhouse.io"
    assert not tracker.is_tripped(LEVER_URL)


def test_record_403_returns_true_when_provider_trips():
    tracker = SourceCooldownTracker(threshold=5, provider_threshold=5)
    for tenant in "abcd":
        assert tracker.record_403(f"https://{tenant}.wd1.myworkdayjobs.com/x") is False
    assert tracker.record_403("https://e.wd1.myworkdayjobs.com/x") is True


def test_tripped_board_is_skipped_but_sibling_boards_are_not(monkeypatch):
    tracker = SourceCooldownTracker(threshold=1)
    tracker.record_403(GH_URL)
    monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
    result = ngj_http.cooldown_skip("Acme", "greenhouse", GH_URL)
    assert result is not None
    assert result.errors[0].kind == KIND_COOLDOWN
    assert "greenhouse.io/acme" in result.errors[0].message
    assert ngj_http.cooldown_skip("Beta", "greenhouse", "https://boards-api.greenhouse.io/v1/boards/beta/jobs") is None


def test_provider_trip_surfaces_as_cooldown_error_for_every_board(monkeypatch):
    tracker = SourceCooldownTracker(threshold=5, provider_threshold=5)
    for board in "abcde":
        tracker.try_admit(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs")
    monkeypatch.setattr(ngj_http, "SOURCE_COOLDOWN", tracker)
    result = ngj_http.cooldown_skip("Fresh", "greenhouse", "https://boards-api.greenhouse.io/v1/boards/fresh/jobs")
    assert result is not None
    assert result.errors[0].kind == KIND_COOLDOWN
    assert "'greenhouse.io'" in result.errors[0].message

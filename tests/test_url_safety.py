#!/usr/bin/env python3
"""Tests for the publish-time URL safety gate (scripts/url_safety.py).

The gate is the last guard before URLs are written into the public
``docs/jobs.json`` artifact, so the emphasis here is on *not leaking* internal
targets while never rejecting a legitimate ATS link.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from url_safety import filter_safe_jobs, is_safe_url


# --------------------------------------------------------------------------- #
# is_safe_url — must-allow (legitimate public ATS URLs)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize('url', [
    'https://boards.greenhouse.io/acme',
    'https://job-boards.greenhouse.io/embed/job_app?token=1',
    'https://jobs.lever.co/acme/abc-123',
    'https://acme.wd1.myworkdayjobs.com/en-US/careers',
    'http://careers.example.com/job/123',
    'https://8x8.com/careers',            # digit-containing label must stay allowed
    'https://api.example.co.uk/v1/jobs',
])
def test_public_urls_are_allowed(url):
    assert is_safe_url(url) is True


# --------------------------------------------------------------------------- #
# is_safe_url — must-block (schemes, private/loopback, malformed)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize('url', [
    'ftp://example.com',
    'javascript:alert(1)',
    'file:///etc/passwd',
    'http://localhost/',
    'http://127.0.0.1/',
    'http://10.0.0.1/',
    'http://192.168.1.10/',
    'http://172.16.5.4/',
    'http://[::1]/',
    'http://0.0.0.0/',
    'http://169.254.169.254/latest/meta-data/',   # AWS/GCP/Azure IMDS
    'http://100.100.100.200/',                     # Alibaba metadata
    'http://metadata.google.internal/',
    'http://intranet/',                            # bare single-label host
])
def test_unsafe_urls_are_blocked(url):
    assert is_safe_url(url) is False


# --------------------------------------------------------------------------- #
# is_safe_url — regression tests for the specific bypasses found in review
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize('url', [
    'http://localhost\\evil.example.com/',  # backslash normalised to '/' by clients
    'http://2130706433/',                   # decimal encoding of 127.0.0.1
    'http://0x7f000001/',                   # hex encoding of 127.0.0.1
    'http://017700000001/',                 # octal encoding of 127.0.0.1
    'http://foo.internal/',                 # private-use TLD
    'http://db.local/',
    'http://service.lan/',
    'http://x.test/',
])
def test_known_bypasses_are_blocked(url):
    assert is_safe_url(url) is False


@pytest.mark.parametrize('value', [None, 123, '', '   ', b'https://x.com'])
def test_non_string_and_empty_are_unsafe(value):
    assert is_safe_url(value) is False


# --------------------------------------------------------------------------- #
# filter_safe_jobs
# --------------------------------------------------------------------------- #
def test_filter_keeps_safe_and_drops_unsafe():
    jobs = [
        {'title': 'a', 'url': 'https://boards.greenhouse.io/a'},
        {'title': 'b', 'apply_url': 'http://127.0.0.1/b'},
        {'title': 'c', 'job_url': 'https://jobs.lever.co/c'},
        {'title': 'd'},                       # no URL field at all
        'not-a-dict',                          # malformed entry
    ]
    safe, blocked, samples = filter_safe_jobs(jobs)
    assert [j['title'] for j in safe] == ['a', 'c']
    assert blocked == 3
    assert '<missing>' in samples
    assert '<non-dict>' in samples


def test_filter_blocks_job_when_any_url_field_is_unsafe():
    jobs = [{
        'title': 'mixed',
        'url': 'https://boards.greenhouse.io/ok',
        'apply_url': 'http://169.254.169.254/',
    }]
    safe, blocked, _ = filter_safe_jobs(jobs)
    assert safe == []
    assert blocked == 1


def test_filter_samples_are_capped():
    jobs = [{'url': 'http://127.0.0.1/%d' % i} for i in range(25)]
    _, blocked, samples = filter_safe_jobs(jobs)
    assert blocked == 25
    assert len(samples) == 10


def test_filter_empty_input():
    assert filter_safe_jobs([]) == ([], 0, [])

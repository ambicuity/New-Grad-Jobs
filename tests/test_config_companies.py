#!/usr/bin/env python3
"""Structural guards for the employer boards configured in ``config.yml``.

Company entries are hand-edited in bulk whenever a sourcing sweep adds boards,
which is exactly when copy-paste mistakes slip in: a slug pasted twice, an
``http://`` endpoint, a Greenhouse URL filed under Ashby, or — the easy one to
miss — a Workday ``/wday/cxs/<tenant>/<site>/jobs`` API URL pasted into
``workday_url`` where the scraper expects the *careers* URL and derives the API
path itself via ``build_workday_api_url``.

These tests assert shape only. Liveness is not asserted here: probing every
board over the network would make the suite slow and flaky, so endpoints are
verified by hand at the time they are added and logged in
``docs/removed-companies.md``.
"""

import os
import sys
from collections import Counter
from typing import Any, Dict, List
from urllib.parse import urlparse

import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import build_workday_api_url  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..')

# Per-source contract: which key holds the endpoint, and the prefix it must carry.
SOURCE_CONTRACT = {
    'greenhouse': ('url', 'https://boards-api.greenhouse.io/v1/boards/'),
    'lever': ('url', 'https://api.lever.co/v0/postings/'),
    'ashby': ('url', 'https://api.ashbyhq.com/posting-api/job-board/'),
}


def _config() -> Dict[str, Any]:
    with open(os.path.join(ROOT, 'config.yml'), 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def _companies(source: str) -> List[Dict[str, str]]:
    return _config()['apis'][source]['companies']


def _endpoint(source: str, entry: Dict[str, str]) -> str:
    key = 'workday_url' if source == 'workday' else 'url'
    return entry[key]


ALL_SOURCES = ['greenhouse', 'lever', 'ashby', 'workday']


@pytest.mark.parametrize('source', ALL_SOURCES)
def test_every_company_has_name_and_endpoint(source: str) -> None:
    for entry in _companies(source):
        assert entry.get('name', '').strip(), f"{source}: entry without a name: {entry}"
        assert _endpoint(source, entry).strip(), f"{source}: {entry['name']} has no endpoint"


@pytest.mark.parametrize('source', ALL_SOURCES)
def test_no_duplicate_company_names_within_a_source(source: str) -> None:
    """One board per employer per source — a repeat means a paste slipped in twice.

    Cross-source repeats are legitimate (an employer can run both a Greenhouse
    and an Ashby board), so this guard is deliberately scoped per source.
    """
    names = [e['name'].strip().lower() for e in _companies(source)]
    duplicates = sorted(n for n, count in Counter(names).items() if count > 1)
    assert not duplicates, f"{source}: duplicate company names: {duplicates}"


def test_no_duplicate_endpoints_anywhere() -> None:
    """The same board URL must not be scraped twice — it doubles the request cost."""
    endpoints = [
        _endpoint(source, entry).strip().lower()
        for source in ALL_SOURCES
        for entry in _companies(source)
    ]
    duplicates = sorted(u for u, count in Counter(endpoints).items() if count > 1)
    assert not duplicates, f"duplicate board endpoints: {duplicates}"


@pytest.mark.parametrize('source', sorted(SOURCE_CONTRACT))
def test_endpoints_match_their_source_prefix(source: str) -> None:
    """A board filed under the wrong source is fetched by the wrong parser."""
    _, prefix = SOURCE_CONTRACT[source]
    for entry in _companies(source):
        url = _endpoint(source, entry)
        assert url.startswith(prefix), f"{source}: {entry['name']} -> {url}"
        slug = url[len(prefix):].strip('/').split('/')[0]
        assert slug, f"{source}: {entry['name']} has an empty board slug"


def test_workday_entries_use_careers_urls_not_cxs_api_urls() -> None:
    """``workday_url`` holds the careers URL; the scraper derives the CXS path.

    Storing the ``/wday/cxs/<tenant>/<site>/jobs`` form instead would make
    ``build_workday_api_url`` treat ``jobs`` as the site id and produce a dead
    endpoint, so the mistake fails silently at scrape time rather than loudly here.
    """
    for entry in _companies('workday'):
        url = entry['workday_url']
        parsed = urlparse(url)
        assert parsed.scheme == 'https', f"{entry['name']}: not https -> {url}"
        assert 'myworkdayjobs.com' in parsed.netloc, f"{entry['name']}: not a Workday host -> {url}"
        assert '/wday/cxs/' not in url, (
            f"{entry['name']}: workday_url must be the careers URL, not the CXS API URL -> {url}"
        )
        api_url = build_workday_api_url(parsed.netloc, parsed.path)
        assert api_url.endswith('/jobs'), f"{entry['name']}: cannot derive an API URL from {url}"


@pytest.mark.parametrize('source', ALL_SOURCES)
def test_all_endpoints_are_https(source: str) -> None:
    for entry in _companies(source):
        url = _endpoint(source, entry)
        assert url.startswith('https://'), f"{source}: {entry['name']} -> {url}"


def test_configured_company_total_clears_the_expected_minimum() -> None:
    """Guards against a bulk edit silently deleting a chunk of the board list."""
    config = _config()
    total = sum(len(config['apis'][source]['companies']) for source in ALL_SOURCES)
    minimum = config['filtering']['min_expected_companies']
    assert total >= minimum, f"only {total} configured boards, expected >= {minimum}"

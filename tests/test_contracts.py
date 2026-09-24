#!/usr/bin/env python3

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from contracts import (  # noqa: E402
    JOBS_SCHEMA_VERSION,
    compute_job_id,
    validate_jobs_json_contract,
)


def test_compute_job_id_is_stable_and_normalized() -> None:
    base = {
        'company': 'Acme',
        'title': 'Software Engineer',
        'url': 'https://example.com/job/1',
        'location': 'Remote',
        'source': 'Greenhouse',
    }
    variant = {
        'company': ' acme ',
        'title': 'software engineer',
        'url': 'https://example.com/job/1',
        'location': 'remote',
        'source': 'greenhouse',
    }
    assert compute_job_id(base) == compute_job_id(variant)


def test_validate_jobs_json_contract_accepts_valid_payload() -> None:
    payload = {
        'meta': {
            'schema_version': JOBS_SCHEMA_VERSION,
            'generated_at': '2026-04-07T00:00:00',
            'total_jobs': 1,
            'categories': [],
        },
        'jobs': [
            {
                'schema_version': JOBS_SCHEMA_VERSION,
                'job_id': 'job_abc',
                'id': '1',
                'company': 'Acme',
                'title': 'SWE',
                'location': 'Remote',
                'url': 'https://example.com',
                'posted_at': '2026-04-07T00:00:00',
                'source': 'Greenhouse',
                'category': {},
                'company_tier': {},
                'flags': {},
                'is_closed': False,
            }
        ],
    }
    ok, errors = validate_jobs_json_contract(payload)
    assert ok is True
    assert errors == []
    legacy_required_keys = {
        'id',
        'company',
        'title',
        'location',
        'url',
        'posted_at',
        'source',
        'category',
        'company_tier',
        'flags',
        'is_closed',
    }
    assert legacy_required_keys.issubset(payload['jobs'][0].keys())


def test_validate_jobs_json_contract_does_not_require_posted_display() -> None:
    """posted_display was dropped: consumers compute relative ages from posted_at."""
    payload = {
        'meta': {'schema_version': JOBS_SCHEMA_VERSION},
        'jobs': [{
            'schema_version': JOBS_SCHEMA_VERSION, 'job_id': 'job_abc', 'id': '1', 'company': 'Acme',
            'title': 'SWE', 'location': 'Remote', 'url': 'https://example.com',
            'posted_at': '2026-04-07T00:00:00Z', 'source': 'Greenhouse', 'category': {},
            'company_tier': {}, 'flags': {}, 'is_closed': False,
        }],
    }
    ok, errors = validate_jobs_json_contract(payload)
    assert ok is True, errors


def test_validate_jobs_json_contract_reports_missing_keys() -> None:
    payload = {'meta': {'schema_version': JOBS_SCHEMA_VERSION}, 'jobs': [{'job_id': 'job_1'}]}
    ok, errors = validate_jobs_json_contract(payload)
    assert ok is False
    assert any('missing keys' in err for err in errors)

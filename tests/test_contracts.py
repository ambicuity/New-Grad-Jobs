#!/usr/bin/env python3

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from contracts import (  # noqa: E402
    JOB_ID_RE,
    JOBS_SCHEMA_VERSION,
    canonical_url,
    compute_job_id,
    validate_jobs_json_contract,
)

JOB_ID = 'job_0123456789abcdef0123'


def _job(**overrides):
    job = {
        'job_id': JOB_ID, 'id': JOB_ID, 'company': 'Acme',
        'title': 'SWE', 'location': 'Remote', 'url': 'https://example.com',
        'posted_at': '2026-04-07T00:00:00Z', 'source': 'Greenhouse', 'category': {},
        'company_tier': {}, 'flags': {}, 'is_closed': False,
    }
    job.update(overrides)
    return job


def _payload(jobs):
    return {'meta': {'schema_version': JOBS_SCHEMA_VERSION}, 'jobs': jobs}


# --- canonical_url ---------------------------------------------------------

@pytest.mark.parametrize('raw, expected', [
    ('https://Boards.Greenhouse.io/acme/jobs/123?gh_jid=123&gh_src=abc&utm_source=x',
     'https://boards.greenhouse.io/acme/jobs/123?gh_jid=123'),
    ('https://jobs.lever.co/acme/ABC-123/', 'https://jobs.lever.co/acme/ABC-123'),
    ('https://jobs.lever.co/acme/ABC-123/?lever-source=linkedin', 'https://jobs.lever.co/acme/ABC-123'),
    ('https://jobs.ashbyhq.com/notion/5f1e?utm_campaign=x#apply', 'https://jobs.ashbyhq.com/notion/5f1e'),
    ('https://www.indeed.com/viewjob?from=serp&jk=abc123', 'https://www.indeed.com/viewjob?jk=abc123'),
    ('https://careers.acme.com/job?jobId=77&ref=li', 'https://careers.acme.com/job?jobid=77'),
    ('HTTPS://EXAMPLE.com:443/a//b/', 'https://example.com/a/b'),
    ('http://example.com:8080/a', 'http://example.com:8080/a'),
    ('https://example.com/', 'https://example.com'),
    ('https://boards.greenhouse.io/robinhood/jobs/8189007?t=gh_src=&gh_jid=8189007',
     'https://boards.greenhouse.io/robinhood/jobs/8189007?gh_jid=8189007'),
])
def test_canonical_url_strips_tracking_and_normalizes(raw, expected):
    assert canonical_url(raw) == expected


@pytest.mark.parametrize('raw', [None, '', '   ', 'javascript:alert(1)', 'mailto:a@b.c', '/relative/path',
                                 'https://', float('nan'), 123, 'https://[::1'])
def test_canonical_url_returns_empty_for_unusable_urls(raw):
    assert canonical_url(raw) == ''


def test_canonical_url_preserves_path_case():
    assert canonical_url('https://x.myworkdayjobs.com/job/Pune/SWE_R-1') == 'https://x.myworkdayjobs.com/job/Pune/SWE_R-1'


# --- compute_job_id --------------------------------------------------------

def test_compute_job_id_format():
    assert JOB_ID_RE.match(compute_job_id({'source': 'Greenhouse', 'url': 'https://a.com/1'}))


def test_compute_job_id_ignores_tracking_params_and_title_edits():
    base = {'company': 'Acme', 'title': 'Software Engineer', 'location': 'Remote',
            'url': 'https://boards.greenhouse.io/acme/jobs/1', 'source': 'Greenhouse'}
    variant = {**base, 'title': 'Software Engineer I', 'location': 'Remote, US',
               'url': 'https://boards.greenhouse.io/acme/jobs/1/?utm_source=linkedin'}
    assert compute_job_id(base) == compute_job_id(variant)


def test_compute_job_id_differs_by_source_and_url():
    a = {'url': 'https://a.com/1', 'source': 'Greenhouse'}
    assert compute_job_id(a) != compute_job_id({**a, 'source': 'Ashby'})
    assert compute_job_id(a) != compute_job_id({**a, 'url': 'https://a.com/2'})


def test_compute_job_id_falls_back_to_company_title_location_without_url():
    base = {'company': 'Acme', 'title': 'SWE', 'location': 'Remote', 'source': 'GraphQL', 'url': ''}
    assert compute_job_id(base) == compute_job_id({**base, 'company': ' acme ', 'url': None})
    assert compute_job_id(base) != compute_job_id({**base, 'title': 'SRE'})


def test_compute_job_id_distinct_for_colliding_legacy_slugs():
    """Same company/title/location (the old id) but two requisitions → two ids."""
    a = {'company': 'Anduril', 'title': 'Systems Engineer', 'location': 'Irvine', 'source': 'Greenhouse',
         'url': 'https://boards.greenhouse.io/andurilindustries/jobs/4843948007'}
    b = {**a, 'url': 'https://boards.greenhouse.io/andurilindustries/jobs/4929997007'}
    assert compute_job_id(a) != compute_job_id(b)


# --- validate_jobs_json_contract ------------------------------------------

def test_contract_accepts_valid_payload_without_per_job_schema_version():
    ok, errors = validate_jobs_json_contract(_payload([_job()]))
    assert ok is True, errors


def test_contract_requires_meta_schema_version():
    ok, errors = validate_jobs_json_contract({'meta': {}, 'jobs': [_job()]})
    assert ok is False
    assert any('meta.schema_version' in e for e in errors)


def test_contract_reports_missing_keys():
    ok, errors = validate_jobs_json_contract(_payload([{'job_id': JOB_ID}]))
    assert ok is False
    assert any('missing keys' in err for err in errors)


def test_contract_rejects_id_not_equal_to_job_id():
    ok, errors = validate_jobs_json_contract(_payload([_job(id='acme-swe-remote')]))
    assert ok is False
    assert any('id must equal job_id' in e for e in errors)


def test_contract_rejects_malformed_job_id():
    ok, errors = validate_jobs_json_contract(_payload([_job(job_id='job_123', id='job_123')]))
    assert ok is False
    assert any('job_id must match' in e for e in errors)


def test_contract_rejects_duplicate_job_ids():
    ok, errors = validate_jobs_json_contract(_payload([_job(), _job(title='Other')]))
    assert ok is False
    assert any('duplicate job_id' in e for e in errors)


def test_contract_rejects_non_object_root_and_non_list_jobs():
    assert validate_jobs_json_contract([])[0] is False
    ok, errors = validate_jobs_json_contract({'meta': {'schema_version': JOBS_SCHEMA_VERSION}, 'jobs': {}})
    assert ok is False and 'jobs must be a list' in errors


def test_contract_type_checks():
    ok, errors = validate_jobs_json_contract(_payload([_job(is_closed='no', flags=None, first_seen=5)]))
    assert ok is False
    joined = ' '.join(errors)
    assert 'is_closed' in joined and 'flags' in joined and 'first_seen' in joined

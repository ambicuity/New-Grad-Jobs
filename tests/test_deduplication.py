#!/usr/bin/env python3
"""Tests for ngj.dedup: same-posting (canonical URL) and cross-source passes."""

import logging
import os
import sys
from typing import Any

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from contracts import compute_job_id  # noqa: E402
from ngj.dedup import (  # noqa: E402
    cross_source_key,
    deduplicate_jobs,
    deduplicate_jobs_with_stats,
    get_job_key,
    is_aggregator_source,
    location_tokens,
    locations_compatible,
    normalize_company,
)


@pytest.fixture(autouse=True)
def _capture_info_logs(caplog):
    caplog.set_level(logging.INFO)


def _make_job(**kwargs) -> dict[str, Any]:
    defaults = {
        'company': 'Test Corp',
        'title': 'Engineer',
        'url': 'https://example.com/job',
        'location': 'New York, NY',
        'posted_at': '2026-03-01',
        'source': 'Greenhouse',
    }
    defaults.update(kwargs)
    return defaults


class TestGetJobKey:
    def test_key_equals_published_job_id(self):
        job = _make_job()
        assert get_job_key(job) == compute_job_id(job)

    def test_tracking_params_do_not_change_key(self):
        a = _make_job(url='https://boards.greenhouse.io/acme/jobs/1?gh_jid=1')
        b = _make_job(url='https://boards.greenhouse.io/acme/jobs/1/?gh_jid=1&gh_src=li&utm_source=x')
        assert get_job_key(a) == get_job_key(b)

    @pytest.mark.parametrize('bad', [None, float('nan'), float('inf'), 123])
    def test_key_tolerates_non_string_values(self, bad):
        assert get_job_key(_make_job(company=bad, title=bad, url=bad)).startswith('job_')


class TestNormalization:
    def test_company_suffixes_and_punctuation(self):
        assert normalize_company('Databricks, Inc.') == normalize_company('databricks')
        assert normalize_company('AT&T') == 'at and t'
        assert normalize_company('Co') == 'co'  # a lone suffix word is kept

    def test_cross_source_key_requires_company_and_title(self):
        assert cross_source_key(_make_job(company='')) is None
        assert cross_source_key(_make_job(title=None)) is None
        assert cross_source_key(_make_job(company='Société Générale')) == ('societe generale', 'engineer')

    @pytest.mark.parametrize('a, b', [
        ('Santa Clara, CA, US', 'US, California, Santa Clara'),
        ('Toronto, Canada', 'Toronto, ON, CA'),
        ('New York, NY, US', 'New York City, New York'),
        ('Palo Alto, CA, US', '2 Locations'),
        ('Remote, US', 'United States (Remote)'),
        ('', 'London'),
    ])
    def test_locations_compatible_across_source_formats(self, a, b):
        assert locations_compatible(a, b)

    @pytest.mark.parametrize('a, b', [
        ('New York, NY', 'London, UK'),
        ('Seattle, WA', 'Austin, TX'),
    ])
    def test_different_cities_are_incompatible(self, a, b):
        assert not locations_compatible(a, b)

    def test_location_tokens_drop_noise(self):
        assert location_tokens('US, California, Santa Clara') == {'santa', 'clara'}
        assert location_tokens('Hybrid - 2 Locations') == frozenset()

    @pytest.mark.parametrize('source, expected', [
        ('JobSpy (Indeed)', True), ('JobSpy (Linkedin)', True), ('', True), (None, True),
        ('Greenhouse', False), ('Ashby', False), ('Workday', False), ('Google Careers', False),
    ])
    def test_is_aggregator_source(self, source, expected):
        assert is_aggregator_source(source) is expected


class TestSamePostingPass:
    def test_no_duplicates_kept_in_order(self):
        jobs = [
            _make_job(company='ACME', title='SWE', url='https://acme.com/swe'),
            _make_job(company='ACME', title='DevOps', url='https://acme.com/devops'),
            _make_job(company='TechCorp', title='SWE', url='https://tech.com/swe'),
        ]
        assert deduplicate_jobs(jobs) == jobs

    def test_exact_duplicates_removed_and_logged(self, caplog):
        job = _make_job(company='ACME', title='SWE', url='https://acme.com/swe')
        result = deduplicate_jobs([job, job, job])
        assert result == [job]
        assert "Removed 2 duplicate jobs" in caplog.text

    def test_tracking_param_variants_are_one_posting(self, caplog):
        a = _make_job(url='https://jobs.lever.co/acme/abc?lever-source=LinkedIn')
        b = _make_job(url='https://jobs.lever.co/acme/abc/')
        assert deduplicate_jobs([a, b]) == [a]

    def test_same_url_is_one_posting_even_if_title_changed(self):
        """The URL identifies the posting; a retitled copy is the same job."""
        a = _make_job(title='Software Engineer', url='https://acme.com/careers/1')
        b = _make_job(title='Software Engineer I', url='https://acme.com/careers/1')
        assert deduplicate_jobs([a, b]) == [a]

    def test_different_urls_same_source_are_kept(self):
        """Distinct requisitions routinely share company/title/location."""
        a = _make_job(url='https://boards.greenhouse.io/anduril/jobs/1')
        b = _make_job(url='https://boards.greenhouse.io/anduril/jobs/2')
        assert deduplicate_jobs([a, b]) == [a, b]

    def test_no_url_falls_back_to_company_title_location(self):
        a = _make_job(url='', source='GraphQL')
        b = _make_job(url=None, source='GraphQL', company=' test corp ')
        c = _make_job(url=None, source='GraphQL', title='Other')
        assert deduplicate_jobs([a, b, c]) == [a, c]

    def test_empty_and_single(self, caplog):
        assert deduplicate_jobs([]) == []
        job = _make_job()
        assert deduplicate_jobs([job]) == [job]
        assert "Removed" not in caplog.text

    def test_input_not_mutated(self):
        jobs = [_make_job(), _make_job()]
        snapshot = [dict(j) for j in jobs]
        deduplicate_jobs(jobs)
        assert jobs == snapshot

    def test_large_list(self):
        base = _make_job()
        jobs = [base] * 500 + [_make_job(url=f'https://example.com/{i}', title=f'T{i}') for i in range(500)]
        assert len(deduplicate_jobs(jobs)) == 501


class TestCrossSourcePass:
    def test_ats_beats_jobspy(self):
        ats = _make_job(source='Greenhouse', url='https://boards.greenhouse.io/acme/jobs/1')
        indeed = _make_job(source='JobSpy (Indeed)', url='https://www.indeed.com/viewjob?jk=1')
        result, stats = deduplicate_jobs_with_stats([indeed, ats])
        assert result == [ats]
        assert stats.cross_source == 1 and stats.same_posting == 0

    def test_company_on_two_atss_keeps_the_richer_one(self):
        gh = _make_job(company='Databricks', source='Greenhouse', url='https://databricks.com/job?gh_jid=1',
                       description='')
        ashby = _make_job(company='Databricks, Inc.', source='Ashby', url='https://jobs.ashbyhq.com/databricks/x',
                          description='A real description', comp={'min': 1, 'max': 2})
        assert deduplicate_jobs([gh, ashby]) == [ashby]

    def test_equal_data_tie_goes_to_first_seen_source(self):
        gh = _make_job(source='Greenhouse', url='https://a.com/1')
        ashby = _make_job(source='Ashby', url='https://b.com/1')
        assert deduplicate_jobs([gh, ashby]) == [gh]
        assert deduplicate_jobs([ashby, gh]) == [ashby]

    def test_all_jobs_of_the_losing_source_are_dropped_winner_keeps_all(self):
        gh = [_make_job(source='Greenhouse', url=f'https://gh.com/{i}', description='long text') for i in range(2)]
        ashby = [_make_job(source='Ashby', url=f'https://ashby.com/{i}', description='') for i in range(2)]
        result, stats = deduplicate_jobs_with_stats(ashby + gh)
        assert result == gh
        assert stats.cross_source == 2

    def test_different_locations_are_not_merged(self):
        gh = _make_job(source='Greenhouse', url='https://a.com/1', location='New York')
        ashby = _make_job(source='Ashby', url='https://b.com/1', location='London')
        assert len(deduplicate_jobs([gh, ashby])) == 2

    def test_blank_company_never_merged(self):
        a = _make_job(company='', source='Greenhouse', url='https://a.com/1')
        b = _make_job(company='', source='JobSpy (Indeed)', url='https://b.com/1')
        assert len(deduplicate_jobs([a, b])) == 2

    def test_reformatted_location_from_indeed_is_merged_into_workday(self):
        workday = _make_job(company='NVIDIA', title='Security Architect - New College Grad 2026',
                            location='US, CA, Santa Clara', source='Workday', url='https://nvidia.wd5.myworkdayjobs.com/x')
        indeed = _make_job(company='Nvidia', title='Security Architect, New College Grad 2026',
                           location='Santa Clara, CA, US', source='JobSpy (Indeed)',
                           url='https://www.indeed.com/viewjob?jk=9')
        assert deduplicate_jobs([indeed, workday]) == [workday]

    def test_loser_in_an_incompatible_city_is_kept(self):
        gh = _make_job(source='Greenhouse', url='https://a.com/1', location='Seattle, WA')
        indeed = [_make_job(source='JobSpy (Indeed)', url='https://www.indeed.com/viewjob?jk=1', location='Seattle, WA'),
                  _make_job(source='JobSpy (Indeed)', url='https://www.indeed.com/viewjob?jk=2', location='Austin, TX')]
        assert deduplicate_jobs([gh] + indeed) == [gh, indeed[1]]

    def test_log_line_splits_counts(self, caplog):
        job = _make_job()
        indeed = _make_job(source='JobSpy (Indeed)', url='https://www.indeed.com/viewjob?jk=1')
        deduplicate_jobs([job, job, indeed])
        assert "Removed 2 duplicate jobs (1 same posting, 1 cross-source)" in caplog.text

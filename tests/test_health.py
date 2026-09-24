#!/usr/bin/env python3
"""Tests for health.json (scripts/ngj/outputs/health.py)."""

import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from ngj.models import KIND_COOLDOWN, KIND_FORBIDDEN, KIND_HTTP, KIND_TIMEOUT, SourceError, SourceResult  # noqa: E402
from ngj.outputs.health import (  # noqa: E402
    MAX_FAILED_COMPANIES_LISTED,
    build_health,
    generate_health_json,
    validate_health,
)

CONFIG = {
    'apis': {
        'greenhouse': {'companies': [{'name': n} for n in 'ABCDEFGH']},  # 8 boards
        'lever': {'companies': [{'name': 'C'}]},
        'ashby': {'companies': [{'name': 'N'}, {'name': 'O'}]},
        'workday': {'enabled': True, 'companies': [{'name': 'D'}]},
        'google': {'enabled': True, 'search_terms': ['new grad software engineer']},
        'jobspy': {'enabled': True, 'search_terms': ['x']},
        'graphql': {'enabled': True, 'sources': [{'company': 'E'}]},
    }
}


def _ok(n):
    return SourceResult(jobs=tuple({'title': f'SWE {i}'} for i in range(n)), raw_count=n)


def _err(company, kind=KIND_HTTP, source='greenhouse'):
    return SourceError(company, source, kind, 500 if kind == KIND_HTTP else None, 'boom')


def _build(jobs, results, **kw):
    return build_health(jobs, results, time.time() - 10, CONFIG, **kw)


def test_ok_status_and_raw_counts_with_deprecated_alias():
    health = _build([{'title': 'SWE'}] * 5, {'greenhouse': _ok(3), 'lever': _ok(2)})
    assert health['status'] == 'ok'
    assert health['total_jobs'] == 5
    assert health['raw_source_counts'] == {'greenhouse': 3, 'lever': 2}
    assert health['source_counts'] == health['raw_source_counts']
    assert health['zero_sources'] == []
    assert health['schema_version'] == '1.1'
    assert health['run_duration_seconds'] >= 10


def test_zero_source_is_degraded_and_zero_total_is_failed():
    assert _build([{'t': 1}] * 3, {'greenhouse': _ok(3), 'lever': _ok(0)})['status'] == 'degraded'
    failed = _build([], {'greenhouse': _ok(0)})
    assert failed['status'] == 'failed'
    assert failed['zero_sources'] == ['greenhouse']


def test_url_safety_blocks_degrade():
    assert _build([{'t': 1}], {'greenhouse': _ok(1)}, url_blocked_count=2)['status'] == 'degraded'


def test_failure_ratio_above_quarter_degrades():
    # 3 of 8 greenhouse boards failed → 0.375 > 0.25
    result = SourceResult(jobs=_ok(5).jobs, errors=(_err('A'), _err('B', KIND_TIMEOUT), _err('C'), _err('C')))
    health = _build([{'t': 1}] * 5, {'greenhouse': result})
    gh = health['sources']['greenhouse']
    assert gh['failure_ratio'] == 0.375
    assert gh['status'] == 'degraded'
    assert gh['errors'] == {
        'count': 4, 'by_kind': {'http': 3, 'timeout': 1},
        'failed_companies': ['A', 'B', 'C'], 'failed_companies_total': 3,
    }
    assert health['degraded_sources'] == ['greenhouse']
    assert health['status'] == 'degraded'


def test_failure_ratio_at_or_below_quarter_is_ok():
    result = SourceResult(jobs=_ok(5).jobs, errors=(_err('A'), _err('B')))  # 2/8 = 0.25
    health = _build([{'t': 1}] * 5, {'greenhouse': result})
    assert health['sources']['greenhouse']['failure_ratio'] == 0.25
    assert health['status'] == 'ok'


def test_cooldown_degrades_even_with_low_failure_ratio():
    result = SourceResult(jobs=_ok(5).jobs, errors=(_err('A', KIND_COOLDOWN),))
    health = _build([{'t': 1}] * 5, {'greenhouse': result})
    assert health['sources']['greenhouse']['in_cooldown'] is True
    assert health['status'] == 'degraded'


def test_failed_company_list_is_capped():
    many = {'apis': {'greenhouse': {'companies': [{'name': str(i)} for i in range(100)]}}}
    errors = tuple(_err(f'co{i:02d}', KIND_FORBIDDEN) for i in range(30))
    health = build_health([{'t': 1}], {'greenhouse': SourceResult(jobs=_ok(1).jobs, errors=errors)}, time.time(), many)
    summary = health['sources']['greenhouse']['errors']
    assert len(summary['failed_companies']) == MAX_FAILED_COMPANIES_LISTED
    assert summary['failed_companies_total'] == 30


def test_unknown_source_has_no_failure_ratio():
    health = _build([{'t': 1}], {'mystery': SourceResult(jobs=_ok(1).jobs, errors=(_err('x'),))})
    assert health['sources']['mystery']['failure_ratio'] is None
    assert health['sources']['mystery']['configured_units'] is None


def test_display_metrics_include_ashby_from_the_registry():
    jobs = [{'company': 'Acme'}, {'company': 'Acme'}, {'company': 'Beta'}, {'company': ''}, {'company': None}]
    health = _build(jobs, {'greenhouse': _ok(2), 'jobspy': _ok(1), 'ashby': _ok(0)})
    # 8 greenhouse + 1 lever + 2 ashby + 1 workday + 1 graphql
    assert health['configured_company_apis'] == 13
    assert health['enabled_sources'] == 7
    assert health['active_hiring_companies'] == 2
    assert health['active_sources'] == 2


def test_generate_writes_file_and_validates(tmp_path):
    returned = generate_health_json([{'t': 1}], {'greenhouse': _ok(1)}, time.time(), CONFIG, tmp_path)
    written = json.loads((tmp_path / 'health.json').read_text())
    assert written == returned
    assert validate_health(written) == []


def test_generate_returns_none_when_write_fails(tmp_path):
    blocker = tmp_path / 'file'
    blocker.write_text('x')
    assert generate_health_json([{'t': 1}], {'greenhouse': _ok(1)}, time.time(), CONFIG, blocker) is None


@pytest.mark.parametrize('mutate, message', [
    (lambda h: h.pop('last_run'), 'missing key: last_run'),
    (lambda h: h.update(status='meh'), 'status must be one of'),
    (lambda h: h.update(total_jobs=-1), 'total_jobs must be a non-negative integer'),
    (lambda h: h.update(raw_source_counts={'x': 'many'}), 'raw_source_counts'),
    (lambda h: h.update(last_run='yesterday'), 'last_run must be an ISO 8601'),
])
def test_validate_health_flags_bad_shapes(mutate, message):
    health = _build([{'t': 1}], {'greenhouse': _ok(1)})
    mutate(health)
    assert any(message in e for e in validate_health(health))


def test_validate_health_rejects_non_object():
    assert validate_health([]) == ['health.json root must be an object']

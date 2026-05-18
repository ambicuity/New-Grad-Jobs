#!/usr/bin/env python3

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from quality import load_evaluation_telemetry, run_integrity_checks, run_liveness_checks  # noqa: E402


class _Response:
    def __init__(self, status_code=200, text=''):
        self.status_code = status_code
        self.text = text
        self.headers = {'Content-Type': 'text/html'}


class _FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)

    def get(self, url, timeout=4, allow_redirects=True):
        if not self._responses:
            raise RuntimeError('no more responses')
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_run_liveness_checks_reports_failures() -> None:
    jobs = [
        {'url': 'https://example.com/a'},
        {'url': 'https://example.com/b'},
    ]
    telemetry = run_liveness_checks(
        jobs,
        sample_pct=1.0,
        max_checks=10,
        retries=0,
        session=_FakeSession([_Response(200, 'ok page'), _Response(404, 'not found')]),
    )
    assert telemetry['checked'] == 2
    assert telemetry['failed'] == 1
    assert telemetry['failure_rate'] == 0.5
    assert telemetry['liveness_state'] == 'degraded'


def test_run_integrity_checks_fails_on_missing_artifacts(tmp_path: Path) -> None:
    docs = tmp_path / 'docs'
    docs.mkdir(parents=True)
    ok, report = run_integrity_checks(tmp_path)
    assert ok is False
    assert report['status'] == 'failed'
    assert any('missing docs/jobs.json' in err for err in report['errors'])


def test_load_evaluation_telemetry_reports_missing_artifact(tmp_path: Path) -> None:
    telemetry = load_evaluation_telemetry(tmp_path / 'job-evaluations.json')
    assert telemetry['evaluation_state'] == 'unavailable'
    assert telemetry['evaluation_reason'] == 'artifact_missing'
    assert telemetry['evaluation_count'] == 0


def test_load_evaluation_telemetry_reports_degraded_for_invalid_contract(tmp_path: Path) -> None:
    path = tmp_path / 'job-evaluations.json'
    path.write_text('{"evaluations":[{"job_id":"job_1"}]}', encoding='utf-8')
    telemetry = load_evaluation_telemetry(path)
    assert telemetry['evaluation_state'] == 'degraded'
    assert telemetry['evaluation_count'] == 0
    assert telemetry['evaluation_reason']

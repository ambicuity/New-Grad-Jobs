"""Status handling of the board adapters on top of ``fetch_json_with_retry``.

Transient statuses (429/5xx) are retried by the session's urllib3 policy
(see tests/test_http_retry.py), so by the time a status reaches the adapter
it is final: exactly one ``limited_get`` call, reported as ``KIND_HTTP``.
"""

import os
import sys

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ngj.models import KIND_HTTP  # noqa: E402
from ngj.sources.greenhouse import fetch_greenhouse_jobs  # noqa: E402
from ngj.sources.lever import fetch_lever_jobs  # noqa: E402


def _response(status_code: int) -> requests.Response:
    resp = requests.models.Response()
    resp.status_code = status_code
    resp._content = b"{}"
    return resp


FETCHERS = [
    pytest.param(fetch_greenhouse_jobs, "https://boards-api.greenhouse.io/v1/boards/test/jobs", id="greenhouse"),
    pytest.param(fetch_lever_jobs, "https://api.lever.co/v0/postings/test", id="lever"),
]


@pytest.mark.parametrize("status", [400, 401, 404, 410, 422, 429, 500, 502, 503])
@pytest.mark.parametrize(("fetch", "url"), FETCHERS)
def test_final_non_2xx_status_is_reported_once_without_manual_retry(monkeypatch, fetch, url, status):
    calls = []

    def fake_limited_get(u, **kwargs):
        calls.append(u)
        return _response(status)

    monkeypatch.setattr("ngj.http.limited_get", fake_limited_get)
    result = fetch("TestCo", url)
    assert result.jobs == ()
    assert [(e.kind, e.status) for e in result.errors] == [(KIND_HTTP, status)]
    assert len(calls) == 1

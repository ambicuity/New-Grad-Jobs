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


class TestJsonBodyPost:
    """fetch_json_with_retry(json_body=...) POSTs with the same handling as GET (used by UKG)."""

    def _ok(self, payload):
        resp = requests.models.Response()
        resp.status_code = 200
        resp._content = __import__("json").dumps(payload).encode()
        return resp

    def test_json_body_sends_a_post_and_never_a_get(self, monkeypatch):
        from ngj import http as ngj_http
        from ngj.models import SourceResult

        posts = []

        def fake_post(url, **kwargs):
            posts.append((url, kwargs.get("json"), kwargs.get("timeout")))
            return self._ok({"n": 1})

        def no_get(url, **kwargs):
            raise AssertionError("GET must not be used when a JSON body is given")

        monkeypatch.setattr("ngj.http.limited_post", fake_post)
        monkeypatch.setattr("ngj.http.limited_get", no_get)
        result = ngj_http.fetch_json_with_retry(
            "TestCo", "ukg", "UKG", "https://recruiting.ultipro.com/X/JobBoard/y/JobBoardView/LoadSearchResults",
            lambda data: SourceResult(raw_count=data["n"]), timeout=7, json_body={"q": 1})
        assert result.raw_count == 1
        assert posts == [("https://recruiting.ultipro.com/X/JobBoard/y/JobBoardView/LoadSearchResults", {"q": 1}, 7)]

    @pytest.mark.parametrize("status", [404, 500])
    def test_post_errors_are_reported_like_get_errors(self, monkeypatch, status):
        from ngj import http as ngj_http
        from ngj.models import SourceResult

        monkeypatch.setattr("ngj.http.limited_post", lambda url, **kwargs: _response(status))
        result = ngj_http.fetch_json_with_retry(
            "TestCo", "ukg", "UKG", "https://recruiting.ultipro.com/X/JobBoard/y", lambda data: SourceResult(),
            timeout=5, json_body={})
        assert [(e.kind, e.status) for e in result.errors] == [(KIND_HTTP, status)]

"""The shared session has exactly one retry layer (urllib3 Retry, GET only).

These tests exercise the *real* ``requests`` → ``HTTPAdapter`` → ``urllib3``
stack; only the wire (``HTTPConnectionPool._make_request``) is faked, so the
attempt counts below are what production would send.
"""

import io
import os
import sys
from typing import Any

import pytest
import urllib3
from urllib3.connectionpool import HTTPConnectionPool
from urllib3.response import HTTPResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ngj import http as ngj_http  # noqa: E402
from ngj.models import KIND_HTTP, KIND_NETWORK, KIND_PARSE, KIND_TIMEOUT  # noqa: E402

URL = "https://boards-api.greenhouse.io/v1/boards/acme/jobs"


class FakeWire:
    """Replays scripted responses at the urllib3 connection-pool level."""

    def __init__(self, monkeypatch, script: list[Any]):
        self.script = list(script)
        self.calls: list[tuple[str, str]] = []
        wire = self

        def fake_make_request(pool, conn, method, url, *args, **kwargs):
            wire.calls.append((method, url))
            step = wire.script.pop(0) if len(wire.script) > 1 else wire.script[0]
            if isinstance(step, BaseException):
                raise step
            status, headers, body = step
            return HTTPResponse(
                body=io.BytesIO(body), status=status, headers=headers, preload_content=False,
                request_method=method, request_url=url, decode_content=False,
            )

        monkeypatch.setattr(HTTPConnectionPool, "_make_request", fake_make_request)

    @property
    def attempts(self) -> int:
        return len(self.calls)


@pytest.fixture
def sleeps(monkeypatch):
    recorded: list[float] = []
    monkeypatch.setattr("time.sleep", lambda s=0: recorded.append(s))
    return recorded


@pytest.fixture
def session():
    return ngj_http.create_session()


def test_get_5xx_is_retried_by_the_adapter_at_most_four_attempts(monkeypatch, session, sleeps):
    wire = FakeWire(monkeypatch, [(503, {}, b"down")])
    response = session.get(URL, timeout=5)
    assert response.status_code == 503  # final response is returned, not raised
    assert wire.attempts == 1 + ngj_http.RETRY_TOTAL
    assert wire.attempts <= 4


def test_get_recovers_after_transient_429(monkeypatch, session, sleeps):
    wire = FakeWire(monkeypatch, [(429, {}, b""), (200, {"Content-Type": "application/json"}, b"{}")])
    response = session.get(URL, timeout=5)
    assert response.status_code == 200
    assert wire.attempts == 2


def test_post_is_never_retried_by_the_adapter(monkeypatch, session, sleeps):
    wire = FakeWire(monkeypatch, [(503, {}, b"down")])
    response = session.post(URL, json={}, timeout=5)
    assert response.status_code == 503
    assert wire.attempts == 1


def test_non_retryable_status_is_not_retried(monkeypatch, session, sleeps):
    wire = FakeWire(monkeypatch, [(404, {}, b"")])
    assert session.get(URL, timeout=5).status_code == 404
    assert wire.attempts == 1


def test_retry_after_is_honoured_but_clamped(monkeypatch, session, sleeps):
    FakeWire(monkeypatch, [(429, {"Retry-After": "3600"}, b""), (200, {}, b"{}")])
    assert session.get(URL, timeout=5).status_code == 200
    assert sleeps, "Retry-After should cause a sleep"
    assert max(sleeps) == ngj_http.MAX_RETRY_AFTER_SECONDS


def test_small_retry_after_is_used_as_is(monkeypatch, session, sleeps):
    FakeWire(monkeypatch, [(503, {"Retry-After": "2"}, b""), (200, {}, b"{}")])
    session.get(URL, timeout=5)
    assert 2 in sleeps


def test_capped_retry_survives_retry_increment():
    retry = ngj_http.CappedRetry(total=3)
    bumped = retry.increment(method="GET", url="/", response=HTTPResponse(status=503))
    assert isinstance(bumped, ngj_http.CappedRetry)


# ---------------------------------------------------------------------------
# fetch_json_with_retry on top of the adapter: no second retry layer
# ---------------------------------------------------------------------------

def _patch_session(monkeypatch, session):
    monkeypatch.setattr(ngj_http, "_session", session)


def test_fetch_json_does_not_re_retry_a_5xx(monkeypatch, session, sleeps):
    _patch_session(monkeypatch, session)
    wire = FakeWire(monkeypatch, [(502, {}, b"")])
    result = ngj_http.fetch_json_with_retry("Acme", "greenhouse", "Greenhouse", URL, lambda d: None, timeout=5)
    assert wire.attempts <= 4
    assert [(e.kind, e.status) for e in result.errors] == [(KIND_HTTP, 502)]


def test_fetch_json_connection_errors_are_retried_only_by_adapter(monkeypatch, session, sleeps):
    _patch_session(monkeypatch, session)
    wire = FakeWire(monkeypatch, [urllib3.exceptions.NewConnectionError(None, "refused")])
    result = ngj_http.fetch_json_with_retry("Acme", "greenhouse", "Greenhouse", URL, lambda d: None, timeout=5)
    assert wire.attempts <= 4
    assert [e.kind for e in result.errors] == [KIND_NETWORK]


def test_fetch_json_read_timeout_is_reported_as_timeout(monkeypatch, session, sleeps):
    _patch_session(monkeypatch, session)
    wire = FakeWire(monkeypatch, [urllib3.exceptions.ReadTimeoutError(None, URL, "slow")])
    result = ngj_http.fetch_json_with_retry("Acme", "greenhouse", "Greenhouse", URL, lambda d: None, timeout=5)
    assert wire.attempts <= 4
    assert [e.kind for e in result.errors] == [KIND_TIMEOUT]


def test_fetch_json_bad_json_is_not_retried(monkeypatch, session, sleeps):
    _patch_session(monkeypatch, session)
    wire = FakeWire(monkeypatch, [(200, {"Content-Type": "application/json"}, b"<html>")])
    result = ngj_http.fetch_json_with_retry("Acme", "greenhouse", "Greenhouse", URL, lambda d: None, timeout=5)
    assert wire.attempts == 1
    assert [e.kind for e in result.errors] == [KIND_PARSE]


def test_fetch_json_unexpected_shape_is_not_retried(monkeypatch, session, sleeps):
    _patch_session(monkeypatch, session)
    wire = FakeWire(monkeypatch, [(200, {}, b"[]")])
    result = ngj_http.fetch_json_with_retry("Acme", "greenhouse", "Greenhouse", URL, lambda d: None, timeout=5)
    assert wire.attempts == 1
    assert [e.kind for e in result.errors] == [KIND_PARSE]

"""retry_transient_failures: a sequential second pass for boards that timed out
while every source was fetching concurrently."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ngj.http import retry_transient_failures  # noqa: E402
from ngj.models import KIND_HTTP, KIND_NETWORK, KIND_TIMEOUT, SourceResult  # noqa: E402

COMPANIES = [{"name": "A"}, {"name": "Big"}, {"name": "Gone"}]


def _first_pass() -> SourceResult:
    return SourceResult.merge([
        SourceResult(jobs=({"company": "A", "title": "t1"},), raw_count=1),
        SourceResult.failure("Big", "greenhouse", KIND_TIMEOUT, "read timed out"),
        SourceResult.failure("Gone", "greenhouse", KIND_HTTP, "404", status=404),
    ])


def test_timed_out_company_is_refetched_and_its_error_replaced():
    calls = []

    def fetch_one(company):
        calls.append(company["name"])
        return SourceResult(jobs=({"company": company["name"], "title": "t2"},), raw_count=1)

    result = retry_transient_failures(COMPANIES, _first_pass(), fetch_one, describe=lambda c: c["name"])

    assert calls == ["Big"]  # 404s are permanent and are not retried
    assert {j["company"] for j in result.jobs} == {"A", "Big"}
    assert [(e.company, e.kind) for e in result.errors] == [("Gone", KIND_HTTP)]
    assert result.raw_count == 2


def test_retry_that_fails_again_keeps_a_single_error():
    def fetch_one(company):
        return SourceResult.failure(company["name"], "greenhouse", KIND_NETWORK, "reset")

    result = retry_transient_failures(COMPANIES, _first_pass(), fetch_one, describe=lambda c: c["name"])

    kinds = sorted((e.company, e.kind) for e in result.errors)
    assert kinds == [("Big", KIND_NETWORK), ("Gone", KIND_HTTP)]


def test_nothing_to_retry_returns_the_first_pass_unchanged():
    first = SourceResult(jobs=({"company": "A"},), raw_count=1)
    assert retry_transient_failures(COMPANIES, first, lambda c: 1 / 0, describe=lambda c: c["name"]) is first

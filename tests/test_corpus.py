#!/usr/bin/env python3
"""corpus-index.json: every unique posting, titles only, tagged with its tier."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from ngj.outputs.corpus import (
    CORPUS_FILENAME,
    FIELDS,
    TIER_CURATED,
    TIER_NEAR_MISS,
    TIER_OUT,
    build_corpus_index,
    validate_corpus,
    write_corpus_index,
)

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)


def _job(title, url, company="Acme", posted="2026-09-20T10:00:00Z", location="Austin, TX"):
    return {"title": title, "company": company, "location": location, "url": url, "posted_at": posted, "source": "Greenhouse"}


def _sample():
    curated = _job("Software Engineer, New Grad", "https://example.com/1")
    near = _job("Software Engineering Intern", "https://example.com/2", posted="2026-09-22T00:00:00Z")
    out_senior = _job("Senior Software Engineer", "https://example.com/3")
    out_unsafe = _job("Marketing  Associate", "javascript:alert(1)")
    return [curated, near, out_senior, out_unsafe], [curated], [near]


def test_rows_are_compact_tier_tagged_and_sorted():
    unique, curated, near = _sample()
    payload = build_corpus_index(unique, curated, near, now=NOW)

    assert payload["meta"] == {
        "schema_version": "corpus-1", "generated_at": NOW.isoformat(), "total": 4,
        "tiers": {"curated": 1, "near_miss": 1, "out": 2}, "fields": list(FIELDS),
    }
    rows = payload["rows"]
    assert [r[6] for r in rows] == [TIER_CURATED, TIER_NEAR_MISS, TIER_OUT, TIER_OUT]
    assert rows[0][:2] == ["Acme", "Software Engineer, New Grad"]
    assert rows[0][4] == "2026-09-20" and rows[0][5] == "software_engineering" and rows[0][7] == "https://example.com/1"
    unsafe = next(r for r in rows if r[1] == "Marketing Associate")  # whitespace collapsed
    assert unsafe[7] == "" and unsafe[5] == "marketing"


def test_duplicate_ids_are_collapsed_and_inputs_untouched():
    unique, curated, near = _sample()
    snapshot = json.dumps(unique, sort_keys=True)
    payload = build_corpus_index(unique + [dict(unique[0])], curated, near, now=NOW)
    assert payload["meta"]["total"] == 4
    assert json.dumps(unique, sort_keys=True) == snapshot


def test_write_and_validate_round_trip(tmp_path):
    unique, curated, near = _sample()
    payload = build_corpus_index(unique, curated, near, now=NOW)
    path = write_corpus_index(tmp_path, payload)
    assert path == tmp_path / CORPUS_FILENAME
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert validate_corpus(loaded, curated_total=1, near_miss_total=1) == []


def test_validate_reports_shape_and_count_problems():
    unique, curated, near = _sample()
    payload = build_corpus_index(unique, curated, near, now=NOW)
    assert any("!= jobs.json" in e for e in validate_corpus(payload, curated_total=5))
    payload["rows"][0][6] = 9
    assert any("unknown tier" in e for e in validate_corpus(payload))
    payload["rows"][0] = ["short"]
    assert any("fields" in e for e in validate_corpus(payload))
    assert validate_corpus({"rows": "nope"}) == ["corpus-index.json must be an object with a rows list"]
    payload["meta"]["fields"] = ["x"]
    assert any("meta.fields" in e for e in validate_corpus(payload))


def test_validate_rejects_unsafe_urls_in_rows():
    unique, curated, near = _sample()
    payload = build_corpus_index(unique, curated, near, now=NOW)
    payload["rows"][0][7] = "javascript:alert(1)"
    assert any("unsafe url" in e for e in validate_corpus(payload))


def test_undated_rows_sort_last_within_their_tier_without_crashing():
    dated = _job("Software Engineer, New Grad", "https://example.com/1")
    undated = _job("Software Engineer, New Grad", "https://example.com/2", posted="")
    payload = build_corpus_index([undated, dated], [dated, undated], [], now=NOW)
    assert [r[4] for r in payload["rows"]] == ["2026-09-20", ""]
    assert validate_corpus(payload, curated_total=2, near_miss_total=0) == []

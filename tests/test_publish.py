#!/usr/bin/env python3

import json

from publish import write_json_artifact


def test_write_json_artifact_creates_parent_dirs_and_writes_valid_json(tmp_path) -> None:
    output_path = tmp_path / "nested" / "artifacts" / "sample.json"
    payload = {
        "message": "Olá, new grad!",
        "count": 3,
        "items": ["alpha", "beta"],
    }

    write_json_artifact(output_path, payload)

    assert output_path.exists()
    assert output_path.parent.is_dir()

    loaded = json.loads(output_path.read_text(encoding="utf-8"))
    assert loaded == payload


def test_write_json_artifact_uses_pretty_json_and_trailing_newline(tmp_path) -> None:
    output_path = tmp_path / "artifact.json"
    payload = {"a": 1, "b": {"c": 2}}

    write_json_artifact(output_path, payload)

    text = output_path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert '\n  "a": 1,' in text
    assert '\n  "b": {' in text


# ── Payload split: slim index + lazily-loaded description shards ─────────────

from publish import (  # noqa: E402
    DESCRIPTION_SHARD_KEYS,
    build_description_shards,
    build_jobs_index,
    description_shard,
    write_site_artifacts,
)


def _public_job(job_id: str, **overrides) -> dict:
    job = {
        "job_id": job_id,
        "id": f"slug-{job_id}",
        "company": "Acme",
        "title": "Software Engineer",
        "location": "Remote",
        "url": "https://example.com/job",
        "posted_at": "2026-09-01T00:00:00",
        "posted_display": "Today",
        "source": "Greenhouse",
        "category": {"id": "software_engineering"},
        "company_tier": {"tier": "other"},
        "flags": {},
        "is_closed": False,
        "comp": None,
        "description": "Short snippet",
    }
    job.update(overrides)
    return job


def test_description_shard_uses_first_hex_digit_of_job_id() -> None:
    assert description_shard("job_a1b2c3") == "a"
    assert description_shard("job_0fffff") == "0"


def test_description_shard_rejects_malformed_job_ids() -> None:
    import pytest

    for bad in ("", "job_", "slug-abc", "job_zz"):
        with pytest.raises(ValueError):
            description_shard(bad)


def test_shard_keys_cover_all_sixteen_hex_digits() -> None:
    assert DESCRIPTION_SHARD_KEYS == tuple("0123456789abcdef")


def test_build_jobs_index_drops_description_and_keeps_list_fields() -> None:
    jobs_json = {"meta": {"total_jobs": 1}, "jobs": [_public_job("job_a1")]}

    index = build_jobs_index(jobs_json)

    assert index["meta"] == {"total_jobs": 1}
    assert "description" not in index["jobs"][0]
    assert index["jobs"][0]["job_id"] == "job_a1"
    assert index["jobs"][0]["company"] == "Acme"
    # Input must not be mutated — jobs.json is still written from it.
    assert "description" in jobs_json["jobs"][0]


def test_build_description_shards_groups_by_shard_and_always_emits_every_shard() -> None:
    shards = build_description_shards({"job_a1": "Alpha role", "job_a2": "Another", "job_03": "Zero"})

    assert set(shards) == set(DESCRIPTION_SHARD_KEYS)
    assert shards["a"] == {"job_a1": "Alpha role", "job_a2": "Another"}
    assert shards["0"] == {"job_03": "Zero"}
    assert shards["f"] == {}


def test_build_description_shards_skips_empty_text() -> None:
    shards = build_description_shards({"job_a1": "", "job_a2": "Kept"})

    assert shards["a"] == {"job_a2": "Kept"}


def test_write_site_artifacts_writes_full_index_and_shards(tmp_path) -> None:
    jobs_json = {"meta": {"total_jobs": 1}, "jobs": [_public_job("job_a1")]}

    write_site_artifacts(tmp_path, jobs_json, {"job_a1": "Full text"})

    full = json.loads((tmp_path / "jobs.json").read_text(encoding="utf-8"))
    index = json.loads((tmp_path / "jobs-index.json").read_text(encoding="utf-8"))
    shard_a = json.loads((tmp_path / "descriptions" / "a.json").read_text(encoding="utf-8"))

    assert full == jobs_json
    assert "description" not in index["jobs"][0]
    assert shard_a == {"job_a1": "Full text"}
    assert sorted(p.name for p in (tmp_path / "descriptions").iterdir()) == [
        f"{k}.json" for k in DESCRIPTION_SHARD_KEYS
    ]


def test_write_site_artifacts_index_and_shards_are_compact(tmp_path) -> None:
    jobs_json = {"meta": {"total_jobs": 1}, "jobs": [_public_job("job_a1")]}

    write_site_artifacts(tmp_path, jobs_json, {"job_a1": "Full text"})

    assert "\n  " not in (tmp_path / "jobs-index.json").read_text(encoding="utf-8")
    assert "\n  " not in (tmp_path / "descriptions" / "a.json").read_text(encoding="utf-8")

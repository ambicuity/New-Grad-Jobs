#!/usr/bin/env python3
"""Integrity checks run against REAL generated artifacts.

Earlier tests validated hand-built payloads, which kept passing while
generate_jobs_json's real output violated the contract (no schema_version).
Every artifact here comes from the pipeline's own writers or pipeline.run.
"""

import json
import time
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

import check_integrity
from ngj import pipeline
from ngj.enrich import enrich_jobs
from ngj.models import SourceResult
from ngj.outputs.health import generate_health_json
from ngj.outputs.jobs_json import generate_jobs_json, write_jobs_artifacts
from ngj.outputs.rss import generate_rss_feed
from ngj.settings import Settings
from publish import description_shard
from quality import run_integrity_checks

NOW = datetime.now(UTC).isoformat()


def _raw_jobs():
    base = {"location": "New York, NY", "posted_at": NOW, "description": "Build things."}
    return [
        {**base, "company": "Acme", "title": "Software Engineer, New Grad", "source": "Greenhouse",
         "url": "https://boards.greenhouse.io/acme/jobs/1?gh_jid=1", "description_html": "<p>Full <b>text</b></p>"},
        # same company/title/location, different requisition: the legacy slug id collided here
        {**base, "company": "Acme", "title": "Software Engineer, New Grad", "source": "Greenhouse",
         "url": "https://boards.greenhouse.io/acme/jobs/2?gh_jid=2"},
        {**base, "company": "Beta", "title": "Data Engineer I", "source": "Workday", "description": "",
         "url": "https://beta.wd5.myworkdayjobs.com/job/NYC/Data-Engineer_R1"},
    ]


@pytest.fixture
def artifacts(tmp_path):
    """Write jobs.json, jobs-index.json, shards, feed.xml and health.json with the real writers."""
    jobs = enrich_jobs(_raw_jobs())
    jobs_json = generate_jobs_json(jobs)
    write_jobs_artifacts(tmp_path, jobs_json, jobs)
    generate_rss_feed(jobs_json["jobs"], tmp_path)
    generate_health_json(jobs, {"greenhouse": SourceResult(jobs=tuple(jobs[:2])),
                                "workday": SourceResult(jobs=tuple(jobs[2:]))},
                         time.time(), {}, tmp_path)
    return tmp_path


def _rewrite(path, mutate):
    payload = json.loads(path.read_text())
    mutate(payload)
    path.write_text(json.dumps(payload))


def _errors(directory):
    ok, report = run_integrity_checks(directory)
    return ok, report["errors"]


def test_real_writer_output_passes_every_check(artifacts):
    ok, report = run_integrity_checks(artifacts)
    assert ok, report["errors"]
    assert report["status"] == "ok"
    assert report["total_jobs"] == 3


def test_real_pipeline_run_output_passes_every_check(tmp_path):
    settings = Settings(repo_root=tmp_path, output_dir=tmp_path / "public", history_path=tmp_path / "h.json")
    config = {"filtering": {"max_age_days": 30, "new_grad_signals": ["new grad"], "track_signals": ["software"],
                            "exclusion_signals": ["senior"]}}
    result = SourceResult(jobs=tuple(_raw_jobs()[:2]), raw_count=2)
    with patch("ngj.pipeline.plan_sources", lambda c, s: {"greenhouse": lambda: result}):
        pipeline.run(config, settings, sync_readme=False)
    ok, report = run_integrity_checks(settings.output_dir)
    assert ok, report["errors"]


@pytest.mark.parametrize("name", ["jobs.json", "health.json", "jobs-index.json", "feed.xml"])
def test_missing_artifact_fails(artifacts, name):
    (artifacts / name).unlink()
    ok, errors = _errors(artifacts)
    assert not ok
    assert f"missing {name}" in errors


def test_invalid_jobs_json(artifacts):
    (artifacts / "jobs.json").write_text("{invalid")
    ok, errors = _errors(artifacts)
    assert not ok and any("jobs.json invalid JSON" in e for e in errors)


def test_contract_errors_surface(artifacts):
    _rewrite(artifacts / "jobs.json", lambda p: p["meta"].pop("schema_version"))
    ok, errors = _errors(artifacts)
    assert not ok and any(e.startswith("jobs contract: meta.schema_version") for e in errors)


def test_duplicate_job_ids_fail(artifacts):
    def dup(p):
        p["jobs"][1]["job_id"] = p["jobs"][1]["id"] = p["jobs"][0]["job_id"]
    _rewrite(artifacts / "jobs.json", dup)
    ok, errors = _errors(artifacts)
    assert not ok and any("duplicate job_id" in e for e in errors)


def test_count_mismatches(artifacts):
    _rewrite(artifacts / "jobs.json", lambda p: p["meta"].update(total_jobs=9))
    _rewrite(artifacts / "health.json", lambda p: p.update(total_jobs=8))
    ok, errors = _errors(artifacts)
    assert not ok
    assert any("jobs count mismatch" in e for e in errors)
    assert any("health total mismatch" in e for e in errors)


def test_index_must_match_jobs_json(artifacts):
    _rewrite(artifacts / "jobs-index.json", lambda p: p["jobs"].pop())
    ok, errors = _errors(artifacts)
    assert not ok
    assert any("jobs-index count mismatch" in e for e in errors)
    assert any("jobs-index job_ids differ" in e for e in errors)


def test_index_must_not_carry_descriptions(artifacts):
    _rewrite(artifacts / "jobs-index.json", lambda p: p["jobs"][0].update(description="x"))
    assert "jobs-index.json must not carry description" in _errors(artifacts)[1]


def test_description_in_wrong_shard_and_missing(artifacts):
    jobs = json.loads((artifacts / "jobs.json").read_text())["jobs"]
    job_id = next(j["job_id"] for j in jobs if j["description"])
    right = description_shard(job_id)
    wrong = "0" if right != "0" else "1"
    right_path, wrong_path = artifacts / "descriptions" / f"{right}.json", artifacts / "descriptions" / f"{wrong}.json"
    text = json.loads(right_path.read_text()).pop(job_id)
    _rewrite(right_path, lambda p: p.pop(job_id))
    _rewrite(wrong_path, lambda p: p.update({job_id: text, "job_ffffffffffffffffffff": "orphan"}))
    ok, errors = _errors(artifacts)
    assert not ok
    assert any("descriptions in the wrong shard" in e and job_id in e for e in errors)
    assert any("descriptions for unpublished job_ids" in e for e in errors)


def test_job_with_snippet_but_no_shard_text(artifacts):
    jobs = json.loads((artifacts / "jobs.json").read_text())["jobs"]
    job_id = next(j["job_id"] for j in jobs if j["description"])
    _rewrite(artifacts / "descriptions" / f"{description_shard(job_id)}.json", lambda p: p.pop(job_id))
    ok, errors = _errors(artifacts)
    assert not ok
    assert any("no shard text" in e and job_id in e for e in errors)


def test_missing_shard_file(artifacts):
    (artifacts / "descriptions" / "a.json").unlink()
    assert "missing descriptions/a.json" in _errors(artifacts)[1]


def test_unsafe_url_fails(artifacts):
    for name in ("jobs.json",):
        _rewrite(artifacts / name, lambda p: p["jobs"][0].update(url="javascript:alert(1)"))
    ok, errors = _errors(artifacts)
    assert not ok and any("unsafe or missing URLs" in e for e in errors)


def test_malformed_feed_fails(artifacts):
    (artifacts / "feed.xml").write_text("<rss version='2.0'><channel><title>x</title>")
    ok, errors = _errors(artifacts)
    assert not ok and any("feed.xml is not well-formed XML" in e for e in errors)


def test_feed_structure_is_validated(artifacts):
    (artifacts / "feed.xml").write_text(
        '<rss version="2.0"><channel><title>t</title><link>l</link><description>d</description>'
        '<item><title>a</title><link>l</link><guid>job_nope</guid></item>'
        '<item><title>b</title><link>l</link><guid>job_nope</guid></item>'
        '<item><title>c</title></item></channel></rss>'
    )
    errors = _errors(artifacts)[1]
    assert any("feed.xml guids not in jobs.json" in e for e in errors)
    assert any("feed.xml duplicate guids" in e for e in errors)
    assert any("feed.xml item 2 missing link, guid" in e for e in errors)


def test_feed_must_be_rss_2(artifacts):
    (artifacts / "feed.xml").write_text('<rss version="0.91"><channel/></rss>')
    assert 'feed.xml root must be <rss version="2.0">' in _errors(artifacts)[1]


def test_health_shape_is_validated(artifacts):
    _rewrite(artifacts / "health.json", lambda p: p.update(status="exploded"))
    assert any("health.json status must be one of" in e for e in _errors(artifacts)[1])


def test_cli_exits_nonzero_on_failure_and_zero_on_success(artifacts, capsys):
    assert check_integrity.main([str(artifacts)]) == 0
    (artifacts / "feed.xml").unlink()
    assert check_integrity.main([str(artifacts)]) == 1
    out = capsys.readouterr().out
    assert "::error::integrity: missing feed.xml" in out


def test_cli_defaults_to_output_dir_env(artifacts, monkeypatch):
    monkeypatch.setenv("NGJ_OUTPUT_DIR", str(artifacts))
    assert check_integrity.main([]) == 0

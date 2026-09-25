"""Pipeline publish guards: partial-collapse guard, failing writes, previous-run state."""

import json
from datetime import UTC, datetime
from unittest.mock import patch
from xml.etree import ElementTree as ET

import pytest

from ngj import pipeline
from ngj.models import SourceResult
from ngj.outputs.previous import (
    NO_PREVIOUS_RUN,
    PreviousRun,
    fetch_remote_previous_run,
    load_local_previous_run,
    load_previous_run,
    parse_previous_run,
)
from ngj.settings import Settings

NOW_ISO = datetime.now(UTC).isoformat()
CONFIG = {
    "filtering": {
        "max_age_days": 30,
        "new_grad_signals": ["new grad"],
        "track_signals": ["software"],
        "exclusion_signals": ["senior"],
    },
    "apis": {"greenhouse": {"companies": [{"name": "x", "url": "https://x"}]}},
}


def _job(n, company="Acme"):
    return {"company": company, "title": "Software Engineer, New Grad", "url": f"https://jobs.acme.com/{n}",
            "location": "New York, NY", "posted_at": NOW_ISO, "source": "Greenhouse", "description": "Build."}


def _result(n):
    return SourceResult(jobs=tuple(_job(i) for i in range(n)), raw_count=n)


@pytest.fixture
def settings(tmp_path):
    return Settings(repo_root=tmp_path, output_dir=tmp_path / "public", history_path=tmp_path / "data" / "h.json")


def _run(settings, results, **kw):
    plan = {name: (lambda r=r: r) for name, r in results.items()}
    with patch("ngj.pipeline.plan_sources", lambda c, s: plan):
        return pipeline.run(CONFIG, settings, sync_readme=kw.pop("sync_readme", False), **kw)


def _outputs(settings):
    return sorted(p.name for p in settings.output_dir.glob("*")) if settings.output_dir.exists() else []


# --- check_partial_collapse -------------------------------------------------

def test_no_problems_without_previous_run():
    assert pipeline.check_partial_collapse(NO_PREVIOUS_RUN, 5, {"greenhouse": 5}) == []


def test_zero_jobs_is_a_problem_even_without_previous():
    assert pipeline.check_partial_collapse(NO_PREVIOUS_RUN, 0, {"greenhouse": 0}) == ["0 jobs to publish"]


def test_total_drop_over_40_percent():
    previous = PreviousRun(origin="x", total_jobs=100)
    assert pipeline.check_partial_collapse(previous, 60, {}) == []  # exactly 40%: allowed
    problems = pipeline.check_partial_collapse(previous, 59, {})
    assert len(problems) == 1 and "fell 41% (100 → 59)" in problems[0]


def test_source_collapse_only_for_big_previously_contributing_sources():
    previous = PreviousRun(origin="x", total_jobs=10, raw_source_counts={"greenhouse": 101, "lever": 100})
    problems = pipeline.check_partial_collapse(previous, 10, {"greenhouse": 0, "lever": 0, "ashby": 0})
    assert problems == ["source greenhouse returned 0 jobs (previous run: 101)"]


def test_disabled_sources_are_not_compared():
    previous = PreviousRun(origin="x", total_jobs=10, raw_source_counts={"workday": 5000})
    assert pipeline.check_partial_collapse(previous, 10, {"greenhouse": 10}) == []


# --- run(): guard wiring ---------------------------------------------------

def test_run_refuses_to_publish_on_collapse_and_writes_nothing(settings):
    previous = PreviousRun(origin="https://site/", total_jobs=100, raw_source_counts={"greenhouse": 500})
    with pytest.raises(pipeline.PublishGuardError) as err:
        _run(settings, {"greenhouse": _result(2)}, previous=previous)
    assert any("fell 98%" in p for p in err.value.problems)
    assert any("NGJ_ALLOW_DROP=1" in p for p in err.value.problems)
    assert _outputs(settings) == []
    assert not settings.history_path.exists()


def test_run_refuses_zero_jobs(settings):
    with pytest.raises(pipeline.PublishGuardError):
        _run(settings, {"greenhouse": _result(0)})
    assert _outputs(settings) == []


def test_allow_drop_publishes_with_a_warning(settings, capsys):
    previous = PreviousRun(origin="x", total_jobs=100)
    summary = _run(settings, {"greenhouse": _result(2)}, previous=previous, allow_drop=True)
    assert summary.published_jobs == 2
    assert "jobs.json" in _outputs(settings)
    assert "::warning::Partial-collapse guard overridden by NGJ_ALLOW_DROP=1" in capsys.readouterr().out


def test_previous_run_defaults_to_the_output_dir(settings):
    settings.output_dir.mkdir(parents=True)
    (settings.output_dir / "health.json").write_text(json.dumps({"total_jobs": 50, "raw_source_counts": {}}))
    with pytest.raises(pipeline.PublishGuardError):
        _run(settings, {"greenhouse": _result(3)})
    assert json.loads((settings.output_dir / "health.json").read_text())["total_jobs"] == 50


def test_first_seen_is_carried_forward_between_runs_and_feeds_rss(settings):
    first = _run(settings, {"greenhouse": _result(2)})
    assert first.errors == ()
    jobs1 = {j["job_id"]: j["first_seen"] for j in json.loads((settings.output_dir / "jobs.json").read_text())["jobs"]}

    second = _run(settings, {"greenhouse": _result(3)})
    assert second.errors == ()
    jobs2 = json.loads((settings.output_dir / "jobs.json").read_text())["jobs"]
    for job in jobs2:
        if job["job_id"] in jobs1:
            assert job["first_seen"] == jobs1[job["job_id"]]
    new = [j for j in jobs2 if j["job_id"] not in jobs1]
    assert len(new) == 1

    root = ET.parse(settings.output_dir / "feed.xml").getroot()
    guids = [g.text for g in root.iter("guid")]
    assert guids[0] == new[0]["job_id"]  # newest discovery first
    assert root.find("channel/link").text == "https://jobs.riteshrana.engineer/"


def test_ids_are_unique_and_equal_job_id_in_published_output(settings):
    jobs = [_job(1), _job(1) | {"url": "https://jobs.acme.com/1?utm_source=x"}, _job(2)]
    _run(settings, {"greenhouse": SourceResult(jobs=tuple(jobs))})
    published = json.loads((settings.output_dir / "jobs.json").read_text())["jobs"]
    assert len(published) == 2
    assert all(j["id"] == j["job_id"] for j in published)


# --- run(): write failures are collected -----------------------------------

def test_feed_and_health_write_failures_are_reported(settings):
    with (
        patch("ngj.pipeline.generate_rss_feeds", return_value=None),
        patch("ngj.pipeline.generate_health_json", return_value=None),
    ):
        summary = _run(settings, {"greenhouse": _result(1)})
    assert summary.errors == ("feed.xml / feeds/*.xml write failed", "health.json write failed")
    assert "jobs.json" in _outputs(settings)  # the rest was still written


def test_market_history_write_failure_is_reported(settings):
    with patch("ngj.pipeline.save_market_history", return_value=False):
        summary = _run(settings, {"greenhouse": _result(1)})
    assert summary.errors == (f"market history write failed: {settings.history_path}",)


def test_jobs_artifact_write_failure_is_reported_and_skips_readme(settings):
    readme = settings.repo_root / "README.md"
    readme.write_text("<!-- COUNT:total -->0<!-- /COUNT -->\n")
    with patch("ngj.pipeline.write_jobs_artifacts", side_effect=OSError("disk full")):
        summary = _run(settings, {"greenhouse": _result(1)}, sync_readme=True)
    assert summary.errors == ("jobs.json/jobs-index.json/descriptions write failed: disk full",)
    assert readme.read_text() == "<!-- COUNT:total -->0<!-- /COUNT -->\n"


def test_readme_duplicate_markers_fail_the_run(settings):
    marker = "<!-- CATEGORY-LISTINGS:START x -->\n<!-- CATEGORY-LISTINGS:END -->\n"
    (settings.repo_root / "README.md").write_text(marker * 2)
    summary = _run(settings, {"greenhouse": _result(1)}, sync_readme=True)
    assert len(summary.errors) == 1
    assert summary.errors[0].startswith("README job-table sync failed: ValueError")


# --- main(): exit codes -----------------------------------------------------

@pytest.fixture
def cli_env(tmp_path):
    config = tmp_path / "config.yml"
    config.write_text("apis: {}\n")
    return config, {"NGJ_OUTPUT_DIR": str(tmp_path / "out"), "NGJ_SITE_URL": "https://example.test"}


def _summary(errors=()):
    return pipeline.RunSummary(total_fetched=1, published_jobs=1, source_results={}, url_blocked_count=0,
                               elapsed_seconds=0.1, errors=tuple(errors))


def test_main_fetches_previous_run_from_the_site_and_passes_allow_drop(cli_env):
    config, env = cli_env
    fetched = []

    def fetch(url):
        fetched.append(url)
        return {"total_jobs": 7} if url.endswith("health.json") else {"jobs": []}

    with patch("ngj.pipeline.run", return_value=_summary()) as run:
        assert pipeline.main(config, env={**env, "NGJ_ALLOW_DROP": "1"}, fetch_previous=fetch) == 0
    assert fetched == ["https://example.test/health.json", "https://example.test/jobs-index.json"]
    assert run.call_args.kwargs["previous"].total_jobs == 7
    assert run.call_args.kwargs["allow_drop"] is True


def test_main_exits_1_and_annotates_when_guard_trips(cli_env, capsys):
    config, env = cli_env
    with patch("ngj.pipeline.run", side_effect=pipeline.PublishGuardError(["0 jobs to publish"])):
        assert pipeline.main(config, env=env, fetch_previous=lambda url: {}) == 1
    assert "::error::Partial-collapse guard: 0 jobs to publish" in capsys.readouterr().out


def test_main_exits_1_when_writes_failed(cli_env, capsys):
    config, env = cli_env
    with patch("ngj.pipeline.run", return_value=_summary(["feed.xml write failed"])):
        assert pipeline.main(config, env=env, fetch_previous=lambda url: {}) == 1
    assert "::error::feed.xml write failed" in capsys.readouterr().out


# --- ngj.outputs.previous ---------------------------------------------------

def test_parse_previous_run_reads_counts_and_first_seen():
    previous = parse_previous_run(
        {"jobs": [{"job_id": "job_a", "first_seen": "2026-09-01"}, {"job_id": "job_b"}, "junk"]},
        {"total_jobs": 2, "raw_source_counts": {"greenhouse": 5, "bad": "x"}},
        origin="o",
    )
    assert previous.total_jobs == 2
    assert previous.raw_source_counts == {"greenhouse": 5}
    assert previous.first_seen == {"job_a": "2026-09-01"}


def test_parse_previous_run_falls_back_to_legacy_fields():
    previous = parse_previous_run({"jobs": [{}, {}, {}]}, {"source_counts": {"lever": 3}}, origin="o")
    assert previous.total_jobs == 3
    assert previous.raw_source_counts == {"lever": 3}


def test_load_local_previous_run(tmp_path):
    assert load_local_previous_run(tmp_path) == NO_PREVIOUS_RUN
    (tmp_path / "jobs.json").write_text("{broken")
    (tmp_path / "health.json").write_text(json.dumps({"total_jobs": 4}))
    assert load_local_previous_run(tmp_path).total_jobs == 4


def test_remote_fetch_failures_mean_no_previous_run():
    def boom(url):
        raise OSError("offline")
    assert fetch_remote_previous_run("https://x", boom) == NO_PREVIOUS_RUN


def test_load_previous_run_prefers_local_and_never_fetches_without_fetcher(tmp_path):
    assert load_previous_run(tmp_path, "https://x/") == NO_PREVIOUS_RUN
    (tmp_path / "health.json").write_text(json.dumps({"total_jobs": 9}))
    assert load_previous_run(tmp_path, "https://x/", fetch=lambda url: pytest.fail("fetched")).total_jobs == 9

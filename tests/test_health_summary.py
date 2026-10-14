#!/usr/bin/env python3
"""scripts/health_summary.py: the watchdog's per-source health summary."""

import json
import pathlib

import yaml

from health_summary import MAX_NAMED_FAILURES, main, render_summary

ROOT = pathlib.Path(__file__).resolve().parent.parent
WATCHDOG = ROOT / ".github" / "workflows" / "scraper-watchdog.yml"


def _source(status="ok", jobs=100, failed=(), ratio=0.0, cooldown=False):
    return {"jobs": jobs, "raw_count": jobs, "configured_units": 10, "failure_ratio": ratio, "in_cooldown": cooldown,
            "status": status, "errors": {"count": len(failed), "by_kind": {"http": len(failed)},
                                         "failed_companies": list(failed), "failed_companies_total": len(failed)}}


def _health(**sources):
    return {"status": "ok", "last_run": "2026-10-14T20:17:08Z", "total_jobs": 6302, "sources": sources,
            "degraded_sources": [n for n, s in sources.items() if s["status"] == "degraded"],
            "zero_sources": [n for n, s in sources.items() if s["jobs"] == 0]}


def test_table_lists_every_source_with_its_failures():
    markdown, warnings = render_summary(_health(
        greenhouse=_source(jobs=32500, failed=["Amplitude"], ratio=0.004),
        workday=_source(jobs=29000),
    ))
    assert "| Source | Status | Jobs | Failure ratio | Failed companies |" in markdown
    assert "| greenhouse | ok | 32,500 | 0.4% | 1: Amplitude |" in markdown
    assert "| workday | ok | 29,000 | 0.0% | — |" in markdown
    assert "6,302" in markdown and "2026-10-14T20:17:08Z" in markdown
    assert warnings == []


def test_degraded_zero_and_cooldown_sources_are_warned_about():
    markdown, warnings = render_summary(_health(
        lever=_source(status="degraded", jobs=40, failed=["A", "B", "C"], ratio=0.3),
        ukg=_source(status="failed", jobs=0, failed=["X"], ratio=1.0),
        ashby=_source(cooldown=True),
    ))
    assert "| lever | **degraded** |" in markdown and "| ukg | **failed** |" in markdown
    assert "ashby | ok (403 cooldown)" in markdown
    assert warnings == [
        "lever is degraded: 3 failed companies (30.0% of units)",
        "ukg is failed: 1 failed company (100.0% of units)",
        "ukg returned 0 jobs",
        "ashby hit the 403 cooldown",
    ]


def test_long_failure_lists_are_truncated_with_a_total():
    names = [f"C{i}" for i in range(MAX_NAMED_FAILURES + 3)]
    markdown, _ = render_summary(_health(workday=_source(failed=names)))
    shown = ", ".join(names[:MAX_NAMED_FAILURES])
    assert f"{len(names)}: {shown}, +3 more" in markdown


def test_table_cells_cannot_break_the_markdown():
    markdown, _ = render_summary(_health(greenhouse=_source(failed=["Pipe | Co"])))
    assert "Pipe \\| Co" in markdown


def test_malformed_source_entries_are_skipped():
    markdown, warnings = render_summary(_health(greenhouse=_source()) | {"sources": {"greenhouse": _source(), "x": "?"}})
    assert "| greenhouse |" in markdown and "| x |" not in markdown and warnings == []


def test_cli_prints_the_table_when_there_is_no_step_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    path = tmp_path / "health.json"
    path.write_text(json.dumps(_health(workday=_source())))
    assert main([str(path)]) == 0
    assert "| workday | ok | 100 | 0.0% | — |" in capsys.readouterr().out


def test_malformed_health_is_one_warning_not_a_crash():
    for bad in ({}, {"sources": "x"}, [], None):
        markdown, warnings = render_summary(bad)
        assert "no per-source data" in markdown
        assert warnings == ["health.json has no per-source data"]


def test_cli_appends_to_the_step_summary_and_prints_annotations(tmp_path, monkeypatch, capsys):
    path = tmp_path / "health.json"
    path.write_text(json.dumps(_health(lever=_source(status="degraded", failed=["A"], ratio=0.5))))
    summary = tmp_path / "summary.md"
    summary.write_text("earlier step\n")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert main([str(path)]) == 0
    assert summary.read_text().startswith("earlier step\n") and "| lever | **degraded** |" in summary.read_text()
    assert capsys.readouterr().out.strip() == "::warning::lever is degraded: 1 failed company (50.0% of units)"


def test_cli_never_fails_the_watchdog(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    missing = tmp_path / "nope.json"
    assert main([str(missing)]) == 0
    broken = tmp_path / "broken.json"
    broken.write_text("{not json")
    assert main([str(broken)]) == 0
    out = capsys.readouterr().out
    assert out.count("::warning::") == 2


def test_watchdog_runs_the_summary_on_the_fetched_health_file():
    steps = yaml.safe_load(WATCHDOG.read_text(encoding="utf-8"))["jobs"]["check"]["steps"]
    age = next(s for s in steps if s.get("id") == "age")
    assert "-o health.json" in age["run"] or "> health.json" in age["run"]
    summary = next(s for s in steps if s.get("name") == "Summarize source health")
    assert summary["run"].strip() == "python3 scripts/health_summary.py health.json"
    checkout = next(s for s in steps if "actions/checkout@" in s.get("uses", ""))
    assert checkout["with"]["persist-credentials"] is False
    assert steps.index(checkout) < steps.index(age) < steps.index(summary)

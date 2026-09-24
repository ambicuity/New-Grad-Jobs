import copy
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from validate_config import check_config, enabled_company_counts, main, validate_config

REPO_ROOT = Path(__file__).resolve().parents[1]

FILTERING = """
filtering:
  max_age_days: 30
  min_expected_companies: {min}
  new_grad_signals: [new grad]
  track_signals: [software]
  exclusion_signals: [senior]
"""


def _gh(slug):
    return {"name": slug.title(), "url": f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"}


def _valid(**apis):
    config = {
        "filtering": {"max_age_days": 30, "new_grad_signals": ["new grad"], "track_signals": ["software"]},
        "apis": {"greenhouse": {"companies": [_gh("acme"), _gh("beta")]}},
    }
    config["apis"].update(apis)
    return config


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


# --- validate_config (file + exit status) ----------------------------------

def test_warning_path_when_below_threshold(tmp_path, caplog) -> None:
    path = _write(tmp_path / "config.yml", FILTERING.format(min=200) + """
apis:
  greenhouse:
    companies:
      - {name: A, url: "https://boards-api.greenhouse.io/v1/boards/a/jobs"}
  lever:
    companies:
      - {name: D, url: "https://api.lever.co/v0/postings/d"}
""")
    caplog.set_level("INFO")
    assert validate_config(str(path)) == 1
    assert "YAML loaded successfully" in caplog.text
    assert "TOTAL: 2 companies" in caplog.text
    assert "WARNING" in caplog.text


def test_threshold_success(tmp_path, caplog) -> None:
    companies = "\n".join(
        f'      - {{name: C{i}, url: "https://boards-api.greenhouse.io/v1/boards/c{i}/jobs"}}' for i in range(5))
    path = _write(tmp_path / "config.yml", FILTERING.format(min=5) + "apis:\n  greenhouse:\n    companies:\n" + companies)
    caplog.set_level("INFO")
    assert validate_config(str(path)) == 0
    assert "TOTAL: 5 companies" in caplog.text
    assert "WARNING" not in caplog.text


def test_file_not_found(tmp_path, caplog) -> None:
    assert validate_config(str(tmp_path / "missing.yml")) == 1
    assert "Config file not found" in caplog.text


def test_invalid_yaml(tmp_path, caplog) -> None:
    assert validate_config(str(_write(tmp_path / "bad.yml", "apis: [\n"))) == 1
    assert "Invalid YAML" in caplog.text


def test_missing_required_key(tmp_path, caplog) -> None:
    path = _write(tmp_path / "bad.yml", "apis:\n  greenhouse:\n    companies: []\n")
    assert validate_config(str(path)) == 1
    assert "Missing required config key: 'filtering'" in caplog.text


def test_empty_file(tmp_path, caplog) -> None:
    assert validate_config(str(_write(tmp_path / "bad.yml", ""))) == 1
    assert "Invalid config structure" in caplog.text


def test_null_sections_are_reported_not_crashing(tmp_path, caplog) -> None:
    path = _write(tmp_path / "bad.yml", "filtering:\napis:\n")
    assert validate_config(str(path)) == 1
    assert "filtering: must be a mapping" in caplog.text
    assert "apis: must be a mapping" in caplog.text


def test_repository_config_is_valid(caplog) -> None:
    caplog.set_level("INFO")
    assert validate_config(str(REPO_ROOT / "config.yml")) == 0


def test_cli_runs_as_a_script_like_ci() -> None:
    proc = subprocess.run([sys.executable, "scripts/validate_config.py"], cwd=REPO_ROOT,
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_main_accepts_a_path(tmp_path) -> None:
    assert main([str(tmp_path / "nope.yml")]) == 1


# --- check_config (schema) -------------------------------------------------

def test_minimal_valid_config_has_no_errors():
    assert check_config(_valid()).errors == []


@pytest.mark.parametrize("mutate, message", [
    (lambda c: c["filtering"].pop("max_age_days"), "filtering.max_age_days: required"),
    (lambda c: c["filtering"].update(max_age_days=0), "filtering.max_age_days: must be an integer in [1, 365]"),
    (lambda c: c["filtering"].update(max_age_days="60"), "filtering.max_age_days: must be an integer"),
    (lambda c: c["filtering"].pop("new_grad_signals"), "filtering.new_grad_signals: required"),
    (lambda c: c["filtering"].update(track_signals=[]), "filtering.track_signals: must not be empty"),
    (lambda c: c["filtering"].update(exclusion_signals=["ok", 3]), "filtering.exclusion_signals: must be a list"),
    (lambda c: c["filtering"].update(min_expected_companies=-1), "filtering.min_expected_companies"),
    (lambda c: c["apis"]["greenhouse"]["companies"].append({"name": "X"}), "apis.greenhouse.companies[2].url"),
    (lambda c: c["apis"]["greenhouse"]["companies"].append("acme"), "apis.greenhouse.companies[2]: must be a mapping"),
    (lambda c: c["apis"]["greenhouse"]["companies"].append({"name": "", "url": "x"}), "companies[2].name: required"),
    (lambda c: c["apis"]["greenhouse"]["companies"].append(
        {"name": "Lev", "url": "https://api.lever.co/v0/postings/lev"}), "does not look like"),
    (lambda c: c["apis"]["greenhouse"]["companies"].append(_gh("acme")), "duplicate name 'acme'"),
    (lambda c: c["apis"]["greenhouse"]["companies"].append(
        {**_gh("acme"), "name": "Other"}), "duplicate url"),
    (lambda c: c["apis"]["greenhouse"].update(companies="nope"), "apis.greenhouse.companies: must be a list"),
    (lambda c: c["apis"].update(ashby={"enabled": "yes", "companies": []}), "apis.ashby.enabled: must be true or false"),
    (lambda c: c["apis"].update(lever=["x"]), "apis.lever: must be a mapping"),
    (lambda c: c["apis"].update(workday={"enabled": True, "page_limit": 50, "companies": []}),
     "apis.workday.page_limit"),
    (lambda c: c["apis"].update(workday={"companies": [{"name": "W", "workday_url": "https://evil.com/x"}]}),
     "apis.workday.companies[0].workday_url"),
    (lambda c: c["apis"].update(graphql={"enabled": True, "sources": [{"name": "g"}]}),
     "apis.graphql.sources[0].endpoint: must be an https URL"),
    (lambda c: c["apis"].update(graphql={"sources": [{"name": "g", "endpoint": "https://g.io/graphql", "query": "q",
                                                      "data_path": "d", "field_mappings": {"title": "t"}}]}),
     "field_mappings: must map at least title and url"),
    (lambda c: c["apis"].update(jobspy={"enabled": True}), "apis.jobspy.search_terms: required"),
    (lambda c: c.update(worker_pools={"lever_max_workers": 0}), "worker_pools.lever_max_workers"),
    (lambda c: c.update(worker_pools=5), "worker_pools: must be a mapping"),
])
def test_schema_errors(mutate, message):
    config = copy.deepcopy(_valid())
    mutate(config)
    errors = check_config(config).errors
    assert any(message in e for e in errors), errors


def test_company_on_two_atss_is_a_warning():
    config = _valid(ashby={"companies": [{"name": "Acme", "url": "https://api.ashbyhq.com/posting-api/job-board/acme"}]})
    report = check_config(config)
    assert report.errors == []
    assert report.warnings == ["company 'acme' is configured on several ATSs: ashby, greenhouse"]


def test_enabled_flags_are_honoured_in_company_counts():
    ashby = {"enabled": False, "companies": [{"name": "N", "url": "https://api.ashbyhq.com/posting-api/job-board/n"}]}
    graphql = {"enabled": False, "sources": [{"name": "g"}]}
    assert enabled_company_counts(_valid(ashby=ashby, graphql=graphql)) == {"greenhouse": 2}
    ashby["enabled"] = True
    assert enabled_company_counts(_valid(ashby=ashby)) == {"greenhouse": 2, "ashby": 1}


def test_repository_config_passes_schema():
    config = yaml.safe_load((REPO_ROOT / "config.yml").read_text(encoding="utf-8"))
    report = check_config(config)
    assert report.errors == []

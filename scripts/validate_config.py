#!/usr/bin/env python3
"""Validate config.yml before the scraper (or CI) uses it.

Hand-written schema checks (no pydantic dependency), each error naming the
config path it is about:

- top level is a mapping with ``filtering`` and ``apis`` sections;
- ``filtering``: ``max_age_days`` (1-365) and non-empty string lists
  ``new_grad_signals`` / ``track_signals``; optional ``exclusion_signals``
  (string list) and ``min_expected_companies`` (>= 0);
- ``apis.greenhouse|lever|ashby``: ``companies`` entries are ``{name, url}``
  with the URL shape of that ATS's public API, names and URLs unique per ATS;
- ``apis.workday``: ``{name, workday_url}`` entries on *.myworkdayjobs.com,
  unique; numeric knobs within range;
- ``apis.graphql`` sources, ``apis.google``, ``apis.jobspy``, ``worker_pools``:
  shapes and numeric ranges; every ``enabled`` flag is a boolean.

Null sections (``filtering:`` with no value) are reported, never crash. The
company total counts only *enabled* sources (ngj.registry, which honours the
``enabled`` flags) and must reach ``filtering.min_expected_companies``.
Companies configured on more than one ATS are reported as warnings.

    python scripts/validate_config.py [path/to/config.yml]
"""

from __future__ import annotations

import logging
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import yaml

from ngj.registry import ATS_COMPANY_SOURCES, source_registry

logger = logging.getLogger(__name__)

DEFAULT_MIN_EXPECTED_COMPANIES = 200

ATS_URL_PATTERNS: dict[str, re.Pattern[str]] = {
    "greenhouse": re.compile(r"^https://boards-api(\.eu)?\.greenhouse\.io/v1/boards/[A-Za-z0-9_.-]+/jobs/?(\?\S*)?$"),
    "lever": re.compile(r"^https://api(\.eu)?\.lever\.co/v0/postings/[A-Za-z0-9_.-]+/?(\?\S*)?$"),
    "ashby": re.compile(r"^https://api\.ashbyhq\.com/posting-api/job-board/[A-Za-z0-9_.%-]+/?(\?\S*)?$"),
}
WORKDAY_URL_PATTERN = re.compile(r"^https://[A-Za-z0-9-]+\.wd\d+\.myworkdayjobs\.com/\S+$")
HTTPS_URL_PATTERN = re.compile(r"^https://[^\s/]+(/\S*)?$")

# (config path, minimum, maximum) for integer knobs. Missing keys are fine
# (the code has defaults); present keys must be integers in range.
INT_RANGES: tuple[tuple[str, int, int], ...] = (
    ("filtering.max_age_days", 1, 365),
    ("filtering.min_expected_companies", 0, 100_000),
    ("apis.workday.page_limit", 1, 20),
    ("apis.workday.max_jobs_per_company", 1, 5_000),
    ("apis.workday.timeout", 1, 120),
    ("apis.workday.max_workers", 1, 64),
    ("apis.google.max_pages", 1, 50),
    ("apis.graphql.timeout", 1, 120),
    ("apis.graphql.max_jobs_per_source", 1, 10_000),
    ("apis.jobspy.results_wanted", 1, 1_000),
    ("apis.jobspy.hours_old", 1, 24 * 365),
)
WORKER_POOL_RANGE = (1, 1_000)
REQUIRED_FILTERING_LISTS = ("new_grad_signals", "track_signals")
OPTIONAL_FILTERING_LISTS = ("exclusion_signals", "strong_new_grad_signals", "level_signals", "non_tech_signals")
ENABLED_FLAG_SECTIONS = ("greenhouse", "lever", "ashby", "google", "jobspy", "workday", "graphql")


@dataclass
class ConfigReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


class _Missing:
    pass


MISSING = _Missing()


def _lookup(config: Mapping[str, Any], dotted: str) -> Any:
    node: Any = config
    for key in dotted.split("."):
        if not isinstance(node, Mapping) or key not in node:
            return MISSING
        node = node[key]
    return node


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_string_list(report: ConfigReport, path: str, value: Any, *, required: bool) -> None:
    if value is MISSING or value is None:
        if required:
            report.errors.append(f"{path}: required (a non-empty list of strings)")
        return
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        report.errors.append(f"{path}: must be a list of non-empty strings")
    elif required and not value:
        report.errors.append(f"{path}: must not be empty")


def _check_filtering(report: ConfigReport, filtering: Any) -> None:
    if not isinstance(filtering, Mapping):
        report.errors.append("filtering: must be a mapping (it is empty or null)")
        return
    if "max_age_days" not in filtering:
        report.errors.append("filtering.max_age_days: required")
    for key in REQUIRED_FILTERING_LISTS:
        _check_string_list(report, f"filtering.{key}", filtering.get(key, MISSING), required=True)
    for key in OPTIONAL_FILTERING_LISTS:
        _check_string_list(report, f"filtering.{key}", filtering.get(key, MISSING), required=False)


def _check_entries(
    report: ConfigReport,
    path: str,
    entries: Any,
    url_key: str,
    url_pattern: re.Pattern[str],
) -> list[Mapping[str, Any]]:
    """Validate a list of {name, <url_key>} entries; return the well-formed ones."""
    if not isinstance(entries, list):
        report.errors.append(f"{path}: must be a list")
        return []
    valid: list[Mapping[str, Any]] = []
    for index, entry in enumerate(entries):
        where = f"{path}[{index}]"
        if not isinstance(entry, Mapping):
            report.errors.append(f"{where}: must be a mapping with name and {url_key}")
            continue
        name, url = entry.get("name"), entry.get(url_key)
        if not isinstance(name, str) or not name.strip():
            report.errors.append(f"{where}.name: required non-empty string")
            continue
        if not isinstance(url, str) or not url_pattern.match(url.strip()):
            report.errors.append(f"{where}.{url_key}: {url!r} does not look like {url_pattern.pattern}")
            continue
        valid.append(entry)
    for label, key in (("name", "name"), (url_key, url_key)):
        counts = Counter(str(e[key]).strip().lower().rstrip("/") for e in valid)
        for value, n in sorted(counts.items()):
            if n > 1:
                report.errors.append(f"{path}: duplicate {label} {value!r} ({n} entries)")
    return valid


def _check_graphql(report: ConfigReport, graphql: Mapping[str, Any]) -> None:
    sources = graphql.get("sources", [])
    if sources is None:
        sources = []
    if not isinstance(sources, list):
        report.errors.append("apis.graphql.sources: must be a list")
        return
    for index, source in enumerate(sources):
        where = f"apis.graphql.sources[{index}]"
        if not isinstance(source, Mapping):
            report.errors.append(f"{where}: must be a mapping")
            continue
        for key in ("name", "query", "data_path"):
            if not isinstance(source.get(key), str) or not source.get(key, "").strip():
                report.errors.append(f"{where}.{key}: required non-empty string")
        if not isinstance(source.get("endpoint"), str) or not HTTPS_URL_PATTERN.match(source["endpoint"]):
            report.errors.append(f"{where}.endpoint: must be an https URL")
        mappings = source.get("field_mappings")
        if not isinstance(mappings, Mapping) or not {"title", "url"} <= set(mappings):
            report.errors.append(f"{where}.field_mappings: must map at least title and url")


def _check_apis(report: ConfigReport, apis: Any) -> None:
    if not isinstance(apis, Mapping):
        report.errors.append("apis: must be a mapping (it is empty or null)")
        return
    for name in ENABLED_FLAG_SECTIONS:
        section = apis.get(name)
        if section is None:
            continue
        if not isinstance(section, Mapping):
            report.errors.append(f"apis.{name}: must be a mapping")
            continue
        if "enabled" in section and not isinstance(section["enabled"], bool):
            report.errors.append(f"apis.{name}.enabled: must be true or false")

    names_by_ats: dict[str, set[str]] = defaultdict(set)
    for name in ATS_COMPANY_SOURCES:
        section = apis.get(name)
        if not isinstance(section, Mapping) or section.get("companies") is None:
            continue
        for entry in _check_entries(report, f"apis.{name}.companies", section["companies"], "url",
                                    ATS_URL_PATTERNS[name]):
            names_by_ats[str(entry["name"]).strip().lower()].add(name)
    workday = apis.get("workday")
    if isinstance(workday, Mapping) and workday.get("companies") is not None:
        _check_entries(report, "apis.workday.companies", workday["companies"], "workday_url", WORKDAY_URL_PATTERN)
    graphql = apis.get("graphql")
    if isinstance(graphql, Mapping):
        _check_graphql(report, graphql)
    google = apis.get("google")
    if isinstance(google, Mapping) and google.get("search_terms") is not None:
        _check_string_list(report, "apis.google.search_terms", google["search_terms"], required=False)
    jobspy = apis.get("jobspy")
    if isinstance(jobspy, Mapping) and jobspy.get("enabled") is True:
        _check_string_list(report, "apis.jobspy.search_terms", jobspy.get("search_terms", MISSING), required=True)

    for company, ats in sorted(names_by_ats.items()):
        if len(ats) > 1:
            report.warnings.append(f"company {company!r} is configured on several ATSs: {', '.join(sorted(ats))}")


def _check_ranges(report: ConfigReport, config: Mapping[str, Any]) -> None:
    for path, low, high in INT_RANGES:
        value = _lookup(config, path)
        if value is MISSING or value is None:
            continue
        if not _is_int(value) or not low <= value <= high:
            report.errors.append(f"{path}: must be an integer in [{low}, {high}], got {value!r}")
    pools = config.get("worker_pools")
    if pools is None:
        return
    if not isinstance(pools, Mapping):
        report.errors.append("worker_pools: must be a mapping")
        return
    low, high = WORKER_POOL_RANGE
    for key, value in pools.items():
        if not _is_int(value) or not low <= value <= high:
            report.errors.append(f"worker_pools.{key}: must be an integer in [{low}, {high}], got {value!r}")


def check_config(config: Any) -> ConfigReport:
    """Schema-check a parsed config.yml. Never raises on malformed input."""
    report = ConfigReport()
    if not isinstance(config, Mapping):
        report.errors.append("Invalid config structure: the top level must be a mapping")
        return report
    for key in ("filtering", "apis"):
        if key not in config:
            report.errors.append(f"Missing required config key: {key!r}")
    if "filtering" in config:
        _check_filtering(report, config["filtering"])
    if "apis" in config:
        _check_apis(report, config["apis"])
    _check_ranges(report, config)
    return report


def enabled_company_counts(config: Mapping[str, Any]) -> dict[str, int]:
    """Company/board counts of the *enabled* company sources (see ngj.registry)."""
    return {name: spec.unit_count for name, spec in source_registry(config).items() if spec.company_api}


def validate_config(config_path: str = "config.yml") -> int:
    """Validate ``config_path``; return 0 when valid and the company threshold is met, else 1."""
    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("❌ Config file not found: %s", config_path)
        return 1
    except yaml.YAMLError as err:
        logger.error("❌ Invalid YAML in %s: %s", config_path, err)
        return 1

    report = check_config(config)
    for warning in report.warnings:
        logger.warning("⚠️  %s", warning)
    if not report.ok:
        for error in report.errors:
            logger.error("❌ %s: %s", config_path, error)
        return 1

    logger.info("✅ YAML loaded successfully!")
    counts = enabled_company_counts(config)
    for name, count in counts.items():
        logger.info("%s: %s companies", name.capitalize(), count)
    total = sum(counts.values())
    logger.info("TOTAL: %s companies", total)

    min_expected = (config.get("filtering") or {}).get("min_expected_companies", DEFAULT_MIN_EXPECTED_COMPANIES)
    if total < min_expected:
        logger.warning("⚠️  WARNING: Expected ~%s companies but only loaded %s!", f"{min_expected:,}", total)
        return 1

    logger.info("✅ All companies loaded correctly!")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = list(sys.argv[1:] if argv is None else argv)
    return validate_config(args[0] if args else "config.yml")


if __name__ == "__main__":
    sys.exit(main())

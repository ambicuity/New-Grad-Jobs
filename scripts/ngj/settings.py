"""Run settings, built once from config.yml (+ environment) and passed explicitly.

Replaces the module globals that ``main()`` used to reassign and the
default-argument timeouts that were bound at import time (so e.g.
``apis.workday.timeout`` never reached the Workday fetcher).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ngj.util import coerce_positive_int

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config.yml"

OUTPUT_DIR_ENV = "NGJ_OUTPUT_DIR"
SITE_URL_ENV = "NGJ_SITE_URL"
# Public URL of the deployed board (feed links, previous-run fetch).
DEFAULT_SITE_URL = "https://jobs.riteshrana.engineer/"
DEFAULT_OUTPUT_SUBDIR = Path("site") / "public"
HISTORY_SUBPATH = Path("data") / "market-history.json"

# Per-request timeout (seconds) for Greenhouse/Lever/Ashby/Google requests.
# Large boards (e.g. Anduril's ~2k-job Greenhouse list) take >5 s to respond.
DEFAULT_HTTP_TIMEOUT = 15
DEFAULT_WORKDAY_TIMEOUT = 6
DEFAULT_GRAPHQL_TIMEOUT = 6

# Worker pools. Greenhouse requests are additionally capped per domain by
# ngj.http.DOMAIN_LIMITER, so its pool size mostly bounds queued work.
DEFAULT_GREENHOUSE_MIN_WORKERS = 30
DEFAULT_GREENHOUSE_MAX_WORKERS = 300
DEFAULT_LEVER_MIN_WORKERS = 15
DEFAULT_LEVER_MAX_WORKERS = 200
DEFAULT_ASHBY_MAX_WORKERS = 10
# SmartRecruiters pages are sequential per company; a few companies at a time
# keeps the shared API host at a polite request rate.
DEFAULT_SMARTRECRUITERS_MAX_WORKERS = 4
# Oracle HCM tenants are slow (a Nokia page took > 30 s); keep per-tenant load low.
DEFAULT_ORACLE_HCM_MAX_WORKERS = 4
DEFAULT_RIPPLING_MAX_WORKERS = 6
DEFAULT_UKG_MAX_WORKERS = 6
# Every ADP Workforce Now tenant shares one host.
DEFAULT_ADP_MAX_WORKERS = 4
DEFAULT_GRAPHQL_MIN_WORKERS = 8
DEFAULT_GRAPHQL_MAX_WORKERS = 80
DEFAULT_JOBSPY_WORKERS = 25
DEFAULT_ORCHESTRATOR_WORKERS = 20

DEFAULT_WORKDAY_PAGE_LIMIT = 20
DEFAULT_WORKDAY_MAX_JOBS_PER_COMPANY = 200
DEFAULT_WORKDAY_MAX_WORKERS = 8
# Per searchText keyword when apis.workday.search_filters.title_keywords is set
# (paging also stops early once a page has no plausible new-grad title).
DEFAULT_WORKDAY_MAX_JOBS_PER_KEYWORD = 200
# Keyword queries run concurrently per tenant (tenants themselves run in parallel
# up to apis.workday.max_workers), keeping per-host load to a few requests.
DEFAULT_WORKDAY_KEYWORD_WORKERS = 3
# Per-company time budget: a slow tenant (RBC: ~7s per search page) keeps the
# pages fetched so far instead of becoming the long pole of the whole run.
DEFAULT_WORKDAY_MAX_SECONDS_PER_COMPANY = 45

# One SmartRecruiters query per target country; results are newest first, and
# 1000 reach back about two months at AbbVie (~1.2k US postings).
DEFAULT_SMARTRECRUITERS_COUNTRIES: tuple[str, ...] = ("us", "ca", "in")
DEFAULT_SMARTRECRUITERS_MAX_JOBS_PER_COUNTRY = 1000
# Oracle HCM's location search takes country names, not codes.
DEFAULT_ORACLE_HCM_COUNTRIES: tuple[str, ...] = ("United States", "Canada", "India")
DEFAULT_ORACLE_HCM_MAX_JOBS_PER_COUNTRY = 1000
DEFAULT_ORACLE_HCM_TIMEOUT = 45
# Wall-clock budget per company; paging stops (keeping what it has) once spent.
DEFAULT_ORACLE_HCM_MAX_SECONDS_PER_COMPANY = 300
# Rippling boards are small (Rippling's own: ~600 postings); the cap bounds list pages.
DEFAULT_RIPPLING_MAX_JOBS_PER_COMPANY = 1000
# UKG boards are newest first; the cap bounds search pages (Gray Media: ~500 postings).
DEFAULT_UKG_MAX_JOBS_PER_COMPANY = 1000
# ADP pages hold at most 20 rows, so the cap also bounds requests (50 pages).
DEFAULT_ADP_MAX_JOBS_PER_COMPANY = 1000

DEFAULT_GOOGLE_MAX_PAGES = 3
DEFAULT_GRAPHQL_MAX_JOBS_PER_SOURCE = 200


# JobSpy runs only when apis.jobspy.enabled is true. Every consumer (Settings,
# the JobSpy adapter, health reporting) must use jobspy_enabled() so the
# default cannot drift between them.
DEFAULT_JOBSPY_ENABLED = False


def jobspy_enabled(section: Mapping[str, Any] | None) -> bool:
    """Whether ``apis.jobspy`` is enabled (default :data:`DEFAULT_JOBSPY_ENABLED`)."""
    if not isinstance(section, Mapping):
        return DEFAULT_JOBSPY_ENABLED
    return bool(section.get("enabled", DEFAULT_JOBSPY_ENABLED))


@dataclass(frozen=True)
class Settings:
    """Immutable knobs for one scraper run. Build with :func:`build_settings`."""

    repo_root: Path
    output_dir: Path
    history_path: Path
    site_url: str = DEFAULT_SITE_URL

    http_timeout: int = DEFAULT_HTTP_TIMEOUT

    greenhouse_min_workers: int = DEFAULT_GREENHOUSE_MIN_WORKERS
    greenhouse_max_workers: int = DEFAULT_GREENHOUSE_MAX_WORKERS
    lever_min_workers: int = DEFAULT_LEVER_MIN_WORKERS
    lever_max_workers: int = DEFAULT_LEVER_MAX_WORKERS
    ashby_max_workers: int = DEFAULT_ASHBY_MAX_WORKERS
    smartrecruiters_max_workers: int = DEFAULT_SMARTRECRUITERS_MAX_WORKERS
    oracle_hcm_max_workers: int = DEFAULT_ORACLE_HCM_MAX_WORKERS
    rippling_max_workers: int = DEFAULT_RIPPLING_MAX_WORKERS
    ukg_max_workers: int = DEFAULT_UKG_MAX_WORKERS
    adp_max_workers: int = DEFAULT_ADP_MAX_WORKERS
    graphql_min_workers: int = DEFAULT_GRAPHQL_MIN_WORKERS
    graphql_max_workers: int = DEFAULT_GRAPHQL_MAX_WORKERS
    jobspy_workers: int = DEFAULT_JOBSPY_WORKERS
    orchestrator_workers: int = DEFAULT_ORCHESTRATOR_WORKERS

    workday_enabled: bool = False
    workday_page_limit: int = DEFAULT_WORKDAY_PAGE_LIMIT
    workday_max_jobs_per_company: int = DEFAULT_WORKDAY_MAX_JOBS_PER_COMPANY
    workday_timeout: int = DEFAULT_WORKDAY_TIMEOUT
    workday_max_workers: int = DEFAULT_WORKDAY_MAX_WORKERS
    workday_search_keywords: tuple[str, ...] = ()
    workday_max_jobs_per_keyword: int = DEFAULT_WORKDAY_MAX_JOBS_PER_KEYWORD
    workday_max_seconds_per_company: int = DEFAULT_WORKDAY_MAX_SECONDS_PER_COMPANY

    smartrecruiters_countries: tuple[str, ...] = DEFAULT_SMARTRECRUITERS_COUNTRIES
    smartrecruiters_max_jobs_per_country: int = DEFAULT_SMARTRECRUITERS_MAX_JOBS_PER_COUNTRY

    oracle_hcm_countries: tuple[str, ...] = DEFAULT_ORACLE_HCM_COUNTRIES
    oracle_hcm_max_jobs_per_country: int = DEFAULT_ORACLE_HCM_MAX_JOBS_PER_COUNTRY
    oracle_hcm_timeout: int = DEFAULT_ORACLE_HCM_TIMEOUT
    oracle_hcm_max_seconds_per_company: int = DEFAULT_ORACLE_HCM_MAX_SECONDS_PER_COMPANY

    rippling_max_jobs_per_company: int = DEFAULT_RIPPLING_MAX_JOBS_PER_COMPANY
    ukg_max_jobs_per_company: int = DEFAULT_UKG_MAX_JOBS_PER_COMPANY
    adp_max_jobs_per_company: int = DEFAULT_ADP_MAX_JOBS_PER_COMPANY

    google_enabled: bool = False
    google_max_pages: int = DEFAULT_GOOGLE_MAX_PAGES

    graphql_enabled: bool = False
    graphql_timeout: int = DEFAULT_GRAPHQL_TIMEOUT
    graphql_max_jobs_per_source: int = DEFAULT_GRAPHQL_MAX_JOBS_PER_SOURCE

    jobspy_enabled: bool = False

    @property
    def jobs_json_path(self) -> Path:
        return self.output_dir / "jobs.json"


def resolve_output_dir(repo_root: Path = REPO_ROOT, env: Mapping[str, str] | None = None) -> Path:
    """Where generated public artifacts go: ``$NGJ_OUTPUT_DIR`` or ``<repo>/site/public``."""
    env = os.environ if env is None else env
    override = (env.get(OUTPUT_DIR_ENV) or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path(repo_root) / DEFAULT_OUTPUT_SUBDIR


def resolve_site_url(env: Mapping[str, str] | None = None) -> str:
    """``$NGJ_SITE_URL`` or :data:`DEFAULT_SITE_URL`, always with a trailing slash."""
    env = os.environ if env is None else env
    url = (env.get(SITE_URL_ENV) or "").strip() or DEFAULT_SITE_URL
    return url if url.endswith("/") else url + "/"


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load config.yml; raise a clear error when it is missing or not a mapping."""
    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        raise ValueError(f"{path} must contain a YAML mapping at the top level")
    return config


def _section(config: Mapping[str, Any], *keys: str) -> Mapping[str, Any]:
    node: Any = config
    for key in keys:
        node = node.get(key) if isinstance(node, Mapping) else None
    return node if isinstance(node, Mapping) else {}


def _string_tuple(value: Any) -> tuple[str, ...]:
    """Non-empty, de-duplicated, stripped strings from a YAML list (anything else → ())."""
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(dict.fromkeys(v.strip() for v in value if isinstance(v, str) and v.strip()))


def build_settings(
    config: Mapping[str, Any],
    env: Mapping[str, str] | None = None,
    repo_root: Path = REPO_ROOT,
) -> Settings:
    """Build :class:`Settings` from a parsed config.yml mapping and the environment."""
    repo_root = Path(repo_root)
    pools = _section(config, "worker_pools")
    workday = _section(config, "apis", "workday")
    workday_search = _section(config, "apis", "workday", "search_filters")
    smartrecruiters = _section(config, "apis", "smartrecruiters")
    oracle_hcm = _section(config, "apis", "oracle_hcm")
    rippling = _section(config, "apis", "rippling")
    ukg = _section(config, "apis", "ukg")
    adp = _section(config, "apis", "adp")
    google = _section(config, "apis", "google")
    graphql = _section(config, "apis", "graphql")
    jobspy = _section(config, "apis", "jobspy")

    def pool(key: str, default: int) -> int:
        return coerce_positive_int(pools.get(key), default, f"worker_pools.{key}")

    google_pages = google.get("MAX_PAGES")
    if google_pages is None:
        google_pages = google.get("max_pages")

    return Settings(
        repo_root=repo_root,
        output_dir=resolve_output_dir(repo_root, env),
        history_path=repo_root / HISTORY_SUBPATH,
        site_url=resolve_site_url(env),
        greenhouse_min_workers=pool("greenhouse_min_workers", DEFAULT_GREENHOUSE_MIN_WORKERS),
        greenhouse_max_workers=pool("greenhouse_max_workers", DEFAULT_GREENHOUSE_MAX_WORKERS),
        lever_min_workers=pool("lever_min_workers", DEFAULT_LEVER_MIN_WORKERS),
        lever_max_workers=pool("lever_max_workers", DEFAULT_LEVER_MAX_WORKERS),
        ashby_max_workers=pool("ashby_max_workers", DEFAULT_ASHBY_MAX_WORKERS),
        smartrecruiters_max_workers=pool("smartrecruiters_max_workers", DEFAULT_SMARTRECRUITERS_MAX_WORKERS),
        oracle_hcm_max_workers=pool("oracle_hcm_max_workers", DEFAULT_ORACLE_HCM_MAX_WORKERS),
        rippling_max_workers=pool("rippling_max_workers", DEFAULT_RIPPLING_MAX_WORKERS),
        ukg_max_workers=pool("ukg_max_workers", DEFAULT_UKG_MAX_WORKERS),
        adp_max_workers=pool("adp_max_workers", DEFAULT_ADP_MAX_WORKERS),
        graphql_min_workers=pool("graphql_min_workers", DEFAULT_GRAPHQL_MIN_WORKERS),
        graphql_max_workers=pool("graphql_max_workers", DEFAULT_GRAPHQL_MAX_WORKERS),
        jobspy_workers=pool("jobspy_workers", DEFAULT_JOBSPY_WORKERS),
        orchestrator_workers=pool("orchestrator_workers", DEFAULT_ORCHESTRATOR_WORKERS),
        workday_enabled=bool(workday.get("enabled", False)),
        workday_page_limit=coerce_positive_int(
            workday.get("page_limit"), DEFAULT_WORKDAY_PAGE_LIMIT, "apis.workday.page_limit"),
        workday_max_jobs_per_company=coerce_positive_int(
            workday.get("max_jobs_per_company"), DEFAULT_WORKDAY_MAX_JOBS_PER_COMPANY,
            "apis.workday.max_jobs_per_company"),
        workday_timeout=coerce_positive_int(
            workday.get("timeout"), DEFAULT_WORKDAY_TIMEOUT, "apis.workday.timeout"),
        workday_max_workers=coerce_positive_int(
            workday.get("max_workers"), DEFAULT_WORKDAY_MAX_WORKERS, "apis.workday.max_workers"),
        workday_search_keywords=_string_tuple(workday_search.get("title_keywords")),
        workday_max_jobs_per_keyword=coerce_positive_int(
            workday_search.get("max_jobs_per_keyword"), DEFAULT_WORKDAY_MAX_JOBS_PER_KEYWORD,
            "apis.workday.search_filters.max_jobs_per_keyword"),
        workday_max_seconds_per_company=coerce_positive_int(
            workday.get("max_seconds_per_company"), DEFAULT_WORKDAY_MAX_SECONDS_PER_COMPANY,
            "apis.workday.max_seconds_per_company"),
        smartrecruiters_countries=tuple(c.lower() for c in _string_tuple(smartrecruiters.get("countries")))
        or DEFAULT_SMARTRECRUITERS_COUNTRIES,
        smartrecruiters_max_jobs_per_country=coerce_positive_int(
            smartrecruiters.get("max_jobs_per_country"), DEFAULT_SMARTRECRUITERS_MAX_JOBS_PER_COUNTRY,
            "apis.smartrecruiters.max_jobs_per_country"),
        oracle_hcm_countries=_string_tuple(oracle_hcm.get("countries")) or DEFAULT_ORACLE_HCM_COUNTRIES,
        oracle_hcm_max_jobs_per_country=coerce_positive_int(
            oracle_hcm.get("max_jobs_per_country"), DEFAULT_ORACLE_HCM_MAX_JOBS_PER_COUNTRY,
            "apis.oracle_hcm.max_jobs_per_country"),
        oracle_hcm_timeout=coerce_positive_int(
            oracle_hcm.get("timeout"), DEFAULT_ORACLE_HCM_TIMEOUT, "apis.oracle_hcm.timeout"),
        oracle_hcm_max_seconds_per_company=coerce_positive_int(
            oracle_hcm.get("max_seconds_per_company"), DEFAULT_ORACLE_HCM_MAX_SECONDS_PER_COMPANY,
            "apis.oracle_hcm.max_seconds_per_company"),
        rippling_max_jobs_per_company=coerce_positive_int(
            rippling.get("max_jobs_per_company"), DEFAULT_RIPPLING_MAX_JOBS_PER_COMPANY,
            "apis.rippling.max_jobs_per_company"),
        ukg_max_jobs_per_company=coerce_positive_int(
            ukg.get("max_jobs_per_company"), DEFAULT_UKG_MAX_JOBS_PER_COMPANY, "apis.ukg.max_jobs_per_company"),
        adp_max_jobs_per_company=coerce_positive_int(
            adp.get("max_jobs_per_company"), DEFAULT_ADP_MAX_JOBS_PER_COMPANY, "apis.adp.max_jobs_per_company"),
        # Historical default: a google section without `enabled` runs.
        google_enabled=bool(google.get("enabled", True)),
        google_max_pages=coerce_positive_int(google_pages, DEFAULT_GOOGLE_MAX_PAGES, "apis.google.max_pages"),
        graphql_enabled=bool(graphql.get("enabled", False)),
        graphql_timeout=coerce_positive_int(graphql.get("timeout"), DEFAULT_GRAPHQL_TIMEOUT, "apis.graphql.timeout"),
        graphql_max_jobs_per_source=coerce_positive_int(
            graphql.get("max_jobs_per_source"), DEFAULT_GRAPHQL_MAX_JOBS_PER_SOURCE,
            "apis.graphql.max_jobs_per_source"),
        jobspy_enabled=jobspy_enabled(jobspy),
    )


def describe_settings(settings: Settings) -> None:
    """Log the effective tunables at the start of a run."""
    logger.info("   Worker pools configured:")
    logger.info("     Greenhouse: %s-%s", settings.greenhouse_min_workers, settings.greenhouse_max_workers)
    logger.info("     Lever: %s-%s", settings.lever_min_workers, settings.lever_max_workers)
    logger.info("     Ashby: up to %s", settings.ashby_max_workers)
    logger.info("     SmartRecruiters: up to %s, countries=%s, max_per_country=%s",
                settings.smartrecruiters_max_workers, ",".join(settings.smartrecruiters_countries),
                settings.smartrecruiters_max_jobs_per_country)
    logger.info("     Oracle HCM: up to %s, countries=%s, max_per_country=%s, timeout=%ss",
                settings.oracle_hcm_max_workers, ",".join(settings.oracle_hcm_countries),
                settings.oracle_hcm_max_jobs_per_country, settings.oracle_hcm_timeout)
    logger.info("     Rippling: up to %s, max_per_company=%s",
                settings.rippling_max_workers, settings.rippling_max_jobs_per_company)
    logger.info("     UKG: up to %s, max_per_company=%s", settings.ukg_max_workers, settings.ukg_max_jobs_per_company)
    logger.info("     ADP: up to %s, max_per_company=%s", settings.adp_max_workers, settings.adp_max_jobs_per_company)
    logger.info("     GraphQL: %s-%s", settings.graphql_min_workers, settings.graphql_max_workers)
    logger.info("     JobSpy: %s", settings.jobspy_workers)
    logger.info("     Orchestrator: %s", settings.orchestrator_workers)
    logger.info(
        "     Workday: page_limit=%s, max_total=%s, timeout=%ss, max_workers=%s",
        settings.workday_page_limit, settings.workday_max_jobs_per_company,
        settings.workday_timeout, settings.workday_max_workers,
    )
    logger.info(
        "     Workday search: %s keyword(s), max %s jobs per keyword",
        len(settings.workday_search_keywords) or "no (full listing)", settings.workday_max_jobs_per_keyword,
    )
    logger.info("     Google: enabled=%s, max_pages=%s", settings.google_enabled, settings.google_max_pages)
    logger.info("     GraphQL timeout: %ss", settings.graphql_timeout)
    logger.info("   Output dir: %s", settings.output_dir)

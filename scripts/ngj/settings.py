"""Run settings, built once from config.yml (+ environment) and passed explicitly.

Replaces the module globals that ``main()`` used to reassign and the
default-argument timeouts that were bound at import time (so e.g.
``apis.workday.timeout`` never reached the Workday fetcher).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import yaml
from ngj.util import coerce_positive_int

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config.yml"

OUTPUT_DIR_ENV = "NGJ_OUTPUT_DIR"
DEFAULT_OUTPUT_SUBDIR = Path("site") / "public"
HISTORY_SUBPATH = Path("data") / "market-history.json"

# Per-request timeout (seconds) for Greenhouse/Lever/Ashby/Google requests.
DEFAULT_HTTP_TIMEOUT = 5
DEFAULT_WORKDAY_TIMEOUT = 6
DEFAULT_GRAPHQL_TIMEOUT = 6

# Worker pools. Greenhouse requests are additionally capped per domain by
# ngj.http.DOMAIN_LIMITER, so its pool size mostly bounds queued work.
DEFAULT_GREENHOUSE_MIN_WORKERS = 30
DEFAULT_GREENHOUSE_MAX_WORKERS = 300
DEFAULT_LEVER_MIN_WORKERS = 15
DEFAULT_LEVER_MAX_WORKERS = 200
DEFAULT_ASHBY_MAX_WORKERS = 10
DEFAULT_GRAPHQL_MIN_WORKERS = 8
DEFAULT_GRAPHQL_MAX_WORKERS = 80
DEFAULT_JOBSPY_WORKERS = 25
DEFAULT_ORCHESTRATOR_WORKERS = 20

DEFAULT_WORKDAY_PAGE_LIMIT = 20
DEFAULT_WORKDAY_MAX_JOBS_PER_COMPANY = 200
DEFAULT_WORKDAY_MAX_WORKERS = 8

DEFAULT_GOOGLE_MAX_PAGES = 3
DEFAULT_GRAPHQL_MAX_JOBS_PER_SOURCE = 200


@dataclass(frozen=True)
class Settings:
    """Immutable knobs for one scraper run. Build with :func:`build_settings`."""

    repo_root: Path
    output_dir: Path
    history_path: Path

    http_timeout: int = DEFAULT_HTTP_TIMEOUT

    greenhouse_min_workers: int = DEFAULT_GREENHOUSE_MIN_WORKERS
    greenhouse_max_workers: int = DEFAULT_GREENHOUSE_MAX_WORKERS
    lever_min_workers: int = DEFAULT_LEVER_MIN_WORKERS
    lever_max_workers: int = DEFAULT_LEVER_MAX_WORKERS
    ashby_max_workers: int = DEFAULT_ASHBY_MAX_WORKERS
    graphql_min_workers: int = DEFAULT_GRAPHQL_MIN_WORKERS
    graphql_max_workers: int = DEFAULT_GRAPHQL_MAX_WORKERS
    jobspy_workers: int = DEFAULT_JOBSPY_WORKERS
    orchestrator_workers: int = DEFAULT_ORCHESTRATOR_WORKERS

    workday_enabled: bool = False
    workday_page_limit: int = DEFAULT_WORKDAY_PAGE_LIMIT
    workday_max_jobs_per_company: int = DEFAULT_WORKDAY_MAX_JOBS_PER_COMPANY
    workday_timeout: int = DEFAULT_WORKDAY_TIMEOUT
    workday_max_workers: int = DEFAULT_WORKDAY_MAX_WORKERS

    google_enabled: bool = False
    google_max_pages: int = DEFAULT_GOOGLE_MAX_PAGES

    graphql_enabled: bool = False
    graphql_timeout: int = DEFAULT_GRAPHQL_TIMEOUT
    graphql_max_jobs_per_source: int = DEFAULT_GRAPHQL_MAX_JOBS_PER_SOURCE

    jobspy_enabled: bool = False

    @property
    def jobs_json_path(self) -> Path:
        return self.output_dir / "jobs.json"


def resolve_output_dir(repo_root: Path = REPO_ROOT, env: Optional[Mapping[str, str]] = None) -> Path:
    """Where generated public artifacts go: ``$NGJ_OUTPUT_DIR`` or ``<repo>/site/public``."""
    env = os.environ if env is None else env
    override = (env.get(OUTPUT_DIR_ENV) or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path(repo_root) / DEFAULT_OUTPUT_SUBDIR


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Load config.yml; raise a clear error when it is missing or not a mapping."""
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        raise ValueError(f"{path} must contain a YAML mapping at the top level")
    return config


def _section(config: Mapping[str, Any], *keys: str) -> Mapping[str, Any]:
    node: Any = config
    for key in keys:
        node = node.get(key) if isinstance(node, Mapping) else None
    return node if isinstance(node, Mapping) else {}


def build_settings(
    config: Mapping[str, Any],
    env: Optional[Mapping[str, str]] = None,
    repo_root: Path = REPO_ROOT,
) -> Settings:
    """Build :class:`Settings` from a parsed config.yml mapping and the environment."""
    repo_root = Path(repo_root)
    pools = _section(config, "worker_pools")
    workday = _section(config, "apis", "workday")
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
        greenhouse_min_workers=pool("greenhouse_min_workers", DEFAULT_GREENHOUSE_MIN_WORKERS),
        greenhouse_max_workers=pool("greenhouse_max_workers", DEFAULT_GREENHOUSE_MAX_WORKERS),
        lever_min_workers=pool("lever_min_workers", DEFAULT_LEVER_MIN_WORKERS),
        lever_max_workers=pool("lever_max_workers", DEFAULT_LEVER_MAX_WORKERS),
        ashby_max_workers=pool("ashby_max_workers", DEFAULT_ASHBY_MAX_WORKERS),
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
        # Historical default: a google section without `enabled` runs.
        google_enabled=bool(google.get("enabled", True)),
        google_max_pages=coerce_positive_int(google_pages, DEFAULT_GOOGLE_MAX_PAGES, "apis.google.max_pages"),
        graphql_enabled=bool(graphql.get("enabled", False)),
        graphql_timeout=coerce_positive_int(graphql.get("timeout"), DEFAULT_GRAPHQL_TIMEOUT, "apis.graphql.timeout"),
        graphql_max_jobs_per_source=coerce_positive_int(
            graphql.get("max_jobs_per_source"), DEFAULT_GRAPHQL_MAX_JOBS_PER_SOURCE,
            "apis.graphql.max_jobs_per_source"),
        jobspy_enabled=bool(jobspy.get("enabled", False)),
    )


def describe_settings(settings: Settings) -> None:
    """Log the effective tunables at the start of a run."""
    logger.info("   Worker pools configured:")
    logger.info("     Greenhouse: %s-%s", settings.greenhouse_min_workers, settings.greenhouse_max_workers)
    logger.info("     Lever: %s-%s", settings.lever_min_workers, settings.lever_max_workers)
    logger.info("     Ashby: up to %s", settings.ashby_max_workers)
    logger.info("     GraphQL: %s-%s", settings.graphql_min_workers, settings.graphql_max_workers)
    logger.info("     JobSpy: %s", settings.jobspy_workers)
    logger.info("     Orchestrator: %s", settings.orchestrator_workers)
    logger.info(
        "     Workday: page_limit=%s, max_total=%s, timeout=%ss, max_workers=%s",
        settings.workday_page_limit, settings.workday_max_jobs_per_company,
        settings.workday_timeout, settings.workday_max_workers,
    )
    logger.info("     Google: enabled=%s, max_pages=%s", settings.google_enabled, settings.google_max_pages)
    logger.info("     GraphQL timeout: %ss", settings.graphql_timeout)
    logger.info("   Output dir: %s", settings.output_dir)

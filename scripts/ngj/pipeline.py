"""Scraper orchestration: fetch → dedupe → filter → enrich → publish.

``main`` is the CLI entrypoint (scripts/update_jobs.py). ``run`` does the work
for an already-loaded config and :class:`~ngj.settings.Settings`.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ngj.dedup import deduplicate_jobs
from ngj.enrich import enrich_jobs
from ngj.filters import filter_jobs
from ngj.log import annotate, configure_logging
from ngj.models import KIND_UNEXPECTED, SourceResult
from ngj.outputs.health import generate_health_json
from ngj.outputs.jobs_json import generate_jobs_json, write_jobs_artifacts
from ngj.outputs.market_history import MarketHistoryError, save_market_history
from ngj.outputs.rss import generate_rss_feed
from ngj.settings import DEFAULT_CONFIG_PATH, Settings, build_settings, describe_settings, load_config
from ngj.sources.ashby import fetch_all_ashby_jobs
from ngj.sources.google import fetch_google_jobs
from ngj.sources.graphql import fetch_all_graphql_jobs
from ngj.sources.greenhouse import fetch_all_greenhouse_jobs, hydrate_greenhouse_descriptions
from ngj.sources.jobspy import fetch_jobspy_jobs
from ngj.sources.lever import fetch_all_lever_jobs
from ngj.sources.workday import build_title_prefilter, fetch_workday_jobs
from ngj.util import sanitize_nan
from url_safety import filter_safe_jobs

logger = logging.getLogger(__name__)

SourceFetcher = Callable[[], SourceResult]


@dataclass(frozen=True)
class RunSummary:
    """What one pipeline run produced (returned by :func:`run` for callers/tests)."""

    total_fetched: int
    published_jobs: int
    source_results: Mapping[str, SourceResult]
    url_blocked_count: int
    elapsed_seconds: float


def plan_sources(config: Mapping[str, Any], settings: Settings) -> dict[str, SourceFetcher]:
    """Map each enabled source name to a zero-arg fetcher bound to ``settings``."""
    apis = config.get('apis', {}) or {}
    plan: dict[str, SourceFetcher] = {}

    for name, fetch_all in (
        ('greenhouse', fetch_all_greenhouse_jobs),
        ('lever', fetch_all_lever_jobs),
        ('ashby', fetch_all_ashby_jobs),
    ):
        companies = (apis.get(name) or {}).get('companies') or []
        if companies:
            plan[name] = (lambda f=fetch_all, c=companies: f(c, settings))

    google = apis.get('google') or {}
    if settings.google_enabled and google.get('search_terms'):
        plan['google'] = lambda: fetch_google_jobs(
            google['search_terms'], max_pages=settings.google_max_pages, timeout=settings.http_timeout,
        )

    if settings.jobspy_enabled:
        plan['jobspy'] = lambda: fetch_jobspy_jobs(apis['jobspy'] or {}, workers=settings.jobspy_workers)

    workday = apis.get('workday') or {}
    if settings.workday_enabled:
        plan['workday'] = lambda: fetch_workday_jobs(
            workday.get('companies') or [],
            page_limit=settings.workday_page_limit,
            max_total_limit=settings.workday_max_jobs_per_company,
            timeout=settings.workday_timeout,
            max_workers=settings.workday_max_workers,
            search_keywords=settings.workday_search_keywords,
            max_jobs_per_keyword=settings.workday_max_jobs_per_keyword,
            title_filter=build_title_prefilter(config.get('filtering') or config.get('filters')),
        )

    graphql_sources = (apis.get('graphql') or {}).get('sources') or []
    if settings.graphql_enabled and graphql_sources:
        plan['graphql'] = lambda: fetch_all_graphql_jobs(graphql_sources, settings)

    return plan


def fetch_all_sources(plan: Mapping[str, SourceFetcher], max_workers: int) -> dict[str, SourceResult]:
    """Run every planned source concurrently; a crashing source becomes an error result."""
    results: dict[str, SourceResult] = {}
    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
        futures = {name: executor.submit(fetcher) for name, fetcher in plan.items()}
        for name, future in futures.items():
            try:
                result = future.result()
                logger.info("  ✅ %s: %s jobs collected", name.upper(), len(result.jobs))
            except Exception as exc:
                logger.error("  ❌ %s failed: %s", name.upper(), exc)
                result = SourceResult.failure(name, name, KIND_UNEXPECTED, f"{type(exc).__name__}: {exc}")
            results[name] = result
    return results


def _log_config_summary(config: Mapping[str, Any], settings: Settings) -> None:
    apis = config.get('apis', {}) or {}
    counts = {
        'Greenhouse': len((apis.get('greenhouse') or {}).get('companies') or []),
        'Lever': len((apis.get('lever') or {}).get('companies') or []),
        'Ashby': len((apis.get('ashby') or {}).get('companies') or []),
        'Workday': len((apis.get('workday') or {}).get('companies') or []),
        'GraphQL': len((apis.get('graphql') or {}).get('sources') or []) if settings.graphql_enabled else 0,
    }
    logger.info("\n📋 Configuration loaded:")
    for name, count in counts.items():
        logger.info("   %s: %s %s", name, count, 'sources' if name == 'GraphQL' else 'companies')
    logger.info("   TOTAL: %s companies", sum(counts.values()))
    logger.info("=" * 60)


def _sync_readme(repo_root: Path, jobs_path: Path) -> None:
    """Refresh the two auto-managed README regions from the freshly written jobs.json.

    README.md is hand-edited *except* the <!-- COUNT:<id> --> digits + "Last
    updated" line (sync_readme_counts) and the <!-- CATEGORY-LISTINGS --> block
    (sync_readme_jobs). A sync failure never fails the scrape.
    """
    from sync_readme_counts import sync_readme_counts
    from sync_readme_jobs import sync_readme_jobs

    for name, sync in (('count', sync_readme_counts), ('job-table', sync_readme_jobs)):
        try:
            sync(repo_root, jobs_path=jobs_path)
        except Exception as exc:
            logger.warning("⚠️  README %s sync skipped: %s", name, exc)


def run(config: Mapping[str, Any], settings: Settings, *, sync_readme: bool = True) -> RunSummary:
    """Fetch, process and publish one scrape. Returns a :class:`RunSummary`."""
    start_time = time.time()
    _log_config_summary(config, settings)

    logger.info("\n📡 Phase 1: Fetching jobs from all sources in parallel...")
    source_results = fetch_all_sources(plan_sources(config, settings), settings.orchestrator_workers)
    all_jobs: list[dict[str, Any]] = [job for result in source_results.values() for job in result.jobs]
    source_counts = {name: len(result.jobs) for name, result in source_results.items()}
    logger.info("\n📊 Total jobs fetched: %s", len(all_jobs))

    logger.info("\n🔄 Phase 2: Deduplicating jobs...")
    unique_jobs = deduplicate_jobs(all_jobs)
    logger.info("   Jobs after deduplication: %s", len(unique_jobs))

    logger.info("\n⚙️ Phase 3: Filtering and enriching jobs...")
    filtered_jobs = filter_jobs(unique_jobs, dict(config))
    logger.info("   Jobs after filtering: %s", len(filtered_jobs))
    # Greenhouse is listed without descriptions; fetch them for survivors only.
    filtered_jobs = hydrate_greenhouse_descriptions(filtered_jobs, timeout=settings.http_timeout)
    enriched_jobs = sanitize_nan(enrich_jobs(filtered_jobs))
    logger.info("   Jobs enriched with categories and flags")

    # Publish-time URL safety gate: drop any job whose URL is not a public
    # http(s) link before anything is written. See scripts/url_safety.py.
    safe_jobs, url_blocked_count, url_blocked_samples = filter_safe_jobs(enriched_jobs)
    if url_blocked_count:
        logger.warning("🛡️  URL safety: blocked %s job(s) with unsafe/missing URLs", url_blocked_count)
        for sample in url_blocked_samples:
            logger.warning("      • %s", sample)

    jobs_json = generate_jobs_json(safe_jobs, dict(config))

    # A corrupt history file is left untouched and flagged, but must not block
    # publishing the job board, which does not depend on it.
    try:
        save_market_history(safe_jobs, settings.history_path)
    except MarketHistoryError as exc:
        annotate("error", f"Market history not updated (file left untouched): {exc}")

    write_jobs_artifacts(settings.output_dir, jobs_json, safe_jobs)
    generate_rss_feed(safe_jobs, settings.output_dir)
    generate_health_json(
        safe_jobs, source_counts, start_time, config, settings.output_dir, url_blocked_count=url_blocked_count,
    )

    if sync_readme:
        _sync_readme(settings.repo_root, settings.jobs_json_path)

    return RunSummary(
        total_fetched=len(all_jobs),
        published_jobs=len(safe_jobs),
        source_results=source_results,
        url_blocked_count=url_blocked_count,
        elapsed_seconds=time.time() - start_time,
    )


def main(config_path: Path | None = None) -> int:
    """CLI entrypoint: load config.yml + env, run the pipeline, report timing."""
    configure_logging()
    logger.info("🚀 Starting job aggregation (PARALLEL MODE)...")
    logger.info("=" * 60)

    config = load_config(config_path or DEFAULT_CONFIG_PATH)
    settings = build_settings(config, os.environ)
    describe_settings(settings)

    summary = run(config, settings)

    logger.info("\n" + "=" * 60)
    logger.info("✅ Job aggregation complete!")
    logger.info(
        "⏱️  Total execution time: %.1f seconds (%.1f minutes)",
        summary.elapsed_seconds, summary.elapsed_seconds / 60,
    )
    logger.info("📊 Final job count: %s", summary.published_jobs)
    logger.info("=" * 60)
    return 0

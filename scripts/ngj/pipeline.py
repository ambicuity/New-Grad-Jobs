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
from functools import partial
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
from ngj.outputs.previous import (
    JsonFetcher,
    PreviousRun,
    http_json_fetcher,
    load_local_previous_run,
    load_previous_run,
)
from ngj.outputs.rss import generate_rss_feed
from ngj.registry import source_registry
from ngj.settings import DEFAULT_CONFIG_PATH, Settings, build_settings, describe_settings, load_config
from ngj.sources.ashby import fetch_all_ashby_jobs
from ngj.sources.google import fetch_google_jobs
from ngj.sources.graphql import fetch_all_graphql_jobs
from ngj.sources.greenhouse import fetch_all_greenhouse_jobs
from ngj.sources.jobspy import fetch_jobspy_jobs
from ngj.sources.lever import fetch_all_lever_jobs
from ngj.sources.workday import fetch_workday_jobs
from ngj.util import sanitize_nan
from url_safety import filter_safe_jobs

logger = logging.getLogger(__name__)

SourceFetcher = Callable[[], SourceResult]

# Partial-collapse guard: refuse to publish when the board shrinks by more
# than this share versus the previous run, or when a source that previously
# returned more than SOURCE_COLLAPSE_MIN_PREVIOUS jobs returns none.
MAX_TOTAL_DROP_RATIO = 0.40
SOURCE_COLLAPSE_MIN_PREVIOUS = 100
ALLOW_DROP_ENV = "NGJ_ALLOW_DROP"


class PublishGuardError(RuntimeError):
    """The run looks like a partial collapse; nothing was written."""

    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class RunSummary:
    """What one pipeline run produced (returned by :func:`run` for callers/tests).

    ``errors`` lists artifact writes/syncs that failed; the CLI exits non-zero
    when it is non-empty (the remaining artifacts were still written).
    """

    total_fetched: int
    published_jobs: int
    source_results: Mapping[str, SourceResult]
    url_blocked_count: int
    elapsed_seconds: float
    errors: tuple[str, ...] = ()


def plan_sources(config: Mapping[str, Any], settings: Settings) -> dict[str, SourceFetcher]:
    """Map each enabled source (see ngj.registry) to a zero-arg fetcher bound to ``settings``."""
    apis = config.get('apis') or {}

    def fetcher(name: str, units: list[Any]) -> SourceFetcher:
        if name == 'greenhouse':
            return partial(fetch_all_greenhouse_jobs, units, settings)
        if name == 'lever':
            return partial(fetch_all_lever_jobs, units, settings)
        if name == 'ashby':
            return partial(fetch_all_ashby_jobs, units, settings)
        if name == 'google':
            return partial(fetch_google_jobs, units, max_pages=settings.google_max_pages,
                           timeout=settings.http_timeout)
        if name == 'jobspy':
            return partial(fetch_jobspy_jobs, apis['jobspy'], workers=settings.jobspy_workers)
        if name == 'workday':
            return partial(
                fetch_workday_jobs, units,
                page_limit=settings.workday_page_limit,
                max_total_limit=settings.workday_max_jobs_per_company,
                timeout=settings.workday_timeout,
                max_workers=settings.workday_max_workers,
            )
        if name == 'graphql':
            return partial(fetch_all_graphql_jobs, units, settings)
        raise ValueError(f"no fetcher for source {name!r}")

    return {name: fetcher(name, list(spec.units)) for name, spec in source_registry(config).items()}


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


def _log_config_summary(config: Mapping[str, Any]) -> None:
    registry = source_registry(config)
    logger.info("\n📋 Configuration loaded (enabled sources):")
    for name, spec in registry.items():
        logger.info("   %s: %s %s", name, spec.unit_count, 'companies' if spec.company_api else 'queries')
    logger.info("   TOTAL: %s", sum(spec.unit_count for spec in registry.values()))
    logger.info("=" * 60)


def check_partial_collapse(
    previous: PreviousRun,
    published_total: int,
    raw_source_counts: Mapping[str, int],
) -> list[str]:
    """Reasons this run looks like a partial collapse (empty list = safe to publish).

    * nothing to publish at all;
    * the published total fell by more than :data:`MAX_TOTAL_DROP_RATIO`
      versus the previous run;
    * a source fetched this run returned 0 jobs after returning more than
      :data:`SOURCE_COLLAPSE_MIN_PREVIOUS` last time (sources not fetched this
      run — disabled in config — are not compared).
    """
    problems: list[str] = []
    if published_total == 0:
        problems.append("0 jobs to publish")
    previous_total = previous.total_jobs
    if previous_total and published_total < previous_total * (1 - MAX_TOTAL_DROP_RATIO):
        drop = 1 - published_total / previous_total
        problems.append(
            f"published jobs fell {drop:.0%} ({previous_total} → {published_total}); "
            f"limit is {MAX_TOTAL_DROP_RATIO:.0%}"
        )
    for name, count in raw_source_counts.items():
        before = previous.raw_source_counts.get(name, 0)
        if count == 0 and before > SOURCE_COLLAPSE_MIN_PREVIOUS:
            problems.append(f"source {name} returned 0 jobs (previous run: {before})")
    return problems


def _enforce_collapse_guard(problems: list[str], previous: PreviousRun, allow_drop: bool) -> None:
    if not problems:
        return
    if allow_drop:
        annotate("warning", f"Partial-collapse guard overridden by {ALLOW_DROP_ENV}=1: {'; '.join(problems)}")
        return
    raise PublishGuardError([
        *problems,
        f"compared with the previous run from {previous.origin}; set {ALLOW_DROP_ENV}=1 to publish anyway",
    ])


def _sync_readme(repo_root: Path, jobs_path: Path) -> list[str]:
    """Refresh the two auto-managed README regions from the freshly written jobs.json.

    README.md is hand-edited *except* the <!-- COUNT:<id> --> digits + "Last
    updated" line (sync_readme_counts) and the <!-- CATEGORY-LISTINGS --> block
    (sync_readme_jobs). Returns one message per failed sync (e.g. the
    duplicate-marker ValueError); the caller fails the run on any.
    """
    from sync_readme_counts import sync_readme_counts
    from sync_readme_jobs import sync_readme_jobs

    errors: list[str] = []
    for name, sync in (('count', sync_readme_counts), ('job-table', sync_readme_jobs)):
        try:
            sync(repo_root, jobs_path=jobs_path)
        except Exception as exc:
            errors.append(f"README {name} sync failed: {type(exc).__name__}: {exc}")
    return errors


def _save_history(jobs: list[dict[str, Any]], settings: Settings) -> list[str]:
    # A corrupt history file is left untouched and flagged, but must not block
    # publishing the job board, which does not depend on it (owner decision).
    # Failing to *write* a readable history is a real failure.
    try:
        if not save_market_history(jobs, settings.history_path):
            return [f"market history write failed: {settings.history_path}"]
    except MarketHistoryError as exc:
        annotate("error", f"Market history not updated (file left untouched): {exc}")
    return []


def _publish(
    safe_jobs: list[dict[str, Any]],
    jobs_json: dict[str, Any],
    source_results: Mapping[str, SourceResult],
    start_time: float,
    config: Mapping[str, Any],
    settings: Settings,
    url_blocked_count: int,
    sync_readme: bool,
) -> list[str]:
    """Write every artifact; return the failures (each artifact is attempted regardless)."""
    errors = _save_history(safe_jobs, settings)

    jobs_written = True
    try:
        write_jobs_artifacts(settings.output_dir, jobs_json, safe_jobs)
    except (OSError, ValueError) as exc:
        jobs_written = False
        errors.append(f"jobs.json/jobs-index.json/descriptions write failed: {exc}")

    if generate_rss_feed(jobs_json['jobs'], settings.output_dir, site_url=settings.site_url) is None:
        errors.append("feed.xml write failed")
    health = generate_health_json(
        safe_jobs, source_results, start_time, config, settings.output_dir, url_blocked_count=url_blocked_count,
    )
    if health is None:
        errors.append("health.json write failed")

    if sync_readme and jobs_written:
        errors.extend(_sync_readme(settings.repo_root, settings.jobs_json_path))
    return errors


def run(
    config: Mapping[str, Any],
    settings: Settings,
    *,
    sync_readme: bool = True,
    previous: PreviousRun | None = None,
    allow_drop: bool = False,
) -> RunSummary:
    """Fetch, process and publish one scrape. Returns a :class:`RunSummary`.

    ``previous`` is the last published run (default: whatever is in the output
    dir — never the network; :func:`main` passes the live site's). Raises
    :class:`PublishGuardError` before writing anything when the run looks like
    a partial collapse, unless ``allow_drop``.
    """
    start_time = time.time()
    _log_config_summary(config)
    if previous is None:
        previous = load_local_previous_run(settings.output_dir)

    logger.info("\n📡 Phase 1: Fetching jobs from all sources in parallel...")
    source_results = fetch_all_sources(plan_sources(config, settings), settings.orchestrator_workers)
    all_jobs: list[dict[str, Any]] = [job for result in source_results.values() for job in result.jobs]
    raw_source_counts = {name: len(result.jobs) for name, result in source_results.items()}
    logger.info("\n📊 Total jobs fetched: %s", len(all_jobs))

    logger.info("\n🔄 Phase 2: Deduplicating jobs...")
    unique_jobs = deduplicate_jobs(all_jobs)
    logger.info("   Jobs after deduplication: %s", len(unique_jobs))

    logger.info("\n⚙️ Phase 3: Filtering and enriching jobs...")
    filtered_jobs = filter_jobs(unique_jobs, dict(config))
    logger.info("   Jobs after filtering: %s", len(filtered_jobs))
    enriched_jobs = sanitize_nan(enrich_jobs(filtered_jobs))
    logger.info("   Jobs enriched with categories and flags")

    # Publish-time URL safety gate: drop any job whose URL is not a public
    # http(s) link before anything is written. See scripts/url_safety.py.
    safe_jobs, url_blocked_count, url_blocked_samples = filter_safe_jobs(enriched_jobs)
    if url_blocked_count:
        logger.warning("🛡️  URL safety: blocked %s job(s) with unsafe/missing URLs", url_blocked_count)
        for sample in url_blocked_samples:
            logger.warning("      • %s", sample)

    jobs_json = generate_jobs_json(safe_jobs, dict(config), previous_first_seen=previous.first_seen)
    published_total = jobs_json['meta']['total_jobs']
    _enforce_collapse_guard(check_partial_collapse(previous, published_total, raw_source_counts),
                            previous, allow_drop)

    errors = _publish(safe_jobs, jobs_json, source_results, start_time, config, settings,
                      url_blocked_count, sync_readme)
    return RunSummary(
        total_fetched=len(all_jobs),
        published_jobs=published_total,
        source_results=source_results,
        url_blocked_count=url_blocked_count,
        elapsed_seconds=time.time() - start_time,
        errors=tuple(errors),
    )


def main(
    config_path: Path | None = None,
    env: Mapping[str, str] | None = None,
    fetch_previous: JsonFetcher | None = None,
) -> int:
    """CLI entrypoint: load config.yml + env, run the pipeline, report timing.

    The previous run is read from the output dir, else fetched from the live
    site (``fetch_previous``, default an HTTP fetcher). Exits 1 when the
    partial-collapse guard refuses to publish or any artifact write / README
    sync failed; each problem is reported as ``::error::``.
    """
    env = os.environ if env is None else env
    configure_logging()
    logger.info("🚀 Starting job aggregation (PARALLEL MODE)...")
    logger.info("=" * 60)

    config = load_config(config_path or DEFAULT_CONFIG_PATH)
    settings = build_settings(config, env)
    describe_settings(settings)
    previous = load_previous_run(settings.output_dir, settings.site_url,
                                 fetch=fetch_previous or http_json_fetcher())
    logger.info("   Previous run: %s (total_jobs=%s)", previous.origin, previous.total_jobs)

    try:
        summary = run(config, settings, previous=previous,
                      allow_drop=(env.get(ALLOW_DROP_ENV) or "").strip() == "1")
    except PublishGuardError as exc:
        for problem in exc.problems:
            annotate("error", f"Partial-collapse guard: {problem}")
        logger.error("❌ Refusing to publish: no artifacts were written.")
        return 1

    logger.info("\n" + "=" * 60)
    logger.info("❌ Job aggregation finished with errors" if summary.errors else "✅ Job aggregation complete!")
    logger.info(
        "⏱️  Total execution time: %.1f seconds (%.1f minutes)",
        summary.elapsed_seconds, summary.elapsed_seconds / 60,
    )
    logger.info("📊 Final job count: %s", summary.published_jobs)
    logger.info("=" * 60)
    for error in summary.errors:
        annotate("error", error)
    return 1 if summary.errors else 0

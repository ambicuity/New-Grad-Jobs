"""JobSpy adapter (Indeed/LinkedIn scraping via the python-jobspy library).

The library is imported lazily so importing this module has no side effects
and a missing install only matters when JobSpy is enabled.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from ngj.compensation import bounded_comp, extract_compensation
from ngj.models import KIND_UNAVAILABLE, KIND_UNEXPECTED, SourceResult
from ngj.settings import DEFAULT_JOBSPY_WORKERS
from ngj.text import clean_description

logger = logging.getLogger(__name__)

SOURCE = "jobspy"
_RETRY_DELAY = 0.3

# Countries searched when config.yml lists none.
DEFAULT_JOBSPY_COUNTRIES: tuple[dict[str, str], ...] = (
    {'code': 'USA', 'location': 'United States'},
    {'code': 'Canada', 'location': 'Canada'},
    {'code': 'India', 'location': 'India'},
)


def load_scrape_jobs() -> Callable[..., Any] | None:
    """Return ``jobspy.scrape_jobs`` or None when the library is not installed."""
    try:
        from jobspy import scrape_jobs
    except ImportError:
        return None
    return scrape_jobs


def _row_comp(row: Any, description: str) -> dict[str, Any] | None:
    # JobSpy returns structured salary on Indeed/LinkedIn when the listing
    # exposes it; prefer that over regex extraction.
    structured_min = row.get('min_amount')
    structured_max = row.get('max_amount')
    try:
        smin = int(structured_min) if structured_min not in (None, '') else None
        smax = int(structured_max) if structured_max not in (None, '') else None
    except (TypeError, ValueError):
        smin = smax = None
    return bounded_comp(smin, smax, 'jobspy') or extract_compensation(description)


def _row_to_job(row: Any, site: str) -> dict[str, Any]:
    description = row.get('description', '') or ''
    return {
        'company': row.get('company', 'Unknown'),
        'title': row.get('title', ''),
        'location': row.get('location', 'Remote'),
        'url': row.get('job_url', ''),
        'posted_at': row.get('date_posted', ''),
        'source': f'JobSpy ({site.title()})',
        'description': clean_description(description),
        'description_html': description,
        'comp': _row_comp(row, description),
    }


def _search_one(
    scrape_jobs: Callable[..., Any],
    site: str,
    search_term: str,
    country: dict[str, str],
    results_wanted: int,
    hours_old: int,
    max_retries: int,
) -> SourceResult:
    """Run one (site, term, country) search with retries."""
    task = f"{site}:{search_term}:{country.get('code', '?')}"
    last_error = "Max retries exceeded"
    for attempt in range(max_retries + 1):
        try:
            jobs_df = scrape_jobs(
                site_name=site,
                search_term=search_term,
                location=country['location'],
                results_wanted=results_wanted,
                hours_old=hours_old,
                country_indeed=country['code'],
            )
            if jobs_df is None or jobs_df.empty:
                return SourceResult()
            jobs = [_row_to_job(row, site) for _, row in jobs_df.iterrows()]
            kept = tuple(job for job in jobs if job['url'] and str(job['url']).startswith('http'))
            return SourceResult(jobs=kept, raw_count=len(jobs))
        except Exception as exc:
            last_error = str(exc)[:100]
            if attempt < max_retries:
                time.sleep(_RETRY_DELAY)
    return SourceResult.failure(task, SOURCE, KIND_UNEXPECTED, last_error)


def fetch_jobspy_jobs(
    config_jobspy: dict[str, Any],
    max_retries: int = 2,
    workers: int = DEFAULT_JOBSPY_WORKERS,
) -> SourceResult:
    """Run every configured (site, search term, country) JobSpy search in parallel."""
    if not config_jobspy.get('enabled', False):
        logger.info("JobSpy is disabled in configuration, skipping...")
        return SourceResult()

    scrape_jobs = load_scrape_jobs()
    if scrape_jobs is None:
        logger.warning("❌ JobSpy library not available (pip install python-jobspy), skipping...")
        return SourceResult.failure('jobspy', SOURCE, KIND_UNAVAILABLE, "python-jobspy is not installed")

    sites = config_jobspy.get('sites', ['linkedin', 'indeed'])
    search_terms = config_jobspy.get('search_terms', ['new grad software engineer'])
    results_wanted = config_jobspy.get('results_wanted', 50)
    hours_old = config_jobspy.get('hours_old', 72)
    countries = config_jobspy.get('countries', list(DEFAULT_JOBSPY_COUNTRIES))

    tasks = [(site, term, country) for site in sites for term in search_terms for country in countries]
    total = len(tasks)
    logger.info(
        "🚀 Starting PARALLEL job search: %s searches across %s sites and %s countries",
        total, len(sites), len(countries),
    )
    logger.info("   Countries: %s", ', '.join(c['code'] for c in countries))
    logger.info("   Using %s concurrent workers...", workers)

    results: list[SourceResult | None] = [None] * total
    completed = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(_search_one, scrape_jobs, site, term, country, results_wanted, hours_old, max_retries): i
            for i, (site, term, country) in enumerate(tasks)
        }
        for future in as_completed(futures):
            index = futures[future]
            site, term, _country = tasks[index]
            completed += 1  # only the consuming thread touches this counter
            result = future.result()
            results[index] = result
            if result.errors:
                logger.warning("  [%s/%s] ❌ %s '%s': %s", completed, total, site.upper(), term, result.errors[0].message)
            elif result.jobs:
                logger.info("  [%s/%s] ✓ %s '%s': %s jobs", completed, total, site.upper(), term, len(result.jobs))
            else:
                logger.info("  [%s/%s] ⚠️ %s '%s': No jobs found", completed, total, site.upper(), term)

    merged = SourceResult.merge(r for r in results if r is not None)
    logger.info("\n✅ Parallel search complete!")
    logger.info("   Total jobs found via JobSpy: %s", len(merged.jobs))
    logger.info("   Successful searches: %s/%s", total - len(merged.errors), total)
    if merged.errors:
        logger.warning("   ⚠️ Errors: %s", len(merged.errors))
    return merged

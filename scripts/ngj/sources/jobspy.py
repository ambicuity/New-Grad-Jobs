"""JobSpy adapter (Indeed/LinkedIn scraping via the python-jobspy library).

The library is imported lazily so importing this module has no side effects
and a missing install only matters when JobSpy is enabled.
"""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from ngj.compensation import bounded_comp, dollar_currency_for_location
from ngj.models import KIND_UNAVAILABLE, KIND_UNEXPECTED, SourceResult
from ngj.settings import DEFAULT_JOBSPY_WORKERS, jobspy_enabled

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


def is_missing(value: Any) -> bool:
    """True for None and pandas' missing markers (float NaN, ``pd.NA``, ``pd.NaT``).

    Needed because ``row.get('x', '') or ''`` keeps NaN — NaN is truthy.
    """
    if value is None:
        return True
    if isinstance(value, float):
        return math.isnan(value)
    return type(value).__name__ in ('NAType', 'NaTType')


def normalize_row(row: Any) -> dict[str, Any]:
    """Plain dict copy of a JobSpy row with every missing marker replaced by None."""
    items = row.items() if hasattr(row, 'items') else dict(row).items()
    return {key: (None if is_missing(value) else value) for key, value in items}


def _text(value: Any) -> str:
    """Normalised row value as stripped text ('' when missing)."""
    return '' if value is None else str(value).strip()


def _amount(value: Any) -> float | None:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(amount) or amount <= 0 else amount


def _row_comp(row: dict[str, Any]) -> dict[str, Any] | None:
    """Structured salary from JobSpy's min/max/currency/interval columns, else None.

    The regex fallback over the description runs later, in ngj.enrich, only
    for jobs that survive filtering. A missing ``currency`` is inferred from
    the location (a bare dollar amount abroad stays unlabelled), and the
    ``interval`` (hourly/monthly/...) is annualised instead of being read as
    a yearly figure.
    """
    smin, smax = _amount(row.get('min_amount')), _amount(row.get('max_amount'))
    if smin is None or smax is None:
        return None
    currency = _text(row.get('currency')).upper() or dollar_currency_for_location(_text(row.get('location')))
    interval = _text(row.get('interval')) or None
    return bounded_comp(smin, smax, 'jobspy', currency=currency, interval=interval)


def _row_to_job(row: Any, site: str) -> dict[str, Any] | None:
    """Build a job from one JobSpy row; None when the row has no usable title."""
    data = normalize_row(row)
    title = _text(data.get('title'))
    if not title or title.lower() in ('nan', 'none'):
        return None
    return {
        'company': _text(data.get('company')) or 'Unknown',
        'title': title,
        'location': _text(data.get('location')),
        'url': _text(data.get('job_url')),
        'posted_at': data.get('date_posted') or '',
        'source': f'JobSpy ({site.title()})',
        # Raw only; cleaned text / regex comp / flags are derived in ngj.enrich after filtering.
        'description': '',
        'description_html': _text(data.get('description')),
        'comp': _row_comp(data),
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
            raw_count = len(jobs_df)
            jobs = (_row_to_job(row, site) for _, row in jobs_df.iterrows())
            kept = tuple(job for job in jobs if job is not None and job['url'].startswith('http'))
            return SourceResult(jobs=kept, raw_count=raw_count)
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
    if not jobspy_enabled(config_jobspy):
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

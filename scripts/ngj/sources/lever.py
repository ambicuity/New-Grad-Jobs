"""Lever postings API adapter (api.lever.co)."""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from ngj import http as ngj_http
from ngj.compensation import extract_compensation
from ngj.models import SourceResult
from ngj.settings import DEFAULT_HTTP_TIMEOUT, Settings
from ngj.text import clean_description

SOURCE = "lever"


def _to_job(company_name: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    description = raw.get('description', '') or raw.get('descriptionPlain', '') or ''
    return {
        'company': company_name,
        'title': raw.get('text', ''),
        'location': raw.get('categories', {}).get('location', 'Remote'),
        'url': raw.get('hostedUrl', ''),
        'posted_at': raw.get('createdAt'),
        'source': 'Lever',
        'description': clean_description(description),
        'description_html': description,
        'comp': extract_compensation(description),
    }


def fetch_lever_jobs(
    company_name: str,
    url: str,
    max_retries: int = 2,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> SourceResult:
    """Fetch one company's Lever postings."""

    def parse(data: Any) -> Optional[SourceResult]:
        if not isinstance(data, list):
            return None
        return SourceResult(jobs=tuple(_to_job(company_name, raw) for raw in data), raw_count=len(data))

    return ngj_http.fetch_json_with_retry(
        company_name, SOURCE, 'Lever', url, parse, timeout=timeout, max_retries=max_retries,
    )


def fetch_all_lever_jobs(companies: Sequence[Dict[str, Any]], settings: Settings) -> SourceResult:
    """Fetch every configured Lever company in parallel."""
    workers = min(settings.lever_max_workers, max(settings.lever_min_workers, len(companies)))
    return ngj_http.fan_out(
        list(companies),
        lambda c: fetch_lever_jobs(c['name'], c['url'], timeout=settings.http_timeout),
        max_workers=workers,
        source=SOURCE,
        describe=lambda c: c.get('name', '<unknown>'),
        label='Lever',
    )

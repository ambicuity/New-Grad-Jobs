"""Lever postings API adapter (api.lever.co)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ngj import http as ngj_http
from ngj.models import SourceResult
from ngj.settings import DEFAULT_HTTP_TIMEOUT, Settings

SOURCE = "lever"


def _to_job(company_name: str, raw: dict[str, Any]) -> dict[str, Any]:
    return {
        'company': company_name,
        'title': raw.get('text') or '',
        'location': (raw.get('categories') or {}).get('location') or '',
        'url': raw.get('hostedUrl') or '',
        'posted_at': raw.get('createdAt'),
        'source': 'Lever',
        # Raw only; cleaned text / comp / flags are derived in ngj.enrich after filtering.
        'description': '',
        'description_html': raw.get('description') or raw.get('descriptionPlain') or '',
    }


def fetch_lever_jobs(
    company_name: str,
    url: str,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> SourceResult:
    """Fetch one company's Lever postings."""

    def parse(data: Any) -> SourceResult | None:
        if not isinstance(data, list):
            return None
        return SourceResult(jobs=tuple(_to_job(company_name, raw) for raw in data), raw_count=len(data))

    return ngj_http.fetch_json_with_retry(company_name, SOURCE, 'Lever', url, parse, timeout=timeout)


def fetch_all_lever_jobs(companies: Sequence[dict[str, Any]], settings: Settings) -> SourceResult:
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

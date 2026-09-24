"""Ashby public Posting API adapter (api.ashbyhq.com/posting-api/job-board/<slug>).

Used by many AI labs and devtools companies. ``includeCompensation=true``
returns structured compensation when the company opts in.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from ngj import http as ngj_http
from ngj.compensation import bounded_comp, extract_compensation
from ngj.models import SourceResult
from ngj.settings import DEFAULT_HTTP_TIMEOUT, Settings
from ngj.text import clean_description

SOURCE = "ashby"


def _with_compensation_flag(url: str) -> str:
    if 'includeCompensation' in url:
        return url
    return url + ('&' if '?' in url else '?') + 'includeCompensation=true'


def _structured_comp(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """First USD per-year tier within the sanity bounds, if any."""
    ashby_comp = raw.get('compensation') or {}
    tiers = ashby_comp.get('compensationTiers') if isinstance(ashby_comp, dict) else None
    if not isinstance(tiers, list):
        return None
    for tier in tiers:
        try:
            interval = (tier.get('interval') or '').lower()
            currency = (tier.get('currencyCode') or 'USD').upper()
            if currency == 'USD' and 'year' in interval:
                comp = bounded_comp(tier.get('minValue'), tier.get('maxValue'), 'ashby')
                if comp:
                    return comp
        except (TypeError, ValueError, AttributeError):
            continue
    return None


def _location(raw: Dict[str, Any]) -> str:
    addr = (raw.get('address') or {}).get('postalAddress') or {}
    parts = [addr.get(k) for k in ('addressLocality', 'addressRegion', 'addressCountry')]
    return ', '.join([p for p in parts if p]) or raw.get('location') or 'Remote'


def _to_job(company_name: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    description = raw.get('descriptionHtml', '') or raw.get('descriptionPlain', '') or ''
    return {
        'company': company_name,
        'title': raw.get('title', ''),
        'location': _location(raw),
        'url': raw.get('jobUrl', '') or raw.get('applyUrl', ''),
        'posted_at': raw.get('publishedAt'),
        'source': 'Ashby',
        'description': clean_description(description),
        'description_html': description,
        # Prefer Ashby's structured compensation; fall back to description regex.
        'comp': _structured_comp(raw) or extract_compensation(description),
    }


def fetch_ashby_jobs(
    company_name: str,
    url: str,
    max_retries: int = 2,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> SourceResult:
    """Fetch one company's Ashby job board."""
    url = _with_compensation_flag(url)

    def parse(data: Any) -> Optional[SourceResult]:
        if not isinstance(data, dict) or 'jobs' not in data:
            return None
        raw_jobs = data.get('jobs', [])
        return SourceResult(jobs=tuple(_to_job(company_name, raw) for raw in raw_jobs), raw_count=len(raw_jobs))

    return ngj_http.fetch_json_with_retry(
        company_name, SOURCE, 'Ashby', url, parse, timeout=timeout, max_retries=max_retries,
    )


def fetch_all_ashby_jobs(companies: Sequence[Dict[str, Any]], settings: Settings) -> SourceResult:
    """Fetch every configured Ashby board in parallel."""
    return ngj_http.fan_out(
        list(companies),
        lambda c: fetch_ashby_jobs(c['name'], c['url'], timeout=settings.http_timeout),
        max_workers=min(settings.ashby_max_workers, len(companies)),
        source=SOURCE,
        describe=lambda c: c.get('name', '<unknown>'),
        label='Ashby',
    )

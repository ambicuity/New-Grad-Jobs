"""Ashby public Posting API adapter (api.ashbyhq.com/posting-api/job-board/<slug>).

Used by many AI labs and devtools companies. ``includeCompensation=true``
returns structured compensation when the company opts in.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ngj import http as ngj_http
from ngj.compensation import bounded_comp
from ngj.models import SourceResult
from ngj.settings import DEFAULT_HTTP_TIMEOUT, Settings

SOURCE = "ashby"


def _with_compensation_flag(url: str) -> str:
    if 'includeCompensation' in url:
        return url
    return url + ('&' if '?' in url else '?') + 'includeCompensation=true'


def _structured_comp(raw: dict[str, Any]) -> dict[str, Any] | None:
    """First per-year tier within its currency's sanity bounds, labelled with its real currency."""
    ashby_comp = raw.get('compensation') or {}
    tiers = ashby_comp.get('compensationTiers') if isinstance(ashby_comp, dict) else None
    if not isinstance(tiers, list):
        return None
    for tier in tiers:
        try:
            interval = (tier.get('interval') or '').lower()
            currency = (tier.get('currencyCode') or 'USD').upper()
            if 'year' in interval:
                comp = bounded_comp(tier.get('minValue'), tier.get('maxValue'), 'ashby', currency=currency)
                if comp:
                    return comp
        except (TypeError, ValueError, AttributeError):
            continue
    return None


def _location(raw: dict[str, Any]) -> str:
    addr = (raw.get('address') or {}).get('postalAddress') or {}
    parts = [addr.get(k) for k in ('addressLocality', 'addressRegion', 'addressCountry')]
    return ', '.join([p for p in parts if p]) or raw.get('location') or ''


def _to_job(company_name: str, raw: dict[str, Any]) -> dict[str, Any]:
    return {
        'company': company_name,
        'title': raw.get('title') or '',
        'location': _location(raw),
        'url': raw.get('jobUrl') or raw.get('applyUrl') or '',
        'posted_at': raw.get('publishedAt'),
        'source': 'Ashby',
        # Raw only; cleaned text / regex comp / flags are derived in ngj.enrich
        # after filtering. Structured comp is cheap and authoritative, so it
        # is kept here and preferred over the regex fallback.
        'description': '',
        'description_html': raw.get('descriptionHtml') or raw.get('descriptionPlain') or '',
        'comp': _structured_comp(raw),
    }


def fetch_ashby_jobs(
    company_name: str,
    url: str,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> SourceResult:
    """Fetch one company's Ashby job board."""
    url = _with_compensation_flag(url)

    def parse(data: Any) -> SourceResult | None:
        if not isinstance(data, dict) or not isinstance(data.get('jobs'), list):
            return None
        raw_jobs = data['jobs']
        return SourceResult(jobs=tuple(_to_job(company_name, raw) for raw in raw_jobs), raw_count=len(raw_jobs))

    return ngj_http.fetch_json_with_retry(company_name, SOURCE, 'Ashby', url, parse, timeout=timeout)


def fetch_all_ashby_jobs(companies: Sequence[dict[str, Any]], settings: Settings) -> SourceResult:
    """Fetch every configured Ashby board in parallel."""
    first_pass = ngj_http.fan_out(
        list(companies),
        lambda c: fetch_ashby_jobs(c['name'], c['url'], timeout=settings.http_timeout),
        max_workers=min(settings.ashby_max_workers, len(companies)),
        source=SOURCE,
        describe=lambda c: c.get('name', '<unknown>'),
        label='Ashby',
    )
    # Big boards can stall past the read timeout while every source runs at
    # once; give timed-out ones a sequential second chance with a longer timeout.
    return ngj_http.retry_transient_failures(
        list(companies),
        first_pass,
        lambda c: fetch_ashby_jobs(c['name'], c['url'], timeout=settings.http_timeout * 2),
        describe=lambda c: c.get('name', '<unknown>'),
    )

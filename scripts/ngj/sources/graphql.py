"""Config-driven adapter for public GraphQL careers endpoints."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

import requests

from ngj import http as ngj_http
from ngj.models import KIND_CONFIG, KIND_NETWORK, KIND_PARSE, KIND_UNEXPECTED, SourceError, SourceResult
from ngj.settings import DEFAULT_GRAPHQL_MAX_JOBS_PER_SOURCE, DEFAULT_GRAPHQL_TIMEOUT, Settings
from ngj.text import clean_description
from ngj.util import get_nested_value

logger = logging.getLogger(__name__)

SOURCE = "graphql"


def normalize_graphql_items(items: Any) -> list[dict[str, Any]]:
    """Normalize GraphQL item arrays and unwrap edge/node shapes."""
    if not isinstance(items, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        normalized.append(item['node'] if isinstance(item.get('node'), dict) else item)
    return normalized


def graphql_value_as_string(value: Any) -> str:
    """Convert mapped GraphQL values to a deterministic string."""
    if value is None:
        return ''
    if isinstance(value, list):
        return '; '.join(str(v).strip() for v in value if v is not None and str(v).strip())
    return str(value).strip()


def _to_job(company_name: str, item: dict[str, Any], field_mappings: dict[str, str]) -> dict[str, Any]:
    def mapped(field: str) -> Any:
        return get_nested_value(item, field_mappings.get(field, ''))

    return {
        'company': company_name,
        'title': graphql_value_as_string(mapped('title')),
        'location': graphql_value_as_string(mapped('location')) or 'Remote',
        'url': graphql_value_as_string(mapped('url')),
        'posted_at': mapped('posted_at'),
        'source': 'GraphQL',
        'description': clean_description(graphql_value_as_string(mapped('description'))),
    }


def fetch_graphql_jobs(
    source_config: dict[str, Any],
    max_jobs: int = DEFAULT_GRAPHQL_MAX_JOBS_PER_SOURCE,
    timeout: int = DEFAULT_GRAPHQL_TIMEOUT,
) -> SourceResult:
    """Fetch jobs from one GraphQL endpoint, following cursor pagination."""
    company_name = source_config.get('name', 'Unknown')
    endpoint = source_config.get('endpoint', '')
    query = source_config.get('query', '')
    base_variables = source_config.get('variables', {}) or {}
    data_path = source_config.get('data_path', '')
    page_info_path = source_config.get('page_info_path', '')
    field_mappings = source_config.get('field_mappings', {}) or {}

    if not endpoint or not query or not data_path:
        logger.warning("  ⚠️  %s: GraphQL source missing endpoint/query/data_path", company_name)
        return SourceResult.failure(company_name, SOURCE, KIND_CONFIG, "missing endpoint/query/data_path")
    if not isinstance(base_variables, dict) or not isinstance(field_mappings, dict):
        logger.warning("  ⚠️  %s: GraphQL variables/field_mappings must be objects", company_name)
        return SourceResult.failure(company_name, SOURCE, KIND_CONFIG, "variables/field_mappings must be objects")

    logger.info("Fetching jobs from %s (GraphQL)...", company_name)
    jobs: list[dict[str, Any]] = []
    errors: list[SourceError] = []
    raw_count = 0
    cursor: Any = None
    headers = {'Content-Type': 'application/json'}

    def fail(kind: str, message: str, status: Any = None) -> None:
        errors.append(SourceError(company_name, SOURCE, kind, status, message))

    try:
        while len(jobs) < max_jobs:
            variables = {**base_variables, 'after': cursor} if cursor else dict(base_variables)
            response = ngj_http.limited_post(
                endpoint,
                json={'query': query, 'variables': variables},
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()

            if not isinstance(payload, dict):
                logger.warning("  ⚠️  %s: GraphQL response must be an object", company_name)
                fail(KIND_PARSE, "GraphQL response must be an object")
                break
            if payload.get('errors'):
                logger.warning("  ⚠️  %s: GraphQL returned errors", company_name)
                fail(KIND_PARSE, "GraphQL returned errors")
                break

            items = normalize_graphql_items(get_nested_value(payload, data_path))
            if not items:
                break
            raw_count += len(items)

            for item in items:
                jobs.append(_to_job(company_name, item, field_mappings))
                if len(jobs) >= max_jobs:
                    break

            if len(jobs) >= max_jobs or not page_info_path:
                break
            page_info = get_nested_value(payload, page_info_path)
            if not isinstance(page_info, dict) or not page_info.get('hasNextPage'):
                break
            cursor = page_info.get('endCursor')
            if not cursor:
                break

    except requests.exceptions.RequestException as exc:
        logger.error("  ❌ Request error for %s (GraphQL): %s", company_name, exc)
        status = getattr(getattr(exc, 'response', None), 'status_code', None)
        fail(KIND_PARSE if isinstance(exc, ValueError) else KIND_NETWORK, str(exc), status)
    except ValueError as exc:
        logger.error("  ❌ Invalid JSON for %s (GraphQL): %s", company_name, exc)
        fail(KIND_PARSE, str(exc))
    except Exception as exc:
        logger.error("  ❌ Error fetching from %s (GraphQL): %s", company_name, exc)
        fail(KIND_UNEXPECTED, f"{type(exc).__name__}: {exc}")

    logger.info("  ✓ Found %s jobs from %s", len(jobs), company_name)
    return SourceResult(jobs=tuple(jobs), errors=tuple(errors), raw_count=raw_count)


def fetch_all_graphql_jobs(sources: Sequence[dict[str, Any]], settings: Settings) -> SourceResult:
    """Fetch all configured GraphQL sources in parallel."""
    workers = min(settings.graphql_max_workers, max(settings.graphql_min_workers, len(sources)))
    return ngj_http.fan_out(
        list(sources),
        lambda s: fetch_graphql_jobs(
            s, max_jobs=settings.graphql_max_jobs_per_source, timeout=settings.graphql_timeout,
        ),
        max_workers=workers,
        source=SOURCE,
        describe=lambda s: s.get('name', 'Unknown'),
        label='GraphQL',
        noun='sources',
    )

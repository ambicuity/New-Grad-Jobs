"""The one place that decides which job sources are enabled for a run.

Used by the pipeline (what to fetch), health.json (configured/enabled counts,
per-source failure ratios) and scripts/validate_config.py, so the three can
no longer disagree (health.json used to leave Ashby out of both
``configured_company_apis`` and ``enabled_sources``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

# Board-per-company ATS sources: ``apis.<name>.companies`` = [{name, url}].
ATS_COMPANY_SOURCES = ("greenhouse", "lever", "ashby")

# Registry order is the fetch/plan order.
SOURCE_ORDER = ("greenhouse", "lever", "ashby", "google", "jobspy", "workday", "graphql")


@dataclass(frozen=True)
class SourceSpec:
    """An enabled source and the configured units (companies/boards/queries) it fetches."""

    name: str
    units: tuple[Any, ...]
    # True when each unit is a company's own careers API (counted in
    # health.json ``configured_company_apis``); False for search-style sources.
    company_api: bool

    @property
    def unit_count(self) -> int:
        return len(self.units)


def _section(apis: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(apis, Mapping):
        return {}
    section = apis.get(name)
    return section if isinstance(section, Mapping) else {}


def _items(section: Mapping[str, Any], key: str) -> tuple[Any, ...]:
    value = section.get(key)
    return tuple(value) if isinstance(value, list) else ()


def _enabled(section: Mapping[str, Any], default: bool) -> bool:
    return bool(section.get("enabled", default))


def source_registry(config: Mapping[str, Any]) -> dict[str, SourceSpec]:
    """Return the enabled sources in :data:`SOURCE_ORDER`.

    Defaults mirror the fetchers: ATS company sources and Google run unless
    ``enabled: false``; JobSpy, Workday and GraphQL only with ``enabled: true``.
    A source with nothing configured (no companies/terms/sources) is not enabled.
    """
    apis = config.get("apis")
    specs: dict[str, SourceSpec] = {}

    for name in ATS_COMPANY_SOURCES:
        section = _section(apis, name)
        companies = _items(section, "companies")
        if companies and _enabled(section, True):
            specs[name] = SourceSpec(name, companies, company_api=True)

    google = _section(apis, "google")
    if _enabled(google, True) and _items(google, "search_terms"):
        specs["google"] = SourceSpec("google", _items(google, "search_terms"), company_api=False)

    jobspy = _section(apis, "jobspy")
    if _enabled(jobspy, False):
        specs["jobspy"] = SourceSpec("jobspy", _items(jobspy, "search_terms"), company_api=False)

    workday = _section(apis, "workday")
    if _enabled(workday, False) and _items(workday, "companies"):
        specs["workday"] = SourceSpec("workday", _items(workday, "companies"), company_api=True)

    graphql = _section(apis, "graphql")
    if _enabled(graphql, False) and _items(graphql, "sources"):
        specs["graphql"] = SourceSpec("graphql", _items(graphql, "sources"), company_api=True)

    return {name: specs[name] for name in SOURCE_ORDER if name in specs}


def configured_company_apis(registry: Mapping[str, SourceSpec]) -> int:
    """Number of company careers APIs (ATS boards, Workday tenants, GraphQL sources) enabled."""
    return sum(spec.unit_count for spec in registry.values() if spec.company_api)

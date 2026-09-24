"""ngj.registry: the single source-enablement decision."""

from pathlib import Path

from ngj.registry import configured_company_apis, source_registry
from ngj.settings import load_config

CO = [{"name": "A", "url": "https://x"}]


def test_live_config_enables_all_five_active_sources_including_ashby():
    registry = source_registry(load_config(Path(__file__).resolve().parents[1] / "config.yml"))
    assert list(registry) == ["greenhouse", "lever", "ashby", "jobspy", "workday"]
    assert configured_company_apis(registry) == sum(
        registry[name].unit_count for name in ("greenhouse", "lever", "ashby", "workday"))


def test_defaults_and_enabled_flags():
    config = {"apis": {
        "greenhouse": {"companies": CO},
        "lever": {"companies": CO, "enabled": False},
        "ashby": {"companies": CO + CO},
        "google": {"search_terms": ["x"]},
        "jobspy": {"search_terms": ["x"]},  # disabled by default
        "workday": {"enabled": True, "companies": []},  # nothing configured
        "graphql": {"enabled": True, "sources": [{"name": "g"}]},
    }}
    registry = source_registry(config)
    assert list(registry) == ["greenhouse", "ashby", "google", "graphql"]
    assert configured_company_apis(registry) == 1 + 2 + 1


def test_null_and_malformed_sections_are_ignored():
    assert source_registry({}) == {}
    assert source_registry({"apis": None}) == {}
    assert source_registry({"apis": {"greenhouse": None, "lever": {"companies": "nope"}}}) == {}

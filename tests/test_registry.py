"""ngj.registry: the single source-enablement decision."""

from pathlib import Path

from ngj.registry import configured_company_apis, source_registry
from ngj.settings import load_config

CO = [{"name": "A", "url": "https://x"}]


def test_live_config_enables_all_fourteen_active_sources():
    registry = source_registry(load_config(Path(__file__).resolve().parents[1] / "config.yml"))
    boards = ("greenhouse", "lever", "ashby", "smartrecruiters", "oracle_hcm", "rippling", "ukg", "adp", "workable",
              "paylocity", "successfactors", "icims")
    assert list(registry) == [*boards, "jobspy", "workday"]
    assert configured_company_apis(registry) == sum(registry[name].unit_count for name in (*boards, "workday"))


def test_icims_is_a_board_source_enabled_by_default():
    registry = source_registry({"apis": {"icims": {"companies": CO}}})
    assert list(registry) == ["icims"] and registry["icims"].company_api is True
    assert source_registry({"apis": {"icims": {"companies": CO, "enabled": False}}}) == {}


def test_successfactors_is_a_board_source_enabled_by_default():
    registry = source_registry({"apis": {"successfactors": {"companies": CO}}})
    assert list(registry) == ["successfactors"] and registry["successfactors"].company_api is True
    assert source_registry({"apis": {"successfactors": {"companies": CO, "enabled": False}}}) == {}


def test_paylocity_is_a_board_source_enabled_by_default():
    registry = source_registry({"apis": {"paylocity": {"companies": CO}}})
    assert list(registry) == ["paylocity"] and registry["paylocity"].company_api is True
    assert source_registry({"apis": {"paylocity": {"companies": CO, "enabled": False}}}) == {}


def test_workable_is_a_board_source_enabled_by_default():
    registry = source_registry({"apis": {"workable": {"companies": CO}}})
    assert list(registry) == ["workable"] and registry["workable"].company_api is True
    assert source_registry({"apis": {"workable": {"companies": CO, "enabled": False}}}) == {}


def test_adp_is_a_board_source_enabled_by_default():
    registry = source_registry({"apis": {"adp": {"companies": CO}}})
    assert list(registry) == ["adp"] and registry["adp"].company_api is True
    assert source_registry({"apis": {"adp": {"companies": CO, "enabled": False}}}) == {}


def test_ukg_is_a_board_source_enabled_by_default():
    registry = source_registry({"apis": {"ukg": {"companies": CO}}})
    assert list(registry) == ["ukg"] and registry["ukg"].company_api is True
    assert source_registry({"apis": {"ukg": {"companies": CO, "enabled": False}}}) == {}


def test_rippling_is_a_board_source_enabled_by_default():
    registry = source_registry({"apis": {"rippling": {"companies": CO}}})
    assert list(registry) == ["rippling"] and registry["rippling"].company_api is True
    assert source_registry({"apis": {"rippling": {"companies": CO, "enabled": False}}}) == {}


def test_oracle_hcm_is_a_board_source_enabled_by_default():
    registry = source_registry({"apis": {"oracle_hcm": {"companies": CO}}})
    assert list(registry) == ["oracle_hcm"] and registry["oracle_hcm"].company_api is True
    assert source_registry({"apis": {"oracle_hcm": {"companies": CO, "enabled": False}}}) == {}


def test_smartrecruiters_is_a_board_source_enabled_by_default():
    registry = source_registry({"apis": {"smartrecruiters": {"companies": CO}}})
    assert list(registry) == ["smartrecruiters"]
    assert registry["smartrecruiters"].company_api is True
    assert source_registry({"apis": {"smartrecruiters": {"companies": CO, "enabled": False}}}) == {}


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

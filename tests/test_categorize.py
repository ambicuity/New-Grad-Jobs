#!/usr/bin/env python3
"""
Unit tests for the job categorization logic in scripts/update_jobs.py.

These tests validate that jobs are correctly classified into categories
like Software Engineering, Data ML, Quant Finance, etc., based on title keywords.
"""

import sys
import os

# Ensure the scripts directory is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from update_jobs import (
    categorize_job,
    get_company_tier,
    detect_sponsorship_flags,
    is_engineering_network_title,
)


class TestCategorizeJob:
    """Tests for the categorize_job() function."""

    def test_software_engineer_title(self):
        result = categorize_job("Software Engineer, New Grad")
        assert result["id"] == "software_engineering"
        assert result["name"] == "Software Engineering"

    def test_swe_abbreviation(self):
        result = categorize_job("SWE Intern - 2025")
        assert result["id"] == "software_engineering"

    def test_swe_abbreviation_2026(self):
        result = categorize_job("SWE Intern - 2026")
        assert result["id"] == "software_engineering"

    def test_frontend_engineer(self):
        result = categorize_job("Frontend Engineer - React")
        assert result["id"] == "software_engineering"

    def test_backend_engineer(self):
        result = categorize_job("Backend Engineer (Python)")
        assert result["id"] == "software_engineering"

    def test_backend_go_engineer(self):
        result = categorize_job("Backend Engineer (Go)")
        assert result["id"] == "software_engineering"

    def test_ml_engineer(self):
        result = categorize_job("ML Engineer - NLP")
        assert result["id"] == "data_ml"
        assert result["name"] == "Data Science & ML"

    def test_research_scientist(self):
        result = categorize_job("Research Scientist, Applied AI")
        assert result["id"] == "data_ml"

    def test_data_engineer(self):
        result = categorize_job("Data Engineer - Platform Team")
        assert result["id"] == "data_engineering"

    def test_data_analyst(self):
        result = categorize_job("Data Analyst, Business Intelligence")
        assert result["id"] == "data_engineering"

    def test_sre_title(self):
        result = categorize_job("Site Reliability Engineer")
        assert result["id"] == "infrastructure_sre"

    def test_devops_title(self):
        result = categorize_job("DevOps Engineer - Platform")
        assert result["id"] == "infrastructure_sre"

    def test_product_manager(self):
        result = categorize_job("Product Manager, Growth")
        assert result["id"] == "product_management"

    def test_tpm_abbreviation(self):
        result = categorize_job("TPM - Infrastructure")
        assert result["id"] == "product_management"

    def test_quant_analyst(self):
        result = categorize_job("Quantitative Analyst")
        assert result["id"] == "quant_finance"

    def test_trader_role(self):
        result = categorize_job("Software Engineer - Algo Trading")
        # "trading" keyword hits quant_finance, but "software engineer" hits SWE first
        # Depending on order, ensure we get a result not Other
        assert result["id"] != "other"

    def test_hardware_engineer(self):
        result = categorize_job("Hardware Engineer - Chip Design")
        assert result["id"] == "hardware"

    def test_embedded_firmware(self):
        result = categorize_job("Embedded Firmware Engineer")
        assert result["id"] == "hardware"

    def test_developer_advocate(self):
        result = categorize_job("Developer Advocate")
        assert result["id"] == "software_engineering"

    def test_devrel(self):
        result = categorize_job("DevRel Engineer")
        assert result["id"] == "software_engineering"

    def test_unmatched_title_returns_other(self):
        result = categorize_job("Office Manager")
        assert result["id"] == "other"
        assert result["name"] == "Other"

    def test_description_keyword_match(self):
        """Verify that description keywords can also match categories."""
        result = categorize_job("Engineer", "Looking for a machine learning specialist")
        assert result["id"] == "data_ml"

    def test_empty_title_returns_other(self):
        result = categorize_job("")
        assert result["id"] == "other"

    def test_returns_required_keys(self):
        """Every result must have id, name, and emoji keys."""
        result = categorize_job("Software Engineer")
        assert "id" in result
        assert "name" in result
        assert "emoji" in result

    def test_network_engineer(self) -> None:
        """Regression: plain 'Network Engineer' maps to infrastructure_sre."""
        result = categorize_job("Network Engineer")
        assert result["id"] == "infrastructure_sre"

    def test_network_security_engineer(self) -> None:
        """Regression: plain 'Network Security Engineer' maps to infrastructure_sre."""
        result = categorize_job("Network Security Engineer")
        assert result["id"] == "infrastructure_sre"

    def test_systems_engineer_networks(self) -> None:
        """Regression: plain 'Systems Engineer, Networks' maps to infrastructure_sre."""
        result = categorize_job("Systems Engineer, Networks")
        assert result["id"] == "infrastructure_sre"

    def test_network_in_description_does_not_override_title(self) -> None:
        """Guard: description-only mentions should not change the title category."""
        result = categorize_job(
            "Software Engineer",
            "Build services on a high-performance network fabric.",
        )
        assert result["id"] == "software_engineering"

    def test_network_domain_software_role_stays_software_engineering(self) -> None:
        """Regression: software roles in a network domain stay software-engineering."""
        result = categorize_job("Software Engineer, Starlink Network")
        assert result["id"] == "software_engineering"

    def test_network_automation(self) -> None:
        result = categorize_job("Network Automation Engineer")
        assert result["id"] == "infrastructure_sre"

    def test_noc_engineer(self) -> None:
        result = categorize_job("NOC Engineer")
        assert result["id"] == "infrastructure_sre"
    
    def test_network_operations_engineer(self) -> None:
        """Regression: 'Network Operations Engineer' maps to infrastructure_sre."""
        result = categorize_job("Network Operations Engineer")
        assert result["id"] == "infrastructure_sre"

    def test_network_operations_center(self) -> None:
        result = categorize_job("Network Operations Center Engineer")
        assert result["id"] == "infrastructure_sre"

    def test_network_performance(self) -> None:
        result = categorize_job("Network Performance Engineer")
        assert result["id"] == "infrastructure_sre"

    def test_netops(self) -> None:
        result = categorize_job("NetOps Engineer")
        assert result["id"] == "infrastructure_sre"

    def test_non_engineering_network_role_stays_other(self) -> None:
        result = categorize_job(
            "Associate, Network Contracting",
            "Partner with providers on network contracting operations.",
        )
        assert result["id"] == "other"

    def test_business_analyst_network_operations_stays_other(self) -> None:
        result = categorize_job("Business Analyst, Network Operations")
        assert result["id"] == "other"

    def test_manager_network_operations_stays_other(self) -> None:
        result = categorize_job("Manager, Network Operations")
        assert result["id"] == "other"

    def test_noc_analyst_stays_other(self) -> None:
        result = categorize_job("NOC Analyst")
        assert result["id"] == "other"

    def test_engineering_network_domain_role_stays_included(self) -> None:
        result = categorize_job("Software Engineer, Networking")
        assert result["id"] == "infrastructure_sre"


class TestEngineeringNetworkTitle:
    def test_none_title_returns_false(self) -> None:
        assert not is_engineering_network_title(None)

    def test_empty_title_returns_false(self) -> None:
        assert not is_engineering_network_title("")

    def test_non_string_title_returns_false(self) -> None:
        assert not is_engineering_network_title(123)

    def test_nan_title_returns_false(self) -> None:
        assert not is_engineering_network_title(float("nan"))

    def test_business_network_title_returns_false(self) -> None:
        assert not is_engineering_network_title("Associate, Network Contracting")

    def test_business_analyst_network_operations_returns_false(self) -> None:
        assert not is_engineering_network_title("Business Analyst, Network Operations")

    def test_manager_network_operations_returns_false(self) -> None:
        assert not is_engineering_network_title("Manager, Network Operations")

    def test_manager_network_infrastructure_returns_false(self) -> None:
        assert not is_engineering_network_title("Manager, Network Infrastructure")

    def test_graduate_analyst_network_services_returns_false(self) -> None:
        assert not is_engineering_network_title("Graduate Analyst, Network Services")

    def test_noc_analyst_returns_false(self) -> None:
        assert not is_engineering_network_title("NOC Analyst")

    def test_engineering_network_title_returns_true(self) -> None:
        assert is_engineering_network_title("Network Engineer")

    def test_networking_engineer_returns_true(self) -> None:
        assert is_engineering_network_title("Networking Engineer")

    def test_noc_engineer_returns_true(self) -> None:
        assert is_engineering_network_title("NOC Engineer")

    def test_network_operations_engineer_returns_true(self) -> None:
        assert is_engineering_network_title("Network Operations Engineer")

    def test_network_services_engineer_returns_true(self) -> None:
        assert is_engineering_network_title("Network Services Engineer")

    def test_software_engineer_networking_returns_true(self) -> None:
        assert is_engineering_network_title("Software Engineer, Networking")


class TestGetCompanyTier:
    """Tests for the get_company_tier() function."""

    def test_faang_google(self):
        result = get_company_tier("Google")
        assert result["tier"] == "faang_plus"
        assert result["label"] == "FAANG+"

    def test_faang_microsoft(self):
        result = get_company_tier("Microsoft")
        assert result["tier"] == "faang_plus"

    def test_unicorn_openai(self):
        result = get_company_tier("OpenAI")
        assert result["tier"] == "unicorn"

    def test_unicorn_stripe(self):
        result = get_company_tier("Stripe")
        assert result["tier"] == "faang_plus"  # Stripe is in FAANG_PLUS

    def test_unknown_company_returns_other(self):
        result = get_company_tier("NoNameTechStartup XYZ")
        assert result["tier"] == "other"
        assert result["label"] == ""

    def test_defense_sector_flag(self):
        result = get_company_tier("Lockheed Martin")
        assert "defense" in result["sectors"]

    def test_finance_sector_flag(self):
        result = get_company_tier("Goldman Sachs")
        assert "finance" in result["sectors"]

    def test_healthcare_sector_flag(self):
        result = get_company_tier("Medtronic")
        assert "healthcare" in result["sectors"]

    def test_returns_sectors_list(self):
        result = get_company_tier("Apple")
        assert isinstance(result["sectors"], list)


class TestDetectSponsorshipFlags:
    """Tests for the detect_sponsorship_flags() function."""

    def test_no_sponsorship_detected(self):
        result = detect_sponsorship_flags(
            "Engineer", "We do not sponsor visas. No sponsorship available."
        )
        assert result["no_sponsorship"] is True

    def test_us_citizenship_required(self):
        result = detect_sponsorship_flags(
            "Engineer", "Requires security clearance and US citizenship."
        )
        assert result["us_citizenship_required"] is True

    def test_both_flags_detected(self):
        result = detect_sponsorship_flags(
            "Software Engineer",
            "U.S. citizens only. Cannot sponsor work authorization.",
        )
        assert result["no_sponsorship"] is True
        assert result["us_citizenship_required"] is True

    def test_no_flags_detected_when_clean(self):
        result = detect_sponsorship_flags(
            "Software Engineer", "Open to all candidates globally."
        )
        assert result["no_sponsorship"] is False
        assert result["us_citizenship_required"] is False

    def test_flag_in_title(self):
        result = detect_sponsorship_flags("No sponsorship Software Engineer", "")
        assert result["no_sponsorship"] is True

    def test_empty_inputs(self):
        result = detect_sponsorship_flags("", "")
        assert result["no_sponsorship"] is False
        assert result["us_citizenship_required"] is False

    def test_empty_description_only(self) -> None:
        result = detect_sponsorship_flags("Software Engineer", "")
        assert result["no_sponsorship"] is False
        assert result["us_citizenship_required"] is False


def test_categorize_cybersecurity_engineer():
    result = categorize_job("Cybersecurity Engineer")
    assert result["id"] == "infrastructure_sre"


def test_categorize_infosec_analyst():
    result = categorize_job("Infosec Analyst")
    assert result["id"] == "infrastructure_sre"

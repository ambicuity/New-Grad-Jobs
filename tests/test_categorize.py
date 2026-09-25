#!/usr/bin/env python3
"""
Unit tests for the job categorization logic in scripts/update_jobs.py.

These tests validate that jobs are correctly classified into categories
like Software Engineering, Data ML, Quant Finance, etc., based on title keywords.
"""

import os
import sys

import pytest

# Ensure the scripts directory is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ngj.enrich import detect_sponsorship_flags  # noqa: E402
from ngj.taxonomy import categorize_job, get_company_tier, is_engineering_network_title  # noqa: E402


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
        assert result["id"] == "frontend"
        assert result["name"] == "Frontend Engineering"

    def test_backend_engineer(self):
        result = categorize_job("Backend Engineer (Python)")
        assert result["id"] == "backend"

    def test_backend_go_engineer(self):
        result = categorize_job("Backend Engineer (Go)")
        assert result["id"] == "backend"

    def test_ios_engineer_is_mobile(self):
        result = categorize_job("iOS Engineer, New Grad")
        assert result["id"] == "mobile"

    def test_generic_swe_title_stays_software_engineering(self):
        # A description mentioning "frontend" must NOT reclassify a general SWE
        # role — specialty tracks are matched on the title only.
        result = categorize_job("Software Engineer, New Grad",
                                "You will work closely with our frontend team.")
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
    assert result["id"] == "security"


def test_categorize_infosec_analyst():
    result = categorize_job("Infosec Analyst")
    assert result["id"] == "security"


def test_network_security_stays_infrastructure():
    # Network-focused security remains infra (network title special-case runs
    # before the security keyword match).
    result = categorize_job("Network Security Engineer")
    assert result["id"] == "infrastructure_sre"


class TestCategorizeTitleFirst:
    """The title decides; the description is only a fallback (audit fix)."""

    def test_tpm_in_swe_description_does_not_make_pm(self):
        result = categorize_job(
            "Software Engineer, New Grad",
            "You will work closely with our TPM and product managers.",
        )
        assert result["id"] == "software_engineering"

    def test_data_scientist_title_beats_swe_description(self):
        result = categorize_job(
            "Data Scientist II",
            "Partner with a software engineer to ship models to our infrastructure.",
        )
        assert result["id"] == "data_ml"

    def test_data_engineer_title_beats_infra_description(self):
        result = categorize_job(
            "Data Engineer, New Grad",
            "Pairs with a full stack developer; our SRE team runs the infrastructure.",
        )
        assert result["id"] == "data_engineering"

    def test_ml_title_beats_swe_description(self):
        result = categorize_job(
            "Machine Learning Engineer",
            "Collaborate with every software engineer on the team.",
        )
        assert result["id"] == "data_ml"

    def test_technical_program_manager_title_is_pm(self):
        result = categorize_job("Technical Program Manager, Infrastructure")
        assert result["id"] == "product_management"

    def test_title_priority_order_is_preserved(self):
        """Within the title, CATEGORY_PATTERNS order still decides ties."""
        assert categorize_job("Frontend Software Engineer")["id"] == "frontend"
        assert categorize_job("Software Engineer, Machine Learning")["id"] == "software_engineering"

    def test_description_used_when_title_matches_nothing(self):
        result = categorize_job("Associate", "Build deep learning models for ranking.")
        assert result["id"] == "data_ml"

    def test_description_never_selects_title_driven_category(self):
        result = categorize_job("Associate", "Partner with the frontend team daily.")
        assert result["id"] == "other"

    def test_keywords_still_need_word_boundaries(self):
        assert categorize_job("Etiquette Coach")["id"] == "other"  # 'etl' inside word


class TestCompanyTierNormalization:
    """Exact-string matching missed common name variants (audit fix)."""

    @pytest.mark.parametrize("name, tier", [
        ("Anduril Industries", "unicorn"),
        ("Snap Inc.", "faang_plus"),
        ("JPMorganChase", "faang_plus"),
        ("JPMorgan Chase & Co.", "faang_plus"),
        ("Amazon.com", "faang_plus"),
        ("Amazon.com Services LLC", "other"),  # extra words: no fuzzy merge
        ("Hewlett Packard Enterprise | HPE", "faang_plus"),
        ("apple", "faang_plus"),
        ("NVIDIA Corporation", "faang_plus"),
        ("The Walt Disney Company", "faang_plus"),
        ("Unity Technologies", "unicorn"),
        ("Unity", "unicorn"),
        ("Checkout.com", "unicorn"),
    ])
    def test_variants_resolve_to_tier(self, name, tier):
        assert get_company_tier(name)["tier"] == tier

    def test_sectors_follow_normalized_name(self):
        assert "defense" in get_company_tier("Anduril Industries")["sectors"]
        assert "finance" in get_company_tier("JPMorganChase")["sectors"]

    @pytest.mark.parametrize("name", [
        "Snapdragon Labs",  # prefix of Snap
        "Metabase",  # prefix of Meta
        "Applied Materials",  # starts like Apple
        "Circle K",  # 'Circle' fintech vs convenience store
        "Sierra Nevada Corporation",  # 'Sierra' unicorn
        "Amazon Web Services",  # different entity string, no fuzzy merge
        "",
    ])
    def test_no_false_merges(self, name):
        assert get_company_tier(name)["tier"] == "other"

    def test_non_string_company_is_other(self):
        assert get_company_tier(None)["tier"] == "other"


class TestTitleFallbackCategories:
    """Generic title words classify a role only after every specific phrase fails.

    A quarter of the live board sat in "Other" because titles such as
    "Associate Engineer Software" or "Manufacturing Engineer II" contain no
    exact category phrase. The fallbacks are matched on the title only.
    """

    @pytest.mark.parametrize(
        ("title", "expected"),
        [
            ("2026 Associate Engineer Software Dulles VA", "software_engineering"),
            ("Junior Developer - KYC - Comp Tech", "software_engineering"),
            ("Associate WordPress Developer (Fresher)", "software_engineering"),
            ("Winter 2027: AI Developer (8 months)", "data_ml"),
            ("Junior Consultant AI Strategy", "data_ml"),
            ("Graduate Development Program - AI & Analytics Associate", "data_ml"),
            ("Data Fulfillment Associate", "data_engineering"),
            ("Manufacturing Development Engineer II", "hardware"),
            ("Early Career Mechanical Design Engineer", "hardware"),
            ("2026 Associate Electronics Engineer - Baltimore MD", "hardware"),
            ("Quality Engineer (Associate or Experienced)", "hardware"),
            ("Associate Test Engineer", "hardware"),
            ("Industrial Engineer I (Onsite)", "hardware"),
            ("Process Engineer II - New Product Development", "hardware"),
            ("Guidance Navigation Control (GNC) Engineer - Level 2", "hardware"),
            ("Associate Automation Engineer", "hardware"),
            ("Semiconductor Foundry Engineer I - Onsite", "hardware"),
            ("IT Support Specialist I", "infrastructure_sre"),
            ("Help Desk Analyst - Entry Level", "infrastructure_sre"),
            ("Cyber Analyst, New Grad", "security"),
        ],
    )
    def test_fallback_keyword_in_title(self, title, expected):
        assert categorize_job(title)["id"] == expected

    def test_specific_phrase_still_wins_over_fallback(self):
        # "data scientist" is a real data_ml phrase; the "software" fallback must not steal it.
        assert categorize_job("Software Data Scientist")["id"] == "data_ml"

    def test_fallback_is_title_only(self):
        # A description mentioning "mechanical" must not file an unrelated role under hardware.
        result = categorize_job("Associate Consultant", "You will work with mechanical teams.")
        assert result["id"] == "other"

    def test_title_fallback_outranks_description_match(self):
        result = categorize_job("Associate Engineer Software", "We use machine learning everywhere.")
        assert result["id"] == "software_engineering"

    def test_fallback_words_match_whole_words_only(self):
        assert categorize_job("Maintenance Planner")["id"] == "other"  # "ai" inside a word
        assert categorize_job("HTML Content Associate")["id"] == "other"  # "ml" inside a word

    def test_hardware_display_name_covers_mechanical(self):
        assert categorize_job("Mechanical Engineer I")["name"] == "Hardware & Mechanical Engineering"

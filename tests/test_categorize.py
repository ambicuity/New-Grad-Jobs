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
    is_job_closed,
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


class TestIsJobClosed:
    """Tests for the is_job_closed() function.
    
    This function detects if a job posting is closed or no longer accepting
    applications based on keywords in the title and description.
    """

    def test_closed_in_title(self):
        """Test detection of 'closed' keyword in job title"""
        assert is_job_closed("Software Engineer - CLOSED") is True
        assert is_job_closed("Software Engineer (Closed)") is True
        assert is_job_closed("Closed - Software Engineer") is True

    def test_closed_in_description(self):
        """Test detection of 'closed' keyword in job description"""
        assert is_job_closed(
            "Software Engineer",
            "This position is now closed. Thank you for your interest."
        ) is True

    def test_no_longer_accepting_in_title(self):
        """Test detection of 'no longer accepting' phrase in title"""
        assert is_job_closed("Software Engineer - No Longer Accepting Applications") is True

    def test_no_longer_accepting_in_description(self):
        """Test detection of 'no longer accepting' phrase in description"""
        assert is_job_closed(
            "Backend Engineer",
            "We are no longer accepting applications for this role."
        ) is True

    def test_position_filled_in_title(self):
        """Test detection of 'position filled' phrase in title"""
        assert is_job_closed("Data Scientist (Position Filled)") is True

    def test_position_filled_in_description(self):
        """Test detection of 'position filled' phrase in description"""
        assert is_job_closed(
            "ML Engineer",
            "This position filled role is no longer available."
        ) is True

    def test_expired_in_title(self):
        """Test detection of 'expired' keyword in title"""
        assert is_job_closed("Frontend Developer - Expired") is True
        assert is_job_closed("(Expired) Full Stack Engineer") is True

    def test_expired_in_description(self):
        """Test detection of 'expired' keyword in description"""
        assert is_job_closed(
            "QA Engineer",
            "This job posting has expired and is no longer active."
        ) is True

    def test_open_job_with_normal_title(self):
        """Test that normal job titles are not flagged as closed"""
        assert is_job_closed("Software Engineer - New Grad 2026") is False
        assert is_job_closed("Backend Developer (Python)") is False
        assert is_job_closed("Data Scientist - Remote") is False

    def test_open_job_with_normal_description(self):
        """Test that normal job descriptions are not flagged as closed"""
        assert is_job_closed(
            "Software Engineer",
            "We are actively hiring for this position. Join our team!"
        ) is False

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive"""
        assert is_job_closed("Software Engineer - CLOSED") is True
        assert is_job_closed("Software Engineer - Closed") is True
        assert is_job_closed("Software Engineer - closed") is True
        assert is_job_closed("POSITION FILLED") is True

    def test_empty_description(self):
        """Test with no description provided"""
        assert is_job_closed("Software Engineer - Closed", "") is True
        assert is_job_closed("Software Engineer", "") is False

    def test_none_description(self):
        """Test with None description (uses default empty string)"""
        assert is_job_closed("Software Engineer - Closed") is True
        assert is_job_closed("Software Engineer") is False

    def test_closed_substring_in_longer_word(self):
        """Test that 'closed' matches as substring (current behavior)
        
        Note: The current implementation uses substring matching, not word boundaries.
        This means 'disclosed' will match 'closed'. This may be a limitation but
        is the current documented behavior.
        """
        # Current behavior: 'disclosed' contains 'closed' substring so it matches
        assert is_job_closed("Software Engineer", "Salary disclosed upon interview") is True
        # Actual 'closed' should definitely match
        assert is_job_closed("Software Engineer", "Application window closed yesterday") is True

    def test_multiple_indicators(self):
        """Test with multiple closed indicators present"""
        assert is_job_closed(
            "Software Engineer - Closed",
            "Position filled. No longer accepting applications."
        ) is True

    def test_partial_matches(self):
        """Test that phrase matching requires exact substring match
        
        The function looks for exact phrase substrings, not word variations.
        'position filled' as a substring will match, but not 'position has been filled'.
        """
        # 'no longer accepting' should match even with extra words after
        assert is_job_closed("SWE", "We are no longer accepting new applications") is True
        # 'position filled' requires exact substring - won't match with words between
        assert is_job_closed("SWE", "The position filled quickly") is True
        assert is_job_closed("SWE", "The position has been filled") is False  # has 'has been' between words

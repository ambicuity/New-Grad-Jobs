#!/usr/bin/env python3
"""
Unit tests for is_valid_location() in scripts/update_jobs.py.

Covers:
  - True positives: USA states/cities, Canada, India, Remote
  - False positives prevented by word-boundary matching
  - Edge cases: empty string, None-like values, Unicode, mixed case
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import is_valid_location


class TestValidLocationTruePositives:
    """Locations that SHOULD match."""

    def test_us_state_full_name(self):
        assert is_valid_location("San Francisco, California") is True

    def test_us_state_abbreviation(self):
        assert is_valid_location("Austin, TX") is True

    def test_us_city(self):
        assert is_valid_location("Mountain View") is True

    def test_remote(self):
        assert is_valid_location("Remote") is True

    def test_remote_us(self):
        assert is_valid_location("Remote - US") is True

    def test_usa_explicit(self):
        assert is_valid_location("New York, USA") is True

    def test_canada_city(self):
        assert is_valid_location("Toronto, ON, Canada") is True

    def test_india_city(self):
        assert is_valid_location("Bangalore, India") is True

    def test_india_state(self):
        assert is_valid_location("Karnataka, India") is True

    def test_worldwide(self):
        assert is_valid_location("Worldwide") is True

    def test_indiana_full(self):
        """Indiana (full name) should match even though 'in' is a short abbreviation."""
        assert is_valid_location("Indianapolis, Indiana") is True


class TestValidLocationFalsePositives:
    """Locations that should NOT match — C4 false-positive regression tests."""

    def test_berlin_germany(self):
        """'in' (Indiana) should NOT match 'Berlin'."""
        assert is_valid_location("Berlin, Germany") is False

    def test_montreal_no_al(self):
        """Montreal returns True because it matches Canada indicators, not because of the 'al' false positive string matcher."""
        assert is_valid_location("Montreal") is True  # Montreal matches Canada indicators

    def test_london_england_rejected(self):
        """Ambiguous city name should not auto-match Canada without Canadian context."""
        assert is_valid_location("London, England") is False

    def test_london_ontario_accepted(self):
        assert is_valid_location("London, Ontario") is True

    def test_paris_france(self):
        assert is_valid_location("Paris, France") is False

    def test_tokyo_japan(self):
        assert is_valid_location("Tokyo, Japan") is False

    def test_beijing_china(self):
        """'in' should NOT match 'Beijing'."""
        assert is_valid_location("Beijing, China") is False

    def test_rome_italy(self):
        """'me' should NOT match inside 'Rome'."""
        assert is_valid_location("Rome, Italy") is False

    def test_shanghai_china(self):
        """'hi' should NOT match inside 'Shanghai'."""
        assert is_valid_location("Shanghai, China") is False

    def test_aarhus_denmark(self):
        """'us' should NOT match inside 'Aarhus'."""
        assert is_valid_location("Aarhus, Denmark") is False

    def test_singapore(self):
        assert is_valid_location("Singapore") is False

    def test_sydney_australia(self):
        assert is_valid_location("Sydney, Australia") is False


class TestValidLocationEdgeCases:
    """Edge cases."""

    def test_empty_string(self):
        assert is_valid_location("") is False

    def test_none(self):
        assert is_valid_location(None) is False

    def test_whitespace_only(self):
        assert is_valid_location("   ") is False

    def test_comma_separated_state_code(self):
        """'San Jose, CA' — 'ca' is 2 chars, should match via word boundary."""
        assert is_valid_location("San Jose, CA") is True

    def test_or_abbreviation(self):
        """'OR' (Oregon) should match when it's a standalone word."""
        assert is_valid_location("Portland, OR") is True

    def test_or_in_word(self):
        """'or' inside a word like 'Lahore' should NOT match Oregon."""
        assert is_valid_location("Lahore, Pakistan") is False

    def test_unicode_foreign_city(self):
        assert is_valid_location("München, Germany") is False

    def test_mixed_case_state_abbreviation(self):
        assert is_valid_location("Indianapolis, iN") is True

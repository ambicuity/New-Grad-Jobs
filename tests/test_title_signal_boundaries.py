"""Token-boundary behaviour of the title signals (audit bug fixes).

The new-grad filter stays deliberately broad (owner decision): an unlevelled
"Software Engineer" keeps passing. These tests pin the *bug fixes* only:

* level signals (I, II, L3, ...) match as level tokens, not any stray "I";
* track signals match whole words ("ai" no longer matches "Maintenance");
* strong signals / cohort years match whole tokens, not req-id substrings;
* level III+ titles are excluded while level II keeps passing.

Examples are real titles taken from the published board (Sep 2026 audit).
"""

import os
from typing import Any

import pytest
import yaml

from ngj.filters import (
    DEFAULT_STRONG_NEW_GRAD_SIGNALS,
    filter_jobs,
    find_padded_signals,
    has_excluded_level,
    has_new_grad_signal,
    has_strong_new_grad_signal,
    has_track_signal,
)

LEVEL_SIGNALS = ["I", "II", "L3", "L4", "E3", "E4"]
POSTED_AT = "2026-08-12T12:00:00"


def _live_filtering() -> dict[str, Any]:
    root = os.path.join(os.path.dirname(__file__), '..')
    with open(os.path.join(root, 'config.yml'), encoding='utf-8') as f:
        return yaml.safe_load(f)['filtering']


def _live_config() -> dict[str, Any]:
    """The shipped config with recency widened so fixed dates never age out."""
    return {'filtering': {**_live_filtering(), 'max_age_days': 36500}}


def _passes(title: str, location: str = "Seattle, WA") -> bool:
    job = {'title': title, 'location': location, 'posted_at': POSTED_AT, 'company': 'Acme'}
    return len(filter_jobs([job], _live_config())) == 1


class TestLevelTokenSignals:
    """(a) ' I ' used to become \\bi\\b and matched any standalone "I"."""

    @pytest.mark.parametrize("title", [
        "Engineer I",
        "Software Engineer I - Payments",
        "Quality Engineer I",
        "Hardware Engineer I",
        "Engineer I, Quality",
        "Software Technologist I/II",
        "Software Technologist I / II",
        "RESEARCH ENGINEER (II) (ENG-ECE)",
        "Software Dev Engineer-II, Infra Supply Chain Automation",
        "Platform Engineer II",
        "Software Development Engineer (L3)",
        "Software Engineer, L4",
        "Software Engineer E3",
        "SDE I",
        "SWE II - Backend",
    ])
    def test_level_tokens_match(self, title):
        assert has_new_grad_signal(title, LEVEL_SIGNALS) is True

    @pytest.mark.parametrize("title", [
        "Alvin I. Goodman Chair, Nephrology",  # middle initial
        "Storage Engineer, I/O Performance",  # I/O is not a level
        "QA Engineer - Networking L2/L3 Testing | 4 - 8 yrs",  # OSI layer
        "L3Harris Mission Systems Analyst",  # company name
        "Software Engineer III",  # III is not I
    ])
    def test_non_level_i_does_not_match(self, title):
        assert has_new_grad_signal(title, LEVEL_SIGNALS) is False

    def test_padded_legacy_signals_behave_like_level_tokens(self):
        """Old configs spelled levels as ' I ' / ' L3'; they must not regress."""
        legacy = [" I ", " II ", " L3", " SDE I"]
        assert has_new_grad_signal("Engineer I", legacy) is True
        assert has_new_grad_signal("Alvin I. Goodman Chair", legacy) is False
        assert has_new_grad_signal("SDE I", legacy) is True

    def test_level_phrases_respect_boundaries(self):
        assert has_new_grad_signal("Engineer Level I", ["level i"]) is True
        assert has_new_grad_signal("Engineer Level III", ["level i"]) is False
        assert has_new_grad_signal("Engineer Level 10", ["level 1"]) is False


class TestTrackSignalWordBoundaries:
    """(b) 'ai' matched Maintenance/Retail/Trainee/Chair; 'ml' matched HTML."""

    SIGNALS = ["ai", "ml", "data", "engineer", "software", "developer", "platform"]

    @pytest.mark.parametrize("title", [
        "Facility Maintenance Technician I",
        "Retail Associate",
        "Trainee Pharmacist",
        "Canada Research Chair (Tier II) in Functional Tissue Biomechanics",
        "Sales Representative II, Pain Interventions",
        "HTML Email Specialist",
    ])
    def test_substrings_inside_words_do_not_match(self, title):
        assert has_track_signal(title, self.SIGNALS) is False

    @pytest.mark.parametrize("title", [
        "AI/ML Engineer",
        "ML-Ops Associate",
        "Applied AI Associate, New Grad",
        "Associate (ML Platform)",
        "Engineering Program 2026",  # 'engineer' inflection
        "Software Developers Program",  # plural
        "Data Platforms Associate",
    ])
    def test_whole_words_and_inflections_match(self, title):
        assert has_track_signal(title, self.SIGNALS) is True

    def test_live_track_signals_reject_maintenance_title(self):
        assert has_track_signal("Facility Maintenance Technician I", _live_filtering()['track_signals']) is False


class TestStrongNewGradSignals:
    """(c) strong signals were raw substrings; bare years matched inside req ids."""

    def test_config_defines_strong_signals(self):
        signals = _live_filtering()['strong_new_grad_signals']
        assert set(signals) == set(DEFAULT_STRONG_NEW_GRAD_SIGNALS)

    def test_default_used_when_config_missing(self):
        assert has_strong_new_grad_signal("New Grad Program", None) is True

    @pytest.mark.parametrize("title", [
        "Technology Cohort 2027",
        "Associate (2026 Start)",
        "Engineer - 2025-2026 Graduate",
        "Campus Hire - Technology",
        "Early Career Program",
        "Test Engineer, New College Graduate,",  # used to match only as a substring
        "University Graduate - Platform",
    ])
    def test_strong_tokens_match(self, title):
        assert has_strong_new_grad_signal(title, DEFAULT_STRONG_NEW_GRAD_SIGNALS) is True

    @pytest.mark.parametrize("title", [
        "Associate Analyst R20251234",  # year inside a req id
        "Associate JR-2026-0042",  # hyphenated req id
        "Associate #2027",
        "Campusano Associate",  # substring of a word
        "Unicampus Associate",
    ])
    def test_substrings_do_not_match(self, title):
        assert has_strong_new_grad_signal(title, DEFAULT_STRONG_NEW_GRAD_SIGNALS) is False


class TestExcludedLevels:
    """(d) Level III+ titles passed because 'software engineer' is a signal."""

    @pytest.mark.parametrize("title", [
        "Software Engineer III",
        "Data Engineer IV",
        "Software Engineer V - Platform",
        "Engineer 3",
        "Software Engineer 4, Payments",
        "Software Engineer Level 4",
        "Software Engineer, L5",
        "Software Engineer (E5)",
        "SDE III",
    ])
    def test_senior_levels_are_detected(self, title):
        assert has_excluded_level(title) is True

    @pytest.mark.parametrize("title", [
        "Software Engineer",
        "Software Engineer I",
        "Software Engineer II",
        "Engineer 2",
        "Software Engineer, L3",
        "Software Engineer II/III",  # hiring at II counts
        "3D Graphics Software Engineer",
        "Software Engineer 3D Rendering",
        "Software Engineer, Level 2",
        "Software Engineer 2026",
        "Software Engineer - Web3",
        "Vitamin V Associate",
    ])
    def test_entry_levels_are_not_detected(self, title):
        assert has_excluded_level(title) is False

    @pytest.mark.parametrize("title", [
        "Software Engineer III",
        "Data Engineer IV",
        "Engineer 3",
        "Software Engineer, L5",
    ])
    def test_filter_drops_senior_levels(self, title):
        assert _passes(title) is False

    @pytest.mark.parametrize("title", [
        "Software Engineer",  # owner decision: generic titles stay
        "Software Engineer II",
        "Platform Engineer II",
        "Data Scientist",
        "Engineer I, Quality",
    ])
    def test_filter_keeps_broad_and_level_ii_titles(self, title):
        assert _passes(title) is True


class TestFilterEndToEndAuditTitles:
    """Published titles that only passed through the substring bugs."""

    @pytest.mark.parametrize("title", [
        "Alvin I. Goodman Chair, Nephrology",
        "Facility Maintenance Technician I",
        "Canada Research Chair (Tier II) in Functional Tissue Biomechanics",
        "QA Engineer - Networking L2/L3 Testing | 4 - 8 yrs",
    ])
    def test_dropped(self, title):
        assert _passes(title) is False

    @pytest.mark.parametrize("title", [
        "Software Development Engineer (L3)",
        "Applied Machine Learning Scientist I",
        "AI and Machine Learning Engineer I Graduate",
        "Research Engineer Graduate (Monetization Technology) - 2027 Start",
        "Analytics Engineer II, Full Stack (Revenue Analytics)",
        # The board covers every profession: a level-II sales role is in scope.
        "Sales Representative II, Pain Interventions- Pittsburgh/Washington, PA",
    ])
    def test_kept(self, title):
        assert _passes(title) is True


class TestSignalConfigHygiene:
    """(6) Leading/trailing spaces used to be stripped silently."""

    def test_find_padded_signals_reports_offenders(self):
        filtering = {'new_grad_signals': ['new grad', ' I ', ' L3'], 'track_signals': ['ai ']}
        assert find_padded_signals(filtering) == {
            'new_grad_signals': [' I ', ' L3'],
            'track_signals': ['ai '],
        }

    def test_shipped_config_has_no_padded_signals(self):
        assert find_padded_signals(_live_filtering()) == {}

    def test_shipped_config_lists_level_signals_as_tokens(self):
        levels = _live_filtering()['level_signals']
        assert {'I', 'II', 'L3', 'L4', 'E3', 'E4'} <= set(levels)

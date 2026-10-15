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


class TestJuniorAbbreviationAndAdministratorTrack:
    """Live postings (Oct 2026) dropped because "Jr." was not read as junior
    and "Administrator" was not a track word."""

    @pytest.mark.parametrize("title", [
        "Jr. Systems Administrator",
        "Jr. Front-End Developer (Korean Bilingual)",
        "Jr Data Analyst",
        "Junior SQL Database Administrator",
    ])
    def test_kept(self, title):
        assert _passes(title) is True

    @pytest.mark.parametrize("title", [
        "Sr. Systems Administrator",
        "Systems Administrator",
        "Office Administrator",
        # "JR" also prefixes Workday req ids; those are not a junior signal.
        "Platform Engineer JR-2026-0042",
        "Data Analyst (JR-000934)",
        "Quality Engineer - JR 1234",
    ])
    def test_dropped(self, title):
        assert _passes(title) is False


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


class TestPartTimeAndSeasonalExcluded:
    """Part-time and seasonal store roles are not new-grad careers (owner
    decision, Oct 2026). Full-time entry-level sales and operations stay in."""

    @pytest.mark.parametrize("title", [
        "Seasonal Sales Associate (Part-Time) - SoHo",
        "Seasonal Operations Associate (Part-Time) - Park Meadows Mall",
        "Part Time Retail Sales Associate",
        "Seasonal Associate Accountant",
    ])
    def test_dropped(self, title):
        assert _passes(title) is False

    @pytest.mark.parametrize("title", [
        "Retail Sales Associate",
        "Operations Associate (Full-Time) - Cherry Creek",
        "Associate Data Analyst (Time Series)",
        "Seasonality Analyst I",
    ])
    def test_kept(self, title):
        assert _passes(title) is True


class TestTemporaryContractAndFractionalFteExcluded:
    """Temporary, fixed-term and contract postings, and fractional-FTE (part-time)
    roles are not new-grad careers (owner decision, 2026-10-15). Titles about
    contracts as a subject ("Contracts Administrator") are full-time roles and stay."""

    @pytest.mark.parametrize("title", [
        "Retail Sales Associate Temp",
        "Clinical Lab Operator I-Temp",
        "Software Engineer II Temp to Hire",
        "Flight Software Engineer I (Temp-to-hire)",
        "Temporary Sales Associate",
        "Junior Accountant (12 Month Temporary Assignment)",
        "Temporary Early Career Electrical Engineer",
        "Associate Field Service Engineer (Fixed Term – 12-month assignment)",
        "Business Analyst, Marketing-1 (Fixed Term)",
        "Customer Experience Associate (3 Month Fixed-Term Contract)",
        "Associate Operations Software Engineer - Operations ( Contract to hire )",
        "Biotech Analyst - Level 1 (Cell Biology) - 12 Month Contract",
        "Clinical Research Assistant II (Contract) - On Call - 6-8 weeks",
        "Junior Recruiter (6-Month Contract)",
        "Associate Regulatory Affairs Specialist - 18 months contract",
        "Associate Product Designer / 6-month contract",
        "Junior Marketing Consultant - Contract (Hybrid)",
        "Revenue Operations Associate -Gurugram (Contractual)",
        "Data Engineer - Flight Data (contract)",
        "Junior Software Engineer (Contractor)",
        "Associate Engineer, Contract",
        "Associate Engineer | Contract",
        "Data Analyst I (Contract Position)",
        "Data Analyst I ( Contract )",
        "Associate Data Analyst 0.9 FTE",
        "Nursing Care Assistant I (CNA) General Medicine Dialysis .3FTE",
        "Associate Data Analyst 0.5 FTE",
    ])
    def test_dropped(self, title):
        assert _passes(title) is False

    @pytest.mark.parametrize("title", [
        "Contract Specialist II",
        "Associate Contracts Administrator",
        "Subcontracts Administrator Associate",
        "Junior Paralegal, Contracts",
        "Associate Business Contracts Officer",
        "Paralegal/Contracts Associate",
        "Leadership Development Program - Contracts (June 2027)",
        "CAD Drafter II – Ground Support Equipment",
        "Nursing Care Assistant I (CNA) 1.0 FTE",
        "Software Engineer I, Temperature Systems",
        "Associate - Contract Administrator",
        "Data Analyst I - Contract Compliance",
        "Contractor Compliance Associate",
        "Contractual Compliance Associate",
        "Contractor Management Analyst I",
        "Software Engineer I, Temporal Platform",
        "Software Engineer I, Template Systems",
        "Data Analyst I (1.5 FTE)",
        "Associate Data Analyst (Time Series)",
    ])
    def test_kept(self, title):
        assert _passes(title) is True


class TestPassesTitleRules:
    """passes_title_rules is classify_job's title-only hard gate (shared with adapters
    that must decide, before fetching details, whether a posting can be listed)."""

    @pytest.mark.parametrize("title", [
        "Software Engineer I", "Associate Data Scientist I", "Jr. Systems Administrator",
        "Software Engineering Intern", "Senior Software Engineer", "Account Executive",
        "Systems Administrator", "Seasonal Sales Associate (Part-Time)", "Data Analyst", "",
    ])
    def test_agrees_with_classify_job_on_the_title(self, title):
        from ngj.filters import classify_job, passes_title_rules

        config = _live_config()
        job = {"title": title, "location": "Seattle, WA", "posted_at": POSTED_AT, "company": "Acme"}
        verdict = classify_job(job, config)
        assert passes_title_rules(title, config["filtering"]) is (verdict.kept or verdict.near_miss)

    def test_internships_pass_so_near_misses_survive(self):
        from ngj.filters import passes_title_rules

        assert passes_title_rules("Software Engineering Intern", _live_filtering()) is True


class TestUnicodeDashesInTitles:
    """Titles from Oracle HCM and Workday boards use Unicode dashes ("Co‑Op" with
    U+2011). Signals are written with an ASCII hyphen, so a co-op or part-time
    title with another dash must still be recognised (Oct 2026)."""

    @pytest.mark.parametrize("dash", ["‐", "‑", "‒", "–", "—", "−"])
    def test_coop_with_any_dash_is_not_curated(self, dash):
        from ngj.filters import classify_job

        title = f"Controls & Automation Engineering Co{dash}Op – Latham, NY - Summer 2027"
        job = {"title": title, "location": "Latham, NY", "posted_at": POSTED_AT, "company": "Acme"}
        verdict = classify_job(job, _live_config())
        assert verdict.kept is False and verdict.reasons == ("intern_or_coop",)

    def test_part_time_with_a_non_breaking_hyphen_is_dropped(self):
        assert _passes("Retail Sales Associate (Part‑Time)") is False

    def test_an_en_dash_separator_still_passes(self):
        assert _passes("Associate Software Engineer – Platform") is True


class TestSeniorAssociateTitles:
    """"Associate" is a new-grad signal, but in law and academia "Associate General
    Counsel", "Associate Dean" and "Associate Professor" are senior roles (Oct 2026)."""

    @pytest.mark.parametrize("title", [
        "Associate General Counsel, Product - Development",
        "Government Contracts Associate General Counsel",
        "Deputy General Counsel",
        "Associate Dean Graduate & International Law Programs - Law Office of the Dean",
        "Assistant Dean for Student Affairs",
        "Assistant or Associate Professor - Software Engineering",
        "Associate Professor of Data Science",
    ])
    def test_dropped(self, title):
        assert _passes(title) is False

    @pytest.mark.parametrize("title", [
        "Associate Counsel, Legal",
        "Associate Software Engineer",
        "Associate Data Analyst - Professor Smith Lab",
        "Dean's Office Program Associate",
    ])
    def test_kept(self, title):
        assert _passes(title) is True


class TestSpacedCoopAndManagerAbbreviation:
    """Seen on SuccessFactors boards (Oct 2026): "Co - Op" with spaced hyphen is a
    co-op, and "Mgr" is a manager."""

    def test_spaced_coop_is_a_near_miss_not_curated(self):
        from ngj.filters import classify_job

        job = {"title": "Co - Op Fall 2026 - Cheraw 2", "location": "Cheraw, SC", "posted_at": POSTED_AT,
               "company": "Acme"}
        assert classify_job(job, _live_config()).reasons == ("intern_or_coop",)

    @pytest.mark.parametrize("title", ["MGR, OPERATIONS II", "Associate; Treasury Product Sales Mgr",
                                       "Engineering Mgr. I"])
    def test_mgr_is_excluded(self, title):
        assert _passes(title) is False

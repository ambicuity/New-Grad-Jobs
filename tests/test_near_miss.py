#!/usr/bin/env python3
"""The near-miss tier: postings that pass every hard rule but fail one or more
soft rules (internship/co-op, level III+, outside US/CA/IN, older than the
curated window). They are published separately in jobs-extended.json with the
reasons attached, so the site can offer opt-in toggles without ever mixing
them into the curated set or its counts.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from ngj.filters import (
    DEFAULT_INTERNSHIP_SIGNALS,
    NEAR_MISS_REASONS,
    classify_job,
    filter_jobs,
    partition_jobs,
)
from ngj.outputs.jobs_json import generate_extended_json
from quality import check_extended

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)


def _job(title, *, days_old=1, location="Austin, TX", url="https://example.com/j/1"):
    return {
        "title": title, "company": "Acme", "location": location, "url": url,
        "posted_at": (NOW - timedelta(days=days_old)).isoformat(), "source": "Greenhouse", "description": "",
    }


def _config():
    return {
        "filtering": {
            "max_age_days": 60,
            "near_miss_max_age_days": 120,
            "new_grad_signals": ["new grad", "junior", "associate", "2027", "software engineer"],
            "strong_new_grad_signals": ["new grad", "2027"],
            "exclusion_signals": ["senior", "staff", "manager", "5+ years"],
            "internship_signals": list(DEFAULT_INTERNSHIP_SIGNALS),
            "track_signals": ["software", "engineer", "marketing", "data"],
        }
    }


class TestClassifyJob:
    def test_curated_when_every_rule_passes(self):
        verdict = classify_job(_job("Software Engineer, New Grad"), _config(), now=NOW)
        assert verdict.kept is True and verdict.near_miss is False and verdict.reasons == ()

    @pytest.mark.parametrize(
        ("title", "reason"),
        [
            ("Software Engineering Intern (Summer 2027)", "intern_or_coop"),
            ("Marketing Co-op - Spring 2027", "intern_or_coop"),
            ("2027 Investment Banking Summer Analyst", "intern_or_coop"),
            ("Software Engineer III - New Grad Team", "level_iii_plus"),
        ],
    )
    def test_soft_title_rules_make_a_near_miss(self, title, reason):
        verdict = classify_job(_job(title), _config(), now=NOW)
        assert verdict.kept is False and verdict.near_miss is True
        assert verdict.reasons == (reason,)

    def test_outside_target_countries_is_soft(self):
        verdict = classify_job(_job("Junior Software Engineer", location="Berlin, Germany"), _config(), now=NOW)
        assert verdict.near_miss is True and verdict.reasons == ("outside_target_countries",)

    def test_recency_is_soft_up_to_the_near_miss_window_then_hard(self):
        assert classify_job(_job("Junior Software Engineer", days_old=59), _config(), now=NOW).kept is True
        older = classify_job(_job("Junior Software Engineer", days_old=90), _config(), now=NOW)
        assert older.near_miss is True and older.reasons == ("older_than_max_age",)
        ancient = classify_job(_job("Junior Software Engineer", days_old=200), _config(), now=NOW)
        assert ancient.kept is False and ancient.near_miss is False

    def test_several_soft_failures_are_all_recorded(self):
        verdict = classify_job(_job("Software Engineering Intern 2027", days_old=90, location="Berlin, Germany"), _config(), now=NOW)
        assert verdict.reasons == ("intern_or_coop", "outside_target_countries", "older_than_max_age")
        assert set(verdict.reasons) <= set(NEAR_MISS_REASONS)

    @pytest.mark.parametrize(
        "title",
        [
            "Senior Software Engineer",          # hard exclusion word
            "Software Engineering Manager",      # hard exclusion word
            "Intern",                            # internship with no role word
            "Associate",                         # new-grad word with no role word
            "Photographer",                      # no new-grad signal at all
            "Staff Software Engineer Intern",    # hard exclusion wins over the soft internship rule
        ],
    )
    def test_hard_failures_are_neither_curated_nor_near_miss(self, title):
        verdict = classify_job(_job(title), _config(), now=NOW)
        assert verdict.kept is False and verdict.near_miss is False

    def test_internship_counts_as_the_early_career_signal(self):
        # "Intern" is not in new_grad_signals; the internship rule supplies it, the track word "marketing" completes it.
        verdict = classify_job(_job("Marketing Intern"), _config(), now=NOW)
        assert verdict.near_miss is True and verdict.reasons == ("intern_or_coop",)


class TestPartitionJobs:
    def test_partition_returns_curated_and_tagged_near_misses_without_mutating_input(self):
        jobs = [
            _job("Software Engineer, New Grad", url="https://example.com/1"),
            _job("Software Engineering Intern 2027", url="https://example.com/2"),
            _job("Senior Software Engineer", url="https://example.com/3"),
        ]
        snapshot = json.dumps(jobs, sort_keys=True)

        curated, near = partition_jobs(jobs, _config(), now=NOW)

        assert [j["url"] for j in curated] == ["https://example.com/1"]
        assert [j["url"] for j in near] == ["https://example.com/2"]
        assert near[0]["near_miss"] == {"reasons": ["intern_or_coop"]}
        assert "near_miss" not in curated[0]
        assert json.dumps(jobs, sort_keys=True) == snapshot

    def test_filter_jobs_is_the_curated_half(self):
        jobs = [_job("Software Engineer, New Grad"), _job("Software Engineering Intern 2027")]
        assert [j["title"] for j in filter_jobs(jobs, _config())] == ["Software Engineer, New Grad"]

    def test_near_misses_are_capped_newest_first(self):
        config = _config()
        config["filtering"]["max_near_misses"] = 2
        jobs = [_job(f"Software Engineering Intern {i} 2027", days_old=i, url=f"https://example.com/{i}") for i in (5, 1, 3)]
        _, near = partition_jobs(jobs, config, now=NOW)
        assert [j["url"] for j in near] == ["https://example.com/1", "https://example.com/3"]

    def test_defaults_apply_without_the_new_config_keys(self):
        config = {"filtering": {"max_age_days": 60, "new_grad_signals": ["junior"], "track_signals": ["software"],
                                "exclusion_signals": ["senior", "intern"]}}
        # With "intern" still in exclusion_signals (old config), an intern is a hard failure, not a near miss.
        curated, near = partition_jobs([_job("Junior Software Intern")], config, now=NOW)
        assert curated == [] and near == []


class TestExtendedJson:
    def _payload(self):
        jobs = [_job("Software Engineering Intern 2027", url="https://example.com/2"),
                _job("Software Engineer III", days_old=90, url="https://example.com/3")]
        _, near = partition_jobs(jobs, _config(), now=NOW)
        for j in near:
            j.update(category={"id": "software_engineering", "name": "Software Engineering", "emoji": "x"},
                     company_tier={"tier": "other"}, flags={"no_sponsorship": False, "us_citizenship_required": False},
                     is_closed=False)
        return generate_extended_json(near, now=NOW)

    def test_meta_and_jobs(self):
        payload = self._payload()
        assert payload["meta"]["tier"] == "near_miss"
        assert payload["meta"]["total_jobs"] == 2
        assert payload["meta"]["reasons"] == {"intern_or_coop": 1, "level_iii_plus": 1, "older_than_max_age": 1,
                                              "outside_target_countries": 0}
        job = payload["jobs"][0]
        assert job["job_id"].startswith("job_") and job["id"] == job["job_id"]
        assert job["near_miss"]["reasons"] in (["intern_or_coop"], ["level_iii_plus", "older_than_max_age"])
        assert "description" not in job, "near misses never ship descriptions (first load stays small)"
        assert {"company", "title", "location", "url", "posted_at", "first_seen", "source", "category",
                "company_tier", "flags", "is_closed", "comp"} <= set(job)

    def test_check_extended_accepts_a_clean_payload_and_rejects_overlap(self, tmp_path):
        payload = self._payload()
        path = tmp_path / "jobs-extended.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        assert check_extended(path, curated_jobs=[]) == []

        overlap = [{"job_id": payload["jobs"][0]["job_id"]}]
        assert any("overlap" in e for e in check_extended(path, curated_jobs=overlap))

        payload["jobs"][0]["near_miss"] = {"reasons": ["made_up"]}
        path.write_text(json.dumps(payload), encoding="utf-8")
        assert any("unknown near-miss reason" in e for e in check_extended(path, curated_jobs=[]))

    def test_check_extended_missing_file_is_not_an_error(self, tmp_path):
        assert check_extended(tmp_path / "jobs-extended.json", curated_jobs=[]) == []

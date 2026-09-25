#!/usr/bin/env python3
"""Export a parity fixture for the site's JavaScript port of the signal matcher.

site/src/lib/signals.js mirrors ngj.filters (_signal_pattern, the track
suffix, the exclusion compiler). This script evaluates the Python
implementation over a fixed set of signals and titles and writes the results
to site/test/fixtures/signal-parity.json; vitest then asserts the port gives
the same answers, and tests/test_signal_parity.py asserts the committed
fixture is current. Run it after changing either side::

    python scripts/export_signal_parity.py
"""

from __future__ import annotations

import json
import pathlib
import sys

from ngj.filters import has_new_grad_signal, has_track_signal, is_title_excluded

FIXTURE_PATH = pathlib.Path(__file__).resolve().parent.parent / "site" / "test" / "fixtures" / "signal-parity.json"

SIGNALS = [
    "new grad", "new graduate", "campus", "early career", "junior", "associate", "2026", "2027",
    "I", "II", "L3", "L4", "sde ii", "level 1", "software engineer", "engineer", "developer",
    "data", "ml", "ai", "c++", "rust", "go", ".net", "node.js", "quant", "0-2 years", "ux/ui",
    "机器学习", "café",
]
EXCLUSIONS = [
    "senior", "sr.", "sr", "staff", "principal", "lead", "manager", "director", "vp", "head of",
    "architect", "10+ years", "5+ years", "intern", "internship", "co-op", "co op", "coop", "student",
    "summer analyst",
]
TITLES = [
    "Software Engineer, New Grad", "Software Engineer II", "Software Engineer III", "Software Engineer I/II",
    "SDE II - Payments", "Engineer (L3)", "Engineer L3Harris", "Alvin I. Goodman Chair", "I/O Engineer",
    "Software Engineer - 2026 Start", "Req JR-2026-0042 Engineer", "Engineer #2026", "R20261234 Analyst",
    "Machine Learning Engineer", "ML-Ops Engineer", "HTML Email Specialist", "Maintenance Planner",
    "AI Engineer", "Data Engineers", "Developers Advocate", "Engineering Manager", "Senior Software Engineer",
    "Sr. Engineer", "Sr Engineer", "Team Leads - Platform", "Tech Lead", "Head of Platform", "VP of Engineering",
    "Software Engineer (10+ years)", "Backend Engineer, 5+ years experience", "Software Engineer Intern",
    "Software Engineering Internship", "Interns - Data Science 2027", "Software Engineer - Intern/Co-op",
    "Software Engineer (Co op)", "Registered Nursing Student", "2027 Investment Banking Summer Analyst",
    "Software Engineer, Internal Tools - New Grad", "Associate Product Manager", "C++ Developer", "Go Developer",
    "Golang Developer", "Rust Engineer", "Trustworthy AI Lead", ".NET Developer", "Node.js Developer",
    "Quantitative Trader", "Quant Researcher", "UX/UI Designer", "Level 10 Engineer", "Level 1 Support",
    "0-2 years experience Analyst", "机器学习工程师", "Café Manager", "Ingénieur logiciel junior",
    "Campus Recruiter", "Early-Career Engineer", "Junior Développeur", "Software Engineer (New Graduate)",
]


def build_fixture() -> dict[str, object]:
    return {
        "signals": SIGNALS,
        "exclusions": EXCLUSIONS,
        "titles": TITLES,
        "new_grad": [[has_new_grad_signal(t, [s]) for s in SIGNALS] for t in TITLES],
        "track": [[has_track_signal(t, [s]) for s in SIGNALS] for t in TITLES],
        "excluded": [[is_title_excluded(t, [e]) for e in EXCLUSIONS] for t in TITLES],
    }


def main() -> int:
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(build_fixture(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {FIXTURE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

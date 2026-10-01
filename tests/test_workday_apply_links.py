#!/usr/bin/env python3
"""Workday apply links include the careers site; job_ids stay what they were before the fix."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from contracts import compute_job_id  # noqa: E402
from ngj.sources.workday import _to_job  # noqa: E402

ITEM = {"title": "DevOps Engineer", "externalPath": "/job/Quantico-VA/DevOps-Engineer_R0245224",
        "locationsText": "Quantico, VA", "postedOn": "Posted Today"}


def test_apply_url_keeps_the_careers_site_segment():
    job = _to_job("Booz Allen Hamilton", "https://bah.wd1.myworkdayjobs.com/BAH_Jobs", ITEM)
    assert job["url"] == "https://bah.wd1.myworkdayjobs.com/BAH_Jobs/job/Quantico-VA/DevOps-Engineer_R0245224"


def test_apply_url_keeps_a_locale_prefixed_site():
    job = _to_job("Acme", "https://acme.wd5.myworkdayjobs.com/en-US/External", ITEM)
    assert job["url"] == "https://acme.wd5.myworkdayjobs.com/en-US/External/job/Quantico-VA/DevOps-Engineer_R0245224"


def test_job_id_is_unchanged_by_the_site_segment():
    fixed = {"source": "Workday", "url": "https://bah.wd1.myworkdayjobs.com/BAH_Jobs/job/Quantico-VA/DevOps-Engineer_R0245224"}
    legacy = {"source": "Workday", "url": "https://bah.wd1.myworkdayjobs.com/job/Quantico-VA/DevOps-Engineer_R0245224"}
    assert compute_job_id(fixed) == compute_job_id(legacy)


def test_non_workday_identity_still_uses_the_full_path():
    a = {"source": "Greenhouse", "url": "https://boards.greenhouse.io/acme/job/1"}
    b = {"source": "Greenhouse", "url": "https://boards.greenhouse.io/job/1"}
    assert compute_job_id(a) != compute_job_id(b)

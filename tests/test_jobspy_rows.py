"""JobSpy rows are normalised at the boundary: NaN never reaches the filters."""

import math
import os
import sys
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ngj.enrich import enrich_jobs  # noqa: E402
from ngj.filters import filter_jobs  # noqa: E402
from ngj.sources.jobspy import _row_to_job, fetch_jobspy_jobs, is_missing, normalize_row  # noqa: E402

NAN = float("nan")


def _row(**overrides):
    base = {
        "title": "Software Engineer, New Grad",
        "company": "Acme",
        "location": "Austin, TX, US",
        "job_url": "https://www.indeed.com/viewjob?jk=1",
        "date_posted": "2026-09-20",
        "description": "Build things.",
        "min_amount": NAN,
        "max_amount": NAN,
        "currency": NAN,
        "interval": NAN,
    }
    base.update(overrides)
    return pd.Series(base)


@pytest.mark.parametrize("value", [None, NAN, pd.NA, pd.NaT, float("nan")])
def test_is_missing_recognises_pandas_missing_markers(value):
    assert is_missing(value)


@pytest.mark.parametrize("value", ["", "x", 0, 0.0, 1.5])
def test_is_missing_keeps_real_values(value):
    assert not is_missing(value)


def test_normalize_row_replaces_every_missing_marker_with_none():
    row = normalize_row(_row(description=NAN, company=pd.NA, date_posted=pd.NaT))
    assert row["description"] is None
    assert row["company"] is None
    assert row["date_posted"] is None
    assert row["title"] == "Software Engineer, New Grad"


def test_nan_description_becomes_empty_string_not_nan():
    job = _row_to_job(_row(description=NAN), "indeed")
    assert job["description_html"] == ""
    assert job["description"] == ""


def test_nan_title_row_is_dropped():
    assert _row_to_job(_row(title=NAN), "indeed") is None
    assert _row_to_job(_row(title="nan"), "indeed") is None
    assert _row_to_job(_row(title="   "), "indeed") is None


def test_missing_location_is_unknown_and_missing_company_is_unknown_label():
    job = _row_to_job(_row(location=NAN, company=NAN), "indeed")
    assert job["location"] == ""
    assert job["company"] == "Unknown"


def test_missing_date_is_empty_string():
    assert _row_to_job(_row(date_posted=pd.NaT), "indeed")["posted_at"] == ""


def test_no_float_nan_anywhere_in_a_job_built_from_an_all_nan_row():
    all_nan = _row(company=NAN, location=NAN, job_url=NAN, date_posted=NAN, description=NAN)
    job = _row_to_job(all_nan, "indeed")
    assert not any(isinstance(v, float) and math.isnan(v) for v in job.values())


def test_fetch_drops_nan_rows_before_filters_and_counts_raw_rows():
    df = pd.DataFrame([
        dict(_row()),
        dict(_row(title=NAN, job_url="https://www.indeed.com/viewjob?jk=2")),
        dict(_row(job_url=NAN)),
    ])
    with patch("ngj.sources.jobspy.load_scrape_jobs", return_value=lambda **kw: df):
        result = fetch_jobspy_jobs({"enabled": True, "sites": ["indeed"], "search_terms": ["x"],
                                    "countries": [{"code": "USA", "location": "United States"}]})
    assert result.raw_count == 3
    assert [job["url"] for job in result.jobs] == ["https://www.indeed.com/viewjob?jk=1"]
    # And the survivors are safe to filter/enrich.
    config = {"filtering": {"new_grad_signals": ["new grad"], "track_signals": ["software"], "max_age_days": 3650}}
    enrich_jobs(filter_jobs(list(result.jobs), config))


# ---------------------------------------------------------------------------
# Structured salary: currency + interval columns
# ---------------------------------------------------------------------------

def test_structured_yearly_usd_salary():
    job = _row_to_job(_row(min_amount=90000.0, max_amount=120000.0, currency="USD", interval="yearly"), "indeed")
    assert job["comp"] == {"min": 90000, "max": 120000, "currency": "USD", "source": "jobspy"}


def test_hourly_salary_is_annualised_not_read_as_yearly():
    job = _row_to_job(_row(min_amount=45.0, max_amount=55.0, currency="USD", interval="hourly"), "indeed")
    assert job["comp"] == {"min": 93600, "max": 114400, "currency": "USD", "source": "jobspy"}


def test_non_usd_salary_keeps_its_currency():
    job = _row_to_job(_row(location="Toronto, ON, CA", min_amount=80000.0, max_amount=95000.0,
                           currency="CAD", interval="yearly"), "indeed")
    assert job["comp"]["currency"] == "CAD"


def test_inr_monthly_salary():
    job = _row_to_job(_row(location="Bengaluru, KA, IN", min_amount=100000.0, max_amount=150000.0,
                           currency="INR", interval="monthly"), "indeed")
    assert job["comp"] == {"min": 1200000, "max": 1800000, "currency": "INR", "source": "jobspy"}


def test_missing_currency_is_inferred_from_location():
    job = _row_to_job(_row(location="Vancouver, BC, CA", min_amount=80000.0, max_amount=95000.0,
                           currency=NAN, interval="yearly"), "indeed")
    assert job["comp"]["currency"] == "CAD"


def test_nan_amounts_give_no_structured_comp_and_enrich_falls_back_to_regex():
    job = _row_to_job(_row(description="Pay: $100,000 - $130,000 per year"), "indeed")
    assert job["comp"] is None
    [enriched] = enrich_jobs([job])
    assert enriched["comp"] == {"min": 100000, "max": 130000, "currency": "USD", "source": "posting"}

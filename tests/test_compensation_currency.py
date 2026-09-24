"""Currency inference in ngj.compensation (a bare "$" is not always USD)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ngj.compensation import bounded_comp, dollar_currency_for_location, extract_compensation  # noqa: E402

RANGE = "The base salary range is $100,000 - $140,000."


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("", "USD"),
        (None, "USD"),
        ("Remote", "USD"),
        ("San Francisco, CA", "USD"),
        ("New York, NY", "USD"),
        ("Remote - United States", "USD"),
        ("Toronto, ON", "CAD"),
        ("Vancouver, BC", "CAD"),
        ("Montreal, Quebec, Canada", "CAD"),
        ("Waterloo", "CAD"),
        ("London, ON", "CAD"),
        ("Remote - Canada", "CAD"),
        ("Bengaluru, India", None),
        ("London, United Kingdom", None),
        ("Sydney, Australia", None),
        ("Toronto, ON; Seattle, WA", None),  # mixed US/Canada: ambiguous
    ],
)
def test_dollar_currency_for_location(location, expected):
    assert dollar_currency_for_location(location) == expected


def test_bare_dollar_in_us_posting_is_usd():
    comp = extract_compensation(RANGE, location="Austin, TX")
    assert comp == {"min": 100000, "max": 140000, "currency": "USD", "source": "posting"}


def test_bare_dollar_without_location_stays_usd_for_backward_compat():
    assert extract_compensation(RANGE)["currency"] == "USD"


def test_bare_dollar_in_canadian_posting_is_cad():
    assert extract_compensation(RANGE, location="Toronto, ON")["currency"] == "CAD"


def test_bare_dollar_in_other_non_us_posting_has_unknown_currency():
    comp = extract_compensation(RANGE, location="Singapore")
    assert comp is not None
    assert comp["currency"] is None
    assert (comp["min"], comp["max"]) == (100000, 140000)


def test_explicit_cad_marker_beats_us_location():
    assert extract_compensation("Salary: C$90,000 - C$110,000", location="Seattle, WA")["currency"] == "CAD"
    assert extract_compensation("Salary: CAD $90,000 - $110,000", location="Seattle, WA")["currency"] == "CAD"


def test_explicit_usd_marker_beats_canadian_location():
    assert extract_compensation("Pay: USD $90,000 - $110,000", location="Toronto, ON")["currency"] == "USD"
    assert extract_compensation("Pay: USD 90,000 to 110,000", location="Toronto, ON")["currency"] == "USD"


def test_pound_range_is_gbp():
    comp = extract_compensation("Salary £35,000 - £45,000 plus benefits", location="London, UK")
    assert comp == {"min": 35000, "max": 45000, "currency": "GBP", "source": "posting"}


def test_euro_range_is_eur():
    comp = extract_compensation("Gehalt: €50,000 – €60,000", location="Berlin, Germany")
    assert comp == {"min": 50000, "max": 60000, "currency": "EUR", "source": "posting"}


def test_rupee_lakh_grouping_range_is_inr():
    comp = extract_compensation("CTC ₹12,00,000 - ₹18,00,000 per annum", location="Bengaluru, India")
    assert comp == {"min": 1200000, "max": 1800000, "currency": "INR", "source": "posting"}


def test_lpa_range_is_inr():
    comp = extract_compensation("Compensation: 12 - 18 LPA", location="Hyderabad, India")
    assert comp == {"min": 1200000, "max": 1800000, "currency": "INR", "source": "posting"}


def test_inr_code_range():
    comp = extract_compensation("INR 1,200,000 to 1,800,000", location="Pune")
    assert comp is not None and comp["currency"] == "INR"


def test_single_annual_value_in_canada_is_cad():
    comp = extract_compensation("Base pay $95,000/year", location="Ottawa, ON")
    assert comp is not None and comp["currency"] == "CAD"


# ---------------------------------------------------------------------------
# bounded_comp: structured ATS / JobSpy values
# ---------------------------------------------------------------------------

def test_bounded_comp_keeps_usd_default():
    assert bounded_comp(100000, 150000, "ashby") == {"min": 100000, "max": 150000, "currency": "USD", "source": "ashby"}


def test_bounded_comp_uses_given_currency():
    assert bounded_comp(100000, 150000, "jobspy", currency="cad")["currency"] == "CAD"


def test_bounded_comp_annualises_hourly():
    comp = bounded_comp(40, 60, "jobspy", currency="USD", interval="hourly")
    assert comp == {"min": 83200, "max": 124800, "currency": "USD", "source": "jobspy"}


def test_bounded_comp_annualises_monthly_inr():
    comp = bounded_comp(100000, 150000, "jobspy", currency="INR", interval="monthly")
    assert comp == {"min": 1200000, "max": 1800000, "currency": "INR", "source": "jobspy"}


def test_bounded_comp_rejects_unknown_interval():
    assert bounded_comp(100000, 150000, "jobspy", interval="per-sprint") is None


def test_bounded_comp_rejects_hourly_value_treated_as_yearly():
    # 45/hour must not be accepted as a $45 yearly salary nor pass bounds un-annualised.
    assert bounded_comp(45, 60, "jobspy", currency="USD", interval="yearly") is None

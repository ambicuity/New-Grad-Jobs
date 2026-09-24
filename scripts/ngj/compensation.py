"""Salary extraction from free-text job descriptions and structured ATS fields.

Currency is never assumed blindly:

- ``USD 120,000`` / ``£`` / ``€`` / ``₹`` / ``INR`` / ``CAD`` / ``C$`` name it outright;
- a bare ``$`` is read through the job location — USD for US or unknown
  locations, CAD for Canadian ones, and ``None`` (unknown) for any other
  non-US location, where a dollar sign may be USD, AUD, SGD, ...
"""

from __future__ import annotations

import re
from typing import Any

from ngj.text import strip_html

# Sanity bounds shared by regex extraction and structured (Ashby/JobSpy) comp:
# they reject sign-on bonuses, valuations and stock prices. Annual amounts in
# the currency's own units.
COMP_MIN = 30_000
COMP_MAX = 600_000
COMP_MAX_SPREAD = 250_000

_BOUNDS: dict[str | None, tuple[int, int, int]] = {
    'USD': (COMP_MIN, COMP_MAX, COMP_MAX_SPREAD),
    'CAD': (COMP_MIN, COMP_MAX, COMP_MAX_SPREAD),
    'GBP': (18_000, 450_000, 200_000),
    'EUR': (18_000, 450_000, 200_000),
    # New-grad India offers are quoted in lakhs: 3 LPA .. 1.5 crore.
    'INR': (300_000, 15_000_000, 10_000_000),
}
# Unknown-currency dollars / other ISO codes: same magnitude as USD.
_DEFAULT_BOUNDS = (COMP_MIN, COMP_MAX, COMP_MAX_SPREAD)

# Multipliers that turn a per-interval amount into an annual one.
_ANNUAL_MULTIPLIER: dict[str, int] = {
    'yearly': 1, 'year': 1, 'annual': 1, 'annually': 1,
    'monthly': 12, 'month': 12,
    'weekly': 52, 'week': 52,
    'daily': 260, 'day': 260,
    'hourly': 2080, 'hour': 2080,
}

# Range patterns first (most specific), single-value patterns second.
# Connector covers: "-", "–", "—", "to", "and up to", "up to", "through".
_COMP_CONNECTOR = r'(?:-|–|—|to|and\s+up\s+to|through)'


def _money_range(symbol: str) -> re.Pattern[str]:
    """"<sym>120,000 - <sym>180,000" with optional .00 cents (CA/NY/CO/WA law style)."""
    return re.compile(
        symbol + r'\s*(\d{2,3})[,]?(\d{3})(?:\.\d{2})?\s*' + _COMP_CONNECTOR +
        r'\s*(?:' + symbol + r'|\$)?\s*(\d{2,3})[,]?(\d{3})(?:\.\d{2})?\b',
        re.IGNORECASE,
    )


def _k_range(symbol: str) -> re.Pattern[str]:
    """"<sym>120K - <sym>180K"."""
    return re.compile(
        symbol + r'\s*(\d{2,3})\s*[Kk]\s*' + _COMP_CONNECTOR + r'\s*(?:' + symbol + r'|\$)?\s*(\d{2,3})\s*[Kk]\b',
        re.IGNORECASE,
    )


def _code_range(code: str) -> re.Pattern[str]:
    """"USD 120,000 to 180,000"."""
    return re.compile(
        r'\b' + code + r'\s*(\d{2,3})[,]?(\d{3})\s*' + _COMP_CONNECTOR + r'\s*(?:' + code + r')?\s*(\d{2,3})[,]?(\d{3})\b',
        re.IGNORECASE,
    )


_ANNUAL_SUFFIX = r'\s*(?:per\s+year|/\s*year|annually|/\s*yr|\s+annual)\b'
_DOLLAR = r'(?<![A-Za-z])\$'
_CAD_PREFIX = r'(?:C\$|CA\$|CAD\s*\$?)'

# (pattern, currency). currency None means "a bare $ — resolve via location".
_USD_PREFIX = r'(?:USD\s*\$|US\$)'

_COMP_RANGE_PATTERNS: list[tuple[re.Pattern[str], str | None]] = [
    (_money_range(_USD_PREFIX), 'USD'),
    (_k_range(_USD_PREFIX), 'USD'),
    (_money_range(_CAD_PREFIX), 'CAD'),
    (_k_range(_CAD_PREFIX), 'CAD'),
    (_money_range(_DOLLAR), None),
    (_k_range(_DOLLAR), None),
    (_code_range('USD'), 'USD'),
    (_code_range('CAD'), 'CAD'),
    (_money_range('£'), 'GBP'),
    (_k_range('£'), 'GBP'),
    (_code_range('GBP'), 'GBP'),
    (_money_range('€'), 'EUR'),
    (_k_range('€'), 'EUR'),
    (_code_range('EUR'), 'EUR'),
]

_COMP_SINGLE_PATTERNS: list[tuple[re.Pattern[str], str | None]] = [
    # "$150,000/year" or "$150,000 annually"
    (re.compile(_DOLLAR + r'\s*(\d{2,3})[,]?(\d{3})' + _ANNUAL_SUFFIX, re.IGNORECASE), None),
    # "$150k/year" or "$150K annually"
    (re.compile(_DOLLAR + r'\s*(\d{2,3})\s*[Kk]' + _ANNUAL_SUFFIX, re.IGNORECASE), None),
    (re.compile(r'£\s*(\d{2,3})[,]?(\d{3})' + _ANNUAL_SUFFIX, re.IGNORECASE), 'GBP'),
    (re.compile(r'€\s*(\d{2,3})[,.]?(\d{3})' + _ANNUAL_SUFFIX, re.IGNORECASE), 'EUR'),
]

# Rupees: "₹12,00,000 - ₹18,00,000" (lakh grouping) or "INR 1,200,000 to 1,800,000",
# and "12 - 18 LPA" / "12-18 lakhs per annum".
_INR_AMOUNT = r'(\d{1,3}(?:,\d{2,3})+|\d{5,8})'
_INR_PREFIX = r'(?:₹|\bINR|\bRs\.?)'
_INR_RANGE_RE = re.compile(
    _INR_PREFIX + r'\s*' + _INR_AMOUNT + r'\s*' + _COMP_CONNECTOR + r'\s*(?:' + _INR_PREFIX + r')?\s*' + _INR_AMOUNT,
    re.IGNORECASE,
)
_LPA_RANGE_RE = re.compile(
    r'\b(\d{1,2}(?:\.\d{1,2})?)\s*' + _COMP_CONNECTOR + r'\s*(\d{1,3}(?:\.\d{1,2})?)\s*'
    r'(?:LPA\b|lakhs?(?:\s+per\s+annum)?\b)',
    re.IGNORECASE,
)
_LAKH = 100_000

# Strip these spans before searching — they're the most common false-positive
# sources in job descriptions (funding announcements, market cap, etc.).
_COMP_BLOCKLIST = re.compile(
    r'('
    r'series\s+[A-Da-d](?:\s+round)?|'
    r'\braised\s+\$[\d.,]+\s*[MmBbKk]?|'
    r'valuation[^.]{0,60}|'
    r'revenue\s+of[^.]{0,40}|'
    r'\$\d+(?:\.\d+)?\s*(?:billion|trillion|million\s+ARR|m\s+ARR|b\s+ARR)|'
    r'fortune\s+\d+|'
    r'market\s+cap[^.]{0,40}|'
    r'(?:nyse|nasdaq):\s*\w+'
    r')',
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Location → currency of a bare "$"
# ---------------------------------------------------------------------------

_CANADA_RE = re.compile(
    r'\bcanada\b|\bcanadian\b|\bontario\b|\bquebec\b|\bbritish columbia\b|\balberta\b|\bmanitoba\b'
    r'|\bsaskatchewan\b|\bnova scotia\b|\bnew brunswick\b|\bnewfoundland\b'
    r'|\btoronto\b|\bvancouver\b|\bmontr[eé]al\b|\bottawa\b|\bcalgary\b|\bedmonton\b|\bwinnipeg\b'
    r'|\bwaterloo\b|\bkitchener\b|\bmississauga\b|\bmarkham\b|\bhalifax\b|\bburnaby\b'
    r'|,\s*(?:ON|BC|QC|AB|MB|SK|NS|NB|NL|PE)\b',
    re.IGNORECASE,
)
_US_STATE_CODES = (
    'AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|'
    'OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC'
)
_US_RE = re.compile(
    r'\bunited states\b|\bu\.?s\.?a?\b|\bamerica\b|,\s*(?:' + _US_STATE_CODES + r')\b'
    r'|\b(?:new york|san francisco|seattle|austin|boston|chicago|los angeles|atlanta|denver|dallas)\b',
    re.IGNORECASE,
)
# Known non-US, non-Canada places: a bare "$" there is not safely USD.
_OTHER_NON_US_RE = re.compile(
    r'\bindia\b|\bbengaluru\b|\bbangalore\b|\bhyderabad\b|\bpune\b|\bmumbai\b|\bdelhi\b|\bgurgaon\b'
    r'|\bgurugram\b|\bnoida\b|\bchennai\b'
    r'|\bunited kingdom\b|\buk\b|\bengland\b|\bscotland\b|\bireland\b|\blondon\b(?!\s*,\s*on)'
    r'|\bgermany\b|\bfrance\b|\bnetherlands\b|\bspain\b|\bpoland\b|\bberlin\b|\bparis\b|\bamsterdam\b'
    r'|\baustralia\b|\bsydney\b|\bmelbourne\b|\bsingapore\b|\bjapan\b|\btokyo\b|\bmexico\b|\bbrazil\b'
    r'|\bisrael\b|\btel aviv\b|\bchina\b|\bhong kong\b|\bphilippines\b|\bnew zealand\b',
    re.IGNORECASE,
)


# Currency of a bare "$" by trailing ISO country code (None: "$" is not local).
_COUNTRY_CODE_CURRENCY: dict[str, str | None] = {'US': 'USD', 'CA': 'CAD', 'IN': None, 'GB': None, 'UK': None}


def dollar_currency_for_location(location: str | None) -> str | None:
    """Currency of a bare ``$`` amount given the job location.

    USD for US or unknown/remote locations, CAD for Canada-only locations,
    ``None`` for other non-US locations or a mix that includes Canada.
    """
    text = location if isinstance(location, str) else ''
    # JobSpy style "City, ST, CC": a trailing two-letter part after two others
    # is an ISO country code ("Vancouver, BC, CA" is Canada, not California).
    parts = [p.strip() for p in text.split(',')]
    if len(parts) >= 3 and parts[-1].upper() in _COUNTRY_CODE_CURRENCY:
        return _COUNTRY_CODE_CURRENCY[parts[-1].upper()]
    is_canada = bool(_CANADA_RE.search(text))
    is_us = bool(_US_RE.search(text))
    if is_canada:
        return None if is_us else 'CAD'
    if is_us:
        return 'USD'
    if _OTHER_NON_US_RE.search(text):
        return None
    return 'USD'


def _within_bounds(lo: int, hi: int, currency: str | None, *, check_spread: bool = True) -> bool:
    cmin, cmax, spread = _BOUNDS.get(currency, _DEFAULT_BOUNDS)
    if not (cmin <= lo <= hi <= cmax):
        return False
    return not check_spread or (hi - lo) <= spread


def _comp(lo: int, hi: int, currency: str | None, source: str) -> dict[str, Any]:
    return {'min': lo, 'max': hi, 'currency': currency, 'source': source}


def bounded_comp(
    lo: Any,
    hi: Any,
    source: str,
    currency: str | None = 'USD',
    interval: str | None = None,
) -> dict[str, Any] | None:
    """Structured comp dict when the (annualised) range is within the currency's bounds, else None.

    ``interval`` (e.g. JobSpy's ``hourly``/``yearly``) annualises the amounts;
    an unrecognised interval yields None rather than a mislabelled figure.
    """
    if not lo or not hi:
        return None
    multiplier = 1
    if interval:
        key = str(interval).strip().lower()
        if key not in _ANNUAL_MULTIPLIER:
            return None
        multiplier = _ANNUAL_MULTIPLIER[key]
    lo_i, hi_i = int(round(float(lo) * multiplier)), int(round(float(hi) * multiplier))
    currency = currency.strip().upper() if isinstance(currency, str) and currency.strip() else currency
    if _within_bounds(lo_i, hi_i, currency, check_spread=False):
        return _comp(lo_i, hi_i, currency, source)
    return None


def _to_int(digits: str) -> int:
    return int(digits.replace(',', ''))


def _extract_inr(text: str) -> dict[str, Any] | None:
    m = _INR_RANGE_RE.search(text)
    if m:
        lo, hi = _to_int(m.group(1)), _to_int(m.group(2))
        if _within_bounds(lo, hi, 'INR'):
            return _comp(lo, hi, 'INR', 'posting')
    m = _LPA_RANGE_RE.search(text)
    if m:
        lo, hi = int(round(float(m.group(1)) * _LAKH)), int(round(float(m.group(2)) * _LAKH))
        if _within_bounds(lo, hi, 'INR'):
            return _comp(lo, hi, 'INR', 'posting')
    return None


def extract_compensation(text: str | None, location: str | None = None) -> dict[str, Any] | None:
    """Find a salary range in a free-text job description.

    Returns ``{'min', 'max', 'currency', 'source': 'posting'}`` with min/max as
    whole annual amounts (e.g. 120000), or None when nothing is confidently
    extractable. ``currency`` is None when a bare ``$`` appears in a posting
    for a non-US, non-Canadian location. Ranges must sit inside the
    currency's bounds (USD/CAD: 30k <= min <= max <= 600k, spread <= 250k).
    """
    if not text:
        return None
    text = strip_html(text)
    text = _COMP_BLOCKLIST.sub(' ', text)
    dollar_currency = dollar_currency_for_location(location)

    for pat, currency in _COMP_RANGE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        if len(g) == 4:
            lo, hi = g[0] * 1000 + g[1], g[2] * 1000 + g[3]
        else:
            lo, hi = g[0] * 1000, g[1] * 1000
        resolved = dollar_currency if currency is None else currency
        if _within_bounds(lo, hi, resolved):
            return _comp(lo, hi, resolved, 'posting')

    for pat, currency in _COMP_SINGLE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        mid = g[0] * 1000 + g[1] if len(g) == 2 else g[0] * 1000
        resolved = dollar_currency if currency is None else currency
        cmin, cmax, _ = _BOUNDS.get(resolved, _DEFAULT_BOUNDS)
        if cmin <= mid <= cmax:
            return _comp(int(round(mid * 0.9)), int(round(mid * 1.1)), resolved, 'posting')

    return _extract_inr(text)

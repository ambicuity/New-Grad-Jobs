"""USD salary extraction from free-text job descriptions."""

from __future__ import annotations

import re
from typing import Any

from ngj.text import strip_html

# Sanity bounds shared by regex extraction and structured (Ashby/JobSpy) comp:
# they reject sign-on bonuses, valuations and stock prices.
COMP_MIN = 30_000
COMP_MAX = 600_000
COMP_MAX_SPREAD = 250_000

# Range patterns first (most specific), single-value patterns second.
# Connector covers: "-", "–", "—", "to", "and up to", "up to", "through".
_COMP_CONNECTOR = r'(?:-|–|—|to|and\s+up\s+to|through)'

_COMP_RANGE_PATTERNS = [
    # "$120,000 - $180,000" with optional .00 cents (CA/NY/CO/WA law style)
    re.compile(
        r'\$\s*(\d{2,3})[,]?(\d{3})(?:\.\d{2})?\s*' + _COMP_CONNECTOR +
        r'\s*\$?\s*(\d{2,3})[,]?(\d{3})(?:\.\d{2})?\b',
        re.IGNORECASE,
    ),
    # "$120K - $180K" or "$120k – $180k"
    re.compile(
        r'\$\s*(\d{2,3})\s*[Kk]\s*' + _COMP_CONNECTOR + r'\s*\$?\s*(\d{2,3})\s*[Kk]\b',
        re.IGNORECASE,
    ),
    # "USD 120,000 to 180,000"
    re.compile(
        r'\bUSD\s*(\d{2,3})[,]?(\d{3})\s*' + _COMP_CONNECTOR + r'\s*(\d{2,3})[,]?(\d{3})\b',
        re.IGNORECASE,
    ),
]

_COMP_SINGLE_PATTERNS = [
    # "$150,000/year" or "$150,000 annually"
    re.compile(
        r'\$\s*(\d{2,3})[,]?(\d{3})\s*(?:per\s+year|/\s*year|annually|/\s*yr|\s+annual)\b',
        re.IGNORECASE,
    ),
    # "$150k/year" or "$150K annually"
    re.compile(
        r'\$\s*(\d{2,3})\s*[Kk]\s*(?:per\s+year|/\s*year|annually|/\s*yr|\s+annual)\b',
        re.IGNORECASE,
    ),
]

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


def bounded_comp(lo: Any, hi: Any, source: str) -> dict[str, Any] | None:
    """Return a USD comp dict when ``COMP_MIN <= lo <= hi <= COMP_MAX``, else None."""
    if not lo or not hi:
        return None
    lo_i, hi_i = int(lo), int(hi)
    if COMP_MIN <= lo_i <= hi_i <= COMP_MAX:
        return {'min': lo_i, 'max': hi_i, 'currency': 'USD', 'source': source}
    return None


def extract_compensation(text: str | None) -> dict[str, Any] | None:
    """Find a USD salary range in a free-text job description.

    Returns {'min', 'max', 'currency': 'USD', 'source': 'posting'} with min/max
    as full integer dollars (e.g. 120000), or None when nothing is confidently
    extractable. Ranges must satisfy 30k <= min <= max <= 600k and
    (max - min) <= 250k.
    """
    if not text:
        return None
    text = strip_html(text)
    text = _COMP_BLOCKLIST.sub(' ', text)

    for pat in _COMP_RANGE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        if len(g) == 4:
            lo, hi = g[0] * 1000 + g[1], g[2] * 1000 + g[3]
        else:
            lo, hi = g[0] * 1000, g[1] * 1000
        if COMP_MIN <= lo <= hi <= COMP_MAX and (hi - lo) <= COMP_MAX_SPREAD:
            return {'min': lo, 'max': hi, 'currency': 'USD', 'source': 'posting'}

    for pat in _COMP_SINGLE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        mid = g[0] * 1000 + g[1] if len(g) == 2 else g[0] * 1000
        if COMP_MIN <= mid <= COMP_MAX:
            return {
                'min': int(round(mid * 0.9)),
                'max': int(round(mid * 1.1)),
                'currency': 'USD',
                'source': 'posting',
            }
    return None

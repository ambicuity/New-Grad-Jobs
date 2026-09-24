"""Job filtering: exclusion signals, new-grad/track signals, recency, location.

``filter_jobs`` is the single inclusion gate applied after deduplication.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from ngj.dates import is_recent_job
from ngj.taxonomy import is_engineering_network_title

# Used when config.yml has no filtering.exclusion_signals.
DEFAULT_EXCLUSION_SIGNALS: tuple[str, ...] = (
    'senior', 'sr.', 'sr ', 'staff', 'principal', 'lead', 'manager',
    'director', 'vp', 'vice president', 'head of', 'architect',
    'distinguished', 'fellow', 'intern', 'internship',
)

# Title phrases strong enough to pass without a track signal.
# Generic role titles are deliberately absent — "Software Engineer" alone must
# not bypass the track-signal requirement. Cohort years mirror
# filtering.new_grad_signals in config.yml; move both forward together as each
# hiring cycle opens.
STRONG_NEW_GRAD_SIGNALS: tuple[str, ...] = (
    "new grad", "new graduate", "graduate program", "campus", "university grad",
    "college grad", "early career", "2025 start", "2026 start", "2027 start",
    "2025", "2026", "2027",
)

# Location indicators used by is_valid_location(). Keep these at module scope so
# we do not rebuild large lists for every job (~2000+ calls per run).
REMOTE_LOCATION_TERMS = frozenset({'remote', 'anywhere', 'worldwide'})

USA_STATE_TERMS = (
    'alabama', 'al', 'alaska', 'ak', 'arizona', 'az', 'arkansas', 'ar',
    'california', 'ca', 'colorado', 'co', 'connecticut', 'ct',
    'delaware', 'de', 'florida', 'fl', 'georgia', 'ga', 'hawaii', 'hi',
    'idaho', 'id', 'illinois', 'il', 'indiana', 'in', 'iowa', 'ia',
    'kansas', 'ks', 'kentucky', 'ky', 'louisiana', 'la', 'maine', 'me',
    'maryland', 'md', 'massachusetts', 'ma', 'michigan', 'mi',
    'minnesota', 'mn', 'mississippi', 'ms', 'missouri', 'mo',
    'montana', 'mt', 'nebraska', 'ne', 'nevada', 'nv', 'new hampshire', 'nh',
    'new jersey', 'nj', 'new mexico', 'nm', 'new york', 'ny',
    'north carolina', 'nc', 'north dakota', 'nd', 'ohio', 'oh',
    'oklahoma', 'ok', 'oregon', 'or', 'pennsylvania', 'pa',
    'rhode island', 'ri', 'south carolina', 'sc', 'south dakota', 'sd',
    'tennessee', 'tn', 'texas', 'tx', 'utah', 'ut', 'vermont', 'vt',
    'virginia', 'va', 'washington', 'wa', 'west virginia', 'wv',
    'wisconsin', 'wi', 'wyoming', 'wy', 'district of columbia', 'dc'
)

USA_CITY_TERMS = (
    'new york', 'los angeles', 'chicago', 'houston', 'phoenix', 'philadelphia',
    'san antonio', 'san diego', 'dallas', 'san jose', 'austin', 'jacksonville',
    'fort worth', 'columbus', 'charlotte', 'san francisco', 'indianapolis',
    'seattle', 'denver', 'boston', 'atlanta', 'miami', 'portland', 'las vegas',
    'detroit', 'nashville', 'baltimore', 'milwaukee', 'raleigh', 'tampa',
    'mountain view', 'palo alto', 'menlo park', 'redwood city', 'cupertino',
    'santa clara', 'sunnyvale', 'bellevue', 'redmond', 'kirkland', 'irvine'
)

USA_INDICATOR_TERMS = ('united states', 'usa', 'us', 'america')

CANADA_INDICATOR_TERMS = (
    'canada', 'ontario', 'quebec', 'british columbia', 'alberta', 'manitoba',
    'saskatchewan', 'nova scotia', 'new brunswick', 'newfoundland', 'prince edward island',
    'toronto', 'vancouver', 'montreal', 'ottawa', 'calgary', 'edmonton', 'winnipeg',
    'quebec city', 'hamilton', 'kitchener', 'waterloo', 'victoria',
    'london, ontario', 'london, on', 'london on'
)

INDIA_INDICATOR_TERMS = (
    'india', 'bangalore', 'bengaluru', 'hyderabad', 'mumbai', 'delhi', 'pune',
    'chennai', 'kolkata', 'gurgaon', 'gurugram', 'noida', 'ahmedabad', 'jaipur',
    'kochi', 'thiruvananthapuram', 'coimbatore', 'indore', 'nagpur', 'lucknow',
    'chandigarh', 'bhubaneswar', 'visakhapatnam', 'mysore', 'mangalore',
    'karnataka', 'maharashtra', 'telangana', 'tamil nadu', 'kerala', 'andhra pradesh',
    'gujarat', 'rajasthan', 'west bengal', 'uttar pradesh', 'madhya pradesh',
    'haryana', 'punjab', 'bihar', 'odisha', 'jharkhand', 'uttarakhand'
)

LOCATION_TERMS = frozenset(
    USA_INDICATOR_TERMS
    + USA_STATE_TERMS
    + USA_CITY_TERMS
    + CANADA_INDICATOR_TERMS
    + INDIA_INDICATOR_TERMS
)

LOCATION_TERM_PATTERN = re.compile(
    r'\b(?:'
    + '|'.join(re.escape(term) for term in sorted(LOCATION_TERMS, key=len, reverse=True))
    + r')\b',
    re.IGNORECASE,
)


def has_new_grad_signal(title: str, signals: list[str]) -> bool:
    """Check if job title contains new grad signals."""
    if not signals:
        return False
    if not isinstance(title, str):
        return False
    if title.strip().lower() in {'nan', 'none'}:
        return False

    normalized_signals = [
        re.escape(s.strip().lower())
        for s in signals
        if isinstance(s, str) and s.strip()
    ]
    if not normalized_signals:
        return False

    combined_signals = "|".join(normalized_signals)
    pattern = rf"\b({combined_signals})\b"
    return bool(re.search(pattern, title.lower()))

# Exclusion signals whose inflections must also exclude. Word-boundary matching
# means "intern" alone no longer covers "internship"/"interns".
_EXCLUSION_SUFFIXES: dict[str, str] = {'intern': r'(?:s|ships?)?'}
# Entry-level titles that contain an exclusion word but are not senior roles.
# Removed from the title before exclusion signals are checked, so a real
# seniority marker elsewhere ("Senior Associate Product Manager") still excludes.
_EXCLUSION_EXCEPTIONS_RE = re.compile(
    r'\bassociate\s+(?:technical\s+)?(?:product|program|project)\s+managers?\b',
    re.IGNORECASE,
)


@lru_cache(maxsize=32)
def _compile_exclusion_pattern(signals: tuple[str, ...]) -> re.Pattern | None:
    """Compile exclusion signals into one whole-word regex.

    Word boundaries are applied only on alphanumeric edges, so punctuation-led
    or -trailed signals ("sr.", "10+ years") keep working. Alphabetic signals
    also match a plural "s" ("managers", "leads"); see _EXCLUSION_SUFFIXES for
    longer inflections.
    """
    parts = []
    for raw in signals:
        if not isinstance(raw, str):
            continue
        core = raw.strip().lower()
        if not core:
            continue
        body = r'\s+'.join(re.escape(word) for word in core.split())
        if core[-1].isalpha():
            body += _EXCLUSION_SUFFIXES.get(core, r's?')
        left = r'(?<![a-z0-9])' if core[0].isalnum() else ''
        right = r'(?![a-z0-9])' if core[-1].isalnum() else ''
        parts.append(f"{left}{body}{right}")
    if not parts:
        return None
    return re.compile('|'.join(parts), re.IGNORECASE)


def is_title_excluded(title: str, exclusion_signals: list[str]) -> bool:
    """Return True when the title carries a seniority/intern exclusion signal."""
    if not isinstance(title, str) or not title:
        return False
    pattern = _compile_exclusion_pattern(tuple(exclusion_signals or ()))
    if pattern is None:
        return False
    return bool(pattern.search(_EXCLUSION_EXCEPTIONS_RE.sub(' ', title)))


def has_track_signal(title: str, signals: list[str]) -> bool:
    """Check if job title contains track signal keywords (e.g. 'software', 'data').

    For the ambiguous 'network' track, require an engineering-focused title so
    business-side roles like provider network contracting do not pass.
    """
    if not isinstance(title, str):
        return False
    if not isinstance(signals, list):
        return False

    title_lower = title.lower()
    for signal in signals:
        if not isinstance(signal, str):
            continue
        signal_lower = signal.strip().lower()
        if not signal_lower:
            continue
        if signal_lower == 'network':
            if is_engineering_network_title(title):
                return True
            continue
        if signal_lower in title_lower:
            return True

    return False


def is_valid_location(location: str) -> bool:
    """Check if job location is in target countries (USA, Canada, India) or Remote"""
    if not location:
        return False

    location_lower = location.lower().strip()
    if not location_lower:
        return False

    # Handle "Remote" locations - include them
    if location_lower in REMOTE_LOCATION_TERMS or 'remote' in location_lower:
        return True

    return bool(LOCATION_TERM_PATTERN.search(location_lower))


def filter_jobs(jobs: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the jobs that pass every inclusion rule (input list is not modified)."""
    filters = config.get('filtering', config.get('filters', {}))
    exclusion_signals = filters.get('exclusion_signals', list(DEFAULT_EXCLUSION_SIGNALS))
    return [job for job in jobs if _passes_filters(job, filters, exclusion_signals)]


def _passes_filters(job: dict[str, Any], filters: dict[str, Any], exclusion_signals: list[str]) -> bool:
    title = job.get('title', '')
    title_lower = title.lower()

    # FIRST: exclusion signals (filter OUT senior/staff/intern roles)
    if is_title_excluded(title, exclusion_signals):
        return False

    if not has_new_grad_signal(title, filters['new_grad_signals']):
        return False

    # Accept if: strong new-grad signal OR (new-grad signal AND track signal)
    has_track = has_track_signal(title, filters['track_signals'])
    has_strong_new_grad = any(signal.lower() in title_lower for signal in STRONG_NEW_GRAD_SIGNALS)
    if not (has_strong_new_grad or has_track):
        return False

    if not is_recent_job(job.get('posted_at', ''), filters['max_age_days']):
        return False

    return is_valid_location(job.get('location', ''))

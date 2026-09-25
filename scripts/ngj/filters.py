"""Job filtering: exclusion signals, new-grad/track signals, recency, location.

``filter_jobs`` is the single inclusion gate applied after deduplication.

The gate is deliberately broad (owner decision): an unlevelled "Software
Engineer" passes on the configured signals. Every signal matches at token
boundaries — never as a raw substring — so "ai" does not match "Maintenance",
"I" does not match a middle initial, and "2026" does not match a req id.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from ngj.dates import is_recent_job
from ngj.locations import is_valid_location
from ngj.taxonomy import is_engineering_network_title

__all__ = [
    'DEFAULT_EXCLUSION_SIGNALS',
    'DEFAULT_LEVEL_SIGNALS',
    'DEFAULT_NON_TECH_SIGNALS',
    'DEFAULT_STRONG_NEW_GRAD_SIGNALS',
    'filter_jobs',
    'find_padded_signals',
    'has_excluded_level',
    'has_new_grad_signal',
    'has_non_tech_signal',
    'has_strong_new_grad_signal',
    'has_track_signal',
    'is_title_excluded',
    'is_valid_location',
]

# Used when config.yml has no filtering.exclusion_signals.
DEFAULT_EXCLUSION_SIGNALS: tuple[str, ...] = (
    'senior', 'sr.', 'sr', 'staff', 'principal', 'lead', 'manager',
    'director', 'vp', 'vice president', 'head of', 'architect',
    'distinguished', 'fellow', 'intern', 'internship',
)

# Used when config.yml has no filtering.strong_new_grad_signals. Phrases strong
# enough to pass without a track signal. Generic role titles are deliberately
# absent — "Software Engineer" alone must not bypass the track-signal
# requirement. Move the cohort years forward as each hiring cycle opens.
DEFAULT_STRONG_NEW_GRAD_SIGNALS: tuple[str, ...] = (
    "new grad", "new graduate", "graduate program", "campus", "university grad",
    "university graduate", "college grad", "college graduate", "early career", "2025 start", "2026 start", "2027 start",
    "2025", "2026", "2027",
)

# Used when config.yml has no filtering.level_signals: entry-level markers
# matched as standalone level tokens ("Engineer I", "SDE II", "(L3)").
DEFAULT_LEVEL_SIGNALS: tuple[str, ...] = ('I', 'II', 'L3', 'L4', 'E3', 'E4')

# Used when config.yml has no filtering.non_tech_signals. A title carrying one
# of these is a non-tech role ("New Grad Registered Nurse", "Investment Banking
# Analyst 2027") and is dropped *unless* it also carries a track signal, so
# "Software Engineer, Healthcare" and "Data Scientist, Marketing" stay. Without
# this gate a strong new-grad phrase alone let any profession onto the board.
DEFAULT_NON_TECH_SIGNALS: tuple[str, ...] = (
    'nurse', 'nursing', 'rn', 'nurse practitioner', 'physician', 'dental', 'pharmacy',
    'pharmacist', 'pharmaceutical', 'clinical', 'therapist', 'therapy', 'medical',
    'caregiver', 'sales', 'marketing', 'recruit', 'recruiter', 'recruitment',
    'talent acquisition', 'human resources', 'hr', 'payroll', 'legal', 'counsel',
    'counselor', 'attorney', 'paralegal', 'audit', 'auditor', 'accountant',
    'accounting', 'cpa', 'tax', 'treasury', 'finance', 'banking', 'wealth',
    'investment', 'actuarial', 'actuary', 'underwriter', 'underwriting', 'claims',
    'supply chain', 'logistics', 'procurement', 'purchasing', 'warehouse',
    'customer service', 'customer success', 'account executive', 'administrative',
    'receptionist', 'cashier', 'retail', 'driver', 'welder', 'technician',
    'real estate', 'geologist', 'chemist', 'biologist', 'packaging',
)

# --- Token matching ----------------------------------------------------------
# Level tokens ("I", "II", "L3") sit after a separator and before the end, a
# separator or a "/<level>" pairing. So "Engineer I", "Engineer I/II", "(L3)"
# and "Engineer-II," match; "Alvin I. Goodman", "I/O", "L2/L3" and "L3Harris"
# do not.
_LEVEL_TOKEN_RE = re.compile(r'^(?:[ivx]+|[le]\d)$', re.IGNORECASE)
_LEVEL_LEFT = r'(?<=[\s(\-,\[])'
_LEVEL_RIGHT = r'(?=$|[\s),\-|:;\]]|/(?:[ivx]+|[le]\d)\b)'

# Senior roman numerals and bare digits only count right after a role noun, so
# "Vitamin V" or "Web3" never look like levels.
_ROLE_NOUNS = (
    r'engineer|developer|scientist|analyst|programmer|technologist|sde|swe|'
    r'specialist|associate|consultant|administrator|designer|technician|level|grade'
)
_ENTRY_LEVEL_RE = re.compile(
    rf'{_LEVEL_LEFT}(?:i|ii){_LEVEL_RIGHT}|\blevel\s*[12]\b|(?<![\w/])[le][34](?![\w/])',
    re.IGNORECASE,
)
_SENIOR_LEVEL_RE = re.compile(
    rf'\b(?:{_ROLE_NOUNS})(?:\s+|\s*,\s*|-)(?:iii|iv|v|vi|vii|viii|[3-9]){_LEVEL_RIGHT}'
    rf'|{_LEVEL_LEFT}[le][5-9]{_LEVEL_RIGHT}',
    re.IGNORECASE,
)

# Track signals also match common inflections: "engineer" -> "Engineering",
# "developer" -> "Developers", "platform" -> "Platforms".
_TRACK_SUFFIX = r'(?:s|es|ing|ings|ers?|ed)?'
# CJK and later blocks have no inter-word spaces, so boundaries cannot apply.
_CJK_START = 0x2E80


def _signal_pattern(raw: str, suffix: str = '') -> str | None:
    """Regex source for one configured signal, matched at token boundaries.

    * a trailing level token ("I", "sde ii", "l3") -> level-token boundaries;
    * a bare number ("2026") -> not inside a longer number or a req id
      ("R20261234", "JR-2026-0042", "#2026");
    * anything else -> whole words; ``suffix`` allows inflections.
    """
    words = raw.strip().lower().split()
    if not words:
        return None
    body = r'\s+'.join(re.escape(word) for word in words)
    if _LEVEL_TOKEN_RE.match(words[-1]):
        left = _LEVEL_LEFT if len(words) == 1 else r'(?<!\w)'
        return f'{left}{body}{_LEVEL_RIGHT}'
    if len(words) == 1 and words[0].isdigit():
        return rf'(?<![\w#]){body}(?!\w|-\d)'
    if suffix and all(ord(ch) >= _CJK_START for ch in ''.join(words)):
        return body  # scripts written without spaces: substring is the word
    if words[-1][-1].isalpha():
        body += suffix
    left = r'(?<!\w)' if words[0][0].isalnum() else ''
    right = r'(?!\w)' if words[-1][-1].isalnum() else ''
    return f'{left}{body}{right}'


@lru_cache(maxsize=64)
def _compile_signals(signals: tuple[Any, ...], suffix: str = '') -> re.Pattern[str] | None:
    parts = [
        pattern
        for raw in signals
        if isinstance(raw, str) and (pattern := _signal_pattern(raw, suffix))
    ]
    if not parts:
        return None
    return re.compile('|'.join(f'(?:{part})' for part in parts), re.IGNORECASE)


def _matches_any(title: Any, signals: Any, suffix: str = '') -> bool:
    if not isinstance(title, str) or not isinstance(signals, (list, tuple)):
        return False
    pattern = _compile_signals(tuple(signals), suffix)
    return bool(pattern and pattern.search(title))


def find_padded_signals(filtering: dict[str, Any]) -> dict[str, list[str]]:
    """Signals with leading/trailing whitespace, keyed by config list name.

    Matching strips whitespace, so a padded entry (" I ", " L3") never meant
    what it looked like; level tokens belong in ``level_signals`` instead.
    """
    padded: dict[str, list[str]] = {}
    for key, values in filtering.items():
        if not str(key).endswith('_signals') or not isinstance(values, list):
            continue
        offenders = [v for v in values if isinstance(v, str) and v != v.strip()]
        if offenders:
            padded[key] = offenders
    return padded


def has_new_grad_signal(title: str, signals: list[str]) -> bool:
    """Check if the job title contains a new-grad signal as a whole token."""
    if not isinstance(title, str) or title.strip().lower() in {'nan', 'none'}:
        return False
    return _matches_any(title, signals)


def has_strong_new_grad_signal(title: str, signals: list[str] | tuple[str, ...] | None) -> bool:
    """Check for a strong new-grad phrase; ``None`` means the built-in defaults."""
    return _matches_any(title, DEFAULT_STRONG_NEW_GRAD_SIGNALS if signals is None else signals)


def has_non_tech_signal(title: str, signals: list[str] | tuple[str, ...] | None) -> bool:
    """Check for a non-tech profession word; ``None`` means the built-in defaults.

    Whole words plus common inflections ("recruit" also matches "Recruiting").
    """
    return _matches_any(title, DEFAULT_NON_TECH_SIGNALS if signals is None else signals, _TRACK_SUFFIX)


def has_excluded_level(title: str) -> bool:
    """True for level III+ titles ("Engineer III", "Engineer 3", "Level 4", "L5").

    Level II stays in scope. A title that also names level I/II ("Software
    Engineer II/III") is hiring at that level too and is kept.
    """
    if not isinstance(title, str):
        return False
    return bool(_SENIOR_LEVEL_RE.search(title)) and not _ENTRY_LEVEL_RE.search(title)


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
def _compile_exclusion_pattern(signals: tuple[str, ...]) -> re.Pattern[str] | None:
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
    """Check if the job title contains a track keyword (e.g. 'software', 'data').

    Whole words only, plus common inflections ("Engineering", "Developers"):
    'ai' matches "AI/ML" but not "Maintenance", 'ml' matches "ML-Ops" but not
    "HTML". The ambiguous 'network' track requires an engineering-focused title
    so business-side roles like provider network contracting do not pass.
    """
    if not isinstance(title, str) or not isinstance(signals, list):
        return False
    plain = [s for s in signals if not (isinstance(s, str) and s.strip().lower() == 'network')]
    if len(plain) != len(signals) and is_engineering_network_title(title):
        return True
    return _matches_any(title, plain, _TRACK_SUFFIX)


def filter_jobs(jobs: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the jobs that pass every inclusion rule (input list is not modified)."""
    filters = config.get('filtering', config.get('filters', {}))
    exclusion_signals = filters.get('exclusion_signals', list(DEFAULT_EXCLUSION_SIGNALS))
    return [job for job in jobs if _passes_filters(job, filters, exclusion_signals)]


def _passes_filters(job: dict[str, Any], filters: dict[str, Any], exclusion_signals: list[str]) -> bool:
    title = job.get('title', '')

    # FIRST: exclusion signals (filter OUT senior/staff/intern roles and III+ levels)
    if is_title_excluded(title, exclusion_signals) or has_excluded_level(title):
        return False

    new_grad_signals = list(filters['new_grad_signals']) + list(
        filters.get('level_signals', DEFAULT_LEVEL_SIGNALS)
    )
    if not has_new_grad_signal(title, new_grad_signals):
        return False

    # Accept if: strong new-grad signal OR (new-grad signal AND track signal)
    has_track = has_track_signal(title, filters['track_signals'])
    if not (has_track or has_strong_new_grad_signal(title, filters.get('strong_new_grad_signals'))):
        return False

    # A strong signal alone must not admit another profession ("New Grad Nurse").
    if not has_track and has_non_tech_signal(title, filters.get('non_tech_signals')):
        return False

    if not is_recent_job(job.get('posted_at', ''), filters['max_age_days']):
        return False

    return is_valid_location(job.get('location', ''))

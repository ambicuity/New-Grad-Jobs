"""Per-job enrichment: category, company tier, sponsorship flags, closed marker.

Enrichment never mutates its inputs: each job comes back as a new dict.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from ngj.taxonomy import categorize_job, get_company_tier

# Sponsorship/visa keywords
NO_SPONSORSHIP_KEYWORDS = [
    'no sponsorship', 'not sponsor', 'cannot sponsor', 'will not sponsor',
    'u.s. citizens only', 'us citizens only', 'citizens only',
    'must be authorized', 'authorization required', 'no visa'
]

US_CITIZENSHIP_KEYWORDS = [
    'u.s. citizen', 'us citizen', 'american citizen', 'citizenship required',
    'security clearance', 'clearance required', 'top secret', 'ts/sci'
]

# Closed-job detection uses strict phrases only. Bare "closed"/"expired"
# substrings produced false positives on ordinary descriptions
# ("closed-loop", "disclosed", "closed-won", "until the requisition is closed").
# "position is filled" alone is deliberately not matched: postings commonly say
# "reviewed on a rolling basis until the position is filled".
_CLOSED_PHRASE_RE = re.compile(
    r'\b(?:'
    r'position\s+(?:has\s+(?:now\s+)?been\s+|is\s+now\s+)?filled'
    r'|no\s+longer\s+accepting(?:\s+applications)?'
    r'|job\s+(?:posting\s+)?(?:has\s+)?expired'
    r'|(?:job\s+)?posting\s+has\s+expired'
    r'|this\s+(?:job|position|posting|role|requisition)\s+(?:is\s+|has\s+)(?:now\s+)?(?:been\s+)?closed'
    r')\b',
    re.IGNORECASE,
)
# Title markers: "[Closed]", "(Expired)", "Closed - ...", "... - Closed",
# "CLOSED POSITION". A bare "Closed" inside a title ("Closed-Loop Controls")
# is not a marker.
_CLOSED_TITLE_RE = re.compile(
    r'[\[(]\s*(?:closed|expired|filled)\s*[\])]'
    r'|^\s*(?:closed|expired)\s*(?:[-–—:|]\s|\bposition\b|$)'
    r'|\s[-–—:|]\s*(?:closed|expired|filled)\s*$'
    r'|\bposition\s+(?:closed|filled)\b',
    re.IGNORECASE,
)


def is_job_closed(title: str, description: str = '') -> bool:
    """Check if a job appears closed via explicit title markers or strict phrases."""
    title = title or ''
    if _CLOSED_TITLE_RE.search(title):
        return True
    combined = f"{title} {description or ''}"
    return bool(_CLOSED_PHRASE_RE.search(combined))


def detect_sponsorship_flags(title: str, description: str = '') -> Dict[str, bool]:
    """Detect sponsorship and citizenship requirements"""
    combined = f"{title.lower()} {description.lower() if description else ''}"

    return {
        'no_sponsorship': any(kw in combined for kw in NO_SPONSORSHIP_KEYWORDS),
        'us_citizenship_required': any(kw in combined for kw in US_CITIZENSHIP_KEYWORDS)
    }


def enrich_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of ``job`` with category, company_tier, flags, is_closed and id."""
    title = job.get('title', '')
    description = job.get('description', '')
    company = job.get('company', '')
    return {
        **job,
        'category': categorize_job(title, description),
        'company_tier': get_company_tier(company),
        'flags': detect_sponsorship_flags(title, description),
        'is_closed': is_job_closed(title, description),
        'id': f"{company}-{title}-{job.get('location', '')}".lower().replace(' ', '-')[:100],
    }


def enrich_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enrich every job (see :func:`enrich_job`); the input list and dicts are untouched."""
    return [enrich_job(job) for job in jobs]

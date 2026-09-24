"""Duplicate removal within and across sources.

Two passes, both order-preserving and non-mutating:

1. **Posting identity** — jobs with the same :func:`contracts.compute_job_id`
   (source + canonical URL, tracking params stripped; see
   :func:`contracts.canonical_url`) are the same posting; the first is kept.
   Because the published ``job_id`` is that same hash, this pass is what
   guarantees job_ids are unique in jobs.json.
2. **Cross-source** — jobs from *different* sources with the same normalized
   company and title and a compatible location are one role listed twice
   (a company whose board exists on both Greenhouse and Ashby, or an ATS
   posting re-listed on Indeed). The preferred source wins: ATS-direct beats
   aggregators (JobSpy/LinkedIn/Indeed); among ATSs, the one carrying more
   data wins; ties go to the source seen first. A losing job is dropped when
   one of the winner's jobs has a compatible location. Jobs from the *same*
   source are never merged here — distinct requisitions often share a title
   and location.

Locations are compared by their place-name words (country/state codes and
words like "remote" or "2 Locations" ignored) because every source formats
them differently ("Santa Clara, CA, US" vs "US, California, Santa Clara"). A
location with no place-name words left is compatible with any other.
"""

from __future__ import annotations

import logging
import math
import re
import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from contracts import compute_job_id

logger = logging.getLogger(__name__)

AGGREGATOR_SOURCE_MARKERS = ("jobspy", "indeed", "linkedin", "glassdoor", "ziprecruiter")

# Trailing legal-entity words ignored when comparing company names.
_COMPANY_SUFFIXES = frozenset({
    "inc", "incorporated", "llc", "ltd", "limited", "corp", "corporation", "co", "company",
    "plc", "gmbh", "ag", "sa", "bv", "pbc",
})

# Words that say nothing about *which* city: countries, US state / Canadian
# province codes and single-word names, and work-arrangement noise. Multi-word
# state names ("New York") are deliberately not listed — they are also cities.
_LOCATION_NOISE = frozenset("""
    us usa u s united states america american canada ca ind india uk gb britain kingdom england
    germany de ireland ie france fr mexico mx singapore sg japan jp china cn australia au
    brazil br netherlands nl spain es poland pl israel il amer emea apac latam na
    al ak az ar co ct de fl ga hi id il in ia ks ky la me md ma mi mn ms mo mt ne nv nh nj nm ny
    nc nd oh ok or pa ri sc sd tn tx ut vt va wa wv wi wy dc
    alabama alaska arizona arkansas california colorado connecticut delaware florida georgia
    hawaii idaho illinois indiana iowa kansas kentucky louisiana maine maryland massachusetts
    michigan minnesota mississippi missouri montana nebraska nevada ohio oklahoma oregon
    pennsylvania tennessee texas utah vermont virginia washington wisconsin wyoming
    on bc ab qc mb sk ns nb nl pe ontario quebec alberta manitoba saskatchewan
    ka mh tg ts hr dl up karnataka maharashtra telangana haryana
    remote hybrid onsite on site office based anywhere within or and locations location
    multiple various city metro area greater region hq headquarters
""".split())

_NON_ALNUM = re.compile(r"[^0-9a-z]+")

# Fields that make a posting more useful when present; used to pick among ATSs.
_DATA_FIELDS = ("description", "description_html", "posted_at", "location", "comp")


@dataclass(frozen=True)
class DedupStats:
    """How many jobs each pass removed."""

    same_posting: int
    cross_source: int

    @property
    def total(self) -> int:
        return self.same_posting + self.cross_source


def _text(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    folded = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return _NON_ALNUM.sub(" ", folded.lower().replace("&", " and ")).strip()


def normalize_company(value: Any) -> str:
    words = _text(value).split()
    while len(words) > 1 and words[-1] in _COMPANY_SUFFIXES:
        words.pop()
    return " ".join(words)


def normalize_title(value: Any) -> str:
    return " ".join(_text(value).split())


def location_tokens(value: Any) -> frozenset[str]:
    """Place-name words of a location (noise and numbers removed)."""
    return frozenset(
        word for word in _text(value).split()
        if word not in _LOCATION_NOISE and not word.isdigit() and len(word) > 1
    )


def locations_compatible(a: Any, b: Any) -> bool:
    """True when two locations may name the same place (see module docstring)."""
    tokens_a, tokens_b = location_tokens(a), location_tokens(b)
    return not tokens_a or not tokens_b or bool(tokens_a & tokens_b)


def get_job_key(job: dict[str, Any]) -> str:
    """Posting-identity key (pass 1): equal to the published ``job_id``."""
    return compute_job_id(job)


def cross_source_key(job: dict[str, Any]) -> tuple[str, str] | None:
    """(company, title) grouping key for pass 2, or None when either is blank."""
    company, title = normalize_company(job.get("company")), normalize_title(job.get("title"))
    if not company or not title:
        return None
    return company, title


def is_aggregator_source(source: Any) -> bool:
    name = str(source or "").lower()
    return not name or any(marker in name for marker in AGGREGATOR_SOURCE_MARKERS)


def data_score(job: dict[str, Any]) -> tuple[int, int]:
    """(number of populated data fields, description length) — higher is richer."""
    populated = sum(1 for field in _DATA_FIELDS if job.get(field) not in (None, "", {}, []))
    description = job.get("description")
    return populated, len(description) if isinstance(description, str) else 0


def _source_rank(jobs: Sequence[dict[str, Any]]) -> tuple[int, tuple[int, int]]:
    return (0 if is_aggregator_source(jobs[0].get("source")) else 1), max(data_score(j) for j in jobs)


def _dedupe_same_posting(jobs: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for job in jobs:
        key = get_job_key(job)
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


def _losers_in_group(jobs: Sequence[dict[str, Any]], by_source: dict[str, list[int]]) -> set[int]:
    # Highest rank wins; ties go to the source seen first (lowest index).
    winner = max(by_source, key=lambda s: (_source_rank([jobs[i] for i in by_source[s]]), -by_source[s][0]))
    winner_locations = [jobs[i].get("location") for i in by_source[winner]]
    return {
        index
        for source, indexes in by_source.items() if source != winner
        for index in indexes
        if any(locations_compatible(jobs[index].get("location"), loc) for loc in winner_locations)
    }


def _cross_source_losers(jobs: Sequence[dict[str, Any]]) -> set[int]:
    """Indexes of jobs whose role is better represented by another source."""
    groups: dict[tuple[str, str], dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for index, job in enumerate(jobs):
        key = cross_source_key(job)
        if key is not None:
            groups[key][str(job.get("source") or "").strip().lower()].append(index)

    losers: set[int] = set()
    for by_source in groups.values():
        if len(by_source) > 1:
            losers |= _losers_in_group(jobs, by_source)
    return losers


def deduplicate_jobs_with_stats(jobs: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], DedupStats]:
    """Return (unique jobs in input order, per-pass removal counts). Input is not modified."""
    unique = _dedupe_same_posting(jobs)
    losers = _cross_source_losers(unique)
    kept = [job for index, job in enumerate(unique) if index not in losers]
    return kept, DedupStats(same_posting=len(jobs) - len(unique), cross_source=len(losers))


def deduplicate_jobs(jobs: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate postings (see module docstring); first occurrence wins."""
    kept, stats = deduplicate_jobs_with_stats(jobs)
    if stats.total > 0:
        logger.info(
            "🔄 Deduplication: Removed %s duplicate jobs (%s same posting, %s cross-source)",
            stats.total, stats.same_posting, stats.cross_source,
        )
    return kept

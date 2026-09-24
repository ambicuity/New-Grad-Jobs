"""Location gate: is a posting in a target country (USA, Canada, India)?

A location string is split into segments ("A; B", "A | B", "A or B"); the
job passes when any segment passes. Each segment is decided in this order:

1. an explicit target country ("United States", "US", "Canada", "India",
   "North America", ...) -> pass;
2. a foreign country or region ("Germany", "UK", "EMEA", ...) -> fail, so
   "Remote - Poland" and "Milan, MI, Italy" no longer slip through;
3. only work-mode words ("Remote", "Hybrid", "Remote, Global") -> pass: an
   unqualified remote role is open to target-country candidates;
4. a US state name, a known US/Canadian/Indian city or region -> pass;
5. a known foreign city ("Berlin", "Bogota") -> fail, which keeps ISO country
   codes in "Berlin, DE" / "Bogota, CO" from reading as Delaware / Colorado;
6. a 2-letter state code as a trailing comma token (", CA" / ", CA, US") or a
   leading "AZ - Scottsdale" token -> pass.

An empty or missing location is *unknown*, not foreign, and passes: sources
that omit locations are overwhelmingly US boards, and dropping them silently
would hide real jobs. (Fetchers that default a missing location to "Remote"
reach the same outcome through rule 3.)
"""

from __future__ import annotations

import re
from typing import Any

USA_STATE_NAMES: tuple[str, ...] = (
    'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado',
    'connecticut', 'delaware', 'florida', 'georgia', 'hawaii', 'idaho',
    'illinois', 'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana', 'maine',
    'maryland', 'massachusetts', 'michigan', 'minnesota', 'mississippi',
    'missouri', 'montana', 'nebraska', 'nevada', 'new hampshire', 'new jersey',
    'new mexico', 'new york', 'north carolina', 'north dakota', 'ohio',
    'oklahoma', 'oregon', 'pennsylvania', 'rhode island', 'south carolina',
    'south dakota', 'tennessee', 'texas', 'utah', 'vermont', 'virginia',
    'washington', 'west virginia', 'wisconsin', 'wyoming',
    'district of columbia', 'puerto rico',
)

USA_STATE_CODES: tuple[str, ...] = (
    'al', 'ak', 'az', 'ar', 'ca', 'co', 'ct', 'de', 'fl', 'ga', 'hi', 'id',
    'il', 'in', 'ia', 'ks', 'ky', 'la', 'me', 'md', 'ma', 'mi', 'mn', 'ms',
    'mo', 'mt', 'ne', 'nv', 'nh', 'nj', 'nm', 'ny', 'nc', 'nd', 'oh', 'ok',
    'or', 'pa', 'ri', 'sc', 'sd', 'tn', 'tx', 'ut', 'vt', 'va', 'wa', 'wv',
    'wi', 'wy', 'dc', 'pr',
)

USA_CITY_TERMS: tuple[str, ...] = (
    'new york', 'los angeles', 'chicago', 'houston', 'phoenix', 'philadelphia',
    'san antonio', 'san diego', 'dallas', 'san jose', 'austin', 'jacksonville',
    'fort worth', 'columbus', 'charlotte', 'san francisco', 'indianapolis',
    'seattle', 'denver', 'boston', 'atlanta', 'miami', 'portland', 'las vegas',
    'detroit', 'nashville', 'baltimore', 'milwaukee', 'raleigh', 'tampa',
    'mountain view', 'palo alto', 'menlo park', 'redwood city', 'cupertino',
    'santa clara', 'sunnyvale', 'bellevue', 'redmond', 'kirkland', 'irvine',
    'nyc', 'bay area',
)

CANADA_INDICATOR_TERMS: tuple[str, ...] = (
    'ontario', 'quebec', 'british columbia', 'alberta', 'manitoba',
    'saskatchewan', 'nova scotia', 'new brunswick', 'newfoundland', 'prince edward island',
    'toronto', 'vancouver', 'montreal', 'montréal', 'ottawa', 'calgary', 'edmonton',
    'winnipeg', 'quebec city', 'hamilton', 'kitchener', 'waterloo', 'victoria',
    'london, ontario', 'london, on', 'london on',
)

INDIA_INDICATOR_TERMS: tuple[str, ...] = (
    'bangalore', 'bengaluru', 'hyderabad', 'mumbai', 'delhi', 'pune',
    'chennai', 'kolkata', 'gurgaon', 'gurugram', 'noida', 'ahmedabad', 'jaipur',
    'kochi', 'thiruvananthapuram', 'coimbatore', 'indore', 'nagpur', 'lucknow',
    'chandigarh', 'bhubaneswar', 'visakhapatnam', 'mysore', 'mangalore',
    'karnataka', 'maharashtra', 'telangana', 'tamil nadu', 'kerala', 'andhra pradesh',
    'gujarat', 'rajasthan', 'west bengal', 'uttar pradesh', 'madhya pradesh',
    'haryana', 'punjab', 'bihar', 'odisha', 'jharkhand', 'uttarakhand',
)

# Rule 1. "america" alone is guarded against Latin/South/Central America.
TARGET_COUNTRY_PATTERN = re.compile(
    r'(?<![\w.])(?:'
    r'united\s+states(?:\s+of\s+america)?|united\s+sates|u\.s\.a?\.?|usa|us|'
    r'north\s+america|americas|amer|'
    r'(?<!latin\s)(?<!south\s)(?<!central\s)america|'
    r'canada|india'
    r')(?!\w)',
    re.IGNORECASE,
)

# Rule 2. Countries/regions outside the target set. Names that are also
# common US place names (Peru IN, Panama City FL, Lebanon PA, ...) are left
# out on purpose; "new mexico" / "new england" are guarded by lookbehind.
FOREIGN_COUNTRY_TERMS: tuple[str, ...] = (
    'germany', 'deutschland', 'uk', 'u.k.', 'united kingdom', 'great britain',
    'england', 'scotland', 'wales', 'ireland', 'france', 'spain', 'portugal',
    'italy', 'netherlands', 'belgium', 'luxembourg', 'switzerland', 'austria',
    'poland', 'czechia', 'czech republic', 'slovakia', 'romania', 'hungary',
    'bulgaria', 'serbia', 'croatia', 'greece', 'sweden', 'norway', 'denmark',
    'finland', 'estonia', 'latvia', 'lithuania', 'ukraine', 'turkey', 'türkiye',
    'israel', 'uae', 'united arab emirates', 'saudi arabia', 'egypt', 'nigeria',
    'kenya', 'south africa', 'ghana', 'morocco', 'brazil', 'argentina', 'chile',
    'colombia', 'mexico', 'costa rica', 'uruguay', 'latin america', 'latam',
    'south america', 'central america', 'emea', 'europe', 'apac', 'asia',
    'singapore', 'japan', 'china', 'hong kong', 'taiwan', 'south korea', 'korea',
    'vietnam', 'thailand', 'malaysia', 'indonesia', 'philippines', 'pakistan',
    'bangladesh', 'sri lanka', 'australia', 'new zealand',
)

# Rule 5. Only cities whose "City, XX" form collides with a US state code and
# that have no commonly-listed US namesake (so no Dublin, Paris, Melbourne,
# Vienna, London).
FOREIGN_CITY_TERMS: tuple[str, ...] = (
    'berlin', 'munich', 'münchen', 'hamburg', 'frankfurt', 'bogota', 'bogotá',
    'medellin', 'medellín', 'lagos', 'warsaw', 'krakow', 'kraków', 'wroclaw',
    'madrid', 'barcelona', 'lisbon', 'amsterdam', 'zurich', 'zürich', 'geneva',
    'stockholm', 'copenhagen', 'oslo', 'helsinki', 'prague', 'bucharest',
    'budapest', 'tel aviv', 'dubai', 'cairo', 'nairobi', 'sao paulo', 'são paulo',
    'buenos aires', 'mexico city', 'guadalajara', 'tokyo', 'seoul', 'beijing',
    'shanghai', 'shenzhen', 'taipei', 'manila', 'jakarta', 'bangkok',
    'kuala lumpur', 'sydney',
)

# Rule 3. A segment made only of these words carries no country at all.
WORK_MODE_WORDS = frozenset({
    'remote', 'remotely', 'hybrid', 'onsite', 'on', 'site', 'in', 'office',
    'friendly', 'first', 'only', 'fully', '100', 'global', 'globally',
    'worldwide', 'anywhere', 'all', 'locations', 'location', 'select',
    'multiple', 'work', 'from', 'home', 'wfh', 'the', 'within', 'travel',
    'required', 'preferred', 'distributed', 'virtual', 'or', 'and', 'flexible',
})


def _term_pattern(terms: tuple[str, ...], guards: str = '') -> re.Pattern[str]:
    """Whole-word alternation of ``terms`` (longest first)."""
    alternation = '|'.join(re.escape(t) for t in sorted(terms, key=len, reverse=True))
    return re.compile(rf'(?<![\w.]){guards}(?:{alternation})(?!\w)', re.IGNORECASE)


FOREIGN_COUNTRY_PATTERN = _term_pattern(FOREIGN_COUNTRY_TERMS, guards=r'(?<!new\s)')
FOREIGN_CITY_PATTERN = _term_pattern(FOREIGN_CITY_TERMS)
TARGET_NAME_PATTERN = _term_pattern(
    USA_STATE_NAMES + USA_CITY_TERMS + CANADA_INDICATOR_TERMS + INDIA_INDICATOR_TERMS
)

_CODES = '|'.join(USA_STATE_CODES)
# ", CA" / ", CA, US" / ", CA 94103" / ", CA (Hybrid)" / "AZ - Scottsdale" / "IN".
STATE_CODE_PATTERN = re.compile(
    rf'(?:(?:^|,)\s*(?:{_CODES})\s*(?=$|,|\(|\d)|^(?:{_CODES})\s+-\s)',
    re.IGNORECASE,
)

_SEGMENT_SPLIT_RE = re.compile(r'\s*(?:;|\||•|\n|(?<!,)\s+or\s+)\s*', re.IGNORECASE)
_WORD_RE = re.compile(r'[^\W_]+')


def _is_work_mode_only(segment: str) -> bool:
    words = _WORD_RE.findall(segment)
    return bool(words) and all(word in WORK_MODE_WORDS for word in words)


def _segment_is_valid(segment: str) -> bool:
    """Decide one location segment (see module docstring for the rule order)."""
    if TARGET_COUNTRY_PATTERN.search(segment):
        return True
    if FOREIGN_COUNTRY_PATTERN.search(segment):
        return False
    if _is_work_mode_only(segment):
        return True
    if TARGET_NAME_PATTERN.search(segment):
        return True
    if FOREIGN_CITY_PATTERN.search(segment):
        return False
    return bool(STATE_CODE_PATTERN.search(segment))


def is_valid_location(location: Any) -> bool:
    """True when the location is in USA/Canada/India, remote without a foreign
    country, or unknown (empty / missing)."""
    if not isinstance(location, str):
        return True
    segments = [seg for seg in _SEGMENT_SPLIT_RE.split(location.strip().lower()) if seg.strip()]
    if not segments:
        return True
    return any(_segment_is_valid(seg.strip()) for seg in segments)

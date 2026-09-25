"""Job categories and company tiers.

``CATEGORY_PATTERNS`` is the single source of truth for category ids: the
README COUNT markers and the site (site/src/lib/taxonomy.js) are
checked against it by tests/test_category_taxonomy_sync.py.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from functools import lru_cache
from typing import Any

from ngj.util import get_nested_value

# FAANG_PLUS: Companies classified as the "FAANG+" company tier.
# Consumed by: get_company_tier().
# This classification surfaces in the frontend's "FAANG+" company-tier filter.
# To add a company: append its canonical name. Lookups use normalize_company_name(),
# so variants like "Snap Inc." or "Amazon.com" need no separate alias.
# A company may appear in both FAANG_PLUS and a sector set (e.g., DEFENSE) simultaneously.
FAANG_PLUS = {
    # Original FAANG
    'Google', 'Meta', 'Facebook', 'Amazon', 'Apple', 'Netflix', 'Microsoft',
    # Extended FAANG+
    'NVIDIA', 'Tesla', 'Adobe', 'Salesforce', 'Oracle', 'IBM', 'Intel',
    'Cisco', 'Qualcomm', 'AMD', 'Uber', 'Lyft', 'Airbnb', 'Stripe', 'PayPal',
    'Block (Square)', 'Visa', 'Mastercard', 'Goldman Sachs', 'Morgan Stanley',
    'JPMorgan', 'J.P. Morgan', 'JPMorgan Chase', 'Bloomberg', 'Two Sigma', 'Citadel', 'Jane Street', 'D.E. Shaw',
    # Defense/Aerospace Giants
    'Raytheon', 'RTX', 'Lockheed Martin', 'Boeing', 'Northrop Grumman',
    'General Dynamics', 'BAE Systems', 'L3Harris', 'Collins Aerospace', 'HII',
    'Huntington Ingalls Industries',
    # Finance/Insurance
    'Wells Fargo', 'Travelers', 'Charles Schwab', 'American Express', 'AMEX',
    'Bank of America', 'Capital One', 'Fidelity', 'State Street', 'TD Bank',
    'Truist Bank', 'Global Payments',
    # Tech Giants
    'TikTok', 'ByteDance', 'Snap', 'Autodesk', 'Akamai', 'DXC Technology',
    'Yahoo', 'Intuit', 'HP', 'Hewlett Packard', 'HPE', 'Hewlett Packard Enterprise',
    'Honeywell', 'Cadence Design Systems', 'Microchip Technology',
    # Entertainment
    'Electronic Arts', 'EA', 'Walt Disney Company', 'Disney', 'Nike',
    'McDonald\'s', 'Expedia Group', 'TripAdvisor',
}

# UNICORNS: High-growth private companies classified as the "Unicorn" company tier.
# Consumed by: get_company_tier().
# This classification surfaces in the frontend's "Unicorn" company-tier filter.
# To add a company: append its canonical name. Lookups use normalize_company_name(),
# so variants like "Snap Inc." or "Amazon.com" need no separate alias.
# A company may appear in both UNICORNS and a sector set (e.g., FINANCE) simultaneously.
UNICORNS = {
    'SpaceX', 'OpenAI', 'Anthropic', 'Databricks', 'Snowflake', 'Palantir',
    'Plaid', 'Robinhood', 'Coinbase', 'Ripple', 'Discord', 'Reddit',
    'Pinterest', 'Snap', 'Instacart', 'DoorDash', 'Figma', 'Notion',
    'Airtable', 'Canva', 'Scale AI', 'Roblox', 'Unity Technologies',
    'Twitch', 'GitLab', 'HashiCorp', 'Datadog', 'MongoDB', 'Elastic',
    'Cloudflare', 'Okta', 'Twilio', 'Atlassian', 'Asana', 'Dropbox',
    'Zoom', 'Slack', 'Vercel', 'Supabase', 'PlanetScale', 'Nuro', 'Waymo',
    'Cruise', 'Aurora', 'Rivian', 'Lucid', 'Chime', 'Brex', 'Affirm',
    'SoFi', 'Upstart', 'Checkout.com', 'Revolut', 'Nubank', 'Klarna',
    'Grammarly', 'Duolingo', 'Coursera', 'Khan Academy',
    'Sierra Space', 'Relativity Space', 'Qumulo', 'Zealthy',
    # New from SimplifyJobs
    'Verkada', 'Samsara', 'Glean', 'Sigma Computing', 'Cerebras', 'Cerebras Systems',
    'Applied Intuition', 'Fireworks AI', 'Suno', 'Sierra', 'WhatNot',
    'Whoop', 'Benchling', 'Marqeta', 'Circle', 'Zip', 'Finix', 'Valon',
    'True Anomaly', 'Anduril', 'Shield AI', 'Blue Origin', 'Rocket Lab', 'Rocket Lab USA',
    'Etsy', 'Chewy', 'StubHub', 'SeatGeek', 'Ticketmaster', 'Fanatics',
    'Underdog Fantasy', 'Glide', 'TRM Labs', 'Pattern Data', 'Crusoe',
    'Replit', 'Continue', 'Meshy', 'WeRide', 'Trexquant',
}

# DEFENSE: Companies classified globally under the defense and aerospace sector tier.
# Consumed by: get_company_tier().
# This classification surfaces in the frontend's "Defense" company-tier filter.
# To add a company: append its canonical name. Lookups use normalize_company_name(),
# so variants like "Snap Inc." or "Amazon.com" need no separate alias.
# A company may appear in both DEFENSE and a tier set (e.g., FAANG_PLUS) simultaneously.
DEFENSE = {
    'Raytheon', 'RTX', 'Lockheed Martin', 'Boeing', 'Northrop Grumman',
    'General Dynamics', 'General Dynamics Mission Systems', 'General Dynamics Information Technology',
    'BAE Systems', 'L3Harris', 'Collins Aerospace', 'HII', 'Huntington Ingalls Industries',
    'Booz Allen Hamilton', 'Booz Allen', 'Leidos', 'SAIC', 'General Atomics', 'Anduril',
    'Shield AI', 'SpaceX', 'Sierra Space', 'Relativity Space', 'Blue Origin',
    'Rocket Lab', 'Rocket Lab USA', 'True Anomaly', 'KBR', 'CACI', 'Peraton', 'Amentum',
    'AMERICAN SYSTEMS', 'T-Rex Solutions', 'Wyetech', 'Altamira Technologies',
}

# FINANCE: Companies classified globally under the finance and banking sector tier.
# Consumed by: get_company_tier().
# This classification surfaces in the frontend's "Finance" company-tier filter.
# To add a company: append its canonical name. Lookups use normalize_company_name(),
# so variants like "Snap Inc." or "Amazon.com" need no separate alias.
# A company may appear in both FINANCE and a tier set (e.g., UNICORNS) simultaneously.
FINANCE = {
    'Goldman Sachs', 'Morgan Stanley', 'JPMorgan', 'J.P. Morgan', 'JP Morgan Chase', 'Bloomberg',
    'Two Sigma', 'Citadel', 'Citadel Securities', 'Jane Street', 'D.E. Shaw', 'DE Shaw', 'DRW',
    'Wolverine Trading', 'Trexquant',
    'Wells Fargo', 'Charles Schwab', 'American Express', 'AMEX', 'Visa', 'Mastercard',
    'PayPal', 'Block (Square)', 'Square', 'Stripe', 'Plaid',
    'Robinhood', 'Coinbase', 'Chime', 'Brex', 'Affirm', 'SoFi', 'Upstart',
    'Travelers', 'Fidelity', 'BlackRock', 'Capital One', 'Bank of America',
    'State Street', 'TD Bank', 'Truist Bank', 'Global Payments',
    'Apex Fintech Solutions', 'Marqeta', 'Circle', 'Finix', 'Zip', 'Valon',
    'GM financial', 'Nelnet', 'Aflac',
}

# HEALTHCARE: Companies classified globally under the healthcare and biotech sector tier.
# Consumed by: get_company_tier().
# This classification surfaces in the frontend's "Healthcare" company-tier filter.
# To add a company: append its canonical name. Lookups use normalize_company_name(),
# so variants like "Snap Inc." or "Amazon.com" need no separate alias.
# A company may appear in both HEALTHCARE and a tier set (e.g., STARTUPS) simultaneously.
HEALTHCARE = {
    'iRhythm', 'Epic Systems', 'Cerner', 'Philips Healthcare', 'Siemens Healthineers',
    'GE Healthcare', 'Medtronic', 'Johnson & Johnson', 'Pfizer', 'Moderna',
    'UnitedHealth', 'Anthem', 'CVS Health', 'Cigna', 'Humana', 'Oscar Health',
    'Tempus', 'Flatiron Health', 'Veracyte', 'Illumina', 'Thermo Fisher',
    'Boston Scientific', 'MultiCare Health System', 'BlueCross BlueShield',
    'Citizen Health', 'Solace Health', 'Healthfirst', 'Candid Health', 'MedImpact',
}

# STARTUPS: Early-stage or smaller companies classified as the "Startup" tier.
# Consumed by: get_company_tier().
# This classification surfaces in the frontend's "Startup" company-tier filter.
# To add a company: append its canonical name. Lookups use normalize_company_name(),
# so variants like "Snap Inc." or "Amazon.com" need no separate alias.
# A company may appear in both STARTUPS and a sector set simultaneously.
STARTUPS = {
    'Vercel', 'Supabase', 'PlanetScale', 'Railway', 'Zepto', 'Zepz',
    'Zealthy', 'Qumulo', 'Runway', 'Hugging Face', 'Weights & Biases',
    'Cohere', 'Mistral', 'Perplexity', 'Replit', 'Modal', 'Resend',
    'Glide', 'Continue', 'Meshy', 'Suno', 'Fireworks AI', 'Nexthop.ai',
    'SpruceID', 'Netic', 'D3', 'Promise', 'Lightfield', 'Fermat', 'N1',
    'OffDeal', 'Eventual', 'Mechanize', 'Remi', 'TrueBuilt', 'Uare.ai',
}

# CATEGORY_PATTERNS: Job categories based on exact title keywords.
# Consumed by: categorize_job().
# This classification determines the category emoji, section, and grouping in the frontend output.
# To add a new category: create a new dictionary key with 'name', 'emoji', and a 'keywords' list.
# To add a new keyword to a category: append the lowercase keyword to the appropriate 'keywords' list.
# Note on matching: Keywords are matched using word boundaries (exact phrase matching using regex '\b').
# If no keyword matches naturally, the job defaults to the 'other' category block.
CATEGORY_PATTERNS = {
    # Specialty engineering tracks. These are matched against the job TITLE only
    # (see TITLE_DRIVEN_CATEGORIES) so a backend role whose description merely
    # mentions "frontend" is not misfiled, and they are ordered before the broad
    # 'software_engineering' bucket so a titled specialist wins over the general
    # match.
    'security': {
        'name': 'Security Engineering',
        'emoji': '🔒',
        'keywords': [
            'security engineer', 'security analyst', 'application security',
            'appsec', 'infosec', 'cybersecurity', 'cyber security',
            'cloud security', 'product security', 'devsecops',
            'penetration tester', 'security researcher'
        ]
    },
    'mobile': {
        'name': 'Mobile Engineering',
        'emoji': '📲',
        'keywords': [
            'mobile engineer', 'mobile developer', 'mobile software engineer',
            'mobile application', 'ios engineer', 'ios developer',
            'android engineer', 'android developer', 'react native',
            'ios', 'android'
        ]
    },
    'frontend': {
        'name': 'Frontend Engineering',
        'emoji': '🎨',
        'keywords': [
            'frontend', 'front-end', 'front end', 'ui engineer',
            'ui developer', 'web developer'
        ]
    },
    'backend': {
        'name': 'Backend Engineering',
        'emoji': '⚙️',
        'keywords': [
            'backend', 'back-end', 'back end', 'server-side', 'server side',
            'api engineer'
        ]
    },
    'software_engineering': {
        'name': 'Software Engineering',
        'emoji': '💻',
        'keywords': [
            'software engineer', 'software developer', 'swe', 'full stack',
            'fullstack', 'application developer', 'systems engineer',
            'platform engineer', 'solutions engineer', 'integration engineer',
            'developer advocate', 'devrel'
        ]
    },
    'data_ml': {
        'name': 'Data Science & ML',
        'emoji': '🤖',
        'keywords': [
            'data scientist', 'machine learning', 'ml engineer', 'ai engineer',
            'deep learning', 'nlp', 'computer vision', 'research scientist',
            'applied scientist', 'research engineer', 'ai research'
        ]
    },
    'data_engineering': {
        'name': 'Data Engineering',
        'emoji': '📊',
        'keywords': [
            'data engineer', 'data analyst', 'analytics engineer', 'bi developer',
            'business intelligence', 'etl', 'data platform', 'data infrastructure'
        ]
    },
    'infrastructure_sre': {
        'name': 'Infrastructure & SRE',
        'emoji': '🏗️',
        'keywords': [
            'sre', 'site reliability', 'devops', 'infrastructure', 'platform',
            'cloud engineer', 'systems administrator', 'network engineer',
            'network automation', 'noc', 'network operations center', 'network operations',
            'network performance', 'netops', 'network ops', 'noc engineer',
            'reliability engineer'
        ]
    },
    'product_management': {
        'name': 'Product Management',
        'emoji': '📱',
        'keywords': [
            'product manager', 'program manager', 'technical program manager',
            'tpm', 'product owner', 'product lead'
        ]
    },
    'quant_finance': {
        'name': 'Quantitative Finance',
        'emoji': '📈',
        'keywords': [
            'quantitative', 'quant', 'trading', 'trader', 'strategist',
            'quantitative analyst', 'quantitative developer', 'algo'
        ]
    },
    'hardware': {
        'name': 'Hardware & Mechanical Engineering',
        'emoji': '🔧',
        'keywords': [
            'hardware engineer', 'electrical engineer', 'mechanical engineer',
            'embedded', 'firmware', 'asic', 'fpga', 'chip', 'silicon',
            'rf engineer', 'antenna', 'circuit', 'pcb'
        ]
    },
    'other': {
        'name': 'Other',
        'emoji': '💼',
        'keywords': []
    }
}

# Categories matched against the job title only (not the description) to keep
# fine-grained specialty buckets from being polluted by incidental mentions of
# an adjacent stack in a long job description.
TITLE_DRIVEN_CATEGORIES = frozenset({'security', 'mobile', 'frontend', 'backend'})

# TITLE_FALLBACK_PATTERNS: generic words that classify a role only after every
# exact CATEGORY_PATTERNS phrase has failed on the title. Matched on the TITLE
# only, whole words, in this order (a category may appear once). Without them
# "Associate Engineer Software", "Junior Developer" and "Manufacturing Engineer
# II" all landed in 'other', which at one point held a quarter of the board.
TITLE_FALLBACK_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ('security', ('cyber', 'security')),
    ('data_ml', ('ai', 'artificial intelligence', 'ml', 'data science')),
    ('data_engineering', ('data', 'analytics')),
    ('infrastructure_sre', (
        'it support', 'help desk', 'service desk', 'desktop support',
        'it specialist', 'it analyst', 'system administrator', 'sysadmin', 'cloud',
    )),
    ('software_engineering', (
        'software', 'developer', 'programmer', 'computer science',
        'computer scientist', 'sdet', 'qa', 'quality assurance', 'test automation',
    )),
    ('hardware', (
        'mechanical', 'electrical', 'electronics', 'electronic', 'manufacturing',
        'industrial engineer', 'industrial engineering', 'quality engineer',
        'quality engineering', 'test engineer', 'test engineering',
        'process engineer', 'process engineering', 'controls', 'automation',
        'design engineer', 'aerospace', 'avionics', 'structural', 'materials',
        'semiconductor', 'gnc', 'guidance navigation', 'thermal', 'propulsion',
        'optical', 'photonics', 'power engineer', 'power electronics',
        'validation engineer', 'tooling', 'composites',
    )),
)

NETWORK_INFRASTRUCTURE_KEYWORDS = {
    'network engineer',
    'network automation',
    'noc',
    'network operations center',
    'network operations',
    'network performance',
    'netops',
    'network ops',
    'noc engineer',
}

NETWORK_ENGINEERING_TITLE_PATTERN = re.compile(
    r"\b(?:"
    r"network(?:ing)? engineer|"
    r"network(?:ing)? (?:security|automation|performance) engineer|"
    r"network operations engineer|"
    r"network operations center engineer|"
    r"network ops engineer|"
    r"netops engineer|"
    r"noc engineer|"
    r"systems engineer\b\s*,\s*networks?|"
    r"network(?:ing)?\s+(?:infrastructure|services|platforms?|reliability|security)\s+"
    r"(?:engineer|engineering|operations|operator|specialist|technician|admin(?:istrator)?)|"
    r"(?:software|systems|data|platform|cloud|devops|site reliability|sre) engineer[^\n]*\b(?:networking|network performance|network services|network platforms?|network reliability|network security)"
    r")\b",
    re.IGNORECASE,
)


def is_engineering_network_title(title: str) -> bool:
    """Return whether a network title is engineering or infrastructure focused.

    Args:
        title: Job title text to evaluate.

    Returns:
        True if the title is a string and matches an engineering-focused
        network-role pattern, otherwise False.
    """
    return isinstance(title, str) and bool(NETWORK_ENGINEERING_TITLE_PATTERN.search(title))


# TPM titles outrank the generic buckets ('infrastructure', 'platform') that a
# "Technical Program Manager, Infrastructure" title also contains.
_TPM_TITLE_RE = re.compile(r'\b(?:tpm|technical program manager)s?\b', re.IGNORECASE)


def _category_keywords(category_id: str) -> list[str]:
    keywords = CATEGORY_PATTERNS[category_id]['keywords']
    if category_id == 'infrastructure_sre':
        # Network roles are decided by is_engineering_network_title() on the title.
        return [kw for kw in keywords if kw not in NETWORK_INFRASTRUCTURE_KEYWORDS]
    return list(keywords)


# One precompiled whole-phrase regex per category, in CATEGORY_PATTERNS order.
CATEGORY_REGEXES: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (
        category_id,
        re.compile(
            r'\b(?:'
            + '|'.join(re.escape(kw) for kw in sorted(_category_keywords(category_id), key=len, reverse=True))
            + r')\b',
            re.IGNORECASE,
        ),
    )
    for category_id in CATEGORY_PATTERNS
    if category_id != 'other' and _category_keywords(category_id)
)


def _phrase_regex(keywords: tuple[str, ...] | list[str]) -> re.Pattern[str]:
    return re.compile(
        r'\b(?:' + '|'.join(re.escape(kw) for kw in sorted(keywords, key=len, reverse=True)) + r')\b',
        re.IGNORECASE,
    )


TITLE_FALLBACK_REGEXES: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (category_id, _phrase_regex(keywords)) for category_id, keywords in TITLE_FALLBACK_PATTERNS
)


def _category(category_id: str) -> dict[str, Any]:
    info = CATEGORY_PATTERNS[category_id]
    return {'id': category_id, 'name': info['name'], 'emoji': info['emoji']}


def _first_match(text: str, *, skip_title_driven: bool) -> str | None:
    for category_id, pattern in CATEGORY_REGEXES:
        if skip_title_driven and category_id in TITLE_DRIVEN_CATEGORIES:
            continue
        if pattern.search(text):
            return category_id
    return None


def _first_title_fallback(title: str) -> str | None:
    for category_id, pattern in TITLE_FALLBACK_REGEXES:
        if pattern.search(title):
            return category_id
    return None


def categorize_job(title: str, description: str = '') -> dict[str, Any]:
    """Categorize a job, title first.

    1. TPM titles -> product_management; engineering network titles ->
       infrastructure_sre.
    2. The first category (CATEGORY_PATTERNS order) whose keywords appear in
       the TITLE wins, so "Data Scientist II" is data_ml even when its
       description says "software engineer".
    3. Then the generic TITLE_FALLBACK_PATTERNS words on the title ("software",
       "developer", "mechanical", ...).
    4. Only when the title matches nothing is the description consulted, and
       never for the title-driven specialty buckets (frontend/backend/...).
    """
    title = title if isinstance(title, str) else ''
    description = description if isinstance(description, str) else ''

    if _TPM_TITLE_RE.search(title):
        return _category('product_management')
    if is_engineering_network_title(title):
        return _category('infrastructure_sre')

    category_id = _first_match(title, skip_title_driven=False)
    if category_id is None:
        category_id = _first_title_fallback(title)
    if category_id is None and description:
        category_id = _first_match(description, skip_title_driven=True)
    return _category(category_id or 'other')


# Company-name normalization for tier lookups: "Snap Inc." == "Snap",
# "Amazon.com" == "Amazon", "JPMorganChase" == "JP Morgan Chase". Only
# trailing legal/corporate suffixes are dropped; no prefix or fuzzy matching,
# so "Snapdragon" never becomes "Snap" and "Amazon Web Services" stays distinct.
_COMPANY_SUFFIXES = frozenset({
    'inc', 'incorporated', 'llc', 'llp', 'lp', 'ltd', 'limited', 'plc', 'corp',
    'corporation', 'co', 'company', 'industries', 'technologies', 'technology',
    'holdings', 'group', 'com',
})
_COMPANY_TOKEN_RE = re.compile(r'[^\W_]+')


def normalize_company_name(name: Any) -> str:
    """Casefolded, punctuation-free key with trailing corporate suffixes removed."""
    if not isinstance(name, str):
        return ''
    tokens = _COMPANY_TOKEN_RE.findall(name.casefold().replace('&', ' and '))
    if tokens and tokens[0] == 'the':
        tokens = tokens[1:]
    while len(tokens) > 1 and tokens[-1] in _COMPANY_SUFFIXES:
        tokens = tokens[:-1]
    while len(tokens) > 1 and tokens[-1] == 'and':
        tokens = tokens[:-1]
    return ''.join(tokens)


def _normalized_set(names: set[str]) -> frozenset[str]:
    return frozenset(key for key in map(normalize_company_name, names) if key)


_NORMALIZED_FAANG_PLUS = _normalized_set(FAANG_PLUS)
_NORMALIZED_UNICORNS = _normalized_set(UNICORNS)
_NORMALIZED_SECTORS: tuple[tuple[str, frozenset[str]], ...] = (
    ('defense', _normalized_set(DEFENSE)),
    ('finance', _normalized_set(FINANCE)),
    ('healthcare', _normalized_set(HEALTHCARE)),
    ('startup', _normalized_set(STARTUPS)),
)


def _company_keys(company_name: Any) -> frozenset[str]:
    """Normalized keys for the name and each "A | B" alias part."""
    if not isinstance(company_name, str):
        return frozenset()
    parts = [company_name, *company_name.split('|')]
    return frozenset(key for key in map(normalize_company_name, parts) if key)


@lru_cache(maxsize=2048)
def _company_tier_parts(company_name: Any) -> tuple[str, str, str, tuple[str, ...]]:
    """Cached (tier, emoji, label, sectors) lookup; company names repeat a lot."""
    keys = _company_keys(company_name)
    if keys & _NORMALIZED_FAANG_PLUS:
        tier = ('faang_plus', '🔥', 'FAANG+')
    elif keys & _NORMALIZED_UNICORNS:
        tier = ('unicorn', '🚀', 'Unicorn')
    else:
        tier = ('other', '', '')

    # Sector classifications can overlap with the tier.
    sectors = tuple(sector for sector, members in _NORMALIZED_SECTORS if keys & members)
    return (*tier, sectors)


def get_company_tier(company_name: Any) -> dict[str, Any]:
    """Company tier classification including sectors (a fresh dict per call)."""
    tier, emoji, label, sectors = _company_tier_parts(company_name if isinstance(company_name, str) else '')
    return {'tier': tier, 'emoji': emoji, 'label': label, 'sectors': list(sectors)}


def iter_category_ids(job: dict[str, Any]) -> Iterator[str]:
    """Yield normalized category IDs from enriched or legacy job category data."""
    if not isinstance(job, dict):
        return

    category_id = get_nested_value(job, 'category.id')
    if isinstance(category_id, str):
        normalized = category_id.strip()
        if normalized:
            yield normalized
            return

    legacy_categories = job.get('categories', [])
    if not isinstance(legacy_categories, list):
        return

    for category in legacy_categories:
        if isinstance(category, str):
            normalized = category.strip()
            if normalized:
                yield normalized

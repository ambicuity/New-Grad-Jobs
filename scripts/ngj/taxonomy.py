"""Job categories and company tiers.

``CATEGORY_PATTERNS`` is the single source of truth for category ids: the
README COUNT markers and the terminal site (docs/terminal/data.jsx) are
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
# To add a company: append its name exactly as it appears in job API responses.
# A company may appear in both FAANG_PLUS and a sector set (e.g., DEFENSE) simultaneously.
FAANG_PLUS = {
    # Original FAANG
    'Google', 'Meta', 'Facebook', 'Amazon', 'Apple', 'Netflix', 'Microsoft',
    # Extended FAANG+
    'NVIDIA', 'Tesla', 'Adobe', 'Salesforce', 'Oracle', 'IBM', 'Intel',
    'Cisco', 'Qualcomm', 'AMD', 'Uber', 'Lyft', 'Airbnb', 'Stripe', 'PayPal',
    'Block (Square)', 'Visa', 'Mastercard', 'Goldman Sachs', 'Morgan Stanley',
    'JPMorgan', 'J.P. Morgan', 'Bloomberg', 'Two Sigma', 'Citadel', 'Jane Street', 'D.E. Shaw',
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
# To add a company: append its name exactly as it appears in job API responses.
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
# To add a company: append its name exactly as it appears in job API responses.
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
# To add a company: append its name exactly as it appears in job API responses.
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
# To add a company: append its name exactly as it appears in job API responses.
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
# To add a company: append its name exactly as it appears in job API responses.
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
        'name': 'Hardware Engineering',
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


def categorize_job(title: str, description: str = '') -> dict[str, Any]:
    """Categorize a job based on its title and description"""
    title_lower = title.lower()
    desc_lower = description.lower() if description else ''
    combined = f"{title_lower} {desc_lower}"

    # Priority check for TPM to avoid matching generic 'infrastructure' or 'program' first
    if re.search(r'\btpm\b', combined):
        return {
            'id': 'product_management',
            'name': CATEGORY_PATTERNS['product_management']['name'],
            'emoji': CATEGORY_PATTERNS['product_management']['emoji']
        }

    # Keep network categorization title-driven so non-engineering roles with
    # incidental network wording in descriptions do not leak into infra views.
    if is_engineering_network_title(title):
        category_id = 'infrastructure_sre'
        return {
            'id': category_id,
            'name': CATEGORY_PATTERNS[category_id]['name'],
            'emoji': CATEGORY_PATTERNS[category_id]['emoji']
        }

    for category_id, category_info in CATEGORY_PATTERNS.items():
        if category_id == 'other':
            continue
        # Specialty tracks (frontend/backend/mobile/security) match on the title
        # only: a title is an unambiguous signal, whereas descriptions routinely
        # mention adjacent stacks ("partner with the frontend team") and would
        # cross-contaminate these fine-grained buckets.
        haystack = title_lower if category_id in TITLE_DRIVEN_CATEGORIES else combined
        for keyword in category_info['keywords']:
            if category_id == 'infrastructure_sre' and keyword in NETWORK_INFRASTRUCTURE_KEYWORDS:
                continue
            # Use word boundaries for exact phrase matching, safely escape the keyword
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, haystack):
                return {
                    'id': category_id,
                    'name': category_info['name'],
                    'emoji': category_info['emoji']
                }

    # Default to 'other' if no match
    return {
        'id': 'other',
        'name': CATEGORY_PATTERNS['other']['name'],
        'emoji': CATEGORY_PATTERNS['other']['emoji']
    }


@lru_cache(maxsize=2048)
def _company_tier_parts(company_name: str) -> tuple:
    """Cached (tier, emoji, label, sectors) lookup; company names repeat a lot."""
    if company_name in FAANG_PLUS:
        tier = ('faang_plus', '🔥', 'FAANG+')
    elif company_name in UNICORNS:
        tier = ('unicorn', '🚀', 'Unicorn')
    else:
        tier = ('other', '', '')

    # Sector classifications can overlap with the tier.
    sectors = tuple(
        sector
        for sector, members in (
            ('defense', DEFENSE),
            ('finance', FINANCE),
            ('healthcare', HEALTHCARE),
            ('startup', STARTUPS),
        )
        if company_name in members
    )
    return tier + (sectors,)


def get_company_tier(company_name: str) -> dict[str, Any]:
    """Company tier classification including sectors (a fresh dict per call)."""
    tier, emoji, label, sectors = _company_tier_parts(company_name)
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

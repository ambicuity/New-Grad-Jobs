#!/usr/bin/env python3
"""
New Grad Jobs Aggregator
Scrapes job postings from Greenhouse, Lever, Google Careers and JobSpy APIs
and updates README.md and jobs.json

Performance Optimizations:
- Connection pooling with persistent sessions
- HTTP/1.1 keep-alive for connection reuse
- Increased parallelism (50+ concurrent workers)
- Compressed responses (gzip/brotli)
- Reduced timeouts with better retry logic
- DNS caching and TCP connection reuse
"""

import json
import math
import os
import random
import re
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Dict, List
from urllib.parse import urlencode, urlparse
from xml.sax.saxutils import escape as xml_escape

import requests
import yaml
from dateutil import parser as date_parser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Optional NumPy import for robust float handling (e.g. from JobSpy/pandas)
try:
    import numpy as np
except ImportError:
    np = None

# Worker pool configuration constants
# These default values act as fallback constants. The active pool sizes
# are read from config.yml under 'worker_pools' during startup.
# Minimums are baseline parallel requests; maximums represent empirically-tested API rate limit boundaries.
DEFAULT_GREENHOUSE_MIN_WORKERS: int = 30
DEFAULT_GREENHOUSE_MAX_WORKERS: int = 300
DEFAULT_LEVER_MIN_WORKERS: int = 15
DEFAULT_LEVER_MAX_WORKERS: int = 200
DEFAULT_GOOGLE_MIN_WORKERS: int = 12
DEFAULT_GOOGLE_MAX_WORKERS: int = 100

# Default Google Careers HTML page parsing limit.
DEFAULT_GOOGLE_MAX_PAGES: int = 3
GOOGLE_MAX_PAGES: int = DEFAULT_GOOGLE_MAX_PAGES

# Constants for fixed worker pools
DEFAULT_JOBSPY_WORKERS: int = 25
DEFAULT_ORCHESTRATOR_WORKERS: int = 20

# Default per-request timeout (seconds) used by all HTTP fetch functions.
# Sourced from empirical testing: p95 latency for Greenhouse/Lever/Google APIs is <2s.
# Override per-call by passing timeout=<int> if a specific source needs more headroom.
DEFAULT_TIMEOUT: int = 5

# Default page limit for Workday API pagination.
# Validated against Workday CXS API defaults; overridden by config.yml if present.
DEFAULT_WORKDAY_PAGE_LIMIT: int = 20
WORKDAY_PAGE_LIMIT: int = DEFAULT_WORKDAY_PAGE_LIMIT

# Maximum total jobs to fetch per company from Workday for safety/performance.
# Guardrail to prevent infinite loops; overridden by config.yml if present.
DEFAULT_WORKDAY_MAX_JOBS_PER_COMPANY: int = 200
WORKDAY_MAX_JOBS_PER_COMPANY: int = DEFAULT_WORKDAY_MAX_JOBS_PER_COMPANY

# Default countries used by JobSpy when none are specified in configuration.
# Consumed by: fetch_jobspy_jobs()
DEFAULT_JOBSPY_COUNTRIES: List[Dict[str, str]] = [
    {'code': 'USA', 'location': 'United States'},
    {'code': 'Canada', 'location': 'Canada'},
    {'code': 'India', 'location': 'India'},
]


# Import JobSpy for additional job site scraping
try:
    from jobspy import scrape_jobs
    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False
    print("⚠️  JobSpy not available. Install with: pip install python-jobspy")

# ============================================================================
# PERFORMANCE OPTIMIZATION: CONNECTION POOLING & SESSION MANAGEMENT
# ============================================================================

def create_optimized_session() -> requests.Session:
    """
    Create a requests session with optimized settings for high-performance scraping:
    - Connection pooling (50 connections per host)
    - Automatic retries with exponential backoff
    - HTTP keep-alive for connection reuse
    - Compression support (gzip, deflate, br)
    - DNS caching via connection pooling
    """
    session = requests.Session()

    # Configure retry strategy with exponential backoff
    retry_strategy = Retry(
        total=3,  # Max 3 retries
        backoff_factor=0.3,  # Wait 0.3, 0.6, 1.2 seconds between retries
        status_forcelist=[422, 429, 500, 502, 503, 504],  # Retry on these HTTP codes (422 = Workday CSRF expired)
        allowed_methods=["GET", "POST"],  # Retry GET and POST
    )

    # Configure HTTP adapter with connection pooling
    # AGGRESSIVE for 10K companies: 1000 pools, 300 connections/host
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=1000,  # Number of connection pools (10K companies)
        pool_maxsize=300,  # Maximum connections per host (massive parallelism)
        pool_block=False  # Don't block on connection pool exhaustion
    )

    # Mount adapter for both HTTP and HTTPS
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set default headers for compression and keep-alive with extended timeout
    session.headers.update({
        'Accept-Encoding': 'gzip, deflate, br',  # Request compressed responses
        'Connection': 'keep-alive',  # Reuse TCP connections
        'Keep-Alive': 'timeout=60, max=2000',  # Keep connections alive longer
        'User-Agent': 'NewGradJobs-Aggregator/3.0 (10K-Companies-Optimized)'
    })

    return session

# Global session for connection reuse across all requests
HTTP_SESSION = create_optimized_session()

# Module-level lock for thread-safe counter updates in parallel fetchers
_COUNTER_LOCK = threading.Lock()


def _coerce_positive_int(value: Any, default: int, name: str) -> int:
    """Parse a positive integer or fall back to the provided default."""
    if value is None:
        return default
    if isinstance(value, bool):
        print(f"  ⚠️  Invalid {name}={value!r}; using default {default}")
        return default
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = int(value.strip())
        except ValueError:
            print(f"  ⚠️  Invalid {name}={value!r}; using default {default}")
            return default
    else:
        print(f"  ⚠️  Invalid {name}={value!r}; using default {default}")
        return default

    if parsed <= 0:
        print(f"  ⚠️  Invalid {name}={value!r}; using default {default}")
        return default
    return parsed


class DomainConcurrencyLimiter:
    """Thread-safe per-domain concurrency limiter using native Python primitives.

    Domains with configured limits are guarded by a BoundedSemaphore. Domains
    without explicit limits are left unthrottled.
    """

    def __init__(self, limits: Dict[str, int]):
        self._limits = {
            domain.lower(): limit
            for domain, limit in limits.items()
            if isinstance(limit, int) and limit > 0
        }
        self._lock = threading.Lock()
        self._semaphores: Dict[str, threading.BoundedSemaphore] = {}

    def _domain_for_url(self, url: str) -> str:
        return (urlparse(url).netloc or "").split(":")[0].lower()

    def _matched_domain(self, domain: str) -> str | None:
        if domain in self._limits:
            return domain

        # Support subdomains matching, e.g. jobs.api.greenhouse.io -> api.greenhouse.io
        for configured_domain in self._limits:
            if domain.endswith(f".{configured_domain}"):
                return configured_domain

        return None

    def _get_semaphore(self, domain: str) -> threading.BoundedSemaphore | None:
        matched_domain = self._matched_domain(domain)
        if matched_domain is None:
            return None

        limit = self._limits[matched_domain]
        with self._lock:
            semaphore = self._semaphores.get(matched_domain)
            if semaphore is None:
                semaphore = threading.BoundedSemaphore(limit)
                self._semaphores[matched_domain] = semaphore
            return semaphore

    @contextmanager
    def acquire(self, url: str):
        domain = self._domain_for_url(url)
        semaphore = self._get_semaphore(domain)
        if semaphore is None:
            yield
            return

        semaphore.acquire()
        try:
            yield
        finally:
            semaphore.release()


# Cap greenhouse API concurrency while leaving other domains unthrottled.
DOMAIN_LIMITER = DomainConcurrencyLimiter({"api.greenhouse.io": 10})


def limited_get(url: str, **kwargs):
    """HTTP GET wrapped with domain-aware concurrency limiting."""
    with DOMAIN_LIMITER.acquire(url):
        return HTTP_SESSION.get(url, **kwargs)


def limited_post(url: str, **kwargs):
    """HTTP POST wrapped with domain-aware concurrency limiting."""
    with DOMAIN_LIMITER.acquire(url):
        return HTTP_SESSION.post(url, **kwargs)

# ============================================================================
# COMPANY CLASSIFICATIONS
# ============================================================================

# FAANG_PLUS: Companies classified as the "FAANG+" company tier.
# Consumed by: get_company_tier() at line ~302.
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
# Consumed by: get_company_tier() at line ~302.
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
# Consumed by: get_company_tier() at line ~302.
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
# Consumed by: get_company_tier() at line ~302.
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
# Consumed by: get_company_tier() at line ~302.
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
# Consumed by: get_company_tier() at line ~302.
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
# Consumed by: categorize_job() at line ~280.
# This classification determines the category emoji, section, and grouping in the frontend output.
# To add a new category: create a new dictionary key with 'name', 'emoji', and a 'keywords' list.
# To add a new keyword to a category: append the lowercase keyword to the appropriate 'keywords' list.
# Note on matching: Keywords are matched using word boundaries (exact phrase matching using regex '\b').
# If no keyword matches naturally, the job defaults to the 'other' category block.
CATEGORY_PATTERNS = {
    'software_engineering': {
        'name': 'Software Engineering',
        'emoji': '💻',
        'keywords': [
            'software engineer', 'software developer', 'swe', 'full stack',
            'fullstack', 'frontend', 'front-end', 'backend', 'back-end',
            'web developer', 'mobile developer', 'ios developer', 'android developer',
            'application developer', 'systems engineer', 'platform engineer',
            'solutions engineer', 'integration engineer', 'api engineer',
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
            'sre', 'site reliability', 'devops', 'infrastructure', 'platform', 'cybersecurity', 'infosec',
            'cloud engineer', 'systems administrator', 'network engineer',
            'security engineer', 'devsecops', 'reliability engineer'
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

def load_config() -> Dict[str, Any]:
    """Load configuration from config.yml"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

def categorize_job(title: str, description: str = '') -> Dict[str, Any]:
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

    for category_id, category_info in CATEGORY_PATTERNS.items():
        if category_id == 'other':
            continue
        for keyword in category_info['keywords']:
            # Use word boundaries for exact phrase matching, safely escape the keyword
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, combined):
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

@lru_cache(maxsize=2048)  # AGGRESSIVE: Increased from 512 for 10K companies
def get_company_tier(company_name: str) -> Dict[str, Any]:
    """Get company tier classification including sectors

    Cached for performance since company names are repeated across multiple jobs.
    """
    # Check primary tiers first
    if company_name in FAANG_PLUS:
        tier_info = {'tier': 'faang_plus', 'emoji': '🔥', 'label': 'FAANG+'}
    elif company_name in UNICORNS:
        tier_info = {'tier': 'unicorn', 'emoji': '🚀', 'label': 'Unicorn'}
    else:
        tier_info = {'tier': 'other', 'emoji': '', 'label': ''}

    # Add sector classifications (can overlap with tier)
    sectors = []
    if company_name in DEFENSE:
        sectors.append('defense')
    if company_name in FINANCE:
        sectors.append('finance')
    if company_name in HEALTHCARE:
        sectors.append('healthcare')
    if company_name in STARTUPS:
        sectors.append('startup')

    tier_info['sectors'] = sectors
    return tier_info

def detect_sponsorship_flags(title: str, description: str = '') -> Dict[str, bool]:
    """Detect sponsorship and citizenship requirements"""
    combined = f"{title.lower()} {description.lower() if description else ''}"

    return {
        'no_sponsorship': any(kw in combined for kw in NO_SPONSORSHIP_KEYWORDS),
        'us_citizenship_required': any(kw in combined for kw in US_CITIZENSHIP_KEYWORDS)
    }

def is_job_closed(title: str, description: str = '') -> bool:
    """Check if job appears to be closed"""
    combined = f"{title.lower()} {description.lower() if description else ''}"
    closed_indicators = ['closed', 'no longer accepting', 'position filled', 'expired']
    return any(indicator in combined for indicator in closed_indicators)

def fetch_greenhouse_jobs(company_name: str, url: str, max_retries: int = 2, timeout: int = DEFAULT_TIMEOUT) -> List[Dict[str, Any]]:
    """Fetch jobs from Greenhouse API with retry logic"""
    jobs = []
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                print(f"  🔄 Retry {attempt} for {company_name}...")
                time.sleep(1)  # Wait before retry

            print(f"Fetching jobs from {company_name} (Greenhouse)...")
            response = limited_get(url, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, dict) or 'jobs' not in data:
                print(f"  ⚠️  {company_name}: Unexpected API response format")
                continue

            for job in data.get('jobs', []):
                description = job.get('content', '') or ''
                jobs.append({
                    'company': company_name,
                    'title': job.get('title', ''),
                    'location': job.get('location', {}).get('name', 'Remote'),
                    'url': job.get('absolute_url', ''),
                    'posted_at': job.get('updated_at') or job.get('created_at'),
                    'source': 'Greenhouse',
                    'description': description[:500] if description else ''
                })
            print(f"  ✓ Found {len(jobs)} jobs from {company_name}")
            break  # Success, exit retry loop

        except requests.exceptions.Timeout:
            if attempt < max_retries:
                print(f"  ⏱️  {company_name} request timed out, retrying...")
                continue
            else:
                print(f"  ❌ {company_name} request timed out after {max_retries + 1} attempts")
        except requests.exceptions.RequestException as e:
            if "404" in str(e):
                print(f"  ⚠️  {company_name} endpoint not found (404) - company may have moved to a different job board")
                break  # Don't retry 404s
            elif attempt < max_retries:
                print(f"  ⚠️  Request error for {company_name}: {e}, retrying...")
                continue
            else:
                print(f"  ❌ Request error for {company_name} after {max_retries + 1} attempts: {e}")
        except Exception as e:
            if attempt < max_retries:
                print(f"  ⚠️  Error fetching from {company_name}: {e}, retrying...")
                continue
            else:
                print(f"  ❌ Error fetching from {company_name} after {max_retries + 1} attempts: {e}")

    return jobs

def fetch_lever_jobs(company_name: str, url: str, max_retries: int = 2, timeout: int = DEFAULT_TIMEOUT) -> List[Dict[str, Any]]:
    """Fetch jobs from Lever API with retry logic"""
    jobs = []
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                print(f"  🔄 Retry {attempt} for {company_name}...")
                time.sleep(1)  # Wait before retry

            print(f"Fetching jobs from {company_name} (Lever)...")
            response = limited_get(url, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, list):
                print(f"  ⚠️  {company_name}: Unexpected API response format")
                continue

            for job in data:
                description = job.get('description', '') or job.get('descriptionPlain', '') or ''
                jobs.append({
                    'company': company_name,
                    'title': job.get('text', ''),
                    'location': job.get('categories', {}).get('location', 'Remote'),
                    'url': job.get('hostedUrl', ''),
                    'posted_at': job.get('createdAt'),
                    'source': 'Lever',
                    'description': description[:500] if description else ''
                })
            print(f"  ✓ Found {len(jobs)} jobs from {company_name}")
            break  # Success, exit retry loop

        except requests.exceptions.Timeout:
            if attempt < max_retries:
                print(f"  ⏱️  {company_name} request timed out, retrying...")
                continue
            else:
                print(f"  ❌ {company_name} request timed out after {max_retries + 1} attempts")
        except requests.exceptions.RequestException as e:
            if "404" in str(e):
                print(f"  ⚠️  {company_name} endpoint not found (404) - company may have moved to a different job board")
                break  # Don't retry 404s
            elif attempt < max_retries:
                print(f"  ⚠️  Request error for {company_name}: {e}, retrying...")
                continue
            else:
                print(f"  ❌ Request error for {company_name} after {max_retries + 1} attempts: {e}")
        except Exception as e:
            if attempt < max_retries:
                print(f"  ⚠️  Error fetching from {company_name}: {e}, retrying...")
                continue
            else:
                print(f"  ❌ Error fetching from {company_name} after {max_retries + 1} attempts: {e}")

    return jobs

def fetch_google_jobs(search_terms: List[str], max_pages: int = 3, max_retries: int = 1, timeout: int = DEFAULT_TIMEOUT) -> List[Dict[str, Any]]:
    """Fetches job listings from Google Careers by scraping search results.

    As the official Google Careers API (v3) is no longer available, this function
    extracts job data by parsing the 'AF_initDataCallback' JSON payload embedded
    within the site's HTML. It performs recursive searching within the
    undocumented nested list structure to isolate job records.

    Args:
        search_terms: A list of strings representing search queries
            (e.g., ["software engineer", "devops"]).
        max_pages: The maximum number of result pages to fetch per search term.
            Defaults to 3.
        max_retries: Number of times to retry a failed request using
            exponential backoff. Defaults to 1.
        timeout: Request timeout in seconds. Defaults to DEFAULT_TIMEOUT.

    Returns:
        A list of dictionaries, where each dictionary represents a job posting
        with the following keys:
            company (str): Name of the hiring company (e.g., 'Google').
            title (str): The job position title.
            location (str): Pipe-separated string of locations or 'Remote'.
            url (str): The direct link to the job application page.
            posted_at (str): ISO 8601 formatted UTC timestamp of the posting.
            source (str): Always 'Google Careers'.
            description (str): A plain-text snippet of the job description
                (max 500 characters).

    Raises:
        This function does not explicitly raise exceptions; instead, it
        logs errors to stdout and returns an empty list or the jobs collected
        prior to the encounter of a critical failure (e.g., 403/429 rate
        limiting or JSON structure changes).
    """
    # Google Jobs array indices (as of March 19th, 2026)
    # Init constants, these map to the index positions in the undocumented JSON structure found below.
    IDX_ID = 0 # For example, would map to index = 0
    IDX_TITLE = 1
    IDX_LINK = 2
    IDX_COMPANY = 7
    IDX_LOCATIONS = 9
    IDX_DESCRIPTION = 10
    IDX_DATE = 12

    MAX_PAGES = max_pages # Put an upper limit on the number of pages we return to avoid rate limits
    all_jobs = [] # init array to return store our results.
    seen_urls = set() # O(1) deduplication with a set, this will contain urls seen with mutliple searches. We want to avoid dupe jobs. This ensures final output is deduplicated.
    # Gather search_term passed from config.yml like 'new grad software engineer'
    for search_term in search_terms:
        page = 1 # This is appended to our URL below, Google enforces 20 results per page, so 2 pages = 40 jobs returned. This gets incremented to allow more results.
        jobs_found_on_page = True

        while jobs_found_on_page:
            params = urlencode({ # Build our URL using the below params, all get built into url var
                'q': search_term, # search term would be our dict injected into the URL directly.
                'hl': 'en', # Enforce english only
                'location': "United States", # Enforce USA only
                'target_level': 'EARLY', # Website has a settings like Mid or Senior, we select Early for new grad jobs per the project.
            }) # Notice that we have two levels, target level APPRENTICE and EARLY do capture more jobs and get the max 'early' jobs.
            # A job in test_utils (test_fetch_google_jobs_url_shape) must be altered if params are changed. Currently we use two and so does the test.

            url = f"https://www.google.com/about/careers/applications/jobs/results/?{params}&target_level=INTERN_AND_APPRENTICE&page={page}"

            html = ""
            # Start Fetching the HTML with exponential backoff. Fetch is in a retry loop
            # If a request times out or fails (500s) we sleep for longer and longer periods of time to avoid being throttled
            # If 403 or 429 is returned, we stop immediately.
            for attempt in range(max_retries + 1):
                try:
                    # Using limited_get which handles connection pooling, compression, and keeps sessions alive
                    response = limited_get(url, timeout=timeout)
                    response.raise_for_status()
                    html = response.text
                    break
                except requests.exceptions.HTTPError as e:
                    if response.status_code in (403, 429):
                        print(f"  ⚠️  Google: Rate limited or blocked (HTTP {response.status_code}). Aborting remaining Google Careers requests.")
                        return all_jobs
                    if response.status_code == 404:
                        print(f"  ⚠️  Google: Endpoint not found (404) for {url}. Fail fast.")
                        break
                    print(f"  ⚠️  Google: HTTP Error {response.status_code} for {url}: {e}")
                except requests.exceptions.ConnectionError as e:
                    print(f"  ⚠️  Google: Connection error for {url}: {e}")
                except requests.exceptions.Timeout:
                    print(f"  ⚠️  Google: Timeout for {url}")
                except requests.exceptions.RequestException as e:
                    print(f"  ⚠️  Google: Request error for {url}: {e}")

                # Set out back off, sleeping for a bit, then increasing before trying again.
                if attempt < max_retries:
                    sleep_time = 3.0 * (2 ** attempt)
                    print(f"  ⚠️  Google: Retrying in {sleep_time} seconds (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(sleep_time)

            if not html:
                print(f"⚠️  Google: Failed to fetch {url} after {max_retries + 1} attempts.")
                return all_jobs # Stop, something is not right.
            # This regex extraction in re.search finds a very specific <script> block AF_initDataCallback (for now) inside page body.
            # This is where google puts raw data used to render the page in the browser. We slice out the inner characters so we just have a nice JSON string
            match = re.search(r"AF_initDataCallback\(\{key: 'ds:1', hash: '[^']+', data:([^<]+)\}\);</script>", html)
            if not match: # If not found, get out. Might be somewhere else or maybe they are on to us.
                print(
                    f"⚠️  Google: AF_initDataCallback payload missing for term={search_term!r}, page={page}, url={url}. Aborting Google Careers Scrape."
                ) # Hard Scrape failure, stop and get out.
                return all_jobs

            data_str = match.group(1)
            start = data_str.find('[')
            end = data_str.rfind(']') + 1
            json_str = data_str[start:end]
            # Begin parsing string into nested Python list using json.loads.
            # After, we pass the structure to find_jobs_array which digs through the lists to isolate the needed array of jobs.
            try:
                parsed = json.loads(json_str)
            except json.JSONDecodeError as e:
                print(
                    f"⚠️  Google: JSON decode error for term={search_term!r}, page={page}, url={url}. Aborting Google Careers Scrape."
                ) # Hard Scrape failure, stop and get out.
                return all_jobs
            except (IndexError, TypeError, ValueError) as e:
                print(f"⚠️  Google: Unexpected error parsing JSON on page {page}: {e}")
                return all_jobs # Unknown error, break off and no retry.

            # Find_jobs_array is used for parsing undocumented string data from google careers using DFS to five into every nested list.
            # This is a recursive search function that goes thru the deep nested python list parsed from JSON looking for a pattern
            # 1. Check if isinstance(obj) > 0: Is the current object a list?
            # 2. isinstance(obj[0], list) - Is the first item also a list? If so keep going
            # 3. Does this inner list have at least one item? (len(obj[0]) > 0)
            # 4. If it does have a item, does the item only have numbers? isinstance(obj[0][0], str) and isdigit()
            # If signature matches, then assume we found the list of jobs and return obj. If not, go through current list and dig deeper with res = find_jobs_array(item)
            # Google does not provide a clean nested JSON for us, instead we find the data in raw HTML (<script> tag)
            # At the very least, if google changes something here, this array can find the path (within reason)
            # This function makes the scrape as a whole more resilient.
            def find_jobs_array(obj):
                if isinstance(obj, list):
                    if len(obj) > 0 and isinstance(obj[0], list) and len(obj[0]) > 0 and isinstance(obj[0][0], str) and obj[0][0].isdigit():
                        return obj
                    for item in obj:
                        res = find_jobs_array(item)
                        if res: return res
                return None
            # Use find_jobs array to try to find a regex match
            jobs_list = find_jobs_array(parsed)
            print(f"DEBUG: Regex Match Found? {match is not None}")
            print(f"DEBUG: jobs_list Found? {jobs_list is not None}")
            if not jobs_list:
                jobs_found_on_page = False # If this is false, it means we might be on page=4, but if there are only 3 pages of jobs, we want to stop.
                continue    # continue and on to the next search term in googles config. Both needed here to prevent a infinite loop

            new_jobs = 0
            # Parse the field into Title, URL, Company, Location, Description and post date(unix timstamp)
            for job in jobs_list:
                try:
                    job_id = job[IDX_ID]
                    title = job[IDX_TITLE]
                    link = job[IDX_LINK]

                    # Validate core fields before proceeding.
                    # title and link must be non-empty strings to avoid downstream crashes in filter_jobs() or generate_readme().
                    if not isinstance(title, str) or not title.strip():
                        continue

                    if not link:
                        link = f"https://www.google.com/about/careers/applications/jobs/results/{job_id}"

                    if not isinstance(link, str) or not link.strip():
                        continue

                    # Should be google only, but just in case. Google has other companies like waymo or Deep Mind.
                    # Defaults to "Google" if the company field is missing, not a string, or empty.
                    raw_company = job[IDX_COMPANY] if len(job) > IDX_COMPANY else None
                    company = raw_company if isinstance(raw_company, str) and raw_company.strip() else "Google"

                    locations = []
                    if len(job) > IDX_LOCATIONS and isinstance(job[IDX_LOCATIONS], list):
                        for loc in job[IDX_LOCATIONS]:
                            if isinstance(loc, list) and len(loc) > 0:
                                locations.append(loc[0])

                    location_str = " | ".join(locations) if locations else "Remote"
                    # Posted date unix timestamp is extracted, we clean up the date into ISO 8601 and also strip HTML tags(br) from it.
                    posted_at = ""
                    if len(job) > IDX_DATE and isinstance(job[IDX_DATE], list) and len(job[IDX_DATE]) > 0:
                        ts = job[IDX_DATE][0]
                        if isinstance(ts, (int, float)):
                            posted_at = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() # ISO 8601

                    desc_html = "" # Init blank text
                    # Below is a bound check, ensure that index access is safe with len(job) before going to higher indices like 7,9,12.
                    if len(job) > IDX_DESCRIPTION and isinstance(job[IDX_DESCRIPTION], list) and len(job[IDX_DESCRIPTION]) > 1:
                        desc_html = job[IDX_DESCRIPTION][1] or ""
                    # strip HTML from the text if any is found.
                    desc_text = re.sub(r'<[^>]+>', ' ', desc_html)
                    desc_text = re.sub(r'\s+', ' ', desc_text).strip()
                    description = desc_text[:500]
                    # Deduplicate in O(1) using a set for faster processing.
                    if link not in seen_urls:
                        seen_urls.add(link)
                        all_jobs.append({
                            "company": company,
                            "title": title,
                            "location": location_str,
                            "url": link,
                            "posted_at": posted_at,
                            "source": "Google Careers", # Single Source, should just be this unless they change it again.
                            "description": description
                        })
                        new_jobs += 1
                except (IndexError, TypeError, ValueError) as e:
                    job_id = job[0] if isinstance(job, list) and len(job) > 0 else "Unknown"
                    print(f"  ⚠️  Google: Error parsing job data (ID: {job_id}): {e}") # Print error for later ref
            # If no new jobs were added at all, most likely hit the end of the unique pages
            # Does current page = or exceed MAX_PAGES?
            #If either is true, break the while loop and start looking at the next search term.
            if new_jobs == 0:
                jobs_found_on_page = False
            else:
                if page >= MAX_PAGES: # MAX_PAGES set above in order to limit any excessive GET requests
                    jobs_found_on_page = False
                else:
                    page += 1 # +1 to add to the page URL rather than look for the next page link.
    print("✓ Found Google Career Jobs returned: ", len(all_jobs)) # Print total number of jobs found for logs
    return all_jobs # Return all jobs found


def build_workday_api_url(host: str, site_path: str) -> str:
    """Build a Workday CXS jobs API endpoint URL.

    Args:
        host: Workday hostname (for example, ``acme.wd5.myworkdayjobs.com``).
        site_path: Path portion from the careers URL (for example,
            ``/Acme_External_Careers`` or ``/tenant/Acme_External_Careers``).

    Returns:
        A full Workday jobs API URL in the format
        ``https://<host>/wday/cxs/<tenant>/<site>/jobs``.

    Raises:
        ValueError: If ``host`` or ``site_path`` is not a non-empty string with
            at least one path segment.
    """
    if not isinstance(host, str):
        raise ValueError("host must be a string")
    if not isinstance(site_path, str):
        raise ValueError("site_path must be a string")

    clean_host = host.strip()
    if not clean_host:
        raise ValueError("host is required")

    path_parts = [part for part in site_path.strip('/').split('/') if part]
    if not path_parts:
        raise ValueError("site_path must include at least one segment")

    host_parts = [part for part in clean_host.split('.') if part]
    if not host_parts:
        raise ValueError("host is required")

    tenant = host_parts[0]
    if re.fullmatch(r"wd\d+", tenant.lower()) and len(path_parts) >= 2:
        # For URLs like wd5.myworkdayjobs.com/<tenant>/<site>, tenant lives in the path.
        # Locale-prefixed variants can be /en-US/<tenant>/<site>.
        if len(path_parts) >= 3 and re.fullmatch(r"[a-z]{2}-[a-z]{2}", path_parts[0].lower()):
            tenant = path_parts[1]
        else:
            tenant = path_parts[0]

    site_id = path_parts[-1]
    return f"https://{clean_host}/wday/cxs/{tenant}/{site_id}/jobs"


def get_workday_csrf_token(host: str, session: requests.Session) -> str:
    """Acquire the X-Calypso-CSRF-Token required by the Workday CXS jobs API.

    Workday's CXS API (``/wday/cxs/.../jobs``) began requiring the
    ``X-Calypso-CSRF-Token`` header as of early 2026.  The token is issued
    by the careers homepage as a ``Set-Cookie: CALYPSO_CSRF_TOKEN=<value>``
    response cookie and must be echoed back as a request header on every
    subsequent POST.

    Args:
        host: Workday hostname, e.g. ``boeing.wd1.myworkdayjobs.com``.
        session: The shared ``requests.Session`` to use for the GET request
            so that cookies are persisted for the lifetime of the session.

    Returns:
        The CSRF token string, or an empty string if acquisition fails
        (graceful degradation — callers should still attempt the POST).
    """
    try:
        careers_url = f"https://{host}/"
        resp = session.get(careers_url, timeout=DEFAULT_TIMEOUT, allow_redirects=True)
        # Prefer the header value; fall back to the Set-Cookie cookie.
        token = resp.headers.get("X-Calypso-CSRF-Token", "")
        if not token:
            token = resp.cookies.get("CALYPSO_CSRF_TOKEN", "")
        return token
    except Exception as exc:
        print(f"  ⚠️  Could not acquire Workday CSRF token for {host}: {exc}")
        return ""


def fetch_workday_jobs(companies: List[Dict[str, str]],
                       page_limit: int | None = None,
                       max_total_limit: int | None = None,
                       max_retries: int = 2) -> List[Dict[str, Any]]:
    """Fetch jobs from Workday API with pagination and safety limits."""
    page_limit = _coerce_positive_int(page_limit, WORKDAY_PAGE_LIMIT, 'page_limit')
    max_total_limit = _coerce_positive_int(
        max_total_limit,
        WORKDAY_MAX_JOBS_PER_COMPANY,
        'max_total_limit',
    )
    all_jobs = []

    for company in companies:
        company_name = company.get('name')
        workday_url = company.get('workday_url')

        if not company_name or not workday_url:
            continue

        print(f"Fetching jobs from {company_name} (Workday)...")

        # Construct Workday API URL
        # Pattern: https://<host>/wday/cxs/<tenant>/<site>/jobs
        try:
            parsed = urlparse(workday_url)
            host = parsed.netloc
            site_path = parsed.path
            api_url = build_workday_api_url(host, site_path)

            # Acquire CSRF token required by Workday CXS API (mandatory since early 2026).
            # The token is obtained from a GET to the careers homepage and echoed back
            # as X-Calypso-CSRF-Token on every POST to the jobs endpoint.
            csrf_token = get_workday_csrf_token(host, HTTP_SESSION)

            jobs = []
            offset = 0

            while True:
                payload = {
                    "appliedFacets": {},
                    "limit": page_limit,
                    "offset": offset,
                    "searchText": ""  # Fetch all, filter locally
                }

                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }

                response = None
                for attempt in range(max_retries + 1):
                    if attempt > 0:
                        time.sleep(1)

                    if csrf_token:
                        headers['X-Calypso-CSRF-Token'] = csrf_token

                    response = limited_post(api_url, json=payload, headers=headers, timeout=6)

                    # Initial structural check for 404 (only on first attempt)
                    if response.status_code == 404 and attempt == 0:
                        path_parts = [part for part in site_path.strip('/').split('/') if part]
                        if len(path_parts) >= 2:
                            fallback_tenant = path_parts[0]
                            if len(path_parts) >= 3 and re.fullmatch(r"[a-z]{2}-[a-z]{2}", path_parts[0].lower()):
                                fallback_tenant = path_parts[1]

                            fallback_api_url = f"https://{host}/wday/cxs/{fallback_tenant}/{path_parts[-1]}/jobs"
                            if fallback_api_url != api_url:
                                api_url = fallback_api_url
                                response = limited_post(api_url, json=payload, headers=headers, timeout=6)

                    # CSRF token expired or transient issue mid-run
                    if response.status_code == 422:
                        print(f"  🔄 {company_name}: 422 received, re-acquiring CSRF token (attempt {attempt+1}/{max_retries+1})...")
                        csrf_token = get_workday_csrf_token(host, HTTP_SESSION)
                        continue # Retry with new token

                    if response.ok:
                        break # Success

                    if attempt < max_retries:
                        print(f"  ⚠️  Workday API error for {company_name}: HTTP {response.status_code}. Retrying ({attempt+1}/{max_retries})...")

                if not response or not response.ok:
                    try:
                        error_body = response.json() if response else "No response"
                    except (json.JSONDecodeError, ValueError):
                        error_body = response.text[:500] if response else "No response"
                    print(f"  ⚠️  Workday API error for {company_name}: HTTP {response.status_code if response else 'N/A'} — {error_body}")
                    break

                data = response.json()
                job_items = data.get('jobPostings', [])

                if not job_items:
                    break

                remaining = max_total_limit - len(jobs)
                if remaining <= 0:
                    print(f"  ℹ️  {company_name}: Reached safety limit of {max_total_limit} jobs. Truncating.")
                    break

                for item in job_items[:remaining]:
                    title = item.get('title', '')
                    external_path = item.get('externalPath', '')
                    job_url = f"https://{host}{external_path}"
                    posted_on = item.get('postedOn', '')

                    jobs.append({
                        'company': company_name,
                        'title': title,
                        'location': item.get('locationsText', 'Remote'),
                        'url': job_url,
                        'posted_at': posted_on,
                        'source': 'Workday',
                        'description': ''  # Not fetching full description to save requests
                    })

                if len(jobs) >= max_total_limit:
                    print(f"  ℹ️  {company_name}: Reached safety limit of {max_total_limit} jobs. Truncating.")
                    break

                offset += page_limit

            print(f"  ✓ Found {len(jobs)} jobs from {company_name}")
            all_jobs.extend(jobs)

        except Exception as e:
            print(f"  ❌ Error processing {company_name}: {e}")
            continue

    return all_jobs

def fetch_jobspy_jobs(config_jobspy: Dict[str, Any], max_retries: int = 2) -> List[Dict[str, Any]]:
    """Fetch jobs using JobSpy library from multiple job sites - PARALLEL VERSION

    Uses ThreadPoolExecutor to run multiple searches concurrently, dramatically
    reducing time from 10+ minutes to ~1-2 minutes for 150+ search terms.
    Now supports multiple countries: USA, Canada, India
    """
    if not JOBSPY_AVAILABLE:
        print("❌ JobSpy library not available, skipping...")
        return []

    if not config_jobspy.get('enabled', False):
        print("JobSpy is disabled in configuration, skipping...")
        return []

    sites = config_jobspy.get('sites', ['linkedin', 'indeed'])
    search_terms = config_jobspy.get('search_terms', ['new grad software engineer'])
    results_wanted = config_jobspy.get('results_wanted', 50)
    hours_old = config_jobspy.get('hours_old', 72)

    countries = config_jobspy.get('countries', DEFAULT_JOBSPY_COUNTRIES)

    # Build list of all (site, search_term, country) combinations
    search_tasks = [(site, term, country) for site in sites for term in search_terms for country in countries]
    total_tasks = len(search_tasks)

    print(f"🚀 Starting PARALLEL job search: {total_tasks} searches across {len(sites)} sites and {len(countries)} countries")
    print(f"   Countries: {', '.join([c['code'] for c in countries])}")
    print(f"   Using 25 concurrent workers for maximum speed...")

    all_jobs = []
    completed = 0
    errors = 0

    def search_single(args):
        """Worker function to search a single site/term/country combination"""
        site, search_term, country = args
        jobs_list = []

        for attempt in range(max_retries + 1):
            try:
                # Use JobSpy to scrape jobs
                jobs_df = scrape_jobs(
                    site_name=site,
                    search_term=search_term,
                    location=country['location'],
                    results_wanted=results_wanted,
                    hours_old=hours_old,
                    country_indeed=country['code']
                )

                if jobs_df is None or jobs_df.empty:
                    return {'site': site, 'term': search_term, 'jobs': [], 'count': 0, 'error': None}

                # Convert DataFrame to list of dictionaries
                for _, row in jobs_df.iterrows():
                    description = row.get('description', '') or ''
                    job = {
                        'company': row.get('company', 'Unknown'),
                        'title': row.get('title', ''),
                        'location': row.get('location', 'Remote'),
                        'url': row.get('job_url', ''),
                        'posted_at': row.get('date_posted', ''),
                        'source': f'JobSpy ({site.title()})',
                        'description': description[:500] if description else ''
                    }

                    if job['url'] and job['url'].startswith('http'):
                        jobs_list.append(job)

                return {'site': site, 'term': search_term, 'jobs': jobs_list, 'count': len(jobs_list), 'error': None}

            except Exception as e:
                if attempt < max_retries:
                    time.sleep(0.3)  # Brief delay before retry (optimized)
                    continue
                return {'site': site, 'term': search_term, 'jobs': [], 'count': 0, 'error': str(e)[:100]}

        return {'site': site, 'term': search_term, 'jobs': [], 'count': 0, 'error': 'Max retries exceeded'}

    # Use ThreadPoolExecutor for parallel execution
    # 25 workers for Indeed-only mode (LinkedIn disabled due to rate limits)
    with ThreadPoolExecutor(max_workers=DEFAULT_JOBSPY_WORKERS) as executor:
        # Submit all tasks
        future_to_task = {executor.submit(search_single, task): task for task in search_tasks}

        # Process results as they complete
        for future in as_completed(future_to_task):
            with _COUNTER_LOCK:
                completed += 1
            result = future.result()

            if result['error']:
                with _COUNTER_LOCK:
                    errors += 1
                print(f"  [{completed}/{total_tasks}] ❌ {result['site'].upper()} '{result['term']}': {result['error']}")
            elif result['count'] > 0:
                all_jobs.extend(result['jobs'])
                print(f"  [{completed}/{total_tasks}] ✓ {result['site'].upper()} '{result['term']}': {result['count']} jobs")
            else:
                print(f"  [{completed}/{total_tasks}] ⚠️ {result['site'].upper()} '{result['term']}': No jobs found")

    print(f"\n✅ Parallel search complete!")
    print(f"   Total jobs found via JobSpy: {len(all_jobs)}")
    print(f"   Successful searches: {completed - errors}/{total_tasks}")
    if errors > 0:
        print(f"   ⚠️ Errors: {errors}")

    return all_jobs

def fetch_serp_api_jobs(config_serp: Dict[str, Any], max_retries: int = 2) -> List[Dict[str, Any]]:
    """Fetch jobs using SerpApi Google Jobs API (placeholder implementation)"""
    if not config_serp.get('enabled', False):
        print("SerpApi is disabled in configuration, skipping...")
        return []

    api_key = config_serp.get('api_key', '').replace('${SERP_API_KEY}', os.getenv('SERP_API_KEY', ''))
    if not api_key or api_key.startswith('${'):
        print("⚠️ SerpApi API key not configured, skipping...")
        return []

    print("🚧 SerpApi integration ready but requires API key configuration")
    print("   Set SERP_API_KEY environment variable to enable")

    return []

def fetch_scraper_api_jobs(config_scraper: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch jobs using ScraperAPI for general web scraping (placeholder implementation)"""
    if not config_scraper.get('enabled', False):
        print("ScraperAPI is disabled in configuration, skipping...")
        return []

    api_key = config_scraper.get('api_key', '').replace('${SCRAPER_API_KEY}', os.getenv('SCRAPER_API_KEY', ''))
    if not api_key or api_key.startswith('${'):
        print("⚠️ ScraperAPI key not configured, skipping...")
        return []

    print("🚧 ScraperAPI integration ready but requires API key configuration")
    print("   Set SCRAPER_API_KEY environment variable to enable")

    return []

# ============================================================================
# PARALLEL FETCHING FUNCTIONS (Performance Optimization)
# ============================================================================

def fetch_all_greenhouse_jobs_parallel(companies: List[Dict[str, Any]], max_workers: int = None) -> List[Dict[str, Any]]:
    """Fetch all Greenhouse jobs in parallel using ThreadPoolExecutor

    Parallelizes ~150+ company API calls with optimized worker count.
    Auto-scales workers based on company count for maximum efficiency.
    """
    all_jobs = []
    total = len(companies)
    completed = 0
    errors = 0

    # AUTO-SCALE: Use 1 worker per 3 companies, min 30, max 300 for 1000+ companies
    if max_workers is None:
        max_workers = min(DEFAULT_GREENHOUSE_MAX_WORKERS, max(DEFAULT_GREENHOUSE_MIN_WORKERS, total // 3))  # AGGRESSIVE: 30-300 workers for 10K

    print(f"\n🚀 Starting PARALLEL Greenhouse fetch: {total} companies with {max_workers} workers")

    def fetch_single(company: Dict[str, str]) -> List[Dict[str, Any]]:
        return fetch_greenhouse_jobs(company['name'], company['url'])

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_company = {executor.submit(fetch_single, c): c for c in companies}

        for future in as_completed(future_to_company):
            with _COUNTER_LOCK:
                completed += 1
            company = future_to_company[future]
            try:
                jobs = future.result()
                all_jobs.extend(jobs)
            except Exception as e:
                with _COUNTER_LOCK:
                    errors += 1
                print(f"  ❌ {company['name']}: {e}")

    print(f"✅ Greenhouse parallel fetch complete: {len(all_jobs)} jobs from {completed - errors}/{total} companies")
    return all_jobs


def fetch_all_lever_jobs_parallel(companies: List[Dict[str, Any]], max_workers: int = None) -> List[Dict[str, Any]]:
    """Fetch all Lever jobs in parallel using ThreadPoolExecutor

    Auto-scales workers based on company count for optimal performance.
    """
    all_jobs = []
    total = len(companies)
    completed = 0
    errors = 0

    # AUTO-SCALE: Use 1 worker per company for small lists, max 100 for 1000+ companies
    if max_workers is None:
        max_workers = min(DEFAULT_LEVER_MAX_WORKERS, max(DEFAULT_LEVER_MIN_WORKERS, total))  # AGGRESSIVE: 15-200 workers for 10K

    print(f"\n🚀 Starting PARALLEL Lever fetch: {total} companies with {max_workers} workers")

    def fetch_single(company: Dict[str, str]) -> List[Dict[str, Any]]:
        return fetch_lever_jobs(company['name'], company['url'])

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_company = {executor.submit(fetch_single, c): c for c in companies}

        for future in as_completed(future_to_company):
            with _COUNTER_LOCK:
                completed += 1
            company = future_to_company[future]
            try:
                jobs = future.result()
                all_jobs.extend(jobs)
            except Exception as e:
                with _COUNTER_LOCK:
                    errors += 1
                print(f"  ❌ {company['name']}: {e}")

    print(f"✅ Lever parallel fetch complete: {len(all_jobs)} jobs from {completed - errors}/{total} companies")
    return all_jobs

def get_job_key(job: Dict[str, Any]) -> str:
    """Generate unique key for job deduplication

    Handles non-string values (NaN, None, float) that may come from JobSpy/pandas.
    """
    def safe_str(value) -> str:
        """Safely convert any value to lowercase string"""
        if value is None:
            return ''
        # Check for built-in floats or NumPy floating types
        if isinstance(value, float) or (np is not None and isinstance(value, np.floating)):
            # Robustly handle NaN and Inf for both built-in and NumPy floats
            if np is not None and isinstance(value, np.floating):
                is_nan = np.isnan(value)
                is_inf = np.isinf(value)
            else:
                is_nan = math.isnan(value)
                is_inf = math.isinf(value)

            if is_nan or is_inf:
                return ''
            return str(value)
        return str(value).lower().strip()

    company = safe_str(job.get('company', ''))
    title = safe_str(job.get('title', ''))
    url = safe_str(job.get('url', ''))
    return f"{company}|{title}|{url}"


def deduplicate_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate jobs based on company, title, and URL"""
    seen_keys = set()
    unique_jobs = []

    for job in jobs:
        key = get_job_key(job)
        if key not in seen_keys:
            seen_keys.add(key)
            unique_jobs.append(job)

    duplicates_removed = len(jobs) - len(unique_jobs)
    if duplicates_removed > 0:
        print(f"🔄 Deduplication: Removed {duplicates_removed} duplicate jobs")

    return unique_jobs

def has_new_grad_signal(title: str, signals: List[str]) -> bool:
    """Check if job title contains new grad signals"""
    title_lower = title.lower()
    return any(signal.lower() in title_lower for signal in signals)

def has_track_signal(title: str, signals: List[str]) -> bool:
    """Check if job title contains track signals"""
    title_lower = title.lower()
    return any(signal.lower() in title_lower for signal in signals)

def normalize_date_string(posted_at: str, now_utc: datetime | None = None) -> str:
    """
    Normalize human-readable date strings from JobSpy/LinkedIn/Indeed/Glassdoor
    to ISO format dates that date_parser can handle.

    Handles formats like:
    - "Posted Today" -> today's date
    - "Posted Yesterday" -> yesterday's date
    - "Posted 2 Days Ago" -> 2 days ago
    - "Posted 30+ Days Ago" -> 30 days ago

    Also handles native datetime.date / datetime.datetime objects returned by
    Workday / JobSpy API clients, coercing them to their ISO-format string so
    that downstream dateparser never receives a non-string argument.
    """
    if not isinstance(posted_at, str):
        # Coerce native date/datetime objects to ISO string rather than
        # returning them raw, which causes dateparser to emit:
        #   "Parser must be a string or character stream, not date"
        if hasattr(posted_at, 'isoformat'):
            return posted_at.isoformat()

        return posted_at

    posted_at_lower = posted_at.lower().strip()
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    now = now_utc.replace(tzinfo=None)

    # Handle "Posted Today" or "Today"
    if 'today' in posted_at_lower:
        return now.strftime('%Y-%m-%d')

    # Handle "Posted Yesterday" or "Yesterday"
    if 'yesterday' in posted_at_lower:
        return (now - timedelta(days=1)).strftime('%Y-%m-%d')

    # Handle "Posted X Days Ago" or "X Days Ago"
    days_match = re.search(r'(\d+)\s*days?\s+ago', posted_at_lower)
    if days_match:
        days = int(days_match.group(1))
        return (now - timedelta(days=days)).strftime('%Y-%m-%d')

    # Handle "Posted 30+ Days Ago" or "30+ Days Ago"
    days_plus_match = re.search(r'(\d+)\+\s*days?\s+ago', posted_at_lower)
    if days_plus_match:
        days = int(days_plus_match.group(1))
        return (now - timedelta(days=days)).strftime('%Y-%m-%d')

    # Return original if no pattern matches
    return posted_at

def _as_utc_naive(dt: datetime) -> datetime:
    """Normalize datetime to UTC, then return timezone-naive value."""
    if dt.tzinfo is None:
        # Treat naive datetimes as already UTC to keep comparisons deterministic.
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def is_recent_job(posted_at: str, max_age_days: int) -> bool:
    """Check if job was posted within the specified number of days"""
    if posted_at is None:
        return False

    if isinstance(posted_at, float) and math.isnan(posted_at):
        return False

    try:
        now_utc = datetime.now(timezone.utc)

        # Handle already parsed date objects
        if isinstance(posted_at, (datetime, date)):
            posted_date = posted_at
            if isinstance(posted_date, date) and not isinstance(posted_date, datetime):
                posted_date = datetime.combine(posted_date, datetime.min.time())
        # Handle timestamp integers (from Lever API)
        elif isinstance(posted_at, (int, float)):
            posted_date = datetime.fromtimestamp(posted_at / 1000, tz=timezone.utc)
        else:
            # Normalize human-readable date strings before parsing
            normalized_date = normalize_date_string(posted_at, now_utc)
            posted_date = date_parser.parse(normalized_date)

        posted_date = _as_utc_naive(posted_date)
        cutoff_date = now_utc.replace(tzinfo=None) - timedelta(days=max_age_days)
        return posted_date >= cutoff_date
    except Exception as e:
        print(f"Error parsing date {posted_at}: {e}")
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

def filter_jobs(jobs: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Filter jobs based on configuration criteria"""
    filtered_jobs = []
    filters = config.get('filtering', config.get('filters', {}))

    # Get exclusion signals (default to common senior keywords if not in config)
    exclusion_signals = filters.get('exclusion_signals', [
        'senior', 'sr.', 'sr ', 'staff', 'principal', 'lead', 'manager',
        'director', 'vp', 'vice president', 'head of', 'architect',
        'distinguished', 'fellow', 'intern', 'internship'
    ])

    for job in jobs:
        title = job.get('title', '')
        title_lower = title.lower()
        location = job.get('location', '')
        posted_at = job.get('posted_at', '')

        # FIRST: Check for exclusion signals (filter OUT senior/staff roles)
        is_excluded = any(signal.lower() in title_lower for signal in exclusion_signals)
        if is_excluded:
            continue

        # Check for new grad signals
        if not has_new_grad_signal(title, filters['new_grad_signals']):
            continue

        # For jobs with clear new grad signals, track signals are optional
        has_track = has_track_signal(title, filters['track_signals'])

        # Strong new grad signals that don't need additional track signals
        # P4: Generic role titles removed — they belong in track_signals only.
        # Without a co-occurring new-grad keyword, "Software Engineer" alone
        # should not bypass the track-signal requirement.
        strong_new_grad_signals = [
            "new grad", "new graduate", "graduate program", "campus", "university grad",
            "college grad", "early career", "2025 start", "2026 start", "2025", "2026",
        ]
        has_strong_new_grad = any(signal.lower() in title_lower for signal in strong_new_grad_signals)

        # Accept if: has strong new grad signal OR (has new grad signal AND track signal)
        if not (has_strong_new_grad or has_track):
            continue

        # Check if job is recent enough
        if not is_recent_job(posted_at, filters['max_age_days']):
            continue

        # Check if job location is in USA
        if not is_valid_location(location):
            continue

        filtered_jobs.append(job)

    return filtered_jobs

def enrich_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add categorization, company tier, and flags to jobs"""
    enriched = []

    for job in jobs:
        title = job.get('title', '')
        description = job.get('description', '')
        company = job.get('company', '')

        # Add categorization
        category = categorize_job(title, description)
        job['category'] = category

        # Add company tier
        tier = get_company_tier(company)
        job['company_tier'] = tier

        # Add sponsorship flags
        flags = detect_sponsorship_flags(title, description)
        job['flags'] = flags

        # Check if closed
        job['is_closed'] = is_job_closed(title, description)

        # Generate unique ID
        job['id'] = f"{company}-{title}-{job.get('location', '')}".lower().replace(' ', '-')[:100]

        enriched.append(job)

    return enriched

def format_posted_date(posted_at: str) -> str:
    """Format posted date for display"""
    try:
        # Handle timestamp integers (from Lever API)
        if isinstance(posted_at, (int, float)):
            posted_date = datetime.fromtimestamp(posted_at / 1000)  # Convert milliseconds to seconds
        else:
            # Normalize human-readable date strings before parsing
            normalized_date = normalize_date_string(posted_at)
            posted_date = date_parser.parse(normalized_date)

        now = datetime.now()
        diff = now - posted_date.replace(tzinfo=None)

        if diff.days == 0:
            return "Today"
        elif diff.days == 1:
            return "1 day ago"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        else:
            return posted_date.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Warning: could not format date '{posted_at}': {e}", file=sys.stderr)
        return "Unknown"

def get_iso_date(posted_at) -> str:
    """Get ISO format date string"""
    try:
        if isinstance(posted_at, (int, float)):
            posted_date = datetime.fromtimestamp(posted_at / 1000)
        else:
            # Normalize human-readable date strings before parsing
            normalized_date = normalize_date_string(posted_at)
            posted_date = date_parser.parse(normalized_date)
        return posted_date.replace(tzinfo=None).isoformat()
    except Exception as e:
        print(f"Warning: could not parse ISO date '{posted_at}': {e}", file=sys.stderr)
        return ""

def generate_jobs_json(jobs: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate JSON data structure for jobs"""

    # Calculate category counts
    category_counts = {}
    for category_id in CATEGORY_PATTERNS.keys():
        category_counts[category_id] = 0

    for job in jobs:
        cat_id = job.get('category', {}).get('id', 'other')
        category_counts[cat_id] = category_counts.get(cat_id, 0) + 1

    # Sort jobs by date
    jobs.sort(key=extract_sort_date, reverse=True)

    # Build JSON structure
    json_jobs = []
    for job in jobs:
        json_jobs.append({
            'id': job.get('id', ''),
            'company': job.get('company', ''),
            'title': job.get('title', ''),
            'location': job.get('location', ''),
            'url': job.get('url', ''),
            'posted_at': get_iso_date(job.get('posted_at')),
            'posted_display': format_posted_date(job.get('posted_at', '')),
            'source': job.get('source', ''),
            'category': job.get('category', {}),
            'company_tier': job.get('company_tier', {}),
            'flags': job.get('flags', {}),
            'is_closed': job.get('is_closed', False)
        })

    return {
        'meta': {
            'generated_at': datetime.now().isoformat(),
            'total_jobs': len(jobs),
            'categories': [
                {
                    'id': cat_id,
                    'name': cat_info['name'],
                    'emoji': cat_info['emoji'],
                    'count': category_counts.get(cat_id, 0)
                }
                for cat_id, cat_info in CATEGORY_PATTERNS.items()
                if category_counts.get(cat_id, 0) > 0
            ]
        },
        'jobs': json_jobs
    }

def save_market_history(jobs: List[Dict[str, Any]]) -> None:
    """
    Save daily market snapshot for historical tracking, comparisons, and ML predictions.
    Stores daily snapshots in docs/market-history.json with 90-day retention.
    """
    # Create today's snapshot
    today = datetime.now().strftime('%Y-%m-%d')


    # Count jobs by category
    category_counts = Counter()
    for job in jobs:
        for category in job.get('categories', []):
            category_counts[category] += 1

    # Count jobs by tier
    tier_counts = Counter()
    for job in jobs:
        tier = job.get('company_tier', {}).get('tier', 'other')
        tier_counts[tier] += 1

    # Get top 10 companies by job count
    company_counts = Counter(job.get('company', 'Unknown') for job in jobs)
    top_companies = [
        {'company': company, 'jobs': count}
        for company, count in company_counts.most_common(10)
    ]

    # Calculate average jobs per company
    unique_companies = len(company_counts)
    avg_jobs_per_company = round(len(jobs) / unique_companies, 2) if unique_companies > 0 else 0

    # Create snapshot object
    snapshot = {
        'date': today,
        'total_jobs': len(jobs),
        'categories': dict(category_counts),
        'tiers': dict(tier_counts),
        'top_companies': top_companies,
        'unique_companies': unique_companies,
        'avg_jobs_per_company': avg_jobs_per_company,
        'timestamp': datetime.now().isoformat()
    }

    # Load existing history
    history_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'market-history.json')

    try:
        if os.path.exists(history_path):
            with open(history_path, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
                history = history_data.get('snapshots', [])
        else:
            history = []
    except Exception as e:
        print(f"  ⚠️  Could not load market history: {e}")
        history = []

    # Check if today's snapshot already exists (avoid duplicates)
    existing_dates = {entry['date'] for entry in history}
    if today not in existing_dates:
        history.append(snapshot)
        print(f"  ✓ Added market snapshot for {today}: {len(jobs)} jobs")
    else:
        # Update today's snapshot if it exists
        for i, entry in enumerate(history):
            if entry['date'] == today:
                history[i] = snapshot
                print(f"  ✓ Updated market snapshot for {today}: {len(jobs)} jobs")
                break

    # Keep only last 90 days
    cutoff_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    history = [entry for entry in history if entry['date'] >= cutoff_date]

    # Sort by date (oldest to newest)
    history.sort(key=lambda x: x['date'])

    # Save back to file
    history_data = {
        'meta': {
            'last_updated': datetime.now().isoformat(),
            'total_snapshots': len(history),
            'date_range': {
                'start': history[0]['date'] if history else None,
                'end': history[-1]['date'] if history else None
            }
        },
        'snapshots': history
    }

    try:
        os.makedirs(os.path.dirname(history_path), exist_ok=True)
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved market history: {len(history)} snapshots (last 90 days)")
    except Exception as e:
        print(f"  ❌ Failed to save market history: {e}")

def predict_hiring_trends() -> None:
    """
    Use Google Gemini API to analyze market history and predict future hiring trends.
    Requires GOOGLE_API_KEY environment variable.
    """
    api_key = os.environ.get('GOOGLE_API_KEY')

    if not api_key:
        print("  ⚠️  GOOGLE_API_KEY not found - skipping ML predictions")
        return

    # Check if predictions were already generated today
    predictions_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'predictions.json')
    today = datetime.now().strftime('%Y-%m-%d')

    try:
        if os.path.exists(predictions_path):
            with open(predictions_path, 'r', encoding='utf-8') as f:
                existing_predictions = json.load(f)
                generated_date = existing_predictions.get('generated_at', '')

                # Check if predictions were generated today
                if generated_date.startswith(today):
                    print(f"  ✓ Predictions already generated today ({today}) - skipping")
                    return
    except Exception as e:
        print(f"  ⚠️  Could not check existing predictions: {e}")

    # Load market history
    history_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'market-history.json')

    try:
        if not os.path.exists(history_path):
            print("  ℹ️  Market history not found - predictions available after data collection")
            return

        with open(history_path, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
            snapshots = history_data.get('snapshots', [])

        if len(snapshots) < 7:
            print(f"  ℹ️  Not enough data for predictions ({len(snapshots)} days, need 7+)")
            return

    except Exception as e:
        print(f"  ❌ Failed to load market history: {e}")
        return

    # Prepare data summary for Gemini
    total_jobs_trend = [s['total_jobs'] for s in snapshots[-30:]]  # Last 30 days
    category_trends = {}
    tier_trends = {}

    # Aggregate category trends
    for snapshot in snapshots[-30:]:
        for category, count in snapshot.get('categories', {}).items():
            if category not in category_trends:
                category_trends[category] = []
            category_trends[category].append(count)

    # Aggregate tier trends
    for snapshot in snapshots[-30:]:
        for tier, count in snapshot.get('tiers', {}).items():
            if tier not in tier_trends:
                tier_trends[tier] = []
            tier_trends[tier].append(count)

    # Call Gemini API
    try:
        headers = {
            'Content-Type': 'application/json',
            'x-goog-api-key': api_key
        }

        prompt = f"""Analyze this new graduate tech hiring market data and provide predictions for the next 30 days.

Historical Data (last {len(total_jobs_trend)} days):
- Total Jobs Trend: {total_jobs_trend}
- Category Trends: {json.dumps({k: v[-7:] for k, v in list(category_trends.items())[:5]})}
- Company Tier Trends: {json.dumps({k: v[-7:] for k, v in tier_trends.items()})}

Current Status:
- Current Total: {total_jobs_trend[-1] if total_jobs_trend else 0} jobs
- 7-Day Average: {sum(total_jobs_trend[-7:]) // 7 if len(total_jobs_trend) >= 7 else 0} jobs
- 30-Day Average: {sum(total_jobs_trend) // len(total_jobs_trend) if total_jobs_trend else 0} jobs

Please provide:
1. Overall market outlook (bullish/neutral/bearish)
2. Predicted total jobs in 7 days
3. Predicted total jobs in 30 days
4. Top 3 growing categories
5. Top 3 declining categories
6. Confidence level (0-100%)
7. Key insights (2-3 sentences)

Respond in JSON format:
{{
  "outlook": "bullish|neutral|bearish",
  "predictions": {{
    "7_days": {{
      "total_jobs": <number>,
      "change_percent": <number>
    }},
    "30_days": {{
      "total_jobs": <number>,
      "change_percent": <number>
    }}
  }},
  "growing_categories": ["category1", "category2", "category3"],
  "declining_categories": ["category1", "category2", "category3"],
  "confidence": <number>,
  "insights": ["insight1", "insight2", "insight3"]
}}"""

        payload = {
            'contents': [{
                'parts': [{'text': prompt}]
            }],
            'generationConfig': {
                'temperature': 0.4,
                'topK': 32,
                'topP': 1,
                'maxOutputTokens': 2048,
            }
        }

        response = limited_post(
            'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent',
            headers=headers,
            json=payload,
            timeout=12  # AGGRESSIVE: Reduced from 20s for 10K companies
        )

        if response.status_code == 200:
            result = response.json()

            # Parse Gemini response
            if 'candidates' in result and len(result['candidates']) > 0:
                content = result['candidates'][0]['content']['parts'][0]['text']

                # Extract JSON from response (handle markdown code blocks)
                content = content.strip()
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()

                predictions = json.loads(content)

                # S6: Validate required keys before trusting LLM output
                required_keys = {'outlook', 'predictions', 'confidence', 'insights'}
                missing = required_keys - set(predictions.keys())
                if missing:
                    print(f"  ⚠️  Gemini response missing keys {missing} — skipping prediction update")
                elif predictions.get('outlook') not in ('bullish', 'neutral', 'bearish'):
                    print(f"  ⚠️  Invalid outlook value '{predictions.get('outlook')}' — skipping prediction update")
                elif not isinstance(predictions.get('confidence'), (int, float)):
                    print(f"  ⚠️  Invalid confidence type — skipping prediction update")
                else:
                    # Add metadata
                    predictions['generated_at'] = datetime.now().isoformat()
                    predictions['data_points'] = len(snapshots)
                    predictions['date_range'] = {
                        'start': snapshots[0]['date'],
                        'end': snapshots[-1]['date']
                    }

                    # Save predictions
                    predictions_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'predictions.json')
                    with open(predictions_path, 'w', encoding='utf-8') as f:
                        json.dump(predictions, f, indent=2, ensure_ascii=False)

                    print(f"  ✓ Generated ML predictions: {predictions['outlook']} outlook (confidence: {predictions['confidence']}%)")
            else:
                print("  ⚠️  No predictions in Gemini response")

        else:
            print(f"  ❌ Gemini API error: {response.status_code} - [response body redacted]")

    except Exception as e:
        error_msg = str(e)
        print(f"  ❌ Failed to generate predictions: {error_msg}")


def extract_sort_date(job: Dict[str, Any]) -> datetime:
    """Extract and parse posted_at for sorting."""
    posted_at = job.get('posted_at')
    if not posted_at:
        return datetime.min
    try:
        if isinstance(posted_at, (int, float)):
            return datetime.fromtimestamp(posted_at / 1000)
        return date_parser.parse(posted_at).replace(tzinfo=None)
    except Exception:
        return datetime.min

def generate_readme(jobs: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
    """Generate README content with job listings - SimplifyJobs style"""

    # Sort jobs by posted date (most recent first)
    jobs.sort(key=extract_sort_date, reverse=True)

    # Calculate category counts
    category_counts = {}
    for job in jobs:
        cat_id = job.get('category', {}).get('id', 'other')
        category_counts[cat_id] = category_counts.get(cat_id, 0) + 1

    # Build README
    readme_content = f"""# 🎓 2026 New Grad Positions

[![GitHub stars](https://img.shields.io/github/stars/ambicuity/New-Grad-Jobs?style=social)](https://github.com/ambicuity/New-Grad-Jobs/stargazers)
[![Last Update](https://img.shields.io/badge/updated-every%205%20min-success)](https://github.com/ambicuity/New-Grad-Jobs/actions)
[![Jobs](https://img.shields.io/badge/jobs-{len(jobs)}-blue)](https://github.com/ambicuity/New-Grad-Jobs#available-positions)
[![codecov](https://codecov.io/github/ambicuity/New-Grad-Jobs/graph/badge.svg?token=1D0TO5UL1T)](https://codecov.io/github/ambicuity/New-Grad-Jobs)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/ambicuity/New-Grad-Jobs/badge)](https://securityscorecards.dev/viewer/?uri=github.com/ambicuity/New-Grad-Jobs)

**Fully automated** list of entry-level tech positions for 2025 & 2026 new graduates!

🔄 Unlike manual lists, this repo uses **150+ company APIs** and updates **every 5 minutes** 24/7.

🙏 **Contribute** by submitting an [issue](https://github.com/ambicuity/New-Grad-Jobs/issues/new/choose)! See [contribution guidelines](CONTRIBUTING.md).

> [!NOTE]
> **Solo-Maintained Project.** This repository is maintained by one person in spare time.
> PRs are reviewed within **1–2 weeks**. Bug fixes take priority over feature requests.
> Before opening an issue, read [SUPPORT.md](.github/SUPPORT.md).

---

## 📂 Browse {len(jobs)} Jobs by Category

"""

    # Add category links
    for cat_id, cat_info in CATEGORY_PATTERNS.items():
        count = category_counts.get(cat_id, 0)
        if count > 0:
            anchor = cat_info['name'].lower().replace(' ', '-').replace('&', '').replace('  ', '-')
            readme_content += f"{cat_info['emoji']} [{cat_info['name']}](#{anchor}) ({count})\n\n"

    readme_content += """---

## 🚀 Legend

| Icon | Meaning |
|------|---------|
| 🔥 | FAANG+ Company |
| 🚀 | Unicorn Startup |
| 🛂 | No Visa Sponsorship |
| 🇺🇸 | US Citizenship Required |
| 🔒 | Position Closed |

---

"""

    # Group jobs by category
    jobs_by_category = {}
    for job in jobs:
        cat_id = job.get('category', {}).get('id', 'other')
        if cat_id not in jobs_by_category:
            jobs_by_category[cat_id] = []
        jobs_by_category[cat_id].append(job)

    # Generate tables for each category
    for cat_id, cat_info in CATEGORY_PATTERNS.items():
        cat_jobs = jobs_by_category.get(cat_id, [])
        if not cat_jobs:
            continue

        readme_content += f"## {cat_info['emoji']} {cat_info['name']} New Grad Roles\n\n"
        readme_content += "[Back to top](#-2026-new-grad-positions)\n\n"
        readme_content += "| Company | Role | Location | Posted | Apply |\n"
        readme_content += "|---------|------|----------|--------|-------|\n"

        for job in cat_jobs:
            company = job.get('company', 'Unknown')
            title = job.get('title', 'Unknown')
            location = job.get('location', 'Remote')
            posted = format_posted_date(job.get('posted_at', ''))
            url = job.get('url', '#')

            # Add company tier emoji
            tier_emoji = job.get('company_tier', {}).get('emoji', '')
            if tier_emoji:
                company = f"{tier_emoji} {company}"

            # Add flags
            flags = job.get('flags', {})
            flag_str = ""
            if flags.get('no_sponsorship'):
                flag_str += " 🛂"
            if flags.get('us_citizenship_required'):
                flag_str += " 🇺🇸"
            if job.get('is_closed'):
                flag_str += " 🔒"

            # Escape pipe characters
            title = title.replace('|', '\\|')
            location = location.replace('|', '\\|')

            apply_link = f"[Apply]({url})" if url and url != '#' and not job.get('is_closed') else "🔒"

            readme_content += f"| {company} | {title}{flag_str} | {location} | {posted} | {apply_link} |\n"

        readme_content += "\n"

    readme_content += f"""---

## 📊 About This Repository

This repository automatically scrapes new graduate job opportunities from various company job boards **every 5 minutes** using multiple data sources and APIs.

### 🔌 Data Sources
- **Direct Company APIs**: Greenhouse and Lever job boards from 70+ tech companies
- **Search APIs**: Google Careers direct searches
- **Job Site Aggregation**: JobSpy integration for LinkedIn, Indeed, and Glassdoor
- **Community Submissions**: User-submitted jobs via GitHub Issues

### ⚡ Key Features
- **Comprehensive Coverage**: 70+ companies across multiple platforms
- **Real-time Updates**: Automatic updates every 5 minutes
- **Smart Filtering**: Advanced filtering for new grad positions
- **USA Focus**: Filters for US-based positions only
- **Category Organization**: Jobs organized by role type
- **Company Badges**: FAANG+ and unicorn companies highlighted

### 🎯 Filtering Criteria
- **New Grad Signals**: new grad, entry-level, junior, associate, trainee, campus, early career
- **Track Focus**: Software, Data Science, ML, Network Engineering, SRE, DevOps, PM
- **Recency**: Jobs posted within the last {config.get('filtering', {}).get('max_age_days', 60)} days
- **Location**: USA-based positions only

### 🏢 Companies Monitored

<details>
<summary>Click to expand (70+ companies)</summary>

**Greenhouse**: {', '.join([company['name'] for company in config['apis']['greenhouse']['companies']])}

**Lever**: {', '.join([company['name'] for company in config['apis']['lever']['companies']])}

**Google Careers**: Direct API searches

**JobSpy**: LinkedIn, Indeed, Glassdoor

</details>

---

### 🧪 Test Coverage

<details>
<summary>Click to view Codecov Sunburst Graph</summary>
<br>
<img src="https://codecov.io/github/ambicuity/New-Grad-Jobs/graphs/sunburst.svg?token=1D0TO5UL1T" alt="Codecov Sunburst Graph" />
</details>

---

## 🤝 Contributing

Found a job we're missing? Want to report a closed position?

1. [Submit a new job](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=new_role.yml)
2. [Report a closed job](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=edit_role.yml)
3. [Report a bug](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=bug_report.yml)

---

⭐ **Star this repo** to stay updated with the latest new grad opportunities!

*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*
"""

    return readme_content


def generate_rss_feed(jobs: List[Dict[str, Any]], max_items: int = 50) -> None:
    """Generate an RSS 2.0 feed from the most recent jobs.

    Writes docs/feed.xml so users can subscribe via any feed reader.
    Zero-cost, zero-infra solution for job alerts.
    """
    feed_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'feed.xml')

    # Sort by date descending, take top N
    jobs.sort(key=extract_sort_date, reverse=True)
    sorted_jobs = jobs[:max_items]

    now_str = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')

    items = []
    for job in sorted_jobs:
        company = job.get('company', 'Unknown')
        title = job.get('title', 'Unknown')
        url = job.get('url', '')
        location = job.get('location', 'Remote')
        category = job.get('category', {}).get('name', 'General')
        posted_at_dt = extract_sort_date(job)
        pubDate = posted_at_dt.strftime('%a, %d %b %Y %H:%M:%S +0000') if posted_at_dt != datetime.min else now_str

        items.append(f"""    <item>
      <title>{xml_escape(title)} at {xml_escape(company)}</title>
      <link>{xml_escape(url)}</link>
      <description>New grad role at {xml_escape(company)} in {xml_escape(location)}. Category: {xml_escape(category)}</description>
      <pubDate>{pubDate}</pubDate>
      <guid isPermaLink="true">{xml_escape(url)}</guid>
    </item>""")

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>New Grad Jobs</title>
    <link>https://ambicuity.github.io/New-Grad-Jobs/</link>
    <description>Automatically updated new graduate job opportunities in Software, Data, and SRE roles.</description>
    <language>en-us</language>
    <lastBuildDate>{now_str}</lastBuildDate>
    <atom:link href="https://ambicuity.github.io/New-Grad-Jobs/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>
"""

    try:
        os.makedirs(os.path.dirname(feed_path), exist_ok=True)
        with open(feed_path, 'w', encoding='utf-8') as f:
            f.write(rss_xml)
        print(f"📡 RSS feed generated with {len(sorted_jobs)} items → docs/feed.xml")
    except Exception as e:
        print(f"⚠️  Failed to write RSS feed: {e}")


def generate_health_json(jobs: List[Dict[str, Any]],
                         source_counts: Dict[str, int],
                         start_time: float) -> None:
    """Generate docs/health.json for monitoring and staleness detection.

    Status values:
      - ok: all sources returned jobs and total > 0
      - degraded: at least one source returned 0 jobs
      - failed: total job count is 0
    """
    health_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'health.json')

    total_jobs = len(jobs)
    zero_sources = [s for s, c in source_counts.items() if c == 0]

    if total_jobs == 0:
        status = 'failed'
    elif zero_sources:
        status = 'degraded'
    else:
        status = 'ok'

    health = {
        'status': status,
        'last_run': datetime.utcnow().isoformat() + 'Z',
        'total_jobs': total_jobs,
        'source_counts': source_counts,
        'zero_sources': zero_sources,
        'run_duration_seconds': round(time.time() - start_time, 1),
    }

    try:
        os.makedirs(os.path.dirname(health_path), exist_ok=True)
        with open(health_path, 'w', encoding='utf-8') as f:
            json.dump(health, f, indent=2)
        print(f"🩺 Health report: status={status}, total_jobs={total_jobs}")
    except Exception as e:
        print(f"⚠️  Failed to write health.json: {e}")


def check_job_url_health(jobs: List[Dict[str, Any]],
                          sample_pct: float = 0.05,
                          max_checks: int = 50) -> None:
    """HEAD-request a random sample of job URLs to detect dead links.

    Updates each sampled job in-place with `url_verified` (bool).
    Best-effort — failures are logged but never block the pipeline.
    """
    sample_size = min(max_checks, max(1, int(len(jobs) * sample_pct)))
    sample = random.sample(jobs, min(sample_size, len(jobs)))
    verified = 0
    dead = 0

    for job in sample:
        url = job.get('url', '')
        if not url or not url.startswith('http'):
            continue

        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ''
            if hostname in ('localhost', '127.0.0.1', '169.254.169.254', '0.0.0.0') or hostname.startswith(('192.168.', '10.', '172.')):
                continue

            resp = HTTP_SESSION.head(url, timeout=4, allow_redirects=True)
            if resp.status_code < 400:
                job['url_verified'] = True
                verified += 1
            else:
                job['url_verified'] = False
                dead += 1
        except Exception:
            job['url_verified'] = False
            dead += 1

    print(f"🔍 URL health check: {verified} verified, {dead} dead/unreachable out of {sample_size} sampled")


def main():
    """Main function to scrape jobs and update README

    PERFORMANCE OPTIMIZED: Uses parallel fetching for all API sources
    to reduce execution time from ~7 min to ~1-2 min.
    """
    start_time = time.time()

    print("🚀 Starting job aggregation (PARALLEL MODE)...")
    print("=" * 60)


    # Load configuration
    config = load_config()

    # Load worker pool configurations from config.yml with fallbacks
    global DEFAULT_GREENHOUSE_MIN_WORKERS, DEFAULT_GREENHOUSE_MAX_WORKERS
    global DEFAULT_LEVER_MIN_WORKERS, DEFAULT_LEVER_MAX_WORKERS
    global DEFAULT_GOOGLE_MIN_WORKERS, DEFAULT_GOOGLE_MAX_WORKERS
    global DEFAULT_JOBSPY_WORKERS, DEFAULT_ORCHESTRATOR_WORKERS

    pools = config.get('worker_pools', {})
    DEFAULT_GREENHOUSE_MIN_WORKERS = pools.get('greenhouse_min_workers', DEFAULT_GREENHOUSE_MIN_WORKERS)
    DEFAULT_GREENHOUSE_MAX_WORKERS = pools.get('greenhouse_max_workers', DEFAULT_GREENHOUSE_MAX_WORKERS)
    DEFAULT_LEVER_MIN_WORKERS = pools.get('lever_min_workers', DEFAULT_LEVER_MIN_WORKERS)
    DEFAULT_LEVER_MAX_WORKERS = pools.get('lever_max_workers', DEFAULT_LEVER_MAX_WORKERS)
    DEFAULT_GOOGLE_MIN_WORKERS = pools.get('google_min_workers', DEFAULT_GOOGLE_MIN_WORKERS)
    DEFAULT_GOOGLE_MAX_WORKERS = pools.get('google_max_workers', DEFAULT_GOOGLE_MAX_WORKERS)
    DEFAULT_JOBSPY_WORKERS = pools.get('jobspy_workers', DEFAULT_JOBSPY_WORKERS)
    DEFAULT_ORCHESTRATOR_WORKERS = pools.get('orchestrator_workers', DEFAULT_ORCHESTRATOR_WORKERS)

    # Load Workday limits from config.yml with validated fallbacks
    global WORKDAY_PAGE_LIMIT, WORKDAY_MAX_JOBS_PER_COMPANY
    workday_cfg = config.get('apis', {}).get('workday', {})
    WORKDAY_PAGE_LIMIT = _coerce_positive_int(
        workday_cfg.get('page_limit'),
        DEFAULT_WORKDAY_PAGE_LIMIT,
        'apis.workday.page_limit',
    )
    WORKDAY_MAX_JOBS_PER_COMPANY = _coerce_positive_int(
        workday_cfg.get('max_jobs_per_company'),
        DEFAULT_WORKDAY_MAX_JOBS_PER_COMPANY,
        'apis.workday.max_jobs_per_company',
    )

    print(f"   Worker pools configured:")
    print(f"     Greenhouse: {DEFAULT_GREENHOUSE_MIN_WORKERS}-{DEFAULT_GREENHOUSE_MAX_WORKERS}")
    print(f"     Lever: {DEFAULT_LEVER_MIN_WORKERS}-{DEFAULT_LEVER_MAX_WORKERS}")
    print(f"     Google: {DEFAULT_GOOGLE_MIN_WORKERS}-{DEFAULT_GOOGLE_MAX_WORKERS}")
    print(f"     JobSpy: {DEFAULT_JOBSPY_WORKERS}")
    print(f"     Orchestrator: {DEFAULT_ORCHESTRATOR_WORKERS}")
    print(f"     Workday: page_limit={WORKDAY_PAGE_LIMIT}, max_total={WORKDAY_MAX_JOBS_PER_COMPANY}")

    # Load Google Careers limits from config.yml with validated fallbacks
    global GOOGLE_MAX_PAGES
    google_cfg = config.get('apis', {}).get('google', {})
    GOOGLE_MAX_PAGES = _coerce_positive_int(
        google_cfg.get('MAX_PAGES'),
        DEFAULT_GOOGLE_MAX_PAGES,
        'apis.google.MAX_PAGES',
    )
    print(f"     Google: max_pages={GOOGLE_MAX_PAGES}")

    # DEBUG: Print company counts from config
    gh_count = len(config['apis'].get('greenhouse', {}).get('companies', []))
    lever_count = len(config['apis'].get('lever', {}).get('companies', []))
    workday_count = len(config['apis'].get('workday', {}).get('companies', []))
    total_companies = gh_count + lever_count + workday_count
    print(f"\n📋 Configuration loaded:")
    print(f"   Greenhouse: {gh_count} companies")
    print(f"   Lever: {lever_count} companies")
    print(f"   Workday: {workday_count} companies")
    print(f"   TOTAL: {total_companies} companies")
    # P6: Removed stale 10K company warning — config has ~200 companies by design.
    print("="  * 60)

    # Collect all jobs using parallel fetchers
    all_jobs = []

    # Phase 1: Fetch from all API sources IN PARALLEL
    print("\n📡 Phase 1: Fetching jobs from all sources in parallel...")

    # Master parallel fetcher: runs Greenhouse, Lever, Google, JobSpy, Workday concurrently
    # Increased to 20 workers (DEFAULT_ORCHESTRATOR_WORKERS) to handle all sources at maximum parallelism for 1000+ companies
    with ThreadPoolExecutor(max_workers=DEFAULT_ORCHESTRATOR_WORKERS) as executor:  # AGGRESSIVE: 20 parallel APIs
        futures = {}

        # Submit Greenhouse parallel fetch
        if 'greenhouse' in config['apis'] and config['apis']['greenhouse'].get('companies'):
            futures['greenhouse'] = executor.submit(
                fetch_all_greenhouse_jobs_parallel,
                config['apis']['greenhouse']['companies']
            )

        # Submit Lever parallel fetch
        if 'lever' in config['apis'] and config['apis']['lever'].get('companies'):
            futures['lever'] = executor.submit(
                fetch_all_lever_jobs_parallel,
                config['apis']['lever']['companies']
            )

        # Submit Google parallel fetch (P5: gated on enabled flag)
        if 'google' in config['apis'] and config['apis']['google'].get('enabled') and config['apis']['google'].get('search_terms'):
            futures['google'] = executor.submit(
                fetch_google_jobs,
                search_terms=config['apis']['google']['search_terms'],
                max_pages=GOOGLE_MAX_PAGES
            )

        # Submit JobSpy fetch (already parallelized internally)
        if 'jobspy' in config['apis']:
            futures['jobspy'] = executor.submit(
                fetch_jobspy_jobs,
                config['apis']['jobspy']
            )

        # Submit Workday parallel fetch
        if 'workday' in config['apis'] and config['apis']['workday'].get('enabled'):
             futures['workday'] = executor.submit(
                fetch_workday_jobs,
                config['apis']['workday']['companies'],
                page_limit=WORKDAY_PAGE_LIMIT,
                max_total_limit=WORKDAY_MAX_JOBS_PER_COMPANY
            )

        # Collect results from all futures
        source_counts = {}  # C1: Track per-source job counts for health.json
        for source, future in futures.items():
            try:
                jobs = future.result()
                all_jobs.extend(jobs)
                source_counts[source] = len(jobs)
                print(f"  ✅ {source.upper()}: {len(jobs)} jobs collected")
            except Exception as e:
                source_counts[source] = 0
                print(f"  ❌ {source.upper()} failed: {e}")

    # Fetch from third-party scraping APIs (if configured) - these are usually disabled
    if 'scraper_apis' in config['apis']:
        scraper_apis = config['apis']['scraper_apis']

        # SerpApi for Google Jobs
        if 'serp_api' in scraper_apis:
            serp_jobs = fetch_serp_api_jobs(scraper_apis['serp_api'])
            all_jobs.extend(serp_jobs)

        # ScraperAPI for general web scraping
        if 'scraper_api' in scraper_apis:
            scraper_jobs = fetch_scraper_api_jobs(scraper_apis['scraper_api'])
            all_jobs.extend(scraper_jobs)

    print(f"\n📊 Total jobs fetched: {len(all_jobs)}")

    # Phase 2: Deduplicate jobs
    print("\n🔄 Phase 2: Deduplicating jobs...")
    all_jobs = deduplicate_jobs(all_jobs)
    print(f"   Jobs after deduplication: {len(all_jobs)}")


    # Phase 3: Filter, enrich, and output
    print("\n⚙️ Phase 3: Filtering and enriching jobs...")

    # Filter jobs
    filtered_jobs = filter_jobs(all_jobs, config)
    print(f"   Jobs after filtering: {len(filtered_jobs)}")

    # Enrich jobs with categorization and flags
    enriched_jobs = enrich_jobs(filtered_jobs)
    print(f"   Jobs enriched with categories and flags")

    # C3: Check a sample of job URLs for dead links
    check_job_url_health(enriched_jobs)

    # Generate JSON data
    # Sanitize jobs to remove NaN values
    def sanitize_value(v):
        if isinstance(v, float):
            if math.isnan(v) or math.isinf(v):
                return None
        return v

    def deep_sanitize(obj):
        if isinstance(obj, dict):
            return {k: deep_sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [deep_sanitize(v) for v in obj]
        else:
            return sanitize_value(obj)

    enriched_jobs = deep_sanitize(enriched_jobs)

    jobs_json = generate_jobs_json(enriched_jobs, config)

    # ========== Save Historical Market Data ==========
    save_market_history(enriched_jobs)

    # ========== Generate ML Predictions ==========
    predict_hiring_trends()

    # Write JSON file to docs/ (GitHub Pages source directory)
    json_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'jobs.json')
    try:
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, 'w') as f:
            json.dump(jobs_json, f, indent=2)
        print(f"jobs.json updated successfully with {len(enriched_jobs)} jobs")
    except Exception as e:
        print(f"Error writing jobs.json: {e}")

    # Generate README content
    readme_content = generate_readme(enriched_jobs, config)

    # Write to README file
    readme_path = os.path.join(os.path.dirname(__file__), '..', 'README.md')
    try:
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        print(f"README.md updated successfully with {len(enriched_jobs)} jobs")
    except Exception as e:
        print(f"Error writing README.md: {e}")
        sys.exit(1)

    # ========== Generate RSS Feed ==========
    generate_rss_feed(enriched_jobs)

    # ========== Generate Health Report ==========
    generate_health_json(enriched_jobs, source_counts, start_time)

    # Report execution time
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"✅ Job aggregation complete!")
    print(f"⏱️  Total execution time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"📊 Final job count: {len(enriched_jobs)}")
    print("=" * 60)

if __name__ == "__main__":
    main()

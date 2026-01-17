#!/usr/bin/env python3
"""
New Grad Jobs Aggregator
Scrapes job postings from Greenhouse, Lever, Google Careers and JobSpy APIs 
and updates README.md and jobs.json
"""

import requests
import yaml
import json
import re
import sys
import time
import os
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from typing import List, Dict, Any, Optional

# Import JobSpy for additional job site scraping
try:
    from jobspy import scrape_jobs
    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False
    print("⚠️  JobSpy not available. Install with: pip install python-jobspy")

# ============================================================================
# COMPANY CLASSIFICATIONS
# ============================================================================

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

# Defense & Aerospace sector
DEFENSE = {
    'Raytheon', 'RTX', 'Lockheed Martin', 'Boeing', 'Northrop Grumman',
    'General Dynamics', 'General Dynamics Mission Systems', 'General Dynamics Information Technology',
    'BAE Systems', 'L3Harris', 'Collins Aerospace', 'HII', 'Huntington Ingalls Industries',
    'Booz Allen Hamilton', 'Booz Allen', 'Leidos', 'SAIC', 'General Atomics', 'Anduril',
    'Shield AI', 'SpaceX', 'Sierra Space', 'Relativity Space', 'Blue Origin',
    'Rocket Lab', 'Rocket Lab USA', 'True Anomaly', 'KBR', 'CACI', 'Peraton', 'Amentum',
    'AMERICAN SYSTEMS', 'T-Rex Solutions', 'Wyetech', 'Altamira Technologies',
}

# Finance sector
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

# Healthcare sector
HEALTHCARE = {
    'iRhythm', 'Epic Systems', 'Cerner', 'Philips Healthcare', 'Siemens Healthineers',
    'GE Healthcare', 'Medtronic', 'Johnson & Johnson', 'Pfizer', 'Moderna',
    'UnitedHealth', 'Anthem', 'CVS Health', 'Cigna', 'Humana', 'Oscar Health',
    'Tempus', 'Flatiron Health', 'Veracyte', 'Illumina', 'Thermo Fisher',
    'Boston Scientific', 'MultiCare Health System', 'BlueCross BlueShield',
    'Citizen Health', 'Solace Health', 'Healthfirst', 'Candid Health', 'MedImpact',
}

# Startups (early-stage, smaller companies)
STARTUPS = {
    'Vercel', 'Supabase', 'PlanetScale', 'Railway', 'Zepto', 'Zepz',
    'Zealthy', 'Qumulo', 'Runway', 'Hugging Face', 'Weights & Biases',
    'Cohere', 'Mistral', 'Perplexity', 'Replit', 'Modal', 'Resend',
    'Glide', 'Continue', 'Meshy', 'Suno', 'Fireworks AI', 'Nexthop.ai',
    'SpruceID', 'Netic', 'D3', 'Promise', 'Lightfield', 'Fermat', 'N1',
    'OffDeal', 'Eventual', 'Mechanize', 'Remi', 'TrueBuilt', 'Uare.ai',
}
}

# Job categories based on title keywords
CATEGORY_PATTERNS = {
    'software_engineering': {
        'name': 'Software Engineering',
        'emoji': '💻',
        'keywords': [
            'software engineer', 'software developer', 'swe', 'full stack',
            'fullstack', 'frontend', 'front-end', 'backend', 'back-end',
            'web developer', 'mobile developer', 'ios developer', 'android developer',
            'application developer', 'systems engineer', 'platform engineer',
            'solutions engineer', 'integration engineer', 'api engineer'
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
    
    for category_id, category_info in CATEGORY_PATTERNS.items():
        if category_id == 'other':
            continue
        for keyword in category_info['keywords']:
            if keyword in combined:
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

def get_company_tier(company_name: str) -> Dict[str, Any]:
    """Get company tier classification including sectors"""
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

def fetch_greenhouse_jobs(company_name: str, url: str, max_retries: int = 2) -> List[Dict[str, Any]]:
    """Fetch jobs from Greenhouse API with retry logic"""
    jobs = []
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                print(f"  🔄 Retry {attempt} for {company_name}...")
                time.sleep(1)  # Wait before retry
            
            print(f"Fetching jobs from {company_name} (Greenhouse)...")
            response = requests.get(url, timeout=15)
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

def fetch_lever_jobs(company_name: str, url: str, max_retries: int = 2) -> List[Dict[str, Any]]:
    """Fetch jobs from Lever API with retry logic"""
    jobs = []
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                print(f"  🔄 Retry {attempt} for {company_name}...")
                time.sleep(1)  # Wait before retry
            
            print(f"Fetching jobs from {company_name} (Lever)...")
            response = requests.get(url, timeout=15)
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

def fetch_google_jobs(search_terms: List[str], max_retries: int = 2) -> List[Dict[str, Any]]:
    """Fetch jobs from Google Careers API with retry logic"""
    all_jobs = []
    
    for search_term in search_terms:
        jobs = []
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    print(f"  🔄 Retry {attempt} for Google search '{search_term}'...")
                    time.sleep(1)  # Wait before retry
                
                print(f"Searching Google careers for '{search_term}'...")
                # Build the search URL with USA location filter
                search_query = search_term.replace(' ', '%20')
                url = f"https://careers.google.com/api/v3/search/?location=United States&q={search_query}&page_size=100"
                
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                if not isinstance(data, dict) or 'jobs' not in data:
                    print(f"  ⚠️  Google: Unexpected API response format for '{search_term}'")
                    continue
                
                for job in data.get('jobs', []):
                    # Extract location information from Google's format
                    locations = job.get('locations', [])
                    location_names = []
                    for loc in locations:
                        if loc.get('country_code') == 'US':  # Only USA locations
                            display_name = loc.get('display', '')
                            if display_name:
                                location_names.append(display_name)
                    
                    if not location_names:  # Skip jobs without USA locations
                        continue
                    
                    location_str = '; '.join(location_names)
                    description = job.get('description', '') or ''
                    
                    jobs.append({
                        'company': 'Google',
                        'title': job.get('title', ''),
                        'location': location_str,
                        'url': job.get('apply_url', ''),
                        'posted_at': job.get('created') or job.get('publish_date'),
                        'source': 'Google Careers',
                        'description': description[:500] if description else ''
                    })
                
                print(f"  ✓ Found {len(jobs)} USA jobs from Google search '{search_term}'")
                all_jobs.extend(jobs)
                break  # Success, exit retry loop
                
            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    print(f"  ⏱️  Google search '{search_term}' timed out, retrying...")
                    continue
                else:
                    print(f"  ❌ Google search '{search_term}' timed out after {max_retries + 1} attempts")
            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    print(f"  ⚠️  Request error for Google search '{search_term}': {e}, retrying...")
                    continue
                else:
                    print(f"  ❌ Request error for Google search '{search_term}' after {max_retries + 1} attempts: {e}")
            except Exception as e:
                if attempt < max_retries:
                    print(f"  ⚠️  Error fetching Google search '{search_term}': {e}, retrying...")
                    continue
                else:
                    print(f"  ❌ Error fetching Google search '{search_term}' after {max_retries + 1} attempts: {e}")
    
    return all_jobs

def fetch_jobspy_jobs(config_jobspy: Dict[str, Any], max_retries: int = 2) -> List[Dict[str, Any]]:
    """Fetch jobs using JobSpy library from multiple job sites"""
    if not JOBSPY_AVAILABLE:
        print("❌ JobSpy library not available, skipping...")
        return []
    
    if not config_jobspy.get('enabled', False):
        print("JobSpy is disabled in configuration, skipping...")
        return []
    
    all_jobs = []
    sites = config_jobspy.get('sites', ['linkedin', 'indeed', 'glassdoor'])
    search_terms = config_jobspy.get('search_terms', ['new grad software engineer'])
    location = config_jobspy.get('location', 'United States')
    results_wanted = config_jobspy.get('results_wanted', 50)
    hours_old = config_jobspy.get('hours_old', 72)
    
    for site in sites:
        for search_term in search_terms:
            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        print(f"  🔄 Retry {attempt} for {site} search '{search_term}'...")
                        time.sleep(2)  # Wait longer before retry for external sites
                    
                    print(f"Searching {site.upper()} for '{search_term}' via JobSpy...")
                    
                    # Use JobSpy to scrape jobs
                    jobs_df = scrape_jobs(
                        site_name=site,
                        search_term=search_term,
                        location=location,
                        results_wanted=results_wanted,
                        hours_old=hours_old,
                        country_indeed='USA'  # For Indeed, specify USA
                    )
                    
                    if jobs_df is None or jobs_df.empty:
                        print(f"  ⚠️  No jobs found on {site.upper()} for '{search_term}'")
                        break
                    
                    # Convert DataFrame to list of dictionaries
                    jobs_found = 0
                    for _, row in jobs_df.iterrows():
                        description = row.get('description', '') or ''
                        # Map JobSpy fields to our standard format
                        job = {
                            'company': row.get('company', 'Unknown'),
                            'title': row.get('title', ''),
                            'location': row.get('location', 'Remote'),
                            'url': row.get('job_url', ''),
                            'posted_at': row.get('date_posted', ''),
                            'source': f'JobSpy ({site.title()})',
                            'description': description[:500] if description else ''
                        }
                        
                        # Only add jobs with valid URLs
                        if job['url'] and job['url'].startswith('http'):
                            all_jobs.append(job)
                            jobs_found += 1
                    
                    print(f"  ✓ Found {jobs_found} jobs from {site.upper()} for '{search_term}'")
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    if attempt < max_retries:
                        print(f"  ⚠️  Error with {site.upper()} search '{search_term}': {str(e)[:100]}, retrying...")
                        continue
                    else:
                        print(f"  ❌ Error with {site.upper()} search '{search_term}' after {max_retries + 1} attempts: {str(e)[:100]}")
                
                # Add delay between different searches to be respectful
                if site == 'linkedin':
                    time.sleep(2)  # LinkedIn needs more time between requests
                else:
                    time.sleep(1)
    
    print(f"Total jobs found via JobSpy: {len(all_jobs)}")
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

def has_new_grad_signal(title: str, signals: List[str]) -> bool:
    """Check if job title contains new grad signals"""
    title_lower = title.lower()
    return any(signal.lower() in title_lower for signal in signals)

def has_track_signal(title: str, signals: List[str]) -> bool:
    """Check if job title contains track signals"""
    title_lower = title.lower()
    return any(signal.lower() in title_lower for signal in signals)

def is_recent_job(posted_at: str, max_age_days: int) -> bool:
    """Check if job was posted within the specified number of days"""
    if not posted_at:
        return False
    
    try:
        # Handle timestamp integers (from Lever API)
        if isinstance(posted_at, (int, float)):
            posted_date = datetime.fromtimestamp(posted_at / 1000)  # Convert milliseconds to seconds
        else:
            posted_date = date_parser.parse(posted_at)
        
        # Remove timezone info for comparison
        posted_date = posted_date.replace(tzinfo=None)
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        return posted_date >= cutoff_date
    except Exception as e:
        print(f"Error parsing date {posted_at}: {e}")
        return False

def is_usa_location(location: str) -> bool:
    """Check if job location is in the USA"""
    if not location:
        return False
    
    location_lower = location.lower().strip()
    
    # Handle explicit non-USA indicators
    non_usa_indicators = [
        'uk', 'united kingdom', 'england', 'london', 'manchester', 'edinburgh',
        'canada', 'toronto', 'vancouver', 'montreal', 'ottawa', 
        'mexico', 'mexico city',
        'japan', 'tokyo', 'osaka',
        'germany', 'berlin', 'munich',
        'france', 'paris',
        'netherlands', 'amsterdam', 
        'ireland', 'dublin',
        'israel', 'tel aviv',
        'australia', 'sydney', 'melbourne',
        'india', 'bangalore', 'mumbai', 'hyderabad', 'chennai', 'delhi', 'bengaluru',
        'singapore',
        'china', 'beijing', 'shanghai',
        'sweden', 'stockholm',
        'denmark', 'copenhagen',
        'norway', 'oslo',
        'finland', 'helsinki',
        'switzerland', 'zurich',
        'spain', 'madrid', 'barcelona',
        'italy', 'milan', 'rome',
        'belgium', 'brussels',
        'austria', 'vienna',
        'poland', 'warsaw',
        'czech republic', 'prague',
        'hungary', 'budapest',
        'romania', 'bucharest',
        'bulgaria', 'sofia',
        'greece', 'athens',
        'portugal', 'lisbon',
        'brazil', 'sao paulo', 'rio de janeiro',
        'argentina', 'buenos aires',
        'chile', 'santiago',
        'colombia', 'bogota',
        'peru', 'lima',
        'luxembourg', 'luxembourg city',
        'philippines', 'manila',
        'thailand', 'bangkok',
        'vietnam', 'ho chi minh',
        'malaysia', 'kuala lumpur',
        'south korea', 'seoul',
        'anz', 'anzac', 'emea',
        'europe', 'asia', 'apac'
    ]
    
    # Check for non-USA indicators
    for indicator in non_usa_indicators:
        if indicator in location_lower:
            return False
    
    # USA state abbreviations and names
    usa_states = [
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
    ]
    
    # USA cities (major ones)
    usa_cities = [
        'new york', 'los angeles', 'chicago', 'houston', 'phoenix', 'philadelphia',
        'san antonio', 'san diego', 'dallas', 'san jose', 'austin', 'jacksonville',
        'fort worth', 'columbus', 'charlotte', 'san francisco', 'indianapolis',
        'seattle', 'denver', 'washington', 'boston', 'el paso', 'nashville',
        'detroit', 'oklahoma city', 'portland', 'las vegas', 'memphis',
        'louisville', 'baltimore', 'milwaukee', 'albuquerque', 'tucson',
        'fresno', 'sacramento', 'mesa', 'kansas city', 'atlanta', 'long beach',
        'colorado springs', 'raleigh', 'miami', 'virginia beach', 'omaha',
        'oakland', 'minneapolis', 'tulsa', 'arlington', 'tampa', 'new orleans',
        'wichita', 'cleveland', 'bakersfield', 'aurora', 'anaheim', 'honolulu',
        'santa ana', 'riverside', 'corpus christi', 'lexington', 'stockton',
        'henderson', 'saint paul', 'st. paul', 'cincinnati', 'pittsburgh',
        'greensboro', 'anchorage', 'plano', 'lincoln', 'orlando', 'irvine',
        'newark', 'durham', 'chula vista', 'toledo', 'fort wayne', 'st. petersburg',
        'laredo', 'jersey city', 'chandler', 'madison', 'lubbock', 'scottsdale',
        'reno', 'buffalo', 'gilbert', 'glendale', 'north las vegas', 'winston-salem',
        'chesapeake', 'norfolk', 'fremont', 'garland', 'irving', 'hialeah',
        'richmond', 'boise', 'spokane', 'baton rouge', 'tacoma', 'san bernardino',
        'modesto', 'fontana', 'des moines', 'moreno valley', 'santa clarita',
        'fayetteville', 'birmingham', 'oxnard', 'rochester', 'port st. lucie',
        'grand rapids', 'huntsville', 'salt lake city', 'grand prairie',
        'mckinney', 'montgomery', 'akron', 'little rock', 'augusta', 'shreveport',
        'mobile', 'worcester', 'knoxville', 'newport news', 'chattanooga',
        'providence', 'fort lauderdale', 'elk grove', 'ontario', 'salem',
        'santa rosa', 'dayton', 'eugene', 'palmdale', 'salinas', 'springfield',
        'pasadena', 'rockford', 'pomona', 'corona', 'paterson', 'overland park',
        'sioux falls', 'alexandria', 'hayward', 'murfreesboro', 'pearland',
        'hartford', 'fargo', 'sunnyvale', 'escondido', 'lakewood', 'hollywood',
        'torrance', 'bridgeport', 'orange', 'garden grove', 'oceanside',
        'jackson', 'fort collins', 'rancho cucamonga', 'cape coral', 'santa maria',
        'vancouver', 'sioux city', 'springfield', 'peoria', 'pembroke pines',
        'elk grove', 'lancaster', 'corona', 'eugene', 'palmdale', 'salinas',
        'mountain view', 'palo alto', 'menlo park', 'redwood city', 'cupertino',
        'santa clara', 'sunnyvale', 'bellevue', 'redmond', 'kirkland'
    ]
    
    # Check for explicit USA indicators
    usa_indicators = [
        'united states', 'usa', 'us', 'america', 'remote - usa', 'remote usa',
        'usa remote', 'us remote', 'remote - us'
    ]
    
    for indicator in usa_indicators:
        if indicator in location_lower:
            return True
    
    # Check for USA states
    for state in usa_states:
        if state in location_lower:
            return True
    
    # Check for USA cities
    for city in usa_cities:
        if city in location_lower:
            return True
    
    # Handle "Remote" locations without explicit country - treat as potentially USA
    if location_lower in ['remote', 'anywhere']:
        return True
    
    # If we can't determine, default to False to be safe
    return False

def filter_jobs(jobs: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Filter jobs based on configuration criteria"""
    filtered_jobs = []
    filters = config['filters']
    
    for job in jobs:
        title = job.get('title', '')
        location = job.get('location', '')
        posted_at = job.get('posted_at', '')
        
        # Check for new grad signals
        if not has_new_grad_signal(title, filters['new_grad_signals']):
            continue
        
        # For jobs with clear new grad signals, track signals are optional
        has_track = has_track_signal(title, filters['track_signals'])
        
        # Strong new grad signals that don't need additional track signals
        strong_new_grad_signals = [
            "new grad", "new graduate", "graduate program", "campus", "university grad", 
            "college grad", "early career", "2025 start", "2026 start"
        ]
        has_strong_new_grad = any(signal.lower() in title.lower() for signal in strong_new_grad_signals)
        
        # Accept if: has strong new grad signal OR (has new grad signal AND track signal)
        if not (has_strong_new_grad or has_track):
            continue
            
        # Check if job is recent enough
        if not is_recent_job(posted_at, filters['max_age_days']):
            continue
        
        # Check if job location is in USA
        if not is_usa_location(location):
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
            posted_date = date_parser.parse(posted_at)
            
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
    except:
        return "Unknown"

def get_iso_date(posted_at) -> str:
    """Get ISO format date string"""
    try:
        if isinstance(posted_at, (int, float)):
            posted_date = datetime.fromtimestamp(posted_at / 1000)
        else:
            posted_date = date_parser.parse(posted_at)
        return posted_date.replace(tzinfo=None).isoformat()
    except:
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
    def get_sort_date(job):
        posted_at = job.get('posted_at')
        if not posted_at:
            return datetime.min
        try:
            if isinstance(posted_at, (int, float)):
                return datetime.fromtimestamp(posted_at / 1000)
            else:
                return date_parser.parse(posted_at).replace(tzinfo=None)
        except:
            return datetime.min
    
    jobs.sort(key=get_sort_date, reverse=True)
    
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

def generate_readme(jobs: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
    """Generate README content with job listings - SimplifyJobs style"""
    
    # Sort jobs by posted date (most recent first)
    def get_sort_date(job):
        posted_at = job['posted_at']
        if not posted_at:
            return datetime.min
        try:
            if isinstance(posted_at, (int, float)):
                return datetime.fromtimestamp(posted_at / 1000)
            else:
                parsed_date = date_parser.parse(posted_at)
                return parsed_date.replace(tzinfo=None)
        except:
            return datetime.min
    
    jobs.sort(key=get_sort_date, reverse=True)
    
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

**Fully automated** list of entry-level tech positions for 2025 & 2026 new graduates!

🔄 Unlike manual lists, this repo uses **70+ company APIs** and updates **every 5 minutes** 24/7.

🙏 **Contribute** by submitting an [issue](https://github.com/ambicuity/New-Grad-Jobs/issues/new/choose)! See [contribution guidelines](CONTRIBUTING.md).

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
- **Recency**: Jobs posted within the last {config['filters']['max_age_days']} days
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

def main():
    """Main function to scrape jobs and update README"""
    print("Starting job aggregation...")
    
    # Load configuration
    config = load_config()
    
    # Collect all jobs
    all_jobs = []
    
    # Fetch from Greenhouse
    for company in config['apis']['greenhouse']['companies']:
        jobs = fetch_greenhouse_jobs(company['name'], company['url'])
        all_jobs.extend(jobs)
    
    # Fetch from Lever  
    for company in config['apis']['lever']['companies']:
        jobs = fetch_lever_jobs(company['name'], company['url'])
        all_jobs.extend(jobs)
    
    # Fetch from Google Careers
    if 'google' in config['apis'] and 'search_terms' in config['apis']['google']:
        google_jobs = fetch_google_jobs(config['apis']['google']['search_terms'])
        all_jobs.extend(google_jobs)
    
    # Fetch from JobSpy (additional job sites)
    if 'jobspy' in config['apis']:
        jobspy_jobs = fetch_jobspy_jobs(config['apis']['jobspy'])
        all_jobs.extend(jobspy_jobs)
    
    # Fetch from third-party scraping APIs (if configured)
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
    
    print(f"Total jobs fetched: {len(all_jobs)}")
    
    # Filter jobs
    filtered_jobs = filter_jobs(all_jobs, config)
    print(f"Jobs after filtering: {len(filtered_jobs)}")
    
    # Enrich jobs with categorization and flags
    enriched_jobs = enrich_jobs(filtered_jobs)
    print(f"Jobs enriched with categories and flags")
    
    # Generate JSON data
    jobs_json = generate_jobs_json(enriched_jobs, config)
    
    # Write JSON file
    json_path = os.path.join(os.path.dirname(__file__), '..', 'jobs.json')
    try:
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

if __name__ == "__main__":
    main()
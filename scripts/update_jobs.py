#!/usr/bin/env python3
"""
New Grad Jobs Aggregator
Scrapes job postings from Greenhouse and Lever APIs and updates README.md
"""

import requests
import yaml
import json
import re
import sys
import time
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from typing import List, Dict, Any
import os

def load_config() -> Dict[str, Any]:
    """Load configuration from config.yml"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

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
                jobs.append({
                    'company': company_name,
                    'title': job.get('title', ''),
                    'location': job.get('location', {}).get('name', 'Remote'),
                    'url': job.get('absolute_url', ''),
                    'posted_at': job.get('updated_at') or job.get('created_at'),
                    'source': 'Greenhouse'
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
                jobs.append({
                    'company': company_name,
                    'title': job.get('text', ''),
                    'location': job.get('categories', {}).get('location', 'Remote'),
                    'url': job.get('hostedUrl', ''),
                    'posted_at': job.get('createdAt'),
                    'source': 'Lever'
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
                    
                    jobs.append({
                        'company': 'Google',
                        'title': job.get('title', ''),
                        'location': location_str,
                        'url': job.get('apply_url', ''),
                        'posted_at': job.get('created') or job.get('publish_date'),
                        'source': 'Google Careers'
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
        
        title_lower = title.lower()
        
        # Exclude senior/principal/staff level positions regardless of other criteria
        # Be very strict about excluding non-entry level positions
        if any(exclusion in title_lower for exclusion in [
            "senior", "sr.", "principal", "staff", "lead", "director", "manager", "head",
            " ii ", " iii ", " iv ", " v ", " vi ", " 2 ", " 3 ", " 4 ", " 5 ", " 6 ",
            "level 2", "level 3", "level 4", "level 5", "level ii", "level iii",
            "engineer ii", "engineer iii", "engineer iv", "engineer 2", "engineer 3", "engineer 4"
        ]):
            continue
        
        # Check for new grad signals
        if not has_new_grad_signal(title, filters['new_grad_signals']):
            continue
        
        # For jobs with clear new grad signals, track signals are optional
        # This matches the reference repo approach where "New Grad Software Engineer" doesn't need additional keywords
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

def generate_readme(jobs: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
    """Generate README content with job listings"""
    readme_config = config['readme']
    
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
                # Remove timezone info for comparison
                return parsed_date.replace(tzinfo=None)
        except:
            return datetime.min
    
    jobs.sort(key=get_sort_date, reverse=True)
    
    readme_content = f"""# {readme_config['title']}

{readme_config['subtitle']}

🔄 **Last updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

📊 **Total jobs found:** {len(jobs)}

---

## Available Positions

"""
    
    if not jobs:
        readme_content += "No new grad positions found matching the criteria. Check back later!\n"
        return readme_content
    
    # Create table header
    headers = readme_config['table_headers']
    readme_content += "| " + " | ".join(headers) + " |\n"
    readme_content += "|" + "|".join([" --- " for _ in headers]) + "|\n"
    
    # Add job rows
    for job in jobs:
        company = job.get('company', 'Unknown')
        title = job.get('title', 'Unknown')
        location = job.get('location', 'Remote')
        posted = format_posted_date(job.get('posted_at', ''))
        url = job.get('url', '#')
        
        # Escape pipe characters in content
        title = title.replace('|', '\\|')
        location = location.replace('|', '\\|')
        
        apply_link = f"[Apply]({url})" if url and url != '#' else "N/A"
        
        readme_content += f"| {company} | {title} | {location} | {posted} | {apply_link} |\n"
    
    readme_content += f"""
---

## About This Repository

This repository automatically scrapes new graduate job opportunities from various company job boards every 5 minutes. 

### Filtering Criteria
- **New Grad Signals:** new grad, new graduate, entry-level, graduate, junior, associate, trainee, campus, recent graduate
- **Track Focus:** Software, Data Science/Engineering, Machine Learning, Network Engineering, Site Reliability Engineering (SRE), DevOps
- **Recency:** Jobs posted within the last {config['filters']['max_age_days']} days
- **Location:** USA-based positions only
- **Sources:** Greenhouse, Lever, and Google Careers job boards

### Companies Monitored
**Greenhouse:** {', '.join([company['name'] for company in config['apis']['greenhouse']['companies']])}

**Lever:** {', '.join([company['name'] for company in config['apis']['lever']['companies']])}

**Google Careers:** Direct API searches for new graduate positions

---

*This list is automatically updated every 5 minutes. Star ⭐ this repo to stay updated!*
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
    
    print(f"Total jobs fetched: {len(all_jobs)}")
    
    # Filter jobs
    filtered_jobs = filter_jobs(all_jobs, config)
    print(f"Jobs after filtering: {len(filtered_jobs)}")
    
    # Generate README content
    readme_content = generate_readme(filtered_jobs, config)
    
    # Write to README file
    readme_path = os.path.join(os.path.dirname(__file__), '..', 'README.md')
    try:
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        print(f"README.md updated successfully with {len(filtered_jobs)} jobs")
    except Exception as e:
        print(f"Error writing README.md: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
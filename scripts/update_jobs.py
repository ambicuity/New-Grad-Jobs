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
        posted_date = date_parser.parse(posted_at)
        # Remove timezone info for comparison
        posted_date = posted_date.replace(tzinfo=None)
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        return posted_date >= cutoff_date
    except Exception as e:
        print(f"Error parsing date {posted_at}: {e}")
        return False

def filter_jobs(jobs: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Filter jobs based on configuration criteria"""
    filtered_jobs = []
    filters = config['filters']
    
    for job in jobs:
        title = job.get('title', '')
        posted_at = job.get('posted_at', '')
        
        # Check for new grad signals
        if not has_new_grad_signal(title, filters['new_grad_signals']):
            continue
            
        # Check for track signals
        if not has_track_signal(title, filters['track_signals']):
            continue
            
        # Check if job is recent enough
        if not is_recent_job(posted_at, filters['max_age_days']):
            continue
            
        filtered_jobs.append(job)
    
    return filtered_jobs

def format_posted_date(posted_at: str) -> str:
    """Format posted date for display"""
    try:
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
    jobs.sort(key=lambda x: date_parser.parse(x['posted_at']) if x['posted_at'] else datetime.min, reverse=True)
    
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
- **Sources:** Greenhouse and Lever job boards

### Companies Monitored
**Greenhouse:** {', '.join([company['name'] for company in config['apis']['greenhouse']['companies']])}

**Lever:** {', '.join([company['name'] for company in config['apis']['lever']['companies']])}

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
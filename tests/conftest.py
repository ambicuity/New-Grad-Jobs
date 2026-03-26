#!/usr/bin/env python3
"""
Shared test fixtures and utilities for New Grad Jobs test suite.

This module provides common test infrastructure including:
- Path setup for importing scripts
- Mock factories for common data structures
- Shared constants and test data
"""
import sys
import os
import pytest
from typing import Dict, Any, List
from datetime import datetime, timedelta

# Add scripts directory to path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


# ============================================================================
# Mock Data Factories
# ============================================================================

@pytest.fixture
def sample_job() -> Dict[str, Any]:
    """Factory for creating a standard job dictionary for testing.

    Returns a job with all common fields populated with realistic test data.
    Use this as a base and modify specific fields for edge case testing.
    """
    return {
        'company': 'Tech Corp',
        'title': 'Software Engineer - New Grad',
        'location': 'San Francisco, CA',
        'url': 'https://example.com/jobs/123',
        'posted_at': datetime.utcnow().isoformat(),
        'description': 'Join our team as a new grad software engineer.',
        'source': 'Test Source'
    }


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Factory for creating a minimal valid config structure.

    Returns a config dict with essential fields for testing filter/fetch functions.
    Modify specific sections as needed for individual tests.
    """
    return {
        'filters': {
            'min_days_old': 60,
            'us_only': False,
            'exclude_keywords': ['senior', 'manager'],
            'required_keywords': []
        },
        'greenhouse': {
            'enabled': True,
            'companies': []
        },
        'lever': {
            'enabled': True,
            'companies': []
        },
        'google_careers': {
            'enabled': True,
            'search_terms': ['new grad software engineer']
        }
    }


@pytest.fixture
def greenhouse_company() -> Dict[str, str]:
    """Factory for creating a Greenhouse company config entry."""
    return {
        'name': 'Example Corp',
        'url': 'https://boards.greenhouse.io/examplecorp'
    }


@pytest.fixture
def lever_company() -> Dict[str, str]:
    """Factory for creating a Lever company config entry."""
    return {
        'name': 'Example Startup',
        'url': 'https://jobs.lever.co/examplestartup'
    }


# ============================================================================
# Test Data Constants
# ============================================================================

# Common location strings for testing location validation
VALID_US_LOCATIONS = [
    'San Francisco, CA',
    'New York, NY',
    'Seattle, WA',
    'Remote - USA',
    'Austin, Texas',
    'United States'
]

VALID_CANADA_LOCATIONS = [
    'Toronto, ON',
    'Vancouver, BC',
    'Montreal, QC',
    'Remote - Canada',
    'Toronto, Ontario'
]

INVALID_LOCATIONS = [
    'London, UK',
    'Berlin, Germany',
    'Tokyo, Japan',
    'Paris, France',
    'Remote - Europe'
]

# Common new grad signal keywords
NEW_GRAD_SIGNALS = [
    'new grad',
    'new graduate',
    'university grad',
    'recent graduate',
    'entry level',
    'entry-level',
    '2026 grad',
    '2027 new grad'
]

# Common exclude keywords
EXCLUDE_KEYWORDS = [
    'senior',
    'staff',
    'principal',
    'lead',
    'manager',
    'director',
    '5+ years',
    '10 years experience'
]


# ============================================================================
# Helper Functions
# ============================================================================

def create_job(
    company: str = 'Test Company',
    title: str = 'Software Engineer',
    location: str = 'San Francisco, CA',
    url: str = 'https://example.com/job',
    posted_at: str = None,
    description: str = '',
    source: str = 'Test',
    **kwargs
) -> Dict[str, Any]:
    """Helper to create a job dict with custom fields.

    Args:
        company: Company name
        title: Job title
        location: Job location
        url: Application URL
        posted_at: ISO timestamp (defaults to now if None)
        description: Job description
        source: Data source name
        **kwargs: Additional custom fields

    Returns:
        Dict with job data
    """
    job = {
        'company': company,
        'title': title,
        'location': location,
        'url': url,
        'posted_at': posted_at or datetime.utcnow().isoformat(),
        'description': description,
        'source': source
    }
    job.update(kwargs)
    return job


def create_jobs_batch(count: int, base_date: datetime = None) -> List[Dict[str, Any]]:
    """Helper to create a batch of jobs for bulk testing.

    Args:
        count: Number of jobs to create
        base_date: Starting date (jobs will have dates going backwards from here)

    Returns:
        List of job dicts with varied dates
    """
    if base_date is None:
        base_date = datetime.utcnow()

    jobs = []
    for i in range(count):
        posted_date = base_date - timedelta(days=i)
        jobs.append(create_job(
            company=f'Company {i}',
            title=f'Engineer {i}',
            url=f'https://example.com/job/{i}',
            posted_at=posted_date.isoformat()
        ))
    return jobs

#!/usr/bin/env python3
"""
Unit tests for generate_rss_feed() in scripts/update_jobs.py.

Covers:
  - Valid XML output
  - Correct item count (max 50)
  - Required RSS elements present
  - XML-unsafe characters are escaped
"""

import sys
import os
import tempfile
from xml.etree import ElementTree as ET
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import generate_rss_feed


def _make_jobs(count=5):
    """Generate a list of minimal job dicts for testing."""
    jobs = []
    for i in range(count):
        jobs.append({
            'title': f'Software Engineer {i}',
            'company': f'Company {i}',
            'url': f'https://example.com/job/{i}',
            'location': 'San Francisco, CA',
            'posted_at': (datetime.now(timezone.utc) - timedelta(days=i)).isoformat(),
            'posted_display': f'{i} days ago',
        })
    return jobs


class TestRssFeedGeneration:
    """Tests for RSS feed output."""

    def _generate_and_parse(self, jobs, tmpdir, max_items=50):
        """Generate RSS feed into tmpdir, parse, and return ET root."""
        feed_path = os.path.join(tmpdir, 'feed.xml')
        with patch('update_jobs.os.path.join', return_value=feed_path):
            with patch('update_jobs.os.makedirs'):
                generate_rss_feed(jobs, max_items=max_items)
        tree = ET.parse(feed_path)
        return tree.getroot()

    def test_valid_xml(self):
        """Output must be well-formed XML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            jobs = _make_jobs(3)
            root = self._generate_and_parse(jobs, tmpdir)
            assert root.tag == 'rss'

    def test_channel_elements(self):
        """Channel must have title, link, and description."""
        with tempfile.TemporaryDirectory() as tmpdir:
            jobs = _make_jobs(3)
            root = self._generate_and_parse(jobs, tmpdir)
            channel = root.find('channel')
            assert channel is not None
            assert channel.find('title').text == 'New Grad Jobs'
            assert channel.find('link') is not None
            assert channel.find('description') is not None

    def test_item_count_matches(self):
        """Number of items should match input count (under max)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            jobs = _make_jobs(5)
            root = self._generate_and_parse(jobs, tmpdir)
            items = root.findall('.//item')
            assert len(items) == 5

    def test_max_items_cap(self):
        """Should cap at max_items even with more jobs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            jobs = _make_jobs(10)
            root = self._generate_and_parse(jobs, tmpdir, max_items=3)
            items = root.findall('.//item')
            assert len(items) == 3

    def test_item_has_required_elements(self):
        """Each item must have title, link, description, guid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            jobs = _make_jobs(1)
            root = self._generate_and_parse(jobs, tmpdir)
            item = root.find('.//item')
            assert item.find('title') is not None
            assert item.find('link') is not None
            assert item.find('description') is not None
            assert item.find('guid') is not None

    def test_empty_jobs(self):
        """Empty input should produce valid XML with no items."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._generate_and_parse([], tmpdir)
            items = root.findall('.//item')
            assert len(items) == 0

    def test_xml_escaping(self):
        """Special characters in job data must be escaped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            jobs = [{
                'title': 'Engineer <script>',
                'company': 'AT&T Corp',
                'url': 'https://example.com/job/1',
                'location': '"Quoted" Location',
                'posted_at': datetime.now(timezone.utc).isoformat(),
                'posted_display': 'Today',
            }]
            # Should not raise XML parse error
            root = self._generate_and_parse(jobs, tmpdir)
            assert root.tag == 'rss'

    def test_handles_none_fields(self):
        """Jobs with None for company/title/url/location must not crash RSS generation.

        Regression for the scheduled scraper failure on main:
            AttributeError: 'NoneType' object has no attribute 'replace'
        raised from xml.sax.saxutils.escape inside generate_rss_feed.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            jobs = [{
                'title': None,
                'company': None,
                'url': None,
                'location': None,
                'category': None,
                'posted_at': datetime.now(timezone.utc).isoformat(),
                'posted_display': 'Today',
            }]
            # Must not raise; must produce valid XML with one item present.
            root = self._generate_and_parse(jobs, tmpdir)
            assert root.tag == 'rss'
            items = root.findall('.//item')
            assert len(items) == 1
            # Null fields should fall back to safe defaults, not crash.
            title_el = items[0].find('title')
            assert title_el is not None
            assert title_el.text == 'Unknown at Unknown'

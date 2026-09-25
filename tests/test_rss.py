#!/usr/bin/env python3
"""
Unit tests for generate_rss_feed() in scripts/ngj/outputs/rss.py.

Covers:
  - Valid XML output
  - Correct item count (default max 200)
  - Required RSS elements present
  - XML-unsafe characters are escaped
"""

import os
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from xml.etree import ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from ngj.outputs.rss import DEFAULT_MAX_ITEMS, generate_rss_feed, render_rss_feed  # noqa: E402

ATOM = '{http://www.w3.org/2005/Atom}'


def _make_jobs(count=5):
    """Generate a list of minimal job dicts for testing."""
    jobs = []
    for i in range(count):
        jobs.append({
            'title': f'Software Engineer {i}',
            'company': f'Company {i}',
            'url': f'https://example.com/job/{i}',
            'location': 'San Francisco, CA',
            'posted_at': (datetime.now(UTC) - timedelta(days=i)).isoformat(),
        })
    return jobs


class TestRssFeedGeneration:
    """Tests for RSS feed output."""

    def _generate_and_parse(self, jobs, tmpdir, max_items=50):
        """Generate RSS feed into tmpdir, parse, and return ET root."""
        feed_path = generate_rss_feed(jobs, tmpdir, max_items=max_items)
        assert str(feed_path) == os.path.join(tmpdir, 'feed.xml')
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
                'posted_at': datetime.now(UTC).isoformat(),
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
                'posted_at': datetime.now(UTC).isoformat(),
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


def test_generate_rss_feed_does_not_reorder_callers_list():
    """The feed sorts a copy; the caller's list keeps its order."""
    with tempfile.TemporaryDirectory() as tmpdir:
        jobs = list(reversed(_make_jobs(4)))  # oldest first
        before = [job['url'] for job in jobs]
        generate_rss_feed(jobs, tmpdir)
        assert [job['url'] for job in jobs] == before


def _parse(xml: str):
    return ET.fromstring(xml.encode('utf-8'))


def test_default_cap_is_200():
    assert DEFAULT_MAX_ITEMS == 200
    jobs = [{'job_id': f'job_{i:020x}', 'title': 'T', 'first_seen': '2026-09-01T00:00:00Z'} for i in range(250)]
    assert len(_parse(render_rss_feed(jobs)).findall('.//item')) == 200


def test_channel_links_point_at_the_custom_domain():
    channel = _parse(render_rss_feed([])).find('channel')
    assert channel.find('link').text == 'https://jobs.riteshrana.engineer/'
    self_link = channel.find(f'{ATOM}link')
    assert self_link.get('href') == 'https://jobs.riteshrana.engineer/feed.xml'
    assert self_link.get('rel') == 'self'


def test_site_url_is_configurable():
    channel = _parse(render_rss_feed([], site_url='https://example.org/board')).find('channel')
    assert channel.find('link').text == 'https://example.org/board/'
    assert channel.find(f'{ATOM}link').get('href') == 'https://example.org/board/feed.xml'


def test_guid_is_job_id_and_not_a_permalink():
    job = {'job_id': 'job_0123456789abcdef0123', 'title': 'SWE', 'url': 'https://a.com/1?x=1&y=2'}
    item = _parse(render_rss_feed([job])).find('.//item')
    guid = item.find('guid')
    assert guid.text == 'job_0123456789abcdef0123'
    assert guid.get('isPermaLink') == 'false'
    assert item.find('link').text == 'https://a.com/1?x=1&y=2'


def test_orders_by_first_seen_not_posted_at():
    backdated_but_new = {'job_id': 'job_a', 'title': 'New', 'posted_at': '2026-01-01T00:00:00Z',
                         'first_seen': '2026-09-20T00:00:00Z'}
    old = {'job_id': 'job_b', 'title': 'Old', 'posted_at': '2026-09-01T00:00:00Z',
           'first_seen': '2026-09-02T00:00:00Z'}
    no_first_seen = {'job_id': 'job_c', 'title': 'Fallback', 'posted_at': '2026-09-10T00:00:00Z'}
    items = _parse(render_rss_feed([old, no_first_seen, backdated_but_new])).findall('.//item')
    assert [i.find('title').text for i in items] == ['New at Unknown', 'Fallback at Unknown', 'Old at Unknown']
    assert items[0].find('pubDate').text == 'Sun, 20 Sep 2026 00:00:00 +0000'


def test_ties_are_deterministic():
    jobs = [{'job_id': f'job_{c}', 'title': c, 'first_seen': '2026-09-01T00:00:00Z'} for c in 'bca']
    titles = [i.find('title').text for i in _parse(render_rss_feed(jobs)).findall('.//item')]
    assert titles == ['c at Unknown', 'b at Unknown', 'a at Unknown']
    assert titles == [i.find('title').text for i in _parse(render_rss_feed(list(reversed(jobs)))).findall('.//item')]


def test_xml_illegal_control_characters_are_stripped():
    job = {'job_id': 'job_x', 'title': 'Soft\x00ware\x0b Eng\x1f', 'company': 'Ac\x08me',
           'location': '\x0cNYC', 'url': 'https://a.com/\x01', 'category': {'name': 'SWE\x1b'}}
    xml = render_rss_feed([job])
    item = _parse(xml).find('.//item')  # would raise on an illegal char
    assert item.find('title').text == 'Software Eng at Acme'
    assert 'NYC' in item.find('description').text


# ---------------------------------------------------------------------------
# Sliced feeds: feeds/<category>.xml, feeds/remote.xml, feeds/no-visa-restriction.xml
# ---------------------------------------------------------------------------

from ngj.outputs.rss import (  # noqa: E402
    FEEDS_DIRNAME,
    feed_slug,
    feed_variants,
    generate_rss_feeds,
    is_remote_job,
    is_visa_unrestricted,
)
from ngj.taxonomy import CATEGORY_PATTERNS  # noqa: E402


def _sliced_jobs():
    base = _make_jobs(4)
    base[0].update(category={'id': 'software_engineering', 'name': 'Software Engineering'}, location='Remote - US',
                   flags={'no_sponsorship': False, 'us_citizenship_required': False})
    base[1].update(category={'id': 'marketing', 'name': 'Marketing'}, location='New York, NY (Hybrid remote)',
                   flags={'no_sponsorship': True, 'us_citizenship_required': False})
    base[2].update(category={'id': 'software_engineering', 'name': 'Software Engineering'}, title='Remote Engineer',
                   location='Austin, TX', flags={'no_sponsorship': False, 'us_citizenship_required': True})
    base[3].update(category={'id': 'other', 'name': 'Other'}, location='Chicago, IL', flags=None)
    return base


def test_feed_slug_mirrors_landing_page_slugs():
    assert feed_slug('software_engineering') == 'software-engineering'
    assert feed_slug('remote') == 'remote'


def test_remote_rule_matches_the_site_facet():
    assert is_remote_job({'location': 'Remote - US', 'title': 'SWE'}) is True
    assert is_remote_job({'location': 'Austin, TX', 'title': 'Remote Engineer'}) is True
    assert is_remote_job({'location': 'NYC (Hybrid remote)', 'title': 'SWE'}) is False
    assert is_remote_job({'location': 'Austin, TX', 'title': 'SWE'}) is False
    assert is_remote_job({}) is False


def test_visa_rule_requires_both_flags_false():
    assert is_visa_unrestricted({'flags': {'no_sponsorship': False, 'us_citizenship_required': False}}) is True
    assert is_visa_unrestricted({'flags': {'no_sponsorship': True, 'us_citizenship_required': False}}) is False
    assert is_visa_unrestricted({'flags': None}) is False
    assert is_visa_unrestricted({}) is False


def test_feed_variants_cover_every_category_plus_remote_and_visa():
    variants = feed_variants(_sliced_jobs())
    slugs = [v.slug for v in variants]
    assert slugs[-2:] == ['remote', 'no-visa-restriction']
    assert set(slugs[:-2]) == {feed_slug(c) for c in CATEGORY_PATTERNS if c != 'other'}
    by_slug = {v.slug: v for v in variants}
    assert len(by_slug['software-engineering'].jobs) == 2
    assert len(by_slug['marketing'].jobs) == 1
    assert len(by_slug['sales'].jobs) == 0  # empty slices still exist so subscriptions never 404
    assert [j['title'] for j in by_slug['remote'].jobs] == [_sliced_jobs()[0]['title'], 'Remote Engineer']
    assert len(by_slug['no-visa-restriction'].jobs) == 1
    assert by_slug['remote'].filename == f'{FEEDS_DIRNAME}/remote.xml'


def test_generate_rss_feeds_writes_main_and_every_slice(tmp_path):
    paths = generate_rss_feeds(_sliced_jobs(), tmp_path, site_url='https://example.test')

    assert paths is not None
    assert paths[0] == tmp_path / 'feed.xml'
    slices = sorted(p.name for p in (tmp_path / FEEDS_DIRNAME).iterdir())
    assert 'software-engineering.xml' in slices and 'remote.xml' in slices and 'no-visa-restriction.xml' in slices
    assert len(slices) == len(CATEGORY_PATTERNS) - 1 + 2

    root = ET.parse(tmp_path / FEEDS_DIRNAME / 'software-engineering.xml').getroot()
    channel = root.find('channel')
    assert channel.find('title').text == 'New Grad Jobs · Software Engineering'
    assert len(channel.findall('item')) == 2
    atom = channel.find('{http://www.w3.org/2005/Atom}link')
    assert atom.get('href') == 'https://example.test/feeds/software-engineering.xml'

    main = ET.parse(tmp_path / 'feed.xml').getroot().find('channel')
    assert 'every field' in main.find('description').text


def test_generate_rss_feeds_reports_a_failed_slice(tmp_path, monkeypatch):
    (tmp_path / FEEDS_DIRNAME).write_text('not a directory', encoding='utf-8')  # mkdir will fail
    assert generate_rss_feeds(_sliced_jobs(), tmp_path) is None
    assert (tmp_path / 'feed.xml').exists(), 'the main feed is still attempted'

"""RSS 2.0 feed (feed.xml) of the most recently *discovered* jobs.

Items are rendered from the published jobs.json entries and ordered by
``first_seen`` (when the board first saw the job, carried forward across runs
by ngj.outputs.jobs_json), falling back to the employer's ``posted_at``. That
way a job whose employer backdated ``posted_at`` still reaches subscribers
when it first appears. Each item's guid is the stable ``job_id``.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape
from xml.sax.saxutils import quoteattr

from ngj.dates import parse_posted_at
from ngj.settings import DEFAULT_SITE_URL

logger = logging.getLogger(__name__)

DEFAULT_MAX_ITEMS = 200
FEED_FILENAME = "feed.xml"
_RFC822 = '%a, %d %b %Y %H:%M:%S +0000'

# Characters XML 1.0 forbids even when escaped (C0 controls except tab/LF/CR,
# surrogates, U+FFFE/U+FFFF). Scraped titles occasionally carry them.
_XML_ILLEGAL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]')


def strip_xml_illegal(text: str) -> str:
    return _XML_ILLEGAL.sub('', text)


def _safe(val: Any, default: str = "") -> str:
    """Coerce to str (None → default) and drop XML-illegal characters."""
    if val is None:
        return default
    return strip_xml_illegal(str(val)) or default


def _text(val: Any, default: str = "") -> str:
    return xml_escape(_safe(val, default))


def _parse(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parse_posted_at(value)
    except Exception:
        return None
    return parsed if parsed != datetime.min else None


def discovered_at(job: dict[str, Any]) -> datetime | None:
    """``first_seen``, else ``posted_at``, as a naive-UTC datetime (None if neither parses)."""
    return _parse(job.get('first_seen')) or _parse(job.get('posted_at'))


def _feed_order_key(job: dict[str, Any]) -> tuple[datetime, str]:
    return discovered_at(job) or datetime.min, str(job.get('job_id') or '')


def select_feed_jobs(jobs: Sequence[dict[str, Any]], max_items: int) -> list[dict[str, Any]]:
    """Newest-discovered first; ties broken by job_id descending (deterministic)."""
    return sorted(jobs, key=_feed_order_key, reverse=True)[:max_items]


def _render_item(job: dict[str, Any], now_str: str) -> str:
    company = _text(job.get('company'), 'Unknown')
    title = _text(job.get('title'), 'Unknown')
    url = _text(job.get('url'))
    location = _text(job.get('location'), 'Remote')
    category_obj = job.get('category') or {}
    category = _text(category_obj.get('name') if isinstance(category_obj, dict) else None, 'General')
    when = discovered_at(job)
    pub_date = when.strftime(_RFC822) if when else now_str
    guid = _text(job.get('job_id') or job.get('url'))
    return f"""    <item>
      <title>{title} at {company}</title>
      <link>{url}</link>
      <description>New grad role at {company} in {location}. Category: {category}</description>
      <pubDate>{pub_date}</pubDate>
      <guid isPermaLink="false">{guid}</guid>
    </item>"""


def render_rss_feed(
    jobs: Sequence[dict[str, Any]],
    max_items: int = DEFAULT_MAX_ITEMS,
    now: datetime | None = None,
    site_url: str = DEFAULT_SITE_URL,
) -> str:
    """Render the feed XML for the ``max_items`` newest-discovered jobs (input not modified)."""
    site_url = site_url if site_url.endswith('/') else site_url + '/'
    newest = select_feed_jobs(jobs, max_items)
    now_str = (now or datetime.now(UTC)).strftime(_RFC822)
    items = "\n".join(_render_item(job, now_str) for job in newest)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>New Grad Jobs</title>
    <link>{xml_escape(site_url)}</link>
    <description>Automatically updated new graduate job opportunities in Software, Data, and SRE roles.</description>
    <language>en-us</language>
    <lastBuildDate>{now_str}</lastBuildDate>
    <atom:link href={quoteattr(site_url + FEED_FILENAME)} rel="self" type="application/rss+xml"/>
{items}
  </channel>
</rss>
"""


def generate_rss_feed(
    jobs: Sequence[dict[str, Any]],
    output_dir: Path,
    max_items: int = DEFAULT_MAX_ITEMS,
    site_url: str = DEFAULT_SITE_URL,
) -> Path | None:
    """Write ``output_dir/feed.xml``. Returns the path, or None if the write failed.

    ``jobs`` should be the published jobs.json entries (they carry ``job_id``
    and ``first_seen``).
    """
    feed_path = Path(output_dir) / FEED_FILENAME
    rss_xml = render_rss_feed(jobs, max_items, site_url=site_url)
    try:
        feed_path.parent.mkdir(parents=True, exist_ok=True)
        feed_path.write_text(rss_xml, encoding='utf-8')
    except OSError as exc:
        logger.error("❌ Failed to write RSS feed: %s", exc)
        return None
    logger.info("📡 RSS feed generated with %s items → %s", min(len(jobs), max_items), feed_path)
    return feed_path

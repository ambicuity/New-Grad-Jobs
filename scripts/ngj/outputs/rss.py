"""RSS 2.0 feed (feed.xml) of the most recent jobs."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

from ngj.dates import extract_sort_date

logger = logging.getLogger(__name__)

DEFAULT_MAX_ITEMS = 50
SITE_URL = "https://ambicuity.github.io/New-Grad-Jobs/"
FEED_URL = SITE_URL + "feed.xml"
_RFC822 = '%a, %d %b %Y %H:%M:%S +0000'


def _safe(val: Any, default: str = "") -> str:
    # xml_escape calls .replace() on its argument; job records may carry None
    # for any optional field, so coerce at the rendering boundary.
    if val is None:
        return default
    return str(val)


def _render_item(job: dict[str, Any], now_str: str) -> str:
    company = _safe(job.get('company'), 'Unknown')
    title = _safe(job.get('title'), 'Unknown')
    url = _safe(job.get('url'))
    location = _safe(job.get('location'), 'Remote')
    category_obj = job.get('category') or {}
    category = _safe(category_obj.get('name') if isinstance(category_obj, dict) else None, 'General')
    posted = extract_sort_date(job)
    pub_date = posted.strftime(_RFC822) if posted != datetime.min else now_str
    return f"""    <item>
      <title>{xml_escape(title)} at {xml_escape(company)}</title>
      <link>{xml_escape(url)}</link>
      <description>New grad role at {xml_escape(company)} in {xml_escape(location)}. Category: {xml_escape(category)}</description>
      <pubDate>{pub_date}</pubDate>
      <guid isPermaLink="true">{xml_escape(url)}</guid>
    </item>"""


def render_rss_feed(
    jobs: Sequence[dict[str, Any]],
    max_items: int = DEFAULT_MAX_ITEMS,
    now: datetime | None = None,
) -> str:
    """Render the feed XML for the ``max_items`` newest jobs (input not modified)."""
    newest = sorted(jobs, key=extract_sort_date, reverse=True)[:max_items]
    now_str = (now or datetime.now(UTC)).strftime(_RFC822)
    items = "\n".join(_render_item(job, now_str) for job in newest)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>New Grad Jobs</title>
    <link>{SITE_URL}</link>
    <description>Automatically updated new graduate job opportunities in Software, Data, and SRE roles.</description>
    <language>en-us</language>
    <lastBuildDate>{now_str}</lastBuildDate>
    <atom:link href="{FEED_URL}" rel="self" type="application/rss+xml"/>
{items}
  </channel>
</rss>
"""


def generate_rss_feed(
    jobs: Sequence[dict[str, Any]],
    output_dir: Path,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> Path | None:
    """Write ``output_dir/feed.xml``. Returns the path, or None if the write failed."""
    feed_path = Path(output_dir) / "feed.xml"
    rss_xml = render_rss_feed(jobs, max_items)
    try:
        feed_path.parent.mkdir(parents=True, exist_ok=True)
        feed_path.write_text(rss_xml, encoding='utf-8')
    except OSError as exc:
        logger.warning("⚠️  Failed to write RSS feed: %s", exc)
        return None
    logger.info("📡 RSS feed generated with %s items → %s", min(len(jobs), max_items), feed_path)
    return feed_path

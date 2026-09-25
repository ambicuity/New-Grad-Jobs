"""RSS 2.0 feeds of the most recently *discovered* jobs.

``feed.xml`` carries every job; ``feeds/<slug>.xml`` carries one slice each
(one per category, plus ``remote`` and ``no-visa-restriction``) so a reader or
an RSS-to-email service can subscribe to exactly the roles it wants.

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
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape
from xml.sax.saxutils import quoteattr

from ngj.dates import parse_posted_at
from ngj.settings import DEFAULT_SITE_URL
from ngj.taxonomy import CATEGORY_PATTERNS

logger = logging.getLogger(__name__)

DEFAULT_MAX_ITEMS = 200
FEED_FILENAME = "feed.xml"
FEEDS_DIRNAME = "feeds"
FEED_TITLE = "New Grad Jobs"
FEED_DESCRIPTION = (
    "New grad and entry-level jobs in every field, pulled straight from company career sites "
    "and refreshed about every 30 minutes."
)
_HYBRID_RE = re.compile(r'\bhybrid\b', re.IGNORECASE)
_REMOTE_RE = re.compile(r'\bremote\b', re.IGNORECASE)
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


@dataclass(frozen=True)
class FeedVariant:
    """One sliced feed: written to ``feeds/<slug>.xml``."""

    slug: str
    title: str
    description: str
    jobs: tuple[dict[str, Any], ...]

    @property
    def filename(self) -> str:
        return f"{FEEDS_DIRNAME}/{self.slug}.xml"


def feed_slug(category_id: str) -> str:
    """``software_engineering`` -> ``software-engineering`` (mirrors the site's /jobs/<slug>/ pages)."""
    return category_id.replace('_', '-')


def is_remote_job(job: dict[str, Any]) -> bool:
    """Same rule as the site's remote facet: "hybrid" wins, otherwise any "remote" in location or title."""
    text = f"{job.get('location') or ''} {job.get('title') or ''}"
    return not _HYBRID_RE.search(text) and bool(_REMOTE_RE.search(text))


def is_visa_unrestricted(job: dict[str, Any]) -> bool:
    """True when the posting states neither a sponsorship exclusion nor a citizenship requirement."""
    flags = job.get('flags')
    return (
        isinstance(flags, dict)
        and flags.get('no_sponsorship') is False
        and flags.get('us_citizenship_required') is False
    )


def _category_id(job: dict[str, Any]) -> str:
    category = job.get('category')
    return str(category.get('id') or '') if isinstance(category, dict) else ''


def feed_variants(jobs: Sequence[dict[str, Any]]) -> list[FeedVariant]:
    """Every sliced feed, in a stable order. Category feeds exist even when empty so URLs never break."""
    variants: list[FeedVariant] = []
    for category_id, info in CATEGORY_PATTERNS.items():
        if category_id == 'other':
            continue
        name = str(info['name'])
        variants.append(FeedVariant(
            slug=feed_slug(category_id),
            title=f"{FEED_TITLE} · {name}",
            description=f"New grad and entry-level {name} roles, refreshed about every 30 minutes.",
            jobs=tuple(job for job in jobs if _category_id(job) == category_id),
        ))
    variants.append(FeedVariant(
        slug='remote',
        title=f"{FEED_TITLE} · Remote",
        description="Remote new grad and entry-level roles, refreshed about every 30 minutes.",
        jobs=tuple(job for job in jobs if is_remote_job(job)),
    ))
    variants.append(FeedVariant(
        slug='no-visa-restriction',
        title=f"{FEED_TITLE} · No visa restriction stated",
        description=(
            "New grad roles whose posting states neither a visa-sponsorship exclusion nor a citizenship "
            "requirement, refreshed about every 30 minutes."
        ),
        jobs=tuple(job for job in jobs if is_visa_unrestricted(job)),
    ))
    return variants


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
    *,
    title: str = FEED_TITLE,
    description: str = FEED_DESCRIPTION,
    filename: str = FEED_FILENAME,
) -> str:
    """Render the feed XML for the ``max_items`` newest-discovered jobs (input not modified)."""
    site_url = site_url if site_url.endswith('/') else site_url + '/'
    newest = select_feed_jobs(jobs, max_items)
    now_str = (now or datetime.now(UTC)).strftime(_RFC822)
    items = "\n".join(_render_item(job, now_str) for job in newest)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{_text(title)}</title>
    <link>{xml_escape(site_url)}</link>
    <description>{_text(description)}</description>
    <language>en-us</language>
    <lastBuildDate>{now_str}</lastBuildDate>
    <atom:link href={quoteattr(site_url + filename)} rel="self" type="application/rss+xml"/>
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


def generate_rss_feeds(
    jobs: Sequence[dict[str, Any]],
    output_dir: Path,
    max_items: int = DEFAULT_MAX_ITEMS,
    site_url: str = DEFAULT_SITE_URL,
) -> list[Path] | None:
    """Write ``feed.xml`` plus every ``feeds/<slug>.xml`` slice. Returns the paths, or None if any write failed.

    Every feed is attempted so one bad write does not hide the others.
    """
    written: list[Path] = []
    failed = False
    main_path = generate_rss_feed(jobs, output_dir, max_items=max_items, site_url=site_url)
    if main_path is None:
        failed = True
    else:
        written.append(main_path)
    now = datetime.now(UTC)
    for variant in feed_variants(jobs):
        path = Path(output_dir) / variant.filename
        xml = render_rss_feed(
            variant.jobs, max_items, now=now, site_url=site_url,
            title=variant.title, description=variant.description, filename=variant.filename,
        )
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(xml, encoding='utf-8')
        except OSError as exc:
            logger.error("❌ Failed to write RSS feed %s: %s", variant.filename, exc)
            failed = True
            continue
        written.append(path)
    logger.info("📡 %s sliced RSS feeds written under %s/", len(written) - (0 if main_path is None else 1), FEEDS_DIRNAME)
    return None if failed else written

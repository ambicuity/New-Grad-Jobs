"""HTML-to-text helpers for ATS job descriptions."""

from __future__ import annotations

import html
import re

# Only real tags (a letter, "/" or "!" right after "<") are stripped so literal
# comparisons such as "< $100k" or "latency > 5ms" survive decoding.
_HTML_TAG_RE = re.compile(r'<(?:!--.*?--|[a-zA-Z/!][^<>]*)>', re.DOTALL)
# Greenhouse double-encodes entities inside its entity-encoded HTML
# ("&amp;nbsp;"), so one unescape pass is not enough. Bounded to stay cheap.
_HTML_UNESCAPE_MAX_PASSES = 3

DEFAULT_DESCRIPTION_CHARS = 3000


def strip_html(text: str) -> str:
    """Remove HTML tags + decode entities.

    Handles raw HTML (Lever's ``descriptionPlain``) and entity-encoded HTML
    (Greenhouse serves ``content`` as &lt;div&gt;-style entities, sometimes
    double-encoded as &amp;nbsp;). Tags are stripped before each unescape
    pass, so tags revealed by decoding are removed on the next pass while
    text-level "<" decoded on the final pass is left alone.
    """
    if not text:
        return text
    for _ in range(_HTML_UNESCAPE_MAX_PASSES):
        text = _HTML_TAG_RE.sub(' ', text)
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = unescaped
    else:
        text = _HTML_TAG_RE.sub(' ', text)
    return text.replace('\xa0', ' ')


def clean_description(text: str | None, max_chars: int = DEFAULT_DESCRIPTION_CHARS) -> str:
    """Strip HTML, collapse whitespace, clip to ``max_chars`` on a word boundary."""
    if not text:
        return ''
    plain = strip_html(text)
    plain = re.sub(r'\s+', ' ', plain).strip()
    if len(plain) <= max_chars:
        return plain
    cut = plain[:max_chars].rsplit(' ', 1)[0]
    return cut + '…'

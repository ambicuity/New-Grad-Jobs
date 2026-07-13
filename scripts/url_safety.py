"""Publish-time URL safety checks (stdlib only)."""

from __future__ import annotations

import ipaddress
from typing import Any, Dict, List, Sequence, Tuple
from urllib.parse import urlparse

_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "metadata",
        "metadata.google.internal",
        "metadata.goog",
        "instance-data",
    }
)


def is_safe_url(url: object) -> bool:
    """Return True iff url is a public http(s) URL safe to publish."""
    if url is None or not isinstance(url, str):
        return False
    text = url.strip()
    if not text:
        return False
    try:
        parsed = urlparse(text)
    except Exception:
        return False
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return False
    host = parsed.hostname
    if host is None:
        return False
    host = host.strip().lower().rstrip(".")
    if not host:
        return False
    if host in _BLOCKED_HOSTS or host.endswith(".localhost"):
        return False
    if "%" in host:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        if host == "localhost" or "/" in host or host.startswith("."):
            return False
        return True
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return False
    if ip == ipaddress.ip_address("169.254.169.254"):
        return False
    return True


def _job_urls(job: Dict[str, Any]) -> List[str]:
    urls: List[str] = []
    for key in ("url", "apply_url", "job_url", "link", "absolute_url"):
        val = job.get(key)
        if isinstance(val, str) and val.strip():
            urls.append(val.strip())
    return urls


def filter_safe_jobs(
    jobs: Sequence[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], int, List[str]]:
    """Split jobs into safe list; return (safe_jobs, blocked_count, blocked_samples)."""
    safe: List[Dict[str, Any]] = []
    blocked_count = 0
    blocked_samples: List[str] = []
    max_samples = 10
    for job in jobs:
        if not isinstance(job, dict):
            blocked_count += 1
            if len(blocked_samples) < max_samples:
                blocked_samples.append("<non-dict>")
            continue
        urls = _job_urls(job)
        if not urls:
            blocked_count += 1
            if len(blocked_samples) < max_samples:
                blocked_samples.append("<missing>")
            continue
        bad = next((u for u in urls if not is_safe_url(u)), None)
        if bad is None:
            safe.append(job)
        else:
            blocked_count += 1
            if len(blocked_samples) < max_samples:
                blocked_samples.append(bad[:200])
    return safe, blocked_count, blocked_samples

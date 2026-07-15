"""Publish-time URL safety checks (stdlib only).

Every URL written into the public ``docs/jobs.json`` artifact must be a public
``http``/``https`` link. This module rejects anything that could point a reader
(or an automated fetcher) at an internal target:

* non-``http(s)`` schemes,
* ``localhost`` and private-use TLDs (``.local``, ``.internal``, ``.test`` …),
* private / loopback / link-local / reserved / multicast IPs — including the
  integer, hex, and octal encodings that browsers silently accept,
* cloud metadata endpoints (``169.254.169.254``, Alibaba ``100.100.100.200``),
* malformed hosts (backslashes, embedded slashes, percent/zone characters,
  bare single-label names).

Pure standard library: ``urllib.parse`` + ``ipaddress``.
"""

from __future__ import annotations

import ipaddress
from typing import Any, Dict, List, Optional, Sequence, Tuple
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

# TLDs reserved for private networks, testing, and documentation
# (RFC 6761, RFC 8375, RFC 2606). None resolve to a public destination.
_PRIVATE_TLDS = (
    ".localhost",
    ".local",
    ".internal",
    ".intranet",
    ".lan",
    ".corp",
    ".home",
    ".home.arpa",
    ".test",
    ".invalid",
    ".example",
)

# Metadata IPs that must never be published even when the generic
# private/link-local checks would otherwise let one through.
_BLOCKED_IPS = frozenset(
    {
        ipaddress.ip_address("169.254.169.254"),  # AWS / Azure / GCP IMDS
        ipaddress.ip_address("100.100.100.200"),  # Alibaba Cloud metadata
    }
)


def _coerce_ip(host: str) -> Optional[ipaddress._BaseAddress]:
    """Parse ``host`` as an IP address, including integer encodings.

    ``urlparse`` leaves ``2130706433`` (decimal), ``0x7f000001`` (hex) and
    ``017700000001`` (octal) as opaque hostnames, yet browsers and many HTTP
    clients resolve all three to ``127.0.0.1``. Decode them explicitly so the
    loopback/private checks below cannot be bypassed. Returns ``None`` when the
    host is not any IP form.
    """
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        pass

    value: Optional[int] = None
    try:
        if host.startswith(("0x", "0X")):
            value = int(host, 16)
        elif host.startswith(("0o", "0O")):
            value = int(host, 8)
        elif host.startswith("0") and len(host) > 1 and host.isdigit():
            value = int(host, 8)  # leading-zero octal, e.g. 017700000001
        elif host.isdigit():
            value = int(host, 10)
    except ValueError:
        value = None

    if value is None or value < 0 or value > 0xFFFFFFFF:
        return None
    return ipaddress.ip_address(value)


def is_safe_url(url: object) -> bool:
    """Return True iff ``url`` is a public http(s) URL safe to publish."""
    if not isinstance(url, str):
        return False
    text = url.strip()
    if not text:
        return False
    try:
        parsed = urlparse(text)
    except Exception:
        return False
    if (parsed.scheme or "").lower() not in ("http", "https"):
        return False

    host = parsed.hostname
    if host is None:
        return False
    host = host.strip().lower().rstrip(".")
    if not host:
        return False

    # Backslashes, embedded slashes and percent/zone characters: many clients
    # normalise "\" to "/", turning localhost\evil.com into a request to
    # localhost. Reject any host containing them outright.
    if "\\" in host or "/" in host or "%" in host:
        return False

    if host in _BLOCKED_HOSTS:
        return False
    if any(host == tld[1:] or host.endswith(tld) for tld in _PRIVATE_TLDS):
        return False

    ip = _coerce_ip(host)
    if ip is not None:
        if ip.version == 6 and ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
            or ip in _BLOCKED_IPS
        ):
            return False
        return True

    # Not an IP: require a dotted, public-looking hostname. Bare single-label
    # names ("intranet") and leading-dot garbage are never public.
    if host.startswith(".") or "." not in host:
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
    """Split jobs into a safe list.

    Returns ``(safe_jobs, blocked_count, blocked_samples)``. A job is blocked
    when it is not a dict, exposes no URL field, or exposes any URL that fails
    :func:`is_safe_url`.
    """
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

"""Publish-time URL safety checks (stdlib only).

Every URL written into the public ``jobs.json`` artifact must be a public
``http``/``https`` link. This module rejects anything that could point a reader
(or an automated fetcher) at an internal target:

* non-``http(s)`` schemes,
* ``localhost`` and private-use TLDs (``.local``, ``.internal``, ``.test`` …),
* any IP literal that is not globally routable unicast (private, loopback,
  link-local, CGNAT, reserved, multicast, IPv4-mapped IPv6 …) — including the
  integer, hex, octal and short (``127.1``) encodings browsers silently accept,
* cloud metadata endpoints (``169.254.169.254``, Alibaba ``100.100.100.200``),
* malformed hosts (backslashes, embedded slashes, percent/zone characters,
  bare single-label names).

Pure standard library: ``urllib.parse`` + ``ipaddress`` + ``socket.inet_aton``
(no DNS resolution is performed).
"""

from __future__ import annotations

import ipaddress
import re
import socket
from collections.abc import Sequence
from typing import Any
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


# A host label that the WHATWG URL parser (browsers) and inet_aton (curl,
# requests via getaddrinfo) treat as a number: decimal, 0x-hex or 0-octal.
_NUMERIC_LABEL_RE = re.compile(r"^(?:0x[0-9a-f]*|[0-9]+)$")


class _InvalidNumericHost(ValueError):
    """Host looks like an IPv4 literal but does not parse as one."""


def _coerce_ip(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Parse ``host`` as an IP address, including every legacy IPv4 encoding.

    ``urlparse`` leaves ``2130706433`` (decimal), ``0x7f000001`` (hex),
    ``0177.0.0.1`` (octal) and short forms such as ``127.1`` / ``0x7f.1`` as
    opaque hostnames, yet browsers and HTTP clients resolve all of them to
    ``127.0.0.1``. ``socket.inet_aton`` implements exactly those legacy forms,
    so it is used to decode any host whose final label is numeric (the same
    rule the WHATWG URL parser uses to decide a host is IPv4). Returns ``None``
    for ordinary DNS names and raises :class:`_InvalidNumericHost` for
    numeric-looking hosts that are not valid IPv4 (``999.1.1.1``,
    ``1.2.3.4.5``, ``foo.0x10``), which browsers reject too.
    """
    if ":" in host:
        return ipaddress.ip_address(host)  # IPv6 literal; ValueError if bogus

    labels = host.split(".")
    if not _NUMERIC_LABEL_RE.match(labels[-1]):
        return None
    if not all(_NUMERIC_LABEL_RE.match(label) for label in labels):
        raise _InvalidNumericHost(host)
    try:
        packed = socket.inet_aton(host)
    except OSError as exc:
        raise _InvalidNumericHost(host) from exc
    return ipaddress.IPv4Address(packed)


def _is_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return (
        ip.is_global
        and not ip.is_multicast
        and not ip.is_reserved
        and ip not in _BLOCKED_IPS
    )


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

    try:
        ip = _coerce_ip(host)
    except ValueError:
        return False  # IP-shaped but unparseable: never publish it
    if ip is not None:
        # Allow-list: only globally routable unicast addresses. This also
        # rejects CGNAT (100.64/10), benchmarking, documentation and other
        # special-purpose ranges that are neither "private" nor "reserved".
        return _is_public_ip(ip)

    # Not an IP: require a dotted, public-looking hostname. Bare single-label
    # names ("intranet") and leading-dot garbage are never public.
    if host.startswith(".") or "." not in host:
        return False
    return True


def _job_urls(job: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key in ("url", "apply_url", "job_url", "link", "absolute_url"):
        val = job.get(key)
        if isinstance(val, str) and val.strip():
            urls.append(val.strip())
    return urls


def filter_safe_jobs(
    jobs: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int, list[str]]:
    """Split jobs into a safe list.

    Returns ``(safe_jobs, blocked_count, blocked_samples)``. A job is blocked
    when it is not a dict, exposes no URL field, or exposes any URL that fails
    :func:`is_safe_url`.
    """
    safe: list[dict[str, Any]] = []
    blocked_count = 0
    blocked_samples: list[str] = []
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

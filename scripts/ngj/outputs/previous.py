"""What the previously published run looked like.

Read once at the start of a run and used for two things:

* the partial-collapse guard (ngj.pipeline) compares this run's counts with
  the previous ``health.json`` (``total_jobs``, ``raw_source_counts``);
* ``first_seen`` carry-forward (ngj.outputs.jobs_json) keeps each job's
  first-seen timestamp stable across runs so the RSS feed can order by
  discovery time.

The previous artifacts come from the output dir when a local run left them
there, otherwise (CI starts from a clean checkout) from the live site. Remote
fetching is opt-in (:func:`load_previous_run` ``fetch``) so tests never touch
the network.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# fetch(url) -> parsed JSON (raise on any failure).
JsonFetcher = Callable[[str], Any]

REMOTE_TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class PreviousRun:
    """Counts and first-seen stamps of the last published run (all optional)."""

    origin: str = "none"
    total_jobs: int | None = None
    raw_source_counts: Mapping[str, int] = field(default_factory=dict)
    first_seen: Mapping[str, str] = field(default_factory=dict)

    @property
    def available(self) -> bool:
        return self.total_jobs is not None


NO_PREVIOUS_RUN = PreviousRun()


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def parse_previous_run(jobs_payload: Any, health_payload: Any, origin: str) -> PreviousRun:
    """Build a :class:`PreviousRun` from parsed jobs(-index).json / health.json (either may be None)."""
    health = health_payload if isinstance(health_payload, dict) else {}
    jobs_doc = jobs_payload if isinstance(jobs_payload, dict) else {}
    raw_jobs = jobs_doc.get("jobs")
    jobs: list[Any] = raw_jobs if isinstance(raw_jobs, list) else []

    total = _int_or_none(health.get("total_jobs"))
    if total is None and isinstance(raw_jobs, list):
        total = len(jobs)

    counts = health.get("raw_source_counts")
    if not isinstance(counts, dict):
        counts = health.get("source_counts")  # health.json schema < 1.1
    raw_source_counts = {
        str(name): count for name, count in (counts or {}).items() if _int_or_none(count) is not None
    } if isinstance(counts, dict) else {}

    first_seen = {
        job["job_id"]: job["first_seen"]
        for job in jobs
        if isinstance(job, dict) and isinstance(job.get("job_id"), str)
        and isinstance(job.get("first_seen"), str) and job["first_seen"]
    }
    return PreviousRun(origin=origin, total_jobs=total, raw_source_counts=raw_source_counts, first_seen=first_seen)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        logger.warning("⚠️  Previous run: could not read %s: %s", path, exc)
        return None


def load_local_previous_run(output_dir: Path) -> PreviousRun:
    """Previous run from ``output_dir/{jobs.json,health.json}``, or :data:`NO_PREVIOUS_RUN`."""
    output_dir = Path(output_dir)
    jobs_payload = _read_json(output_dir / "jobs.json")
    health_payload = _read_json(output_dir / "health.json")
    if jobs_payload is None and health_payload is None:
        return NO_PREVIOUS_RUN
    return parse_previous_run(jobs_payload, health_payload, origin=str(output_dir))


def http_json_fetcher(timeout: float = REMOTE_TIMEOUT_SECONDS) -> JsonFetcher:
    """A :data:`JsonFetcher` backed by ``requests`` (imported lazily)."""
    def fetch(url: str) -> Any:
        import requests

        response = requests.get(url, timeout=timeout, headers={"Accept": "application/json"})
        response.raise_for_status()
        return response.json()
    return fetch


def fetch_remote_previous_run(site_url: str, fetch: JsonFetcher) -> PreviousRun:
    """Previous run from the live site's health.json + jobs-index.json (best effort)."""
    base = site_url if site_url.endswith("/") else site_url + "/"
    payloads: dict[str, Any] = {}
    for name in ("health.json", "jobs-index.json"):
        try:
            payloads[name] = fetch(base + name)
        except Exception as exc:  # network/HTTP/JSON: all mean "unknown"
            logger.warning("⚠️  Previous run: could not fetch %s%s: %s", base, name, exc)
            payloads[name] = None
    if payloads["health.json"] is None and payloads["jobs-index.json"] is None:
        return NO_PREVIOUS_RUN
    return parse_previous_run(payloads["jobs-index.json"], payloads["health.json"], origin=base)


def load_previous_run(output_dir: Path, site_url: str, fetch: JsonFetcher | None = None) -> PreviousRun:
    """Local artifacts first; then the live site when ``fetch`` is given."""
    previous = load_local_previous_run(output_dir)
    if previous.available or fetch is None:
        return previous
    return fetch_remote_previous_run(site_url, fetch)

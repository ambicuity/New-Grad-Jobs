#!/usr/bin/env python3
"""Per-source health summary for the scraper watchdog.

Reads the live ``health.json`` (already fetched by the watchdog), appends a
markdown table of every source to the job summary (``$GITHUB_STEP_SUMMARY``),
and prints one ``::warning::`` annotation per degraded, failed, zero-job or
403-cooled source. It is informational: it always exits 0, so it never fails
the watchdog or changes when the scraper is re-dispatched (staleness alone
decides that).

    python3 scripts/health_summary.py health.json

Standard library only: the watchdog job installs no dependencies.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping, Sequence
from typing import Any

MAX_NAMED_FAILURES = 5
NO_DATA = "health.json has no per-source data"


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|")


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word.replace('company', 'companies')}"


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _failed(source: Mapping[str, Any]) -> tuple[int, list[str]]:
    errors = _mapping(source.get("errors"))
    names = [str(n) for n in errors.get("failed_companies") or ()]
    total = errors.get("failed_companies_total")
    return (total if isinstance(total, int) else len(names)), names


def _failed_cell(total: int, names: Sequence[str]) -> str:
    if not total:
        return "—"
    shown = ", ".join(_cell(n) for n in names[:MAX_NAMED_FAILURES])
    more = total - min(len(names), MAX_NAMED_FAILURES)
    return f"{total}: {shown}" + (f", +{more} more" if more > 0 else "")


def render_summary(health: Any) -> tuple[str, list[str]]:
    """Markdown for the job summary, and the warning annotations to print."""
    sources = health.get("sources") if isinstance(health, Mapping) else None
    if not isinstance(sources, Mapping) or not sources:
        return f"### Scraper source health\n\n{NO_DATA}.\n", [NO_DATA]

    lines = [
        "### Scraper source health",
        "",
        f"Last scrape `{health.get('last_run', '?')}` · {health.get('total_jobs', 0):,} curated jobs",
        "",
        "| Source | Status | Jobs | Failure ratio | Failed companies |",
        "|---|---|---:|---:|---|",
    ]
    warnings: list[str] = []
    zero = set(health.get("zero_sources") or ())
    for name, source in sources.items():
        if not isinstance(source, Mapping):
            continue
        status = str(source.get("status", "?"))
        jobs = source.get("jobs") if isinstance(source.get("jobs"), int) else 0
        ratio = source.get("failure_ratio") if isinstance(source.get("failure_ratio"), (int, float)) else 0.0
        total, names = _failed(source)
        shown_status = status if status == "ok" else f"**{status}**"
        if source.get("in_cooldown"):
            shown_status += " (403 cooldown)"
        lines.append(f"| {_cell(name)} | {shown_status} | {jobs:,} | {ratio:.1%} | {_failed_cell(total, names)} |")
        if status != "ok":
            warnings.append(f"{name} is {status}: {_plural(total, 'failed company')} ({ratio:.1%} of units)")
        if name in zero or jobs == 0:
            warnings.append(f"{name} returned 0 jobs")
        if source.get("in_cooldown"):
            warnings.append(f"{name} hit the 403 cooldown")
    return "\n".join(lines) + "\n", warnings


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    path = args[0] if args else "health.json"
    try:
        with open(path, encoding="utf-8") as f:
            health: Any = json.load(f)
    except (OSError, ValueError) as exc:
        sys.stdout.write(f"::warning::could not read {path}: {exc}\n")
        return 0
    markdown, warnings = render_summary(health)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(markdown)
    else:
        sys.stdout.write(markdown)
    for warning in warnings:
        sys.stdout.write(f"::warning::{warning}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

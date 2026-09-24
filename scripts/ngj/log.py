"""Logging setup for the CLI run and GitHub Actions annotations."""

from __future__ import annotations

import logging
import sys

LOG_FORMAT = "%(message)s"


def configure_logging(level: int = logging.INFO) -> None:
    """Send log records to stdout, one plain line each (Actions-friendly).

    Called once from the CLI ``main``; importing the package never configures
    logging.
    """
    logging.basicConfig(level=level, format=LOG_FORMAT, stream=sys.stdout, force=True)


def annotate(level: str, message: str) -> None:
    """Emit a GitHub Actions workflow command (``::error::`` / ``::warning::``).

    Written straight to stdout: the runner only recognises these commands on
    stdout, regardless of how logging is configured.
    """
    if level not in ("error", "warning", "notice"):
        raise ValueError(f"unsupported annotation level: {level!r}")
    print(f"::{level}::{message}", flush=True)

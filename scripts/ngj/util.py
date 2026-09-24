"""Small dependency-free helpers shared across the package."""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


def coerce_positive_int(value: Any, default: int, name: str) -> int:
    """Parse a positive integer or fall back to ``default`` (logging why)."""
    if value is None:
        return default
    if isinstance(value, bool):
        logger.warning("  ⚠️  Invalid %s=%r; using default %s", name, value, default)
        return default
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = int(value.strip())
        except ValueError:
            logger.warning("  ⚠️  Invalid %s=%r; using default %s", name, value, default)
            return default
    else:
        logger.warning("  ⚠️  Invalid %s=%r; using default %s", name, value, default)
        return default

    if parsed <= 0:
        logger.warning("  ⚠️  Invalid %s=%r; using default %s", name, value, default)
        return default
    return parsed


def get_nested_value(obj: Any, path: str) -> Any:
    """Resolve dot-separated paths in nested dict/list structures.

    Numeric tokens index lists; any other token applied to a list collects that
    key from every dict element.
    """
    if not isinstance(obj, dict):
        return None
    if not isinstance(path, str) or not path.strip():
        return None

    current = obj
    for token in path.split('.'):
        if isinstance(current, dict):
            if token not in current:
                return None
            current = current[token]
            continue

        if isinstance(current, list):
            if token.isdigit():
                index = int(token)
                if index < 0 or index >= len(current):
                    return None
                current = current[index]
                continue

            extracted = [item[token] for item in current if isinstance(item, dict) and token in item]
            if not extracted:
                return None
            current = extracted
            continue

        return None

    return current


def sanitize_nan(obj: Any) -> Any:
    """Return a copy of ``obj`` with NaN/inf floats replaced by None (JSON-safe)."""
    if isinstance(obj, dict):
        return {k: sanitize_nan(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_nan(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj

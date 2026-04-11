import json
from pathlib import Path
from typing import TypeAlias

JSON_INDENT = 2
JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]


def write_json_artifact(path: Path, payload: JSONValue) -> None:
    """Write JSON payload to an artifact file with pretty indentation.

    Args:
        path: Target JSON file path.
        payload: JSON-serializable object to write.

    Returns:
        None
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=JSON_INDENT, allow_nan=False)
        handle.write("\n")

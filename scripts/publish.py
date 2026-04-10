import json
from pathlib import Path
from typing import Any

JSON_INDENT = 2


def write_json_artifact(path: Path, payload: Any) -> None:
    """Write JSON payload to an artifact file with pretty indentation.

    Args:
        path: Target JSON file path.
        payload: JSON-serializable object to write.
    """ 
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=JSON_INDENT)
        handle.write("\n")

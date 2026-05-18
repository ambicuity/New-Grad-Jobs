#!/usr/bin/env python3

import json

from publish import write_json_artifact


def test_write_json_artifact_creates_parent_dirs_and_writes_valid_json(tmp_path) -> None:
    output_path = tmp_path / "nested" / "artifacts" / "sample.json"
    payload = {
        "message": "Olá, new grad!",
        "count": 3,
        "items": ["alpha", "beta"],
    }

    write_json_artifact(output_path, payload)

    assert output_path.exists()
    assert output_path.parent.is_dir()

    loaded = json.loads(output_path.read_text(encoding="utf-8"))
    assert loaded == payload


def test_write_json_artifact_uses_pretty_json_and_trailing_newline(tmp_path) -> None:
    output_path = tmp_path / "artifact.json"
    payload = {"a": 1, "b": {"c": 2}}

    write_json_artifact(output_path, payload)

    text = output_path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert '\n  "a": 1,' in text
    assert '\n  "b": {' in text

#!/usr/bin/env python3
"""
Unit tests for scripts/publish.py::write_json_artifact.
Tests cover writing JSON artifacts with proper formatting, directory creation, and UTF-8 handling.
"""

import json
import tempfile
from pathlib import Path

import pytest
from scripts.publish import write_json_artifact


class TestWriteJsonArtifact:
    def test_writes_none_payload_as_null(self):
        """Test that write_json_artifact serializes None payload as JSON null."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "none.json"
            write_json_artifact(temp_path, None)
            content = temp_path.read_text(encoding="utf-8")
            assert json.loads(content) is None
            assert content.startswith("null")

    def test_rejects_nan_payload(self):
        """Test that write_json_artifact rejects NaN to keep output strict JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "nan.json"
            with pytest.raises(ValueError, match=r"Out of range float values|NaN"):
                write_json_artifact(temp_path, {"value": float("nan")})

    def test_raises_type_error_for_non_serializable_payload(self):
        """Test that non-JSON-serializable objects raise TypeError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "invalid.json"
            with pytest.raises(TypeError):
                write_json_artifact(temp_path, {"x": object()})

    def test_creates_missing_parent_directories(self):
        """Test that write_json_artifact creates missing parent directories automatically."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            nested_path = temp_path / "deep" / "nested" / "dir" / "artifact.json"

            # Ensure the directory doesn't exist yet
            assert not nested_path.parent.exists()

            payload = {"test": "data"}
            write_json_artifact(nested_path, payload)

            # Check that the parent directory was created
            assert nested_path.parent.exists()
            assert nested_path.parent.is_dir()

    def test_writes_valid_json_with_pretty_indentation(self):
        """Test that write_json_artifact writes valid JSON with pretty indentation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "test.json"

            payload = {"key": "value", "nested": {"inner": "data"}, "list": [1, 2, 3]}
            write_json_artifact(temp_path, payload)

            # Read back and verify
            with temp_path.open("r", encoding="utf-8") as f:
                content = f.read()

            # Parse to ensure valid JSON
            parsed = json.loads(content)
            assert parsed == payload

            # Check indentation (should be 2 spaces)
            lines = content.splitlines()
            # First level should have no indent
            assert lines[0] == "{"
            # Second level should have 2 spaces
            assert lines[1].startswith("  ")
            # Nested object should have 4 spaces
            nested_line = next(line for line in lines if '"inner"' in line)
            assert nested_line.startswith("    ")

    def test_writes_empty_payloads(self):
        """Test that empty dict/list payloads serialize and roundtrip correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dict_path = Path(temp_dir) / "empty_dict.json"
            list_path = Path(temp_dir) / "empty_list.json"

            write_json_artifact(dict_path, {})
            write_json_artifact(list_path, [])

            dict_text = dict_path.read_text(encoding="utf-8")
            list_text = list_path.read_text(encoding="utf-8")

            assert json.loads(dict_text) == {}
            assert json.loads(list_text) == []
            assert dict_text.endswith("\n")
            assert list_text.endswith("\n")

    def test_writes_very_long_string_payload(self):
        """Test that very long UTF-8 strings are preserved and newline is appended."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "long_string.json"
            long_text = "🚀" + ("abc123" * 2000) + "世界"
            payload = {"blob": long_text}

            write_json_artifact(temp_path, payload)

            content = temp_path.read_text(encoding="utf-8")
            parsed = json.loads(content)
            assert parsed == payload
            assert parsed["blob"] == long_text
            assert content.endswith("\n")

    def test_preserves_utf8_content(self):
        """Test that write_json_artifact preserves UTF-8 content without escaping."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "utf8_test.json"

            payload = {"message": "Hello 世界 🌍", "emoji": "🚀", "accented": "café"}
            write_json_artifact(temp_path, payload)

            # Read back and verify
            with temp_path.open("r", encoding="utf-8") as f:
                content = f.read()

            # Parse to ensure valid JSON
            parsed = json.loads(content)
            assert parsed == payload

            # Check that UTF-8 characters are not escaped
            assert "世界" in content
            assert "🌍" in content
            assert "🚀" in content
            assert "café" in content
            # Ensure no \u escapes for these characters
            assert "\\u" not in content

    def test_writes_trailing_newline(self):
        """Test that write_json_artifact writes a trailing newline at EOF."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "newline_test.json"

            payload = {"test": "value"}
            write_json_artifact(temp_path, payload)

            # Read the entire file including potential newline
            with temp_path.open("rb") as f:
                content_bytes = f.read()

            # Check that the last byte is a newline
            assert content_bytes.endswith(b"\n")

            # Also verify the content without newline is valid JSON
            content_str = content_bytes.decode("utf-8").rstrip("\n")
            parsed = json.loads(content_str)
            assert parsed == payload

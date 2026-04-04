#!/usr/bin/env python3
"""Deterministic tests for prediction artifact generation and validation."""

import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import update_jobs


FIXED_NOW = datetime(2026, 4, 3, 12, 0, 0)


def _fixed_datetime_class(fixed_now: datetime):
    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_now.replace(tzinfo=None)
            return fixed_now.astimezone(tz)

        @classmethod
        def fromtimestamp(cls, ts, tz=None):
            return datetime.fromtimestamp(ts, tz=tz)

    return _FixedDateTime


def _patch_artifact_paths(monkeypatch, tmp_path):
    docs_dir = str(tmp_path / "docs")
    os.makedirs(docs_dir, exist_ok=True)
    history_path = os.path.join(docs_dir, "market-history.json")
    predictions_path = os.path.join(docs_dir, "predictions.json")
    status_path = os.path.join(docs_dir, "predictions-status.json")

    original_join = os.path.join

    def patched_join(*parts):
        if parts and parts[-1] == "market-history.json":
            return history_path
        if parts and parts[-1] == "predictions.json":
            return predictions_path
        if parts and parts[-1] == "predictions-status.json":
            return status_path
        return original_join(*parts)

    monkeypatch.setattr(update_jobs.os.path, "join", patched_join)
    return history_path, predictions_path, status_path


def _write_history(history_path, num_days=8):
    snapshots = []
    for offset in range(num_days):
        day = (FIXED_NOW - timedelta(days=num_days - offset - 1)).strftime("%Y-%m-%d")
        snapshots.append(
            {
                "date": day,
                "total_jobs": 100 + offset,
                "categories": {"swe": 50 + offset},
                "tiers": {"faang-plus": 20 + offset},
                "top_companies": [{"company": "Google", "jobs": 10}],
                "unique_companies": 10,
                "avg_jobs_per_company": 10.0,
                "timestamp": FIXED_NOW.isoformat(),
            }
        )

    history_data = {
        "meta": {
            "last_updated": FIXED_NOW.isoformat(),
            "total_snapshots": len(snapshots),
            "date_range": {"start": snapshots[0]["date"], "end": snapshots[-1]["date"]},
        },
        "snapshots": snapshots,
    }
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history_data, f)
    return snapshots


def _gemini_response_for(payload):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]
    }
    return response


def test_predict_hiring_trends_writes_valid_artifact(monkeypatch, tmp_path):
    history_path, predictions_path, status_path = _patch_artifact_paths(monkeypatch, tmp_path)
    snapshots = _write_history(history_path)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setattr(update_jobs, "datetime", _fixed_datetime_class(FIXED_NOW))

    payload = {
        "outlook": "bullish",
        "predictions": {
            "7_days": {"total_jobs": 220, "change_percent": 5.5},
            "30_days": {"total_jobs": 280, "change_percent": 12.0},
        },
        "growing_categories": ["swe", "ml", "data"],
        "declining_categories": ["product", "design", "sales"],
        "confidence": 82.5,
        "insights": ["Demand is rising.", "ML roles are accelerating.", "Hiring remains selective."],
    }

    with patch("update_jobs.limited_post", return_value=_gemini_response_for(payload)) as mock_post:
        result = update_jobs.predict_hiring_trends()

    assert mock_post.call_count == 1
    assert result["state"] == "generated"
    assert os.path.exists(predictions_path)
    with open(predictions_path, "r", encoding="utf-8") as f:
        artifact = json.load(f)
    assert artifact["outlook"] == "bullish"
    assert artifact["predictions"]["7_days"]["total_jobs"] == 220
    assert artifact["predictions"]["30_days"]["change_percent"] == 12.0
    assert artifact["generated_at"] == FIXED_NOW.isoformat()
    assert artifact["data_points"] == len(snapshots)
    assert artifact["date_range"] == {
        "start": snapshots[0]["date"],
        "end": snapshots[-1]["date"],
    }
    assert os.path.exists(status_path)
    with open(status_path, "r", encoding="utf-8") as f:
        status = json.load(f)
    assert status["state"] == "generated"
    assert status["prediction_artifact"]["exists"] is True


@pytest.mark.parametrize(
    "payload, expected_message",
    [
        (
            {
                "outlook": "bullish",
                "predictions": {
                    "7_days": {"total_jobs": 220, "change_percent": 5.5},
                    "30_days": {"total_jobs": 280, "change_percent": 12.0},
                },
                "declining_categories": ["product"],
                "confidence": 82.5,
                "insights": ["ok"],
            },
            "missing keys",
        ),
        (
            {
                "outlook": "bullish",
                "predictions": {
                    "7_days": {"total_jobs": "220", "change_percent": 5.5},
                    "30_days": {"total_jobs": 280, "change_percent": 12.0},
                },
                "growing_categories": ["swe"],
                "declining_categories": ["product"],
                "confidence": 82.5,
                "insights": ["ok"],
            },
            "Invalid predictions.7_days.total_jobs type",
        ),
        (
            {
                "outlook": "bullish",
                "predictions": {
                    "7_days": {"total_jobs": 220, "change_percent": 5.5},
                    "30_days": {"total_jobs": 280, "change_percent": 12.0},
                },
                "growing_categories": "swe",
                "declining_categories": ["product"],
                "confidence": 82.5,
                "insights": ["ok"],
            },
            "Invalid growing_categories type",
        ),
    ],
)
def test_predict_hiring_trends_rejects_invalid_payloads(
    monkeypatch, tmp_path, payload, expected_message, capsys
):
    history_path, predictions_path, status_path = _patch_artifact_paths(monkeypatch, tmp_path)
    _write_history(history_path)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setattr(update_jobs, "datetime", _fixed_datetime_class(FIXED_NOW))

    with patch("update_jobs.limited_post", return_value=_gemini_response_for(payload)):
        result = update_jobs.predict_hiring_trends()

    assert not os.path.exists(predictions_path)
    assert result["state"] == "invalid_payload"
    assert os.path.exists(status_path)
    with open(status_path, "r", encoding="utf-8") as f:
        status = json.load(f)
    assert status["state"] == "invalid_payload"
    assert expected_message in capsys.readouterr().out


def test_predict_hiring_trends_writes_no_key_status(monkeypatch, tmp_path):
    history_path, predictions_path, status_path = _patch_artifact_paths(monkeypatch, tmp_path)
    _write_history(history_path, num_days=10)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr(update_jobs, "datetime", _fixed_datetime_class(FIXED_NOW))

    result = update_jobs.predict_hiring_trends()

    assert result["state"] == "no_api_key"
    assert not os.path.exists(predictions_path)
    with open(status_path, "r", encoding="utf-8") as f:
        status = json.load(f)
    assert status["state"] == "no_api_key"
    assert status["prediction_artifact"]["exists"] is False


def test_predict_hiring_trends_writes_insufficient_history_status(monkeypatch, tmp_path):
    history_path, predictions_path, status_path = _patch_artifact_paths(monkeypatch, tmp_path)
    _write_history(history_path, num_days=3)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setattr(update_jobs, "datetime", _fixed_datetime_class(FIXED_NOW))

    result = update_jobs.predict_hiring_trends()

    assert result["state"] == "insufficient_history"
    assert not os.path.exists(predictions_path)
    with open(status_path, "r", encoding="utf-8") as f:
        status = json.load(f)
    assert status["state"] == "insufficient_history"
    assert status["available_history_snapshots"] == 3

# Predictions Artifact Contract

This document defines the producer/consumer contract for the stats forecast panel at:

- `/docs/stats.html` (local)
- `/New-Grad-Jobs/docs/stats.html` (GitHub Pages)

## Files and Paths

- Market history input: `docs/market-history.json`
- Forecast output: `docs/predictions.json`
- Forecast pipeline status: `docs/predictions-status.json`

The stats page (`docs/stats.js`) reads these files from:

- `./<file>.json`
- `../<file>.json`
- `/New-Grad-Jobs/docs/<file>.json`

## Required Forecast Schema (`docs/predictions.json`)

```json
{
  "outlook": "bullish|neutral|bearish",
  "predictions": {
    "7_days": { "total_jobs": 123, "change_percent": 1.2 },
    "30_days": { "total_jobs": 456, "change_percent": -3.4 }
  },
  "growing_categories": ["..."],
  "declining_categories": ["..."],
  "confidence": 82.5,
  "insights": ["..."],
  "generated_at": "ISO-8601 timestamp",
  "data_points": 31,
  "date_range": { "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" }
}
```

Minimum history required: `7` daily snapshots in `docs/market-history.json`.

## Status Schema (`docs/predictions-status.json`)

This file is written on each prediction attempt.

```json
{
  "state": "generated|already_generated|no_api_key|history_missing|insufficient_history|invalid_payload|generation_failed",
  "message": "human-readable summary",
  "updated_at": "ISO-8601 timestamp",
  "requires_api_key": true,
  "minimum_history_snapshots": 7,
  "available_history_snapshots": 31,
  "prediction_artifact": {
    "path": "docs/predictions.json",
    "exists": true
  },
  "details": {}
}
```

## Local Bootstrap

Use the prediction bootstrap command after `docs/market-history.json` exists:

```bash
make predict
```

Equivalent direct command:

```bash
cd scripts && ../.venv/bin/python generate_predictions.py
```

Force regeneration even if today's artifact exists:

```bash
cd scripts && ../.venv/bin/python generate_predictions.py --force
```

## Truthful States in UI

The forecast panel distinguishes these outcomes:

- loading
- pipeline not run yet
- forecast file missing
- API key missing
- insufficient history
- malformed forecast artifact
- fetch/path failure
- successful render

# 🛠️ The Operator's Manual

Welcome to the Operator's Manual! This document provides copy-pasteable recipes, troubleshooting steps, and performance tuning configurations for managing the New Grad Jobs scraper engine.

## 🍳 Common Recipes

### 1. Adding a New Keyword Filter
To drop jobs containing a specific word (e.g., "Senior"):
1. Open `config.yml`.
2. Locate the `filters.exclude_keywords` list.
3. Append your new keyword to the bottom of the list in lowercase.
```yaml
exclude_keywords:
  - senior
  - staff
  - new_keyword
```

### 2. Tuning the Thread Pool Size
If you are hitting rate limits or GitHub Actions is running out of memory:
1. Open `scripts/update_jobs.py`.
2. Locate the `ThreadPoolExecutor` declaration.
3. Modify `max_workers=50` to a lower number (e.g., `20`).

### 3. Adding a New JobSpy Location
To target a highly specific location via JobSpy (e.g., only "London, UK"):
1. Open `config.yml`.
2. Locate the `jobspy.locations` list.
3. Append the exact string:
```yaml
jobspy:
  locations:
    - London, UK
```

---

## 🚑 Troubleshooting Tree

| Symptom | Root Cause Hypothesis | Resolution Action |
|---------|-----------------------|-------------------|
| **Jobs count suddenly drops by 50%** | JobSpy API structure changed or IP blocked. | Check Actions logs. If 403 Forbidden, wait 24h. If parsing error, update `python-jobspy` in `requirements.txt`. |
| **Commit fails with "Merge Conflict"** | Two overlapping cron jobs tried to write to `README.md` simultaneously. | Ignore it. The GitHub Actions workflow is built with exponential backoff and will retry automatically. |
| **No output in `jobs.json`** | All jobs were filtered out as "stale" or non-grad. | Verify the `filters.date_recency_days` in `config.yml` isn't set too aggressively (e.g., 1 day). |
| **`make setup` fails on `numpy`** | C++ compiler missing for Python 3.13 on macOS. | Use the DevContainer (`python:3.11`) or explicitly use Python 3.11 locally where `numpy` wheels exist. |

---

## ⚡ Performance Tuning

The system is currently tuned for maximum throughput within a 5-minute GitHub Actions window.

1. **Connection Pooling**: The `create_optimized_session()` uses `pool_connections=1000` and `pool_maxsize=300`. If you reduce the number of companies scraped, you can safely halve these values to save memory.
2. **Cron Frequency**: The `.github/workflows/update-jobs.yml` runs every `*/5 * * * *`. To save on compute (and git bloat), change this to `0 * * * *` (hourly).

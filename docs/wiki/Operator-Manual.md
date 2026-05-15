# 🛠️ The Operator's Manual

Welcome to the Operator's Manual! This document provides copy-pasteable recipes, troubleshooting steps, and performance tuning configurations for managing the New Grad Jobs scraper engine.

## 🍳 Common Recipes

### 1. Adding a New Keyword Filter
To drop jobs containing a specific word (e.g., "Senior"):
1. Open `config.yml`.
2. Locate the `filtering.exclusion_signals` list.
3. Append your new keyword to the bottom of the list in lowercase.
```yaml
filtering:
  exclusion_signals:
    - senior
    - staff
    - new_keyword
```

### 2. Tuning the Thread Pool Size
If you are hitting rate limits or GitHub Actions is running out of memory:
1. Prefer configuration over code edits.
2. In `config.yml`, add or update a top-level `worker_pools` block.
3. Lower the source-specific worker count that is causing pressure, then test with the `Update New Grad Jobs` workflow.
```yaml
worker_pools:
  greenhouse_min_workers: 20
  greenhouse_max_workers: 150
  lever_min_workers: 10
  lever_max_workers: 100
  google_min_workers: 8
  google_max_workers: 50
  graphql_min_workers: 5
  graphql_max_workers: 40
  jobspy_workers: 15
  orchestrator_workers: 10
```

The current checked-in `config.yml` may omit this block; `scripts/update_jobs.py` supports it and otherwise uses its fallback constants. Routine tuning should not require editing `ThreadPoolExecutor` calls directly.

### 3. Adding a New JobSpy Country
To add a country-level JobSpy search target:
1. Open `config.yml`.
2. Locate `apis.jobspy.countries`.
3. Append a `code` and `location` pair supported by JobSpy/Indeed:
```yaml
apis:
  jobspy:
    countries:
      - code: "USA"
        location: "United States"
      - code: "Canada"
        location: "Canada"
      - code: "India"
        location: "India"
```

Specific cities are currently expressed through `apis.jobspy.search_terms` (for example, "Toronto new grad software"), not through a dedicated JobSpy location list.

## 🚦 CI/CD Monitoring Guide (For Solo Maintainers)

As a solo maintainer, your time is precious. Do not become a slave to your own CI pipelines. The infrastructure is heavily automated, so you should only look at CI when it explicitly blocks you.

Here is exactly what you should care about:

1. **The Gatekeeper (`CI — Lint & Validate`)**:
   * **Why it matters**: This tests your actual Python scraper structure. If this fails on a PR, **do not merge**. It means `update_jobs.py` has a syntax error or `config.yml` is corrupted, which would break the scheduled `Update New Grad Jobs` scraper.
2. **Dependabot CI (`Dependabot Auto-Merge`)**:
   * **Why it matters**: Patch and minor Dependabot PRs are auto-approved and set to auto-merge after required checks pass. Review major updates manually, and look at any Dependabot PR where a required check fails.
3. **Pre-commit (`Code Hygiene (Pre-commit)`)**:
   * **Why it matters**: It automatically catches messy formatting, merge markers, oversized files, private keys, and secret leaks so you don't have to leave nitpicky review comments. If it fails, just ask the contributor to run `pre-commit run --all-files` locally before you merge.
4. **Security workflows (`CodeQL Security Scan`, `Vulnerability Scanner (Trivy)`, `OpenSSF Scorecard`, `SBOM Generator`)**:
   * **Why it matters**: These provide code scanning, dependency/container vulnerability checks, supply-chain posture checks, and SBOM output. GitHub will send you an email alert if a critical vulnerability is found. You only need to look at these if you get an alert or one of these required checks blocks a PR.
5. **Scraper publisher (`Update New Grad Jobs`)**:
   * **Why it matters**: This is the scheduled scraper. It runs every five minutes, writes generated docs artifacts on `main`, and skips commit/push when manually dispatched on a non-main ref for artifact verification.

**TL;DR:** Trust the bots for first-pass signal, but check all required workflows before merging. The `CI — Lint & Validate` check is the structural gate for scraper/config breakage; other required checks can still block a PR.

### Diagnosing "Release Please" Failures
If you see a `Release Please / Release Please (push) Failing` with an error containing:
`Error: release-please failed: GitHub Actions is not permitted to create or approve pull requests.`

**Resolution**: You need to grant the `GITHUB_TOKEN` permission to create pull requests in the repository settings.
1. Go to **Settings** > **Actions** > **General** in your GitHub repository.
2. Scroll down to **Workflow permissions**.
3. Check the box for **"Allow GitHub Actions to create and approve pull requests"**.
4. Click **Save**.

---

## 🚑 Troubleshooting Tree

| Symptom | Root Cause Hypothesis | Resolution Action |
|---------|-----------------------|-------------------|
| **Jobs count suddenly drops by 50%** | JobSpy API structure changed or IP blocked. | Check Actions logs. If 403 Forbidden, wait 24h. If parsing error, update `python-jobspy` in `requirements.txt`. |
| **Commit fails with "Merge Conflict"** | A concurrent scraper or maintainer push updated `main` while the workflow was preparing its generated-docs commit. | Check the `Update New Grad Jobs` run. It pulls with `--autostash`, then retries rejected pushes up to three times. Intervene only if all retries fail. |
| **No output in `jobs.json`** | All jobs were filtered out as stale or non-grad. | Verify `filtering.max_age_days` in `config.yml` and check whether `filtering.new_grad_signals`, `filtering.track_signals`, or `filtering.exclusion_signals` became too restrictive. |
| **`make setup` fails on `numpy`** | C++ compiler missing for Python 3.13 on macOS. | Use the DevContainer (`python:3.11`) or explicitly use Python 3.11 locally where `numpy` wheels exist. |

---

## ⚡ Performance Tuning

The system is currently tuned for maximum throughput within a 5-minute GitHub Actions window.

1. **Worker pools**: Tune source concurrency through `worker_pools` in `config.yml` when possible. The script reads these values at startup and falls back to constants in `scripts/update_jobs.py` when the block is absent.
2. **Connection pooling**: `create_optimized_session()` currently uses `pool_connections=1000` and `pool_maxsize=300`. Treat these as advanced HTTP adapter settings. Change them only after worker-pool tuning fails to solve the problem.
3. **Cron frequency**: `.github/workflows/update-jobs.yml` runs every `*/5 * * * *`. To save compute and reduce generated-commit churn, change this to `0 * * * *` (hourly).

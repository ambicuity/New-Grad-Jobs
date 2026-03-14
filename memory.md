# New-Grad-Jobs Test Improver Memory (Mar 2026)

## Commands
- **Test**: `~/.local/bin/pytest tests/ -q` (or `python -m pytest tests/`)
- **Coverage**: auto via pyproject.toml addopts
- **Lint**: `flake8 <file> --select=E9,F63,F7,F82`
- **Install**: `pip install --break-system-packages pytest pytest-cov flake8`

## Coverage
- Current (Mar 14): update_jobs.py 46%, total 42%, 166 tests (↑5 tests from Mar 13)

## Backlog
1. `is_recent_job()` with int ms timestamps (1375-1404)
2. `deduplicate_jobs()` end-to-end (1290-1303)
3. `has_new_grad_signal()` / `has_track_signal()` (1307-1313)
4. `extract_sort_date()` (1882-1892)
5. `generate_jobs_json()` (1552-1581)

## Completed
- PR #151: enrichment tests (49 tests, +4pp), draft status - awaiting maintainer review

## Status
- PR #151: Open, draft, no CI checks run (created Mar 11, still pending review)
- Issue #152: Monthly Activity updated with latest test counts and run history
- Issue #157: Workflow failure from Mar 12 - Test Improver already investigated and commented
- Next: Task 2 (identify new opportunities), Task 3 (implement more tests when PR #151 is merged)

## Last Updated
- Run ID: 23081130613 (2026-03-14 05:14 UTC)

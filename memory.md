# New-Grad-Jobs Test Improver Memory (Mar 2026)

## Commands
- **Test**: `~/.local/bin/pytest tests/ -q` (or `python -m pytest tests/`)
- **Coverage**: auto via pyproject.toml addopts
- **Lint**: `flake8 <file> --select=E9,F63,F7,F82`
- **Install**: `pip install --break-system-packages pytest pytest-cov flake8`

## Coverage
- Current (Mar 13): update_jobs.py 45%, total 40%, 161 tests

## Backlog
1. `is_recent_job()` with int ms timestamps (1375-1404)
2. `deduplicate_jobs()` end-to-end (1290-1303)
3. `has_new_grad_signal()` / `has_track_signal()` (1307-1313)
4. `extract_sort_date()` (1882-1892)
5. `generate_jobs_json()` (1552-1581)

## Completed
- PR #151: enrichment tests (49 tests, +4pp), draft status

## Status
- PR #151: Open, draft, no CI checks
- Issue #157: Workflow failure, commented
- Issue #152: Monthly Activity updated
- Next: Task 5 (comment issues), Task 6 (infrastructure)

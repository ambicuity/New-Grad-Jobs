# New-Grad-Jobs Test Improver Memory (Mar 2026)

## Commands
- **Test**: `python -m pytest tests/ -q`
- **Coverage**: auto via pyproject.toml addopts
- **Lint**: `flake8 <file> --select=E9,F63,F7,F82`
- **Install**: `pip install --break-system-packages pytest pytest-cov flake8`

## Coverage
- Current (Mar 15): update_jobs.py 46%, total 42%, 200 tests

## Backlog
1. `is_recent_job()` - ✅ Already well-tested in test_date_normalization.py
2. ~~`deduplicate_jobs()` end-to-end~~ ✅ DONE (PR #152)
3. `has_new_grad_signal()` / `has_track_signal()` (lines ~1307-1313)
4. `extract_sort_date()` (lines ~1882-1892)
5. `generate_jobs_json()` (lines ~1552-1581)

## Completed
- PR #151: enrichment tests (49 tests, +4pp), draft - awaiting maintainer review
- PR #152: deduplication tests (25 tests), draft, created Mar 15

## Status
- PR #151: Open, draft, created Mar 11 (enrichment functions)
- PR #152: Open, draft, created Mar 15 (deduplication)
- Monthly Activity #153: Created for March 2026
- Next: Monitor PR review, consider Task 2 (identify more opportunities) or Task 3 (implement more tests)

## Last Updated
- Run ID: 23104295954 (2026-03-15 05:39 UTC)

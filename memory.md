# New-Grad-Jobs Test Improver Memory (Mar 2026)

## Commands
- **Test**: `python -m pytest tests/ -q`
- **Coverage**: auto via pyproject.toml addopts
- **Lint**: `flake8 <file> --select=E9,F63,F7,F82`
- **Install**: `pip install --break-system-packages pytest pytest-cov flake8`

## Coverage
- Current (Mar 16): update_jobs.py 46%, total 42%, 210 tests

## Backlog
1. `is_recent_job()` - ✅ Already well-tested in test_date_normalization.py
2. ~~`deduplicate_jobs()` end-to-end~~ ✅ DONE (PR #152)
3. ~~`has_new_grad_signal()` / `has_track_signal()`~~ ✅ DONE (PR #193, 35 tests)
4. `extract_sort_date()` (lines ~1882-1892)
5. `generate_jobs_json()` (lines ~1552-1581)
6. `filter_jobs()` - master filter pipeline

## Completed
- PR #151: enrichment tests (49 tests, +4pp), draft
- PR #152: deduplication tests (25 tests), draft
- PR #193: signal detection tests (35 tests), draft - created Mar 16

## Status
- PR #151: Open, draft, created Mar 11 (enrichment functions)
- PR #152: Open, draft, created Mar 15 (deduplication)
- PR #193: Open, draft, created Mar 16 (signal detection)
- Monthly Activity #191: Updated Mar 16 with PR #192 and #193 info
- Next: Task 4 (Maintain PRs), Task 7 (Update Monthly Activity with PR #193)

## Last Updated
- Run ID: 23129886288 (2026-03-16 05:51 UTC)

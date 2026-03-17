# New-Grad-Jobs Test Improver Memory (Mar 2026)

## Commands
- **Test**: `python -m pytest tests/ -q`
- **Coverage**: auto via pyproject.toml addopts
- **Lint**: `flake8 <file> --select=E9,F63,F7,F82`
- **Install**: `pip install --break-system-packages pytest pytest-cov flake8`

## Coverage
- Current (Mar 17): update_jobs.py 46%, total 42%, 175 tests (main)
- PR #151 baseline: 186 tests (49 enrichment tests added)
- PR #192 baseline: 200 tests (25 dedup tests added)
- PR #195 baseline: 210 tests (35 signal tests added)

## Backlog
1. ✅ `deduplicate_jobs()` - DONE (PR #192)
2. ✅ `has_new_grad_signal()` / `has_track_signal()` - DONE (PR #195)
3. `extract_sort_date()` (lines ~1882-1892)
4. `generate_jobs_json()` (lines ~1552-1581)
5. `filter_jobs()` - master filter pipeline

## Completed
- PR #151: enrichment tests (49 tests, +4pp), draft, created Mar 11
- PR #192: deduplication tests (25 tests), draft, created Mar 15
- PR #195: signal detection tests (35 tests), draft, created Mar 16

## Status
- PR #151: Open, draft, created Mar 11 (enrichment functions)
- PR #192: Open, draft, created Mar 15 (deduplication)
- PR #195: Open, draft, created Mar 16 (signal detection)
- Monthly Activity #191: Updated Mar 17 with all 3 PRs
- Main branch healthy: 175 tests pass, no regressions

## Last Updated
- Run ID: 23179757068 (2026-03-17 05:26 UTC)
- Tasks completed: Task 4 (verified PRs), Task 7 (updated monthly activity)

# New-Grad-Jobs Test Improver Memory

## Commands (Validated 2026-03-11)
- **Test**: `~/.local/bin/pytest tests/ -q`
- **Coverage**: auto via pyproject.toml addopts `--cov=scripts --cov-report=term-missing`
- **Lint**: `~/.local/bin/flake8 <file> --select=E9,F63,F7,F82`
- **Install**: `pip install --break-system-packages pytest pytest-cov flake8`
- **CI**: `ci.yml` (flake8+pytest), `pre-commit.yml`

## Testing Notes
- Import: `sys.path.insert(0, '../scripts')` then `from update_jobs import ...`
- Pattern: factory `_make_job(**kwargs)`, class-based test groups
- `get_company_tier()` uses `@lru_cache` — safe in tests
- Constants: `NO_SPONSORSHIP_KEYWORDS`, `US_CITIZENSHIP_KEYWORDS`, `FAANG_PLUS`, `UNICORNS`, `DEFENSE`, `FINANCE`, `HEALTHCARE`, `STARTUPS`
- `is_job_closed` checks exact substrings: 'closed', 'no longer accepting', 'position filled', 'expired'

## Coverage (2026-03-11)
- Before: update_jobs.py 42% (637 missing), total 38% (759 missing), 137 tests
- After: update_jobs.py 46% (592 missing), total 41% (714 missing), 186 tests

## Backlog (prioritized)
1. `is_recent_job()` with int ms timestamps and date objects (1375-1404)
2. `deduplicate_jobs()` end-to-end (1290-1303)
3. `has_new_grad_signal()` / `has_track_signal()` (1307-1313)
4. `extract_sort_date()` (1882-1892)
5. `generate_jobs_json()` (1552-1581)

## Completed
- 2026-03-11: `tests/test_enrichment.py` (49 tests, +4pp), PR submitted on branch test-assist/enrichment-functions

## Round-Robin (last run 2026-03-11)
- Task 1 (commands) ✓, Task 2 (opportunities) ✓, Task 3 (implement) ✓, Task 7 (monthly) ✓
- Next: Task 4 (maintain PRs), Task 5 (comment issues), Task 6 (infrastructure)

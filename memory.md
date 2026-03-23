# Test Improver Memory

## Commands
Test: `python -m pytest tests/ -q`
Cov: `pytest --cov=scripts --cov-report=term-missing`
Lint: `flake8 <f> --select=E9,F63,F7,F82`

## Status
375 tests, 65% update_jobs, 61% total

## PRs (all draft)
151(enrich,49), 192(dedup,25), 195(sig,35), 207(sort,25), 212(recent,39), 213(conftest), NEW(filter,51)

## Backlog
1. ✅ Done: enrich, dedup, signals, sort, recent, conftest, filter_jobs
2. NEXT: generate_jobs_json (JSON output)
3. normalize_date_string (date parsing)
4. API fetch functions (needs mocks)

## Notes
filter_jobs: None title → crash (line 1857). Test documents bug.

## Last
23423188967 (23-03) T3,4,7

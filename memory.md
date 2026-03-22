# Test Improver Memory

## Commands
- Test: `python -m pytest tests/ -q` or `pytest tests/ -q`
- Lint: `flake8 <f> --select=E9,F63,F7,F82`
- Coverage: `pytest tests/ --cov=scripts --cov-report=term-missing`
- Install: `pip install --break-system-packages pytest pytest-cov flake8`

## Coverage
Main: 65% update_jobs, 61% total, 324 tests

## PRs
#151(enrich,49), #192(dedup,25), #195(sig,35), #207(sort,25), #212(is_recent_job,39), #NEW(conftest)

## Infrastructure
- ✅ conftest.py created (NEW PR) - shared fixtures, helpers, constants
- Fixtures: sample_job, sample_config, greenhouse_company, lever_company
- Helpers: create_job(), create_jobs_batch()
- Constants: VALID_US_LOCATIONS, NEW_GRAD_SIGNALS, EXCLUDE_KEYWORDS

## Backlog
1. ✅ dedup (192), signals (195), sort (207), enrich (151), is_recent_job (212), conftest (NEW)
2. filter_jobs (master filter, lines 1555-1609) - integration tests **NEXT HIGH-VALUE TARGET**
3. generate_jobs_json (JSON output, lines 1698-1747)
4. normalize_date_string (date parsing, lines 1437-1480)
5. Parallel fetch functions (JobSpy, Greenhouse, Lever, Google) - API integrations (lines 1278-1468)

## Last Run
23396381724 (22-03 05:22) T1,2,6,7

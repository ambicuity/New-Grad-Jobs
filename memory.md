# Test Improver Memory

## Commands
- Test: `python -m pytest tests/ -q`
- Lint: `flake8 <f> --select=E9,F63,F7,F82`
- Coverage: `pytest tests/ --cov=scripts --cov-report=term-missing`

## Coverage
Main: 47% update_jobs, 42% total, 214 tests

## PRs
#151(enrich,49), #192(dedup,25), #195(sig,35), #207(sort,25), #NEW(is_recent_job,39)

## Backlog
1. ✅ dedup (192), signals (195), sort (207), enrich (151), is_recent_job (NEW)
2. filter_jobs (master filter, lines 1555-1609) - integration tests
3. generate_jobs_json (JSON output, lines 1698-1747)
4. normalize_date_string (date parsing, lines 1437-1480)

## Last Run
23372614899 (21-03 05:09) T3,4,7

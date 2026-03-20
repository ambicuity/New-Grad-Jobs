# Test Improver Memory

## Commands
- Test: `python -m pytest tests/ -q`
- Lint: `flake8 <f> --select=E9,F63,F7,F82`
- Coverage: `pytest tests/ --cov=scripts --cov-report=term-missing`

## Coverage
Main: 47% update_jobs, 42% total, 175 tests

## PRs
#151(enrich,49), #192(dedup,25), #195(sig,35), #207(sort,25)

## Backlog
1. ✅ dedup (192), signals (195), sort (207), enrich (151)
2. filter_jobs (master filter, lines 1555-1609)
3. generate_jobs_json (JSON output, lines 1698-1747)
4. normalize_date_string (date parsing, lines 1437-1480)

## Last Run
23330128279 (20-03 05:17) T1,2,7

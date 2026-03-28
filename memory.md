# Test Improver Memory

## Cmds
`pytest tests/ -q`
`pytest --cov=scripts --cov-report=term-missing`

## Status
405 tests, 65% update_jobs.py (validated 2026-03-28)

## Open PRs
151,192,195,207,214,222 (all draft, no CI failures)

## Completed
✅ #212 is_recent_job (merged)
✅ #213 conftest.py (merged)
✅ #219 generate_jobs_json (merged)
✅ #220 (community PR, merged)

## Next
normalize_date_string (issue #48 - but already well-tested in test_date_normalization.py)
OR parallel fetch functions (needs network mocks)

## Last Run
23678322192 (T1,T4,T7) - Validated commands, checked PRs, updated activity

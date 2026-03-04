## Linked Issue

Fixes #

## Summary

<!-- What changed and why? One or two sentences max. -->

## Changes Made

<!-- List the files you changed and why. -->
- `scripts/update_jobs.py` — 
- `config.yml` — 
- `tests/` — 

## Testing

<!-- How did you verify this works locally? -->
- [ ] `python -m py_compile scripts/update_jobs.py` — no errors
- [ ] `make test` — all tests pass
- [ ] `pre-commit run --all-files` — no errors
- [ ] Scraper tested locally if applicable: `cd scripts && python update_jobs.py`

## Self-Review Checklist

- [ ] I am assigned to the linked issue (I commented `/assign` first)
- [ ] My branch is rebased on the latest `main` (`git fetch upstream && git rebase upstream/main`)
- [ ] I have NOT modified `README.md` or `jobs.json` (both are auto-generated — run `git checkout README.md` if you did)
- [ ] My changes are scoped to the described problem — no unrelated edits
- [ ] Commit messages follow Conventional Commits format (`feat:`, `fix:`, `docs:`, etc.)
- [ ] If I added a function in `update_jobs.py`, I added a test in `tests/`

## Notes for Reviewer

<!-- Anything unusual about the approach? Leave blank if straightforward. -->

---

> 🤖 **Tip:** Title your PR `@coderabbitai` and CodeRabbit will generate a compliant Conventional Commit title automatically.

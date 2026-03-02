## Pull Request Summary

<!-- Provide a concise, one-paragraph description of what this PR does and why. -->

Fixes # <!-- Issue number, e.g. Fixes #42 -->

---

## Type of Change

<!-- Mark the appropriate option(s) with an `x` -->

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that causes existing behavior to change)
- [ ] 🏗️ Refactor (code restructuring with no behavior change)
- [ ] 📝 Documentation update
- [ ] ⚙️ CI/CD or configuration change
- [ ] 🏷️ Company / data addition to `config.yml`

---

## Changes Made

<!-- List the key changes in this PR. Be specific — include function names, config keys, files. -->

- 
- 
- 

---

## Scraper Testing (if applicable)

> Skip this section if your change does not touch `scripts/update_jobs.py` or `config.yml`.

- [ ] Ran `cd scripts && python update_jobs.py` locally — completed without fatal errors
- [ ] Verified new company/API returns > 0 matching jobs in local output
- [ ] Ran `python -m py_compile scripts/update_jobs.py` — no syntax errors
- [ ] Reverted `README.md` after local testing (`git checkout README.md`)

**Sample output from local run (paste relevant lines):**
```
# Paste a few lines of output here, e.g.:
#   ✓ Found 12 jobs from Acme Corp (Greenhouse)
#   ✓ Found 4 new grad matches after filtering
```

---

## Frontend Testing (if applicable)

> Skip this section if your change does not touch `docs/`.

- [ ] Opened `docs/index.html` in a browser — no console errors
- [ ] Verified the feature/fix works end-to-end in the UI
- [ ] Tested on at least one mobile viewport (Firefox/Chrome dev tools)

---

## General Checklist

- [ ] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) format (e.g. `feat(scraper): add Workday support`)
- [ ] I have not manually edited `README.md` (it is auto-generated)
- [ ] My changes are scoped to the described problem — no unrelated modifications
- [ ] I have updated documentation if my change alters behavior or configuration
- [ ] `python test_config.py` passes

---

## Additional Notes for Reviewer

<!-- Anything the reviewer should know: edge cases, known limitations, follow-up issues, etc. -->

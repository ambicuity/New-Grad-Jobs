<!--
  PR TITLE — READ BEFORE TYPING (bot will auto-reject if wrong)
  ─────────────────────────────────────────────────────────────
  Format:  <type>(<scope>): <short summary, lowercase, no period>

  Types:
    feat     – new feature or company added
    fix      – bug fix
    docs     – documentation only
    test     – tests only, no production code
    chore    – maintenance (deps, CI, housekeeping)
    refactor – code change that is neither fix nor feature
    perf     – performance improvement

  Scopes (optional but recommended):
    scraper, config, filter, dedup, ci, docs, tests, frontend

  ✅ feat(config): add Stripe to Greenhouse companies
  ✅ fix(scraper): handle None date in normalize_date_string
  ✅ fix(filter): handle Unicode characters in company names
  ✅ test(dedup): add edge case for get_job_key with math.nan
  ✅ chore(ci): pin trivy-action to v0.28.0
  ✅ docs(contributing): clarify assignment workflow

  ❌ Update config          ← no type, no description
  ❌ Fixed the bug          ← no type, too vague
  ❌ feat: Added companies  ← capital letter, past tense

  Shortcut: title the PR "@coderabbitai" and the bot renames it correctly.
-->

## Linked Issue

Fixes #

## Summary

<!-- What changed and why? One or two sentences max. -->

## Changes Made

<!-- Which files changed and why? Delete rows that don't apply. -->

| File | What changed |
|------|-------------|
| `scripts/update_jobs.py` | |
| `config.yml` | |
| `tests/` | |
| Other | |

## Testing

<!-- How did you verify this locally before pushing? -->

- [ ] `python -m py_compile scripts/update_jobs.py` — no errors
- [ ] `make test` — all tests pass
- [ ] `pre-commit run --all-files` — clean

## Notes for Reviewer

<!-- Anything non-obvious about the approach? Leave blank if straightforward. -->

---

> **📋 What is checked automatically by CI — you do not need to self-certify these:**
>
> | Check | Enforced by |
> |-------|-------------|
> | PR title follows Conventional Commits | `bot-pr-title-check` — auto-rejects on open |
> | PR links to an assigned issue | `bot-linked-issue-enforcer` + `bot-assignment-check` |
> | `README.md` and `jobs.json` not manually edited | `bot-pr-protected-files` — hard CI failure |
> | Branch is up to date with `main` | Branch protection — merge blocked if behind |
> | Python syntax and lint (E9/F-class) | `ci.yml` — required status check |
> | All unit tests pass | `tests.yml` — required status check |
> | Pre-commit hooks (secrets, YAML, whitespace) | `pre-commit.yml` — required status check |
> | Security scan (CodeQL + Trivy) | `codeql.yml` + `trivy.yml` |


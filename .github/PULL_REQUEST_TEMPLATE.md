<!--
  PR TITLE — Conventional Commits
  ───────────────────────────────
  Format:  <type>(<scope>): <short summary, lowercase, no period>

  Types:   feat, fix, docs, test, chore, refactor, perf, ci
  Scopes (optional): scraper, config, filter, dedup, sources, outputs, site, ci, docs, tests

  ✅ feat(config): add Stripe to Greenhouse companies
  ✅ fix(filter): keep "Software Engineer I/II" titles
  ✅ test(dedup): cover cross-source match with missing location
  ✅ docs(contributing): document the Ashby config shape

  ❌ Update config          ← no type, no description
  ❌ feat: Added companies  ← capital letter, past tense

  PRs are squash-merged, so the PR title becomes the commit message.
-->

## Linked Issue

Fixes #

## Summary

<!-- What changed and why? One or two sentences. -->

## Changes Made

<!-- Which files changed and why? Delete rows that don't apply. -->

| Area | What changed |
|------|-------------|
| `config.yml` | |
| `scripts/` | |
| `site/` | |
| `tests/` | |
| Other | |

## Testing

<!-- How did you verify this locally before pushing? Tick what applies. -->

- [ ] `make test` passes (pytest, coverage floor 75%)
- [ ] `make lint` is clean (ruff + pre-commit)
- [ ] `python scripts/validate_config.py` passes (if `config.yml` changed)
- [ ] `cd site && npm run lint && npm test && npm run build` passes (if `site/` changed)
- [ ] I did **not** commit generated data (`site/public/jobs*.json`, `descriptions/`, `feed.xml`, `health.json`) or hand-edit README COUNT markers / the CATEGORY-LISTINGS block

## Notes for Reviewer

<!-- Anything non-obvious about the approach? Leave blank if straightforward. -->

---

> **What CI checks automatically — you do not need to self-certify these:**
>
> | Check | Workflow / job |
> |-------|----------------|
> | Ruff, actionlint, `config.yml` schema validation | `ci.yml` → `lint` |
> | mypy | `ci.yml` → `typecheck` |
> | pytest on Python 3.11 and 3.13, coverage floor | `ci.yml` → `test (3.11)`, `test (3.13)` |
> | Site lint, vitest, Vite build, Playwright e2e + axe | `ci.yml` → `site` |
> | Pre-commit hooks (whitespace, YAML/JSON, secrets) | `pre-commit.yml` |
> | Static security analysis | `codeql.yml` |
>
> The live site is deployed by `update-jobs.yml` after merge; PRs never deploy.

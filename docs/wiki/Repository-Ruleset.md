# 🔒 Repository Ruleset

This document defines the complete set of rules, protections, and policies governing the `New-Grad-Jobs` repository. These rules are enforced at three levels: **GitHub Rulesets** (API-level), **Repository Settings** (UI-level), and **Automation** (workflow-level).

---

## 1. Branch Protection — `main`

| Rule | Enforcement | Rationale |
|------|-------------|-----------|
| **Prevent deletion** | 🔴 Hard block | `main` can never be deleted, even by admins. |
| **Prevent force push** | 🔴 Hard block | History rewriting is forbidden. Protects the integrity of the auto-generated `README.md` and `jobs.json`. |
| **Require PR before merge** | 🟡 Enforced (0 reviews) | All changes must go through a PR. Currently set to 0 required approvals since the project is solo-maintained. Increase to 1 when a second core maintainer joins. |
| **Dismiss stale reviews on push** | ✅ Enabled | If a PR is approved and then new commits are pushed, the approval is automatically dismissed. |
| **Require conversation resolution** | ✅ Enabled | All review threads on a PR must be resolved before merging. |
| **Required status checks** | ✅ Enforced | The following CI checks **must pass** before merge: |
| | | • `Python Lint & Syntax Check` (from `ci.yml`) |
| | | • `Run Pre-commit Hooks` (from `pre-commit.yml`) |

### Bypass Actors
Only **Repository Admins** (`@ambicuity`) can bypass these rules. This is intentional for:
- Emergency hotfixes to the scraper cron job.
- Bot-generated commits (e.g., `update-jobs.yml` auto-commits to `main`).

> [!IMPORTANT]
> When a second core maintainer joins, update `required_approving_review_count` to `1` and enable `require_code_owner_review`.

---

## 2. Tag Protection — `v*`

| Rule | Enforcement | Rationale |
|------|-------------|-----------|
| **Block tag creation** | 🔴 Non-admins blocked | Only admins (or Release Please bot) can create version tags. |
| **Block tag update** | 🔴 Non-admins blocked | Tags are immutable once created. |
| **Block tag deletion** | 🔴 Non-admins blocked | Published releases cannot be silently removed. |

This ensures that `Release Please` is the only entity creating `v*` tags, and that contributors cannot tamper with the release history.

---

## 3. Merge Policy

| Setting | Value | Rationale |
|---------|-------|-----------|
| **Squash merge** | ✅ **Only allowed method** | Keeps `main` history clean with one commit per PR. |
| **Merge commit** | ❌ Disabled | Prevents messy merge bubbles in the linear history. |
| **Rebase merge** | ❌ Disabled | Avoids SHA rewriting that confuses `Release Please`. |
| **Squash commit title** | PR Title | Uses Conventional Commits format (e.g., `feat(ci): ...`). |
| **Squash commit message** | PR Body | Preserves the full PR description in the commit message. |
| **Delete branch on merge** | ✅ Enabled | Automatically cleans up feature branches after merge. |
| **Auto-merge** | ✅ Enabled | Allows Dependabot and approved PRs to merge when CI passes. |

---

## 4. Code Ownership (`CODEOWNERS`)

| Path | Owner Team | Implication |
|------|-----------|-------------|
| `*` (everything) | `@ambicuity/core-maintainers` | Default reviewer for all PRs. |
| `scripts/update_jobs.py` | `@ambicuity/core-maintainers` | Core scraper requires maintainer sign-off. |
| `config.yml` | `@ambicuity/core-maintainers` | Configuration changes affect the entire pipeline. |
| `.github/workflows/` | `@ambicuity/devops` | CI/CD changes require DevOps review. |
| `docs/`, `CONTRIBUTING.md` | `@ambicuity/tech-writers` | Documentation quality gate. |
| `SECURITY.md`, `CODEOWNERS` | `@ambicuity/security` | Security-sensitive files locked to security team. |

---

## 5. Automated Quality Gates (Pre-merge)

These are enforced via GitHub Actions workflows and `pre-commit`:

| Gate | Workflow | What it checks |
|------|----------|---------------|
| **Python syntax** | `ci.yml` | `py_compile` on all `.py` files |
| **Flake8 lint** | `ci.yml` | Errors only: `E9`, `F63`, `F7`, `F82` |
| **Config validation** | `ci.yml` | `config.yml` has required keys |
| **Unit tests** | `tests.yml` | `pytest` suite passes |
| **Pre-commit hooks** | `pre-commit.yml` | Trailing whitespace, YAML/JSON, secrets, imports |
| **CodeQL** | `codeql.yml` | Static analysis for Python security vulnerabilities |
| **Trivy** | `trivy.yml` | Dependency vulnerability scanning |
| **PR size labels** | `pr-size.yml` | Auto-labels PRs as XS/S/M/L/XL |

---

## 6. Security Controls

| Control | Status | Details |
|---------|--------|---------|
| **Secret scanning** | ✅ Enabled | GitHub scans all pushes for leaked credentials. |
| **Push protection** | ✅ Enabled | Blocks pushes that contain detected secrets. |
| **Dependabot alerts** | ✅ Enabled | Alerts on vulnerable dependencies. |
| **Gitleaks (pre-commit)** | ✅ Enabled | Local secret detection before push. |
| **Private key detection** | ✅ Enabled | Pre-commit hook blocks private keys. |
| **Workflow permissions** | Scoped | Each workflow declares minimum required permissions. |

---

## 7. Contributor Lifecycle Rules

| Rule | Mechanism | Details |
|------|-----------|---------|
| **Issue assignment** | `issue-ops.yml` | Contributors claim issues via `/assign` or `.take` commands. |
| **Inactivity ping** | `reaper-bot.yml` | After 2 days of silence, the bot checks in. |
| **Auto-unassign** | `reaper-bot.yml` | After 7 days with no response, contributors are unassigned. |
| **Slash commands** | `slash-commands.yml` | `/working`, `/need help`, `/unassign` — only assignees can use these. |
| **All-Contributors** | `all-contributors.yml` | Only OWNER/MEMBER/COLLABORATOR can trigger `@all-contributors add`. |
| **Auto-thank** | `auto-thank.yml` | Celebrates first-time merges automatically. |

---

## 8. Scaling Checklist

When you bring on a second maintainer, update these settings:

- [ ] Increase `required_approving_review_count` from `0` to `1` in the "Protect Main Branch" ruleset
- [ ] Enable `require_code_owner_review` in the ruleset
- [ ] Create GitHub teams (`core-maintainers`, `devops`, `tech-writers`, `security`) and add members
- [ ] Add the new maintainer to `CODEOWNERS` as appropriate
- [ ] Update `GOVERNANCE.md` to reflect the new team structure

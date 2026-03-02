# 🔒 Repository Ruleset

> **Audience**: You, the solo maintainer. This document explains how every rule in the repository directly protects your time, your `main` branch, and your sanity.

---

## Why These Rules Exist

As a solo maintainer, you don't have a team to catch mistakes. These rules act as your **automated second pair of eyes**:

1. **Contributors can't break `main`** — they must go through PRs with passing CI.
2. **You can push directly** — admin bypass means zero friction for you.
3. **Bots handle the chores** — auto-merge, auto-label, auto-unassign.

---

## 1. Branch Protection — `main`

**What it does for you**: Prevents contributors from pushing directly to `main`. You keep full bypass.

| Rule | What it protects you from |
|------|--------------------------|
| **Block deletion** | Nobody can accidentally delete `main`. |
| **Block force push** | Nobody can rewrite history and destroy your auto-generated `README.md`. |
| **Require PR** | Contributors must open a PR. You see the diff before it touches `main`. |
| **0 required reviews** | You don't have to approve your own PRs. Merge instantly. |
| **Dismiss stale reviews** | If Copilot/Gemini approved a PR and the contributor sneaks in new commits, the approval resets. |
| **Resolve all threads** | Contributors must address every review comment before merging. No ignored feedback. |
| **CI must pass** | `Python Lint & Syntax Check` and `Pre-commit Hooks` must be green. Catches broken Python before it hits your scraper cron. |

**Your workflow**: You push directly to `main` whenever you want. The rules only apply to contributors.

---

## 2. Tag Protection — `v*`

**What it does for you**: Nobody can create fake releases or delete your existing ones.

Only you (and Release Please) can create `v*` tags. A contributor cannot publish a version, modify a changelog entry, or delete a past release.

---

## 3. Merge Policy

**What it does for you**: Keeps your `main` history clean without any effort.

| Setting | Why it helps you |
|---------|-----------------|
| **Squash only** | Every PR becomes one clean commit. No merge bubbles, no 47-commit PRs cluttering your log. |
| **PR title as commit** | Commit messages follow Conventional Commits automatically (`feat:`, `fix:`, `docs:`). This feeds directly into Release Please for auto-changelogs. |
| **Auto-delete branches** | Merged branches are cleaned up automatically. No stale branch buildup. |
| **Auto-merge enabled** | Dependabot PRs merge themselves when CI passes. You never have to click "merge" on a patch update again. |

---

## 4. Code Ownership (`CODEOWNERS`)

**What it does for you**: You're automatically requested as a reviewer on every PR. You never miss one.

| Path | Why it's protected |
|------|-------------------|
| `scripts/update_jobs.py`, `config.yml` | The scraper engine. A bad change here kills the daily cron job. |
| `.github/workflows/` | CI/CD pipelines. A bad change here can leak secrets or break automation. |
| `SECURITY.md`, `CODEOWNERS` | Security-sensitive. Only you should touch these. |

---

## 5. Pre-merge Quality Gates

**What it does for you**: Contributors' code is automatically checked before you even open the PR. If CI is red, you don't waste time reviewing.

| Gate | What it catches |
|------|----------------|
| `py_compile` | Syntax errors in Python files. |
| `flake8` | Undefined variables, broken imports. |
| `config.yml` validation | Missing required keys that would crash the scraper. |
| `pytest` | Broken categorization or filtering logic. |
| `pre-commit` | Trailing whitespace, mixed line endings, leaked secrets. |
| `CodeQL` | Security vulnerabilities in Python code. |
| `Trivy` | Vulnerable dependencies. |

---

## 6. Security Controls

**What it does for you**: Catches secrets and vulnerabilities automatically so you don't have to audit every PR manually.

| Control | What it catches |
|---------|----------------|
| **Secret scanning** | API keys, tokens, passwords accidentally committed. |
| **Push protection** | Blocks pushes containing detected secrets *before* they hit GitHub. |
| **Gitleaks** | Pre-commit local secret detection. |
| **Dependabot alerts** | Notifies you when a dependency has a known CVE. |

---

## 7. Contributor Lifecycle

**What it does for you**: The issue tracker is self-cleaning. You don't have to chase contributors.

| Rule | What it saves you |
|------|-------------------|
| **Auto-assign via `/assign`** | Contributors claim issues themselves. You don't assign manually. |
| **Ping after 2 days** | Bot checks in with idle contributors. You don't write "hey, still working on this?" |
| **Auto-unassign after 7 days** | Stale contributors are removed. Issues are freed up for others. |
| **Slash commands** | Only assignees can use `/working` and `/need help`. Prevents random users from messing with labels. |
| **Auto-thank on merge** | Bot celebrates their first PR. You don't have to write "thanks!" on every merge. |

---

## 8. When You Scale

When a second maintainer joins, flip these three switches:

1. **Settings → Rules → Protect Main Branch** → Set `required_approving_review_count` to `1`
2. **Same ruleset** → Enable `require_code_owner_review`
3. **GitHub Teams** → Create `core-maintainers`, `devops`, `tech-writers` teams and populate them

Everything else is already designed to scale.

---

## Quick Reference: Your Admin Powers

| Action | Can you do it? | Can contributors do it? |
|--------|:-------------:|:-----------------------:|
| Push directly to `main` | ✅ | ❌ |
| Force push `main` | ✅ | ❌ |
| Create `v*` tags | ✅ | ❌ |
| Merge PRs without reviews | ✅ | ✅ (0 reviews required) |
| Bypass CI checks | ✅ | ❌ |
| Delete branches | ✅ | ❌ (auto-deleted on merge) |

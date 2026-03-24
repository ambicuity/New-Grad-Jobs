# Contributing to New Grad Jobs

First off — **thank you** for taking the time to contribute! 🎉

> [!TIP]
> **TL;DR Quick Start (3 steps):**
> 1. **Find** an issue tagged [`good first issue`](https://github.com/ambicuity/New-Grad-Jobs/labels/good%20first%20issue) and comment `/assign`
> 2. **Setup** your local environment: `git clone` → `make setup` → `make test` (all green)
> 3. **Ship** your change on a branch, then open a PR with `Fixes #<issue-number>` in the description
>
> Full details in the sections below.

New Grad Jobs is a fully automated job aggregator that helps new graduates find their first tech role. Every contribution — whether it's submitting a missing job, fixing a bug in the scraper, improving the frontend, or helping with docs — directly helps thousands of job seekers.

> **Heads-up:** `README.md` is auto-generated every 5 minutes by GitHub Actions. **Never edit it manually** — your changes will be overwritten.

---

## Table of Contents

1. [Ways to Contribute](#1-ways-to-contribute)
2. [The AI-Assisted Workflow](#2-the-ai-assisted-workflow-highly-recommended)
3. [Local Development Setup](#3-local-development-setup)
4. [Full Contribution Lifecycle](#4-full-contribution-lifecycle)
   - [Phase 1: Claiming the Issue](#phase-1-claiming-the-issue--alignment)
   - [Phase 2: Git Hygiene & Local Setup](#phase-2-git-hygiene--local-setup)
   - [Phase 3: Development & Code Standards](#phase-3-development--code-standards)
   - [Phase 4: Conflict Prevention & Committing](#phase-4-conflict-prevention-the-rebase--committing)
   - [Phase 5: Opening the Pull Request](#phase-5-opening-the-pull-request)
   - [Phase 6: Code Review & History Cleanup](#phase-6-code-review--history-cleanup)
5. [Project Architecture](#5-project-architecture)
6. [Branching & Commit Standards](#6-branching--commit-standards)
7. [Pull Request Checklist](#7-pull-request-checklist)
8. [Reporting Issues](#8-reporting-issues)
9. [Adding a Company or Job](#9-adding-a-company-or-job)
10. [Code Style](#10-code-style)
11. [Good First Issues](#11-good-first-issues)
12. [Bot Commands (Slash Commands)](#12-bot-commands-slash-commands)
13. [When Will My PR Be Merged?](#13-when-will-my-pr-be-merged)
14. [Security & Signed Releases](#14-security--signed-releases)

---

## 1. Ways to Contribute

We organize work into clear tiers. If you are new here, look for issues tagged appropriately to get started:

- [`good first issue`](https://github.com/ambicuity/New-Grad-Jobs/labels/good%20first%20issue) — Great for your first PR. Small, scoped, and well-defined tasks (e.g., adding a missing company endpoint).
- [`help wanted`](https://github.com/ambicuity/New-Grad-Jobs/labels/help%20wanted) — Medium complexity tasks where maintainer support is available.
- [`architecture proposal`](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=architecture_proposal.yml) — For proposing major structural changes. Discuss these before writing code!

**Non-coding contributions:**
- 🐛 **Bug report** or 🆕 **Missing job**: Use our [Issue Templates](https://github.com/ambicuity/New-Grad-Jobs/issues/new/choose).
- 🌐 **Translation**: Add a translated README (e.g. `README.zh-CN.md`).

---

## 2. The AI-Assisted Workflow (Highly Recommended)

We are a solo-maintained repository, which means we rely heavily on AI to help manage contributions. We use **CodeRabbit** as our Lead Architect.

To write code for this repository, follow this exact workflow:

1. **Open an Issue**: Use the [AI-Assisted Task](https://github.com/ambicuity/New-Grad-Jobs/issues/new/choose) template or add the `plan-me` label to a Bug/Feature issue.
2. **Wait 10 Minutes**: CodeRabbit will automatically scan our entire codebase and reply to your issue with a step-by-step Implementation Plan.
3. **Refine the Plan**: If the plan looks wrong or you have questions, reply to the issue with `@coderabbitai clarify <your question>`. CodeRabbit will update the plan.
4. **Write the Code**: You can hand CodeRabbit's exact plan to Cursor, GitHub Copilot, or write it yourself.
5. **Open a PR**: You **must** link the PR to the issue (`Fixes #123`).
6. **Auto-Title your PR**: Make the title of your PR literally just `@coderabbitai`. CodeRabbit will read your code and automatically rename the PR to a perfect Conventional Commit title (e.g., `feat: add workday scraper`).
7. **The Gatekeeper**: CodeRabbit will cross-examine your code against its original plan. If you skipped tests or cut corners, it will block your PR before a human ever looks at it.

---

## 3. Local Development Setup

We believe in a "single command setup". You do not need to decipher a 10-page guide to run this project.

### Prerequisites

- Python **3.11+**
- Git
- `make`

### The Single Command

```bash
# 1. Fork the repo on GitHub, then clone YOUR fork
git clone https://github.com/<your-username>/New-Grad-Jobs.git
cd New-Grad-Jobs

# 2. Run the automated setup
make setup
```

The `make setup` command automatically:
1. Creates a Python virtual environment (`.venv`).
2. Installs runtime dependencies from `requirements.txt` and dev/test tooling from `pyproject.toml` (`.[dev]`, including `pytest` and `pytest-cov`).
3. Configures `pre-commit` hooks to run on every commit.

*(Alternatively, if you use DevContainers, just open this repository in VS Code and click "Reopen in Container". Everything is pre-configured!)*

### Verification

```bash
# Activate the environment
source .venv/bin/activate

# Run the tests to ensure everything is green
make test

# To run the scraper locally (takes 4-6 minutes)
make run
```

### Key local files

| File | Role | Edit? |
|------|------|-------|
| `config.yml` | Central configuration — companies, filters, search terms | ✅ Yes |
| `scripts/update_jobs.py` | Core scraper + filterer + README generator | ✅ Yes |
| `.github/workflows/update-jobs.yml` | GitHub Actions job | ✅ Yes (test via manual trigger) |
| `requirements.txt` | Python dependencies | ✅ Yes |
| `docs/` | GitHub Pages website (HTML/CSS/JS) | ✅ Yes |
| `README.md` | **AUTO-GENERATED** — never edit manually | ❌ Never |

---

## 4. Full Contribution Lifecycle

This section documents the **end-to-end lifecycle** of a contribution, from claiming an issue to getting your PR merged with a clean history. Follow every phase in order.

---

### Phase 1: Claiming the Issue & Alignment

**Before writing a single line of code**, you must claim and fully understand the issue.

#### 1.1 — Claim the issue

Comment on the issue with the bot command:

```
/assign
```

This assigns the issue to you and signals to other contributors that it is being worked on. Do not start work until you are assigned — it prevents duplicate effort.

#### 1.2 — Clarify scope before coding

Read the issue description carefully. If anything is ambiguous — especially for `architecture` or `help wanted` issues — ask clarifying questions in the issue thread **before** writing code.

Good questions to ask:
- Is the expected behavior clearly defined?
- Are there specific files or functions I should or should not touch?
- Are there existing tests I must not break?

> **Rule:** The cost of a clarifying question is 5 minutes. The cost of building the wrong thing is a reverted PR.

---

### Phase 2: Git Hygiene & Local Setup

This phase ensures your local environment is correctly isolated from the upstream repository.

#### 2.1 — Fork and clone

If you haven't already, fork the repo on GitHub, then clone **your fork** (not the upstream):

```bash
git clone https://github.com/<your-username>/New-Grad-Jobs.git
cd New-Grad-Jobs
```

#### 2.2 — Add the upstream remote (CRITICAL)

```bash
git remote add upstream https://github.com/ambicuity/New-Grad-Jobs.git
```

Verify the remotes are set up correctly:

```bash
git remote -v
# Expected output:
# origin    https://github.com/<your-username>/New-Grad-Jobs.git (fetch)
# origin    https://github.com/<your-username>/New-Grad-Jobs.git (push)
# upstream  https://github.com/ambicuity/New-Grad-Jobs.git (fetch)
# upstream  https://github.com/ambicuity/New-Grad-Jobs.git (push)
```

You will **never** push to `upstream`. `upstream` is read-only — it is only used to pull the latest changes from the maintainer's repository.

#### 2.3 — Create a dedicated feature branch

**Never work on `main`**. Create a short-lived, descriptively named branch:

```bash
git checkout -b feat/add-workday-microsoft
# or
git checkout -b fix/issue-123-greenhouse-timeout
# or
git checkout -b docs/update-contributing-guide
```

Branch naming convention:

| Prefix | When to use |
|--------|-------------|
| `feat/` | New feature or new company scraper |
| `fix/` | Bug fix |
| `docs/` | Documentation only |
| `chore/` | Maintenance (deps, CI config, etc.) |

---

### Phase 3: Development & Code Standards

#### 3.1 — Run the local environment first

Before writing code, confirm the test suite is green on your machine:

```bash
source .venv/bin/activate
make test
```

If tests fail before your changes, **stop and report it** — do not proceed on a broken base.

#### 3.2 — Implement only what the issue describes

Stay strictly within the scope of the issue. Do **not**:
- Rename unrelated variables or refactor functions you didn't touch.
- Fix style issues in lines you didn't author.
- Add unrelated features "while you're in there".

Code review scope creep is one of the most common reasons PRs are rejected.

#### 3.3 — Write tests for your changes

If your change adds or modifies any function in `scripts/update_jobs.py`, add a corresponding test in `tests/`:

```bash
# Run only your new tests to confirm they pass
pytest tests/test_your_module.py -v

# Run the full suite to confirm you haven't broken anything
make test
```

Tests must be **deterministic** — inject `datetime` via parameters. No live network calls in tests.

#### 3.4 — Run the pre-commit hooks

Our pre-commit suite runs whitespace checks, YAML/JSON validation, import sorting, and secret detection. Run it manually before committing:

```bash
pre-commit run --all-files
```

Fix any errors it reports before proceeding.

#### 3.5 — Syntax and style check

```bash
# Syntax check (required — must produce zero output)
python -m py_compile scripts/update_jobs.py

# Style check (optional but recommended)
python -m flake8 scripts/ --max-line-length=120
```

---

### Phase 4: Conflict Prevention (The Rebase) & Committing

This is the most commonly skipped phase — and the one that causes the most pain at review time.

#### 4.1 — Fetch and rebase onto upstream (CRITICAL)

Before pushing your branch, always sync with the upstream `main`:

```bash
# Step 1: Fetch all changes from the upstream repository
git fetch upstream

# Step 2: Rebase your feature branch on top of upstream/main
git rebase upstream/main
```

> **Why rebase instead of merge?** Rebasing places your commits on top of the latest upstream commits, producing a clean, linear history with no merge commits. Our PRs are squash-merged, so a clean rebase prevents conflicts at merge time.

If you encounter rebase conflicts:

```bash
# After resolving conflicts in the affected files:
git add <resolved-files>
git rebase --continue

# To abort the rebase and return to your previous state:
git rebase --abort
```

#### 4.2 — Write atomic, logical commits

Each commit should represent one logical unit of work. Avoid:
- `"fix"` (too vague)
- `"WIP"` / `"temp"` commits
- Mixing unrelated changes in a single commit

Good commit examples:
```
feat(config): add Microsoft to Workday scraper targets
fix(greenhouse): handle paginated response beyond 100 jobs
docs(contributing): add upstream remote setup instructions
test(filter): add edge case for None location field
```

We enforce [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary in imperative mood>

Types:
  feat     – new feature or new company added to scraper
  fix      – bug fix
  docs     – documentation only
  test     – adding missing tests
  chore    – maintenance (deps, CI config, etc.)
  refactor – code change that is neither a fix nor a feature
```

---

### Phase 5: Opening the Pull Request

#### 5.1 — Push your branch to your fork

```bash
git push origin feat/add-workday-microsoft
```

#### 5.2 — Open the PR against the correct base branch

Open the PR against **`main`** in the upstream repository (`ambicuity/New-Grad-Jobs`). Do **not** target your own fork's `main`.

GitHub will default to the correct base if your fork is set up properly.

#### 5.3 — Use the PR template

Fill out the PR description template completely. Partial descriptions slow down review.

For scraper changes, include:
- Which API/source was modified
- Sample output showing jobs found (or a zero-output explanation)
- Whether any timeouts or errors were seen in local testing

#### 5.4 — Link the issue to auto-close it

Include one of these in the PR description to automatically close the issue when the PR is merged:

```
Fixes #123
Closes #456
Resolves #789
```

This is a **hard requirement**. Unlinked PRs will be asked to add the link before review begins.

#### 5.5 — Title your PR correctly (most common mistake)

> [!IMPORTANT]
> **The bot will reject your PR automatically if the title is wrong.** It will post a
> comment explaining the correct format. Fix the title and the check will re-run.

##### Format

```
<type>(<scope>): <short summary in imperative mood, lowercase, no period>
```

##### Types — pick the one that matches your change

| Type | Use when… | Example |
|------|-----------|---------|
| `feat` | You added a new feature or new company | `feat(config): add Stripe to Greenhouse companies` |
| `fix` | You fixed a bug | `fix(scraper): handle None date in normalize_date_string` |
| `docs` | Documentation only, no code change | `docs(contributing): clarify assignment workflow` |
| `test` | Added or fixed tests, no production code change | `test(filter): add edge case for empty location string` |
| `chore` | Maintenance — deps, CI config, housekeeping | `chore(ci): bump actions/checkout from v3 to v4` |
| `refactor` | Code change that is neither a fix nor a feature | `refactor(scraper): extract date parsing into helper` |
| `perf` | Performance improvement | `perf(scraper): cache company tier lookups with lru_cache` |

##### Scopes — optional but recommended

Use the area of the repo your change touches:

| Scope | When to use |
|-------|-------------|
| `scraper` | Changes to `scripts/update_jobs.py` |
| `config` | Changes to `config.yml` |
| `filter` | Changes to `filter_jobs()` or related logic |
| `dedup` | Changes to `deduplicate_jobs()` or `get_job_key()` |
| `ci` | GitHub Actions workflow changes |
| `docs` | Markdown files, `docs/` website |
| `tests` | Files under `tests/` |
| `frontend` | HTML/CSS/JS in `docs/` |

##### Real examples from this repo

```
✅ feat(config): add Palantir and Two Sigma to Greenhouse companies
✅ fix(scraper): skip jobs with NaN posted_at instead of crashing
✅ fix(filter): handle Unicode characters in company names
✅ docs(readme): update contribution steps in CONTRIBUTING.md
✅ test(dedup): add test for get_job_key with math.nan input
✅ chore(ci): pin trivy-action to v0.28.0 for reproducibility
✅ refactor(scraper): move sponsorship detection to detect_sponsorship_flags()
✅ perf(scraper): reduce max_workers from 300 to 100 for Workday endpoints

❌ Update config                          ← no type, no scope
❌ Fixed the bug                          ← no type, too vague
❌ feat: Added new companies to the list  ← not imperative mood, has capital letter
❌ WIP: testing stuff                     ← not a valid type
```

##### Shortcut: let the bot do it

Name your PR exactly `@coderabbitai` as the title. CodeRabbit will read your
diff and rename it to a correct Conventional Commit title automatically within
a few seconds of opening the PR.

---

### Phase 6: Code Review & History Cleanup

#### 6.1 — Responding to review feedback

When a maintainer or CodeRabbit requests changes:
- Respond to **every comment**, even if just to acknowledge.
- If you disagree with a suggestion, explain your reasoning clearly. We prefer a short discussion over a silent revert.
- Do not close the PR and open a new one to avoid review comments.

#### 6.2 — Interactive rebase to squash messy commits (CRITICAL)

After rounds of review, your branch will likely have accumulated noisy commits like `"address review feedback"`, `"fix typo in test"`, `"forgot to add import"`. Before your PR is merged, clean these up:

```bash
# Squash all commits back to a clean set of logical commits
git rebase -i upstream/main
```

In the interactive editor, `pick` your first meaningful commit and `squash` or `fixup` the rest:

```
pick a1b2c3d feat(config): add Microsoft to Workday targets
fixup d4e5f6g fix: address review feedback
fixup 7h8i9j0 fix: forgot to add import
```

The result should be one (or a small number of) clean, atomic commits with proper Conventional Commit messages.

#### 6.3 — Force-push safely after rebasing

After rebasing or squashing, you must force-push your branch. Always use `--force-with-lease` — it is a safety net that will refuse to overwrite commits someone else may have pushed to your branch:

```bash
git push origin feat/add-workday-microsoft --force-with-lease
```

> **Never use `git push --force`** without `--lease`. Bare `--force` can destroy commits without warning.

The PR will automatically update with the cleaned history. No need to close and reopen it.

---

## 5. Project Architecture

```
New-Grad-Jobs/
├── scripts/
│   └── update_jobs.py          # Main scraper (~2000 lines)
│       ├── create_optimized_session()   # Connection pooling
│       ├── fetch_greenhouse_jobs()      # Greenhouse API
│       ├── fetch_lever_jobs()           # Lever API
│       ├── fetch_google_jobs()          # Google Careers API
│       ├── fetch_jobspy_jobs()          # JobSpy (Indeed/LinkedIn)
│       ├── filter_jobs()               # Eligibility filter
│       ├── categorize_job()            # Role categorization
│       └── generate_readme()           # README table output
├── config.yml                  # Companies, filters, search configuration
├── jobs.json                   # Full jobs dataset (auto-generated)
├── docs/                       # GitHub Pages frontend
│   ├── index.html              # Main job board UI
│   ├── app.js                  # Frontend logic (Vanilla JS)
│   ├── styles.css              # Styling
│   └── jobs.json               # Mirrored jobs data for Pages
└── .github/
    ├── workflows/
    │   └── update-jobs.yml     # Runs every 5 minutes
    └── ISSUE_TEMPLATE/         # Structured issue forms
```

**Data flow:** `config.yml` → Multi-source parallel fetch → Filter/deduplicate → Categorize → `jobs.json` + `README.md`

---

## 6. Branching & Commit Standards

We use **GitHub Flow** (Trunk-based development). This means:
1. `main` is always deployable and green.
2. All feature work happens in short-lived branches created from `main`.

When your PR is merged, it will be "Squash and Merged" to maintain a single atomic commit per feature. This is why clean, rebased history matters — the single squash commit is what lands in `main`.

---

## 7. Pull Request Checklist

Before opening a PR, confirm every item below:

- [ ] I have commented `/assign` on the issue and have been officially assigned.
- [ ] I have added `upstream` as a remote (`git remote add upstream https://github.com/ambicuity/New-Grad-Jobs.git`).
- [ ] I am working on a feature branch — **not** on `main`.
- [ ] I ran `git fetch upstream && git rebase upstream/main` before pushing.
- [ ] `python -m py_compile scripts/update_jobs.py` passes with no errors.
- [ ] `make test` passes with no failures.
- [ ] `pre-commit run --all-files` passes with no errors.
- [ ] I have reverted `README.md` if it was modified during testing: `git checkout README.md`.
- [ ] I have verified any scraper changes locally (`cd scripts && python update_jobs.py`).
- [ ] My changes are scoped to the described problem — no unrelated modifications.
- [ ] Commit messages follow the Conventional Commits format.
- [ ] The PR is linked to the issue with `Fixes #<number>` in the description.
- [ ] The PR is opened against `main` in the **upstream** repository, not my fork.
- [ ] I have updated relevant documentation (`config.yml` comments, `JOB_SCRAPING_APIS.md`, etc.) if applicable.

---

## 8. Reporting Issues

Use the structured issue templates:

- **[🤖 AI-Assisted Task](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=01_ai_assisted_task.yml)** — Start here! CodeRabbit will analyze the repo and generate a step-by-step coding plan for your idea.
- **[Bug Report](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=bug_report.yml)** — broken links, scraper failures, incorrect listings
- **[Feature Request](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=feature_request.yml)** — suggest an improvement
- **[New Role](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=new_role.yml)** — submit a job our scraper missed
- **[Edit Role](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=edit_role.yml)** — report a closed or incorrect listing
- **[Architecture Proposal](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=architecture_proposal.yml)** — major structural changes

> 💬 Not sure if it's an issue? Start a [Discussion](https://github.com/ambicuity/New-Grad-Jobs/discussions) instead.

> 🔒 **Security issues**: Please email `contact@riteshrana.engineer` — **do not** open a public issue. See [SECURITY.md](./SECURITY.md).

---

## 9. Adding a Company or Job

### Adding a company to the scraper (code contribution)

The scraper is configured via `config.yml`. To add a new company:

1. Identify the company's ATS (Applicant Tracking System): Greenhouse, Lever, or Workday
2. Find the API endpoint:
   - **Greenhouse**: `https://api.greenhouse.io/v1/boards/<slug>/jobs`
   - **Lever**: `https://api.lever.co/v0/postings/<slug>`
3. Add the entry to the appropriate section in `config.yml`
4. Test locally with `cd scripts && python update_jobs.py`
5. Submit a PR with the addition

### Submitting a single missing job (no code required)

Use the **[New Role issue template](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=new_role.yml)**.

---

## 10. Code Style

- **Python**: Follow [PEP 8](https://pep8.org/). Use type hints for all new functions.
- **JavaScript** (`docs/app.js`, `docs/stats.js`): Vanilla JS, no frameworks. Follow existing patterns.
- **YAML** (`config.yml`): Use 2-space indentation.
- **Markdown**: Use ATX-style headers (`#`, `##`), not underline style.

Run a quick style check before committing:
```bash
python -m py_compile scripts/update_jobs.py   # Syntax
python -m flake8 scripts/ --max-line-length=120 --ignore=E501  # Style (optional)
```

---

## 11. Good First Issues

New here? Look for issues tagged:

- [`good first issue`](https://github.com/ambicuity/New-Grad-Jobs/labels/good%20first%20issue) — small, self-contained tasks
- [`help wanted`](https://github.com/ambicuity/New-Grad-Jobs/labels/help%20wanted) — medium tasks where maintainer support is available
- [`documentation`](https://github.com/ambicuity/New-Grad-Jobs/labels/documentation) — docs improvements (no coding required)

**Internationalization (i18n)**: Want to translate the README? Add `README.<lang>.md` (e.g., `README.zh-CN.md`) and open a PR. No coding skills required — just fluency in the target language!

---

## 12. Bot Commands (Slash Commands)

Our repository uses bots to automate the contributor workflow. You can interact with them by posting a comment on any issue:

| Command | What it does |
|---------|-------------|
| `/assign` or `.take` | Assigns the issue to you and marks it as in-progress |
| `/working` | Tells the bot you're still actively working (resets inactivity timer) |
| `/need help` | Pings the maintainer and adds a `help-needed` label |
| `/unassign` | Removes yourself from the issue so someone else can pick it up |

### How the lifecycle works

1. **Claim an issue** → Comment `/assign` on any unassigned issue.
2. **Work on it** → You have 7 days to open a PR. If you need more time, just comment `/working`.
3. **Stuck?** → Comment `/need help` and a maintainer will assist you.
4. **Life happens?** → Comment `/unassign` to gracefully step away. No hard feelings.
5. **Went silent?** → After 2 days of inactivity, the bot will check in. After 7 days with no response, it will gently unassign you so someone else can help.

---

## 13. When Will My PR Be Merged?

The maintainer (`@ambicuity`) merges PRs manually after reviewing. Here is the exact decision matrix:

### ✅ Ready to Merge — all of the following must be true:

| Check | Required? |
|-------|-----------|
| All required CI checks are green | ✅ Yes |
| At least one maintainer approval (`@ambicuity`) | ✅ Yes |
| PR body contains `Fixes #N` / `Closes #N` | ✅ Yes |
| PR title follows Conventional Commits format | ✅ Yes |
| No merge conflicts with `main` | ✅ Yes |
| PR has been open ≥ 24 hours (except trivial config additions) | ✅ Yes |

### ⚠️ Partial Red — Some failures are acceptable:

| Failing Check | Can We Merge? | Why |
|---------------|--------------|-----|
| Codecov upload | ✅ Yes | Informational only — token issues don't block correctness |
| Check Dead Links (on config-only PRs) | ✅ Yes | README link checker fires false positives on `config.yml` PRs |
| All-Contributors bot | ✅ Yes | Community recognition — never blocks a merge |

### ❌ Hard Blockers — Do NOT merge:

| Failing Check | Why It Blocks |
|---------------|--------------|
| `CI — Lint & Validate` | Syntax errors or broken config will break the scraper |
| `Test Suite (pytest)` | Failing tests = known regression |
| `Code Hygiene (Pre-commit)` | Secrets, malformed YAML, broken imports |
| `CodeQL Security Scan` | Security vulnerability in merged code |
| `Trivy` | Known dependency CVE at CRITICAL/HIGH severity |
| `Validate Job Submissions` | Malformed `jobs.json` will break GitHub Pages |
| `PR Title Check` | PR cannot be auto-merged without a clean commit message |
| `Linked Issue Enforcer` | Every community PR must be tied to a tracked issue |
| Merge conflict | Cannot squash-merge a conflicted PR |

### Auto-Merge (Dependabot)

Dependabot patch and minor updates are **automatically approved and squash-merged** once all CI checks pass. No manual action needed. Major version bumps require explicit maintainer review.

---

## 14. Security & Signed Releases

New Grad Jobs takes supply chain security seriously. We have achieved a **10/10** on the OpenSSF Scorecard for Signed Releases!

### What Does This Mean for You?
Every release of this repository is automatically packaged and cryptographically signed using **Sigstore** (keyless OIDC signing).
When you download a release from our Releases page, you'll also find a `.sig` file alongside the `.tar.gz` archive.

If you are just contributing code, you don't need to do anything! Our automated `release-please.yml` workflow takes care of the signing automatically whenever a new version is published.

---


## 🏆 Contributors

Every contribution is recognized! When your PR is merged, a maintainer will add you to our [Contributors Hall of Fame](./CONTRIBUTORS.md).

---
## 🏆 Hall of Fame Credit

Contributors are automatically added to the Hall of Fame using the workflow:
`.github/workflows/auto-thank.yml`.

### When does it happen?
- After your Pull Request (PR) is successfully merged.

### When might it not work?
- If the PR is created by a bot
- If the GitHub Actions workflow fails
- If the workflow is skipped due to configuration conditions

### What should you do if your credit does not appear?
- Comment on your PR or the related issue
- A maintainer will review and add you manually if needed
---

Thank you for helping new graduates land their first job. Every contribution matters. 🚀

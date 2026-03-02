# Contributing to New Grad Jobs

First off — **thank you** for taking the time to contribute! 🎉

New Grad Jobs is a fully automated job aggregator that helps new graduates find their first tech role. Every contribution — whether it's submitting a missing job, fixing a bug in the scraper, improving the frontend, or helping with docs — directly helps thousands of job seekers.

> **Heads-up:** `README.md` is auto-generated every 5 minutes by GitHub Actions. **Never edit it manually** — your changes will be overwritten.

---

## Table of Contents

1. [Ways to Contribute](#1-ways-to-contribute)
2. [Local Development Setup](#2-local-development-setup)
3. [Project Architecture](#3-project-architecture)
4. [Branching & Commit Standards](#4-branching--commit-standards)
5. [Pull Request Guidelines](#5-pull-request-guidelines)
6. [Reporting Issues](#6-reporting-issues)
7. [Adding a Company or Job](#7-adding-a-company-or-job)
8. [Code Style](#8-code-style)
9. [Good First Issues](#9-good-first-issues)

---

## 1. Ways to Contribute (The Sprints)

We organize work into clear tiers. If you are new here, look for issues tagged appropriately to get started:

- [`good first issue`](https://github.com/ambicuity/New-Grad-Jobs/labels/good%20first%20issue) — Great for your first PR. Small, scoped, and well-defined tasks (e.g., adding a missing company endpoint).
- [`help wanted`](https://github.com/ambicuity/New-Grad-Jobs/labels/help%20wanted) — Medium complexity tasks where maintainer support is available.
- [`architecture proposal`](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=architecture_proposal.yml) — For proposing major structural changes. Discuss these before writing code!

**Non-coding contributions:**
- 🐛 **Bug report** or 🆕 **Missing job**: Use our [Issue Templates](https://github.com/ambicuity/New-Grad-Jobs/issues/new/choose).
- 🌐 **Translation**: Add a translated README (e.g. `README.zh-CN.md`).

---

## 2. Local Development Setup (The Setup)

We believe in a "single command setup". You do not need to decipher a 10-page guide to run this project.

### Prerequisites

- Python **3.11+**
- Git
- `make`

### The Single Command

```bash
# 1. Fork the repo, clone it, and enter the directory
git clone https://github.com/<your-username>/New-Grad-Jobs.git
cd New-Grad-Jobs

# 2. Run the automated setup
make setup
```

The `make setup` command automatically:
1. Creates a Python virtual environment (`.venv`).
2. Installs all project and testing dependencies.
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

## 3. Project Architecture

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

## 4. Branching & Commit Standards (The Workflow)

We use **GitHub Flow** (Trunk-based development). This means:
1. `main` is always deployable and green.
2. All feature work happens in short-lived branches created from `main`.

### Git Workflow: Rebase > Merge

To keep our Git history clean and linear, we prefer **rebasing** over merge commits when syncing your feature branch with `main`.

```bash
# When main has new commits, update your branch:
git fetch origin
git rebase origin/main
```

When your PR is merged, it will be "Squash and Merged" to maintain a single atomic commit per feature.

### Branch naming

Create a branch from `main` using one of these prefixes:

```
feat/add-workday-scraper
fix/issue-123-greenhouse-timeout
docs/update-contributing-guide
chore/pin-dependency-versions
```

### Commit messages (Conventional Commits)

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

Types:
  feat     – new feature or new company added to scraper
  fix      – bug fix
  docs     – documentation only
  chore    – maintenance (deps, CI config, etc.)
```

This format enables our **Semantic Release** pipeline to automatically generate changelogs and version bumps.

---

## 5. Pull Request Guidelines

Before opening a PR, please confirm:

- [ ] `python -m py_compile scripts/update_jobs.py` passes with no errors
- [ ] `python test_config.py` passes
- [ ] You have tested any scraper changes locally (via `cd scripts && python update_jobs.py`)
- [ ] You have reverted `README.md` (`git checkout README.md`) if it was modified during testing
- [ ] Your changes are scoped to the described problem — no unrelated modifications
- [ ] Your commit messages follow the Conventional Commits format above
- [ ] You have updated relevant documentation (`config.yml` comments, `JOB_SCRAPING_APIS.md`, etc.)

**For scraper changes**, please include in your PR description:
- Which API/source was modified
- Sample output showing jobs found (or zero-output explanation)
- Whether any timeouts or errors were seen in local testing

---

## 6. Reporting Issues

Use the structured issue templates:

- **[Bug Report](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=bug_report.yml)** — broken links, scraper failures, incorrect listings
- **[New Role](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=new_role.yml)** — submit a job our scraper missed
- **[Edit Role](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=edit_role.yml)** — report a closed or incorrect listing
- **[Feature Request](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=feature_request.yml)** — suggest an improvement
- **[Architecture Proposal](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=architecture_proposal.yml)** — major structural changes

> 💬 Not sure if it's an issue? Start a [Discussion](https://github.com/ambicuity/New-Grad-Jobs/discussions) instead.

> 🔒 **Security issues**: Please email `contact@riteshrana.engineer` — **do not** open a public issue. See [SECURITY.md](./SECURITY.md).

---

## 7. Adding a Company or Job

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

## 8. Code Style

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

## 9. Good First Issues

New here? Look for issues tagged:

- [`good first issue`](https://github.com/ambicuity/New-Grad-Jobs/labels/good%20first%20issue) — small, self-contained tasks
- [`help wanted`](https://github.com/ambicuity/New-Grad-Jobs/labels/help%20wanted) — medium tasks where maintainer support is available
- [`documentation`](https://github.com/ambicuity/New-Grad-Jobs/labels/documentation) — docs improvements (no coding required)

**Internationalization (i18n)**: Want to translate the README? Add `README.<lang>.md` (e.g., `README.zh-CN.md`) and open a PR. No coding skills required — just fluency in the target language!

---

Thank you for helping new graduates land their first job. Every contribution matters. 🚀

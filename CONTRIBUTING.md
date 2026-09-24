# Contributing to New Grad Jobs

Thanks for helping new graduates find their first tech role. This guide covers everything
you need to send a good pull request. It is written for humans. AI coding agents should
also read [AGENTS.md](AGENTS.md).

> [!TIP]
> **Quick start**
> 1. Pick an issue (or open one) and comment that you are working on it.
> 2. `git clone` your fork → `make setup` → `make test` (all green).
> 3. Make the change on a branch, then open a PR with `Fixes #<issue>` in the description.

## Contents

1. [Ways to contribute](#1-ways-to-contribute)
2. [How the project works](#2-how-the-project-works)
3. [Development setup](#3-development-setup)
4. [Adding a company](#4-adding-a-company)
5. [Adding a source or a category](#5-adding-a-source-or-a-category)
6. [Testing](#6-testing)
7. [Lint, formatting and pre-commit](#7-lint-formatting-and-pre-commit)
8. [Commits and pull requests](#8-commits-and-pull-requests)
9. [Issues and labels](#9-issues-and-labels)
10. [Things to never do](#10-things-to-never-do)

---

## 1. Ways to contribute

- **Report a missing or closed job:** use the
  [New Role](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=new_role.yml) or
  [Edit Role](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=edit_role.yml)
  forms. No code needed.
- **Add a company** the scraper does not cover yet (see [section 4](#4-adding-a-company)).
  This is the most common first PR.
- **Fix a bug** in the scraper, the filters or the site.
- **Improve docs:** this file, [docs/](docs/), or a translated README (`README.<lang>.md`).
- **Propose a larger change** with the
  [Architecture Proposal](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=architecture_proposal.yml)
  form *before* writing code.

This is a solo-maintained project. PRs are usually reviewed within 1–2 weeks, and bug fixes
come first. Before starting non-trivial work, comment on the issue so the maintainer can
confirm the approach and nobody duplicates it. Issues are not formally assigned.

## 2. How the project works

```
config.yml ─▶ scripts/update_jobs.py (ngj package)
               fetch (Greenhouse, Lever, Ashby, Workday, JobSpy) → dedup → filter → enrich
               └─▶ site/public/{jobs.json, jobs-index.json, descriptions/, feed.xml, health.json}
                    └─▶ vite build (site/) ─▶ GitHub Pages: https://jobs.riteshrana.engineer
```

- `.github/workflows/update-jobs.yml` runs this about **every 30 minutes**. It scrapes,
  checks artifact integrity, builds the site and deploys it with `deploy-pages`.
- Generated data is **not committed**. The only files CI commits back are `README.md`
  (job counts and per-category tables) and `data/market-history.json`.
- `README.md` is hand-edited *except* the `<!-- COUNT:* -->` markers, the "Last updated"
  line and the `CATEGORY-LISTINGS` block, which the scraper rewrites.

For more detail see [docs/architecture.md](docs/architecture.md). Operations and
troubleshooting are in [docs/operations.md](docs/operations.md), and past design decisions
in [docs/adr/](docs/adr/).

| Path | What it is |
|---|---|
| `config.yml` | Companies per ATS, filter signals, source settings |
| `scripts/ngj/` | The scraper package: `pipeline.py`, `sources/`, `filters.py`, `dedup.py`, `taxonomy.py`, `outputs/` |
| `scripts/*.py` | Contracts, publishing, integrity checks, URL safety, README sync, config validation |
| `tests/` | pytest suite |
| `site/` | Vite + React 18 job board (`src/lib` = pure logic, `src/components` = UI) |
| `data/market-history.json` | Daily snapshot history, committed by CI |

## 3. Development setup

**Prerequisites:** Python 3.11+, Git, `make`, and Node 20.19+ for site work (CI uses 22).
The repo also ships a Dev Container (Python 3.11 + Node 22).

```bash
git clone https://github.com/<you>/New-Grad-Jobs.git
cd New-Grad-Jobs
git remote add upstream https://github.com/ambicuity/New-Grad-Jobs.git

make setup          # .venv, hash-locked deps (runtime + dev), pre-commit hook
source .venv/bin/activate
make test           # should be green before you change anything
```

Run `make help` for every target. The ones you will use:

| Command | What it does |
|---|---|
| `make test` | pytest with coverage (floor: 75%) |
| `make lint` | ruff + all pre-commit hooks |
| `make format` | ruff safe autofixes (import order, pyupgrade, …) |
| `make typecheck` | mypy over `scripts/` |
| `make run` | a real scrape (hits live APIs, takes a few minutes) |
| `make lock` | regenerate hash-locked `requirements*.txt` (needs [uv](https://docs.astral.sh/uv/)) |

**Running the scraper locally.** Point the output somewhere disposable, then validate it:

```bash
NGJ_OUTPUT_DIR=/tmp/ngj make run
python scripts/check_integrity.py /tmp/ngj
git checkout -- README.md data/market-history.json   # a local run rewrites these; don't commit them
```

**Working on the site:**

```bash
cd site
npm ci
npm run fetch-data   # download the live data into public/ (gitignored)
npm run dev          # local dev server
npm test             # vitest
npm run lint         # eslint
npm run build        # production build into dist/ (includes /job/<id>/ pages and sitemap)
```

Keep data logic in `site/src/lib/` as pure functions with tests next to them.

## 4. Adding a company

1. Find the company's ATS and public job-board slug.
2. Add an entry to `config.yml` in the matching section:

   ```yaml
   apis:
     greenhouse:
       companies:
         - name: "Stripe"
           url: "https://boards-api.greenhouse.io/v1/boards/stripe/jobs"
     lever:
       companies:
         - name: "Spotify"
           url: "https://api.lever.co/v0/postings/spotify"
     ashby:
       companies:
         - name: "OpenAI"
           url: "https://api.ashbyhq.com/posting-api/job-board/openai"
     workday:
       companies:
         - name: "Microsoft"
           workday_url: "https://microsoft.wd10.myworkdayjobs.com/en-US/Microsoft"
   ```

3. Check that the endpoint returns jobs, for example with
   `curl -s <url> | head -c 500`. For Workday, open the careers page in a browser.
4. Validate the config. This checks required keys, URL shape per ATS, duplicates and
   numeric ranges:

   ```bash
   python scripts/validate_config.py
   ```

5. If you remove or move a company, add a line to
   [docs/removed-companies.md](docs/removed-companies.md) explaining why.

A company must have a public, unauthenticated ATS endpoint. Sites that need a login are out
of scope.

## 5. Adding a source or a category

**A new ATS source** (open an issue first):

1. Add `scripts/ngj/sources/<name>.py` with a fetcher that returns
   `ngj.models.SourceResult`. Per-company failures go in `errors`, not exceptions. Use
   `ngj.http` (`limited_get` / `limited_post`) for every request.
2. Register it in `scripts/ngj/registry.py` (`SOURCE_ORDER` + enable rule) and wire it
   in `ngj.pipeline.plan_sources`.
3. Add its settings to `ngj/settings.py` and its schema checks to
   `scripts/validate_config.py`.
4. Add tests with mocked HTTP responses: success, a partial failure and a malformed
   payload.

**A new job category:** `CATEGORY_PATTERNS` in `scripts/ngj/taxonomy.py` is the single
source of truth. Add the category there, then:

- add its id to `site/src/lib/taxonomy.js` (`CATEGORY_TYPE`, `TYPE_LABEL`, `TYPE_ORDER`);
- add a `<!-- COUNT:<id> -->0<!-- /COUNT -->` row to the README category table.

`tests/test_category_taxonomy_sync.py` fails until all three agree. Categorization matches
the **title first**. The description is only consulted when the title matches nothing.

**Filter changes** (`filtering.*` in `config.yml`) match at token boundaries, never as raw
substrings. Titles at level III and above are excluded. Locations must be in the US,
Canada or India (remote included). Add a test in `tests/test_filter.py` or
`tests/test_location.py` for every new case.

## 6. Testing

Write the test first, watch it fail, then make it pass.

```bash
make test                                  # full suite + coverage
pytest tests/test_filter.py -k level -q    # one area
cd site && npm test                        # site unit tests
```

- **Network is blocked** in pytest (`tests/conftest.py`). Mock HTTP instead. A test that
  really needs the network must be marked `@pytest.mark.network`.
- `time.sleep` longer than 0.1 s is a no-op in tests. Mark `@pytest.mark.real_sleep` if
  you need a real one.
- Inject `now` instead of calling `datetime.now()`, so tests never age out.
- Coverage floors: 75% for `scripts/` (pytest fails below it), 80% of lines for
  `site/src/lib`.
- Tests follow Arrange-Act-Assert with descriptive names, e.g.
  `test_excludes_level_three_titles`.

## 7. Lint, formatting and pre-commit

- **Python:** [ruff](https://docs.astral.sh/ruff/) is the only linter and import sorter.
  Its config is in `pyproject.toml` (line length 120). Use type hints on every function,
  `logging` instead of `print`, specific exceptions and named constants.
- **Site:** ESLint (`npm run lint`).
- **pre-commit** (installed by `make setup`) runs whitespace/EOF fixes, YAML/JSON/TOML
  checks, a large-file check, private-key detection, ruff and gitleaks. CI runs it with
  `--all-files`, so run `pre-commit run --all-files` before pushing.
- **Dependencies:** ranges go in `pyproject.toml`, and exact hash-locked versions in
  `requirements.txt` / `requirements-dev.txt`. After changing dependencies, run
  `make lock` and commit both files.

## 8. Commits and pull requests

**Commits and PR titles** follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<optional scope>): <summary in lowercase, no period>

feat(config): add Stripe to Greenhouse companies
fix(filter): keep "Software Engineer I/II" titles
docs(contributing): document the Ashby config shape
```

Types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `perf`, `ci`. PRs are
**squash-merged**, so the PR title becomes the commit on `main`.

**Workflow:**

1. Branch from an up-to-date `main`:
   `git fetch upstream && git switch -c fix/short-name upstream/main`.
2. Keep the change focused on one issue.
3. Rebase on `upstream/main` before pushing if `main` has moved.
4. Open the PR against `ambicuity/New-Grad-Jobs:main`, fill in the template, and link the
   issue with `Fixes #<n>`.

**Required checks.** A PR is mergeable only when these are green:

| Check | What it runs |
|---|---|
| `lint` | ruff, actionlint, `validate_config.py` |
| `test (3.11)`, `test (3.13)` | pytest with the coverage floor |
| `site` | `npm ci`, eslint, vitest, `vite build` |
| `Run Pre-commit Hooks` | pre-commit on all files |

`typecheck` (mypy) and CodeQL also run. mypy is non-blocking for now. Codecov upload
failures never block a merge. PRs do not deploy anything: the site is deployed by
`update-jobs.yml` after merge.

## 9. Issues and labels

Use the [issue forms](https://github.com/ambicuity/New-Grad-Jobs/issues/new/choose): Bug
Report, Feature Request, New Role, Edit Role, Architecture Proposal, Sponsorship / CTA
Placement. The maintainer uses the tiered task templates (Good First Issue → Beginner →
Intermediate → Advanced). Questions belong in
[Discussions](https://github.com/ambicuity/New-Grad-Jobs/discussions).

Security problems: **do not open a public issue.** Use
[private vulnerability reporting](https://github.com/ambicuity/New-Grad-Jobs/security/advisories/new)
(see [SECURITY.md](SECURITY.md)).

The labels you will see most often (full list in [.github/labels.md](.github/labels.md)):

| Label | Meaning |
|---|---|
| `good first issue` | Small, guided task for newcomers |
| `good first issue candidate` | Might become a GFI once the maintainer reviews it |
| `beginner` / `intermediate` / `advanced` | Difficulty tiers beyond GFI |
| `help wanted` | Open for community contributions |
| `needs-triage` | Not yet reviewed by the maintainer |
| `new-role` / `edit-role` / `link-expired` | Job-data reports |
| `bug` / `enhancement` / `documentation` / `architecture` | Type of change |
| `possible-duplicate` | Flagged by the duplicate-issue guardrail |
| `scraper-stale` | Opened automatically by the watchdog when data stops refreshing |

## 10. Things to never do

- Commit generated data (`site/public/jobs*.json`, `descriptions/`, `feed.xml`,
  `health.json`) or the `README.md` / `data/market-history.json` changes from a local run.
- Edit inside README's COUNT markers or `CATEGORY-LISTINGS` block, or change the sponsor
  blocks (their copy and images are contractual).
- Show invented, estimated or placeholder numbers on the site or in the README.
- Edit `CHANGELOG.md`. The maintainer writes it at release time.
- Add a server, database, external scheduler or secret. The project runs entirely on
  GitHub Actions and Pages.

---

Every merged contributor is credited in [CONTRIBUTORS.md](CONTRIBUTORS.md). If your credit
is missing, comment on your PR and the maintainer will add you. Thank you!

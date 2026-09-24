# Changelog

All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org).
This changelog is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [1.0.1] - 2026-09-24

A full overhaul driven by a codebase and live-site audit: the job filter is more
accurate, the site is a real build instead of in-browser Babel, generated data no
longer bloats git, and every stage is tested. The public `jobs.json` schema moves to
**1.1** (see README): `id` now equals the stable `job_id`, `first_seen` is added and
`posted_display` is removed.

### Breaking / operational

- **Deployment:** the site is built with Vite and deployed by `update-jobs.yml` via
  `actions/deploy-pages` (Pages source: GitHub Actions). `pages-deployment.yml` is removed.
- **Generated data is no longer committed:** `jobs.json`, `jobs-index.json`,
  `descriptions/`, `feed.xml` and `health.json` are built into the Pages artifact and
  served at the site root (`https://jobs.riteshrana.engineer/jobs.json`, …). Only
  `README.md` and `data/market-history.json` (moved from `docs/`) are committed back.
- **Removed:** the Gemini predictions pipeline (`GOOGLE_API_KEY` no longer used),
  `evaluate_jobs.py`, `generate_companies.py`, `fix_nan_only.py`, `enrichment.py`,
  `verify_new_urls.py`, the stale root `jobs.json` and the `docs/terminal` site.
- **`jobs.json` schema 1.1:** `meta.schema_version`; `id == job_id`
  (`sha256(source, canonical URL)`); `first_seen`; `posted_at` is UTC with a trailing
  `Z`; every category is present in `meta.categories` (zero counts included).

### Scraper

- Split the 3,550-line `update_jobs.py` into the `scripts/ngj` package (sources, http,
  filters, locations, taxonomy, dedup, enrich, outputs, pipeline) with a frozen
  `Settings` object (config timeouts and limits now actually apply), `SourceResult` /
  `SourceError` per-company error reporting, structured logging and no import-time
  side effects.
- **Filter accuracy (bug fixes, matching stays broad):** exclusion words and track /
  level / strong signals match whole tokens (no more `intern`→"Internal",
  `manager`→"Associate Product Manager", `ai`→"Maintenance", `ml`→"HTML", years inside
  req ids); level III+ titles are excluded; locations must be in the US, Canada or
  India (no more "Remote - Poland" or "Berlin, DE" read as Delaware); missing
  locations are treated as unknown rather than "Remote".
- **Closed detection** uses strict phrases and title markers — all 17 previously
  "closed" jobs were false positives ("closed-loop", "disclosed").
- **Categories** are decided by the title first; the description is only a fallback.
  Company tiers match normalized names ("Snap Inc.", "Anduril Industries", "Amazon.com").
- **Descriptions** decode double-encoded entities (`&amp;nbsp;`), removing literal
  `&nbsp;` from ~72% of listings.
- **Workday:** companies are fetched in parallel with per-keyword searches (no more
  200-job truncation); 19 tenants corrected and 33 dead entries removed — every
  remaining Workday company now fetches successfully (previously 52 of 92 failed with
  HTTP 422/401).
- **Greenhouse / Ashby / Lever:** 48 dead boards removed, 12 companies re-added on the
  ATS they moved to; `posted_at` prefers `first_published` (edits no longer make old
  jobs look new); lists are fetched without content and descriptions are fetched only
  for jobs that pass the filter; boards that time out under contention get a
  sequential second pass.
- **HTTP:** a single retry layer (GET only, ≤4 attempts, `Retry-After` capped at 30 s)
  and a 403 cooldown keyed per tenant/board instead of per ATS domain.
- **Data quality:** stable unique `job_id`s (68 old id collisions), cross-source dedup
  that prefers the ATS posting over Indeed copies, currency inference (CAD/INR/GBP/EUR
  instead of assuming USD), JobSpy NaN rows normalized at the boundary.
- **Safety nets:** the run fails without publishing if the job count drops >40% or a
  large source goes to zero (`NGJ_ALLOW_DROP=1` overrides); any artifact/README write
  failure fails the run; a corrupt market-history file is never overwritten; the
  integrity checker validates `jobs.json`, `jobs-index.json`, description shards,
  URLs, `feed.xml` and `health.json` before deploy.
- **RSS:** 200 items ordered by `first_seen`, correct site links, XML-safe text.
- **health.json:** per-source error summaries, failed companies, cooldown state and a
  `degraded` status; Ashby is counted; `raw_source_counts` (old `source_counts` kept as
  a deprecated alias).
- A real run now takes ~2 minutes (was ~8.5) with ~35% less peak memory.

### Website

- Rebuilt with **Vite + React 18** as ES modules: ~78 KB gzipped JS instead of ~916 KB
  of development React plus in-browser Babel; self-hosted fonts; no unpkg dependency.
- Fixed crashes: pressing **Esc** blanked the page; an empty or failed data load
  crashed instead of showing an error; error boundaries now isolate each tab.
- **Honest numbers only:** removed invented deadlines, hard-coded deltas, "base + equity"
  labels, a fake cohort facet and company-size buckets; "visa sponsored" is now "no visa
  restriction stated"; the contributors view shows real GitHub data only.
- **Virtualized job list** (~1.4k DOM nodes instead of ~42k), deferred search.
- **Shareable state:** filters, search, sort, selected job and tab live in the URL;
  Back/Forward work; saved jobs persist in localStorage keyed by `job_id`.
- **Accessibility (WCAG 2.2 AA):** listbox semantics, real APPLY links, labelled search
  with a visible focus ring, modal dialogs with focus traps, live-region toasts,
  landmarks and skip links, ≥4.5:1 contrast, ≥11 px text, ≥24 px targets.
- **SEO:** a static page per job with `JobPosting` JSON-LD, `sitemap.xml`, `robots.txt`,
  a prerendered crawlable job list, canonical/OG tags and an OG image.
- **Security:** strict CSP (no inline scripts), http(s)-only links everywhere, a boot
  timeout fallback and `<noscript>` content.

### Security

- README job tables escape Markdown/HTML from scraped titles and links (tracking pixels,
  injected links and fake markers are rendered inert).
- `url_safety` blocks legacy IPv4 forms (`127.1`, `0x7f.1`, `0177.0.0.1`), CGNAT and all
  non-global addresses.
- The scraper step no longer persists a push token in `.git/config`; dependencies are
  hash-locked (`requirements*.txt`, generated with uv).
- The scraper can no longer push merge-conflict markers (`--autostash` removed).
- The duplicate-issue bot escapes titles it quotes.

### CI and tooling

- CI jobs: `lint` (ruff, actionlint, config schema validation), `typecheck` (mypy,
  blocking), `test (3.11)`, `test (3.13)`, `site` (eslint, Vitest, build, Playwright
  e2e + axe); CodeQL now also scans JavaScript and workflows.
- ruff replaces flake8/isort/black; pytest blocks the network and enforces a 75%
  coverage floor (actual ~97%); `pip install -e .[dev]` works again.
- Tests: 1,466 pytest, 327 Vitest, 52 Playwright (desktop + mobile) with axe scans.
- The watchdog reads the live `health.json`; dead automation config removed.

### Documentation

- New `AGENTS.md` (canonical instructions for AI coding agents), `docs/operations.md`
  runbook and ADR 0005 (Vite site + Actions deploy); rewritten `CONTRIBUTING.md`,
  `docs/architecture.md` and ADRs 0001/0003/0004; the stale wiki and Copilot agent
  personas are removed; the update cadence is stated correctly (about every 30 minutes).

### Earlier fixes included in this release

- scraper: support `hours ago` and `minutes ago` patterns in `normalize_date_string()`, resolving them to today's date ([#80](https://github.com/ambicuity/New-Grad-Jobs/issues/80))
- extract hardcoded Workday API pagination and safety limits to configurable constants `WORKDAY_PAGE_LIMIT` and `WORKDAY_MAX_JOBS_PER_COMPANY` ([#43](https://github.com/ambicuity/New-Grad-Jobs/issues/43)); runtime limits are now overridable via `config.yml`.
- enhance `safe_str` in `get_job_key` to robustly handle `numpy.floating` NaNs and Infs when deduping jobs originating from JobSpy/pandas; NumPy import hoisted to module-level for hot-path optimization.
- add support for `'hours ago'` and `'minutes ago'` relative time formats in `normalize_date_string()` to improve JobSpy/LinkedIn data parsing ([#79](https://github.com/ambicuity/New-Grad-Jobs/issues/79)).
- add `'developer advocate'` and `'devrel'` to `software_engineering` keyword list in `categorize_job()` so DevRel roles are no longer classified as `other` ([#87](https://github.com/ambicuity/New-Grad-Jobs/issues/87))
- add domain-aware concurrency limiter for scraper HTTP calls, capping `api.greenhouse.io` concurrency while preserving high parallelism for other domains
- normalize timezone-aware date handling in `is_recent_job` by standardizing parsed values to UTC before recency comparison; add explicit guards/tests for `None`, `NaN`, UTC-offset strings, aware datetimes, and boundary windows
- stabilize CI workflow reliability: fix duplicate key in `.github/labeler.yml` and update Trivy action reference to a valid release
- calibrate config sanity threshold in `test_config.py` to match current source volume baseline
- scope `update-jobs` workflow push trigger to scraper inputs and generated docs behavior to prevent recursive self-trigger loops on `main`
- add sponsorship-flag regression test for non-empty title with empty description
- `CONTRIBUTING.md` rewritten with full dev-environment setup, Conventional Commits guide, and ASCII architecture diagram
- `CODE_OF_CONDUCT.md` — Contributor Covenant v2.1
- `SECURITY.md` — private vulnerability disclosure policy with supported-versions table
- `LICENSE` — MIT License
- `ROADMAP.md` — versioned project roadmap (v1.0, v1.1, v2.0)
- `.pre-commit-config.yaml` — trailing whitespace, YAML/JSON validation, large-file guard, secret detection, import sorting
- `.github/CODEOWNERS` — automatic PR routing to `@ambicuity` for scraper, config, and workflow files
- `.github/FUNDING.yml` — Sponsor button linking to GitHub Sponsors and Ko-fi
- `.github/labels.md` — label reference with colors and descriptions for all repository labels
- `.github/create-labels.sh` — shell script to recreate all labels in forks or fresh repositories
- `.github/workflows/ci.yml` — PR linting, syntax validation, and unit test pipeline
- `.github/workflows/release-please.yml` — automated CHANGELOG generation and GitHub Releases from Conventional Commits
- `.github/workflows/codeql.yml` — weekly CodeQL security scanning for Python CVEs and injection risks
- `.github/workflows/stale.yml` — automatic stale issue and PR management (30-day warning, 44-day close)
- `.github/ISSUE_TEMPLATE/feature_request.yml` — structured feature request form with area selector
- `.github/ISSUE_TEMPLATE/architecture_proposal.yml` — major change proposal form with design discussion gate
- `.github/PULL_REQUEST_TEMPLATE.md` — contributor PR checklist covering scraper testing, frontend testing, and commit standards
- `docs/adr/0001-python-scraper-architecture.md` — Architecture Decision Record: single-script vs. multi-module vs. microservices
- `docs/adr/0002-github-pages-deployment.md` — Architecture Decision Record: GitHub Pages vs. Vercel/Next.js
- Interactive job board website with dark theme, real-time search, and multi-filter system (categories, sectors, locations)
- Automated job scraping pipeline via GitHub Actions, updating every 5 minutes
- Greenhouse API integration for direct company ATS scraping
- Lever API integration for direct company ATS scraping
- Google Careers integration via search-term matching
- JobSpy integration for LinkedIn and Indeed job data
- Smart new-grad signal detection to filter out senior and staff roles
- USA, Canada, and India location validation with state/province/city matching
- Job enrichment pipeline: role-type categorization, company-tier classification (FAANG+, Unicorn), sector tagging (Defense, Finance, Healthcare, Startup)
- Sponsorship and US citizenship requirement flag detection
- JSON-based job data output (`jobs.json`) for fast frontend rendering
- GitHub Issue templates for submitting new roles and reporting incorrect listings
- Contributing guidelines and bug report template
- `README.md` replaced with auto-generated job board index (generated by scraper)
-

## 0.1.0 (2026-03-03)


### Features

* **ci:** add CodeRabbit Issue Planner config and AI-Assisted Task template ([31b565f](https://github.com/ambicuity/New-Grad-Jobs/commit/31b565fc9c00afacbe549867f8957b371d422800))
* **ci:** implement contributor lifecycle automation and slash commands ([#40](https://github.com/ambicuity/New-Grad-Jobs/issues/40)) ([9e2f3a8](https://github.com/ambicuity/New-Grad-Jobs/commit/9e2f3a84e9fbb4045a7c135cae808d2fa96fb164))
* **community:** Onboard Python 3-Tier Onboarding and AD Taboos ([78441ae](https://github.com/ambicuity/New-Grad-Jobs/commit/78441aefdf1545f4dd040c06ce99bf04eaa3755a))
* **repo:** Onboard Community Engine, DevContainers, and AI rules ([f673fa4](https://github.com/ambicuity/New-Grad-Jobs/commit/f673fa4762f093e360464b24aaf93a072c04ec3f))


### Bug Fixes

* **categorize:** resolve TPM category collision by prioritizing Product Management explicitly ([a3b2abd](https://github.com/ambicuity/New-Grad-Jobs/commit/a3b2abde70725e337ba72d953ffa5ebabe222ef6))
* **ci:** address AI code review security and logic feedback ([ce4cd9d](https://github.com/ambicuity/New-Grad-Jobs/commit/ce4cd9db8c626d680b893c720dfb917c0a6f8197))
* **ci:** fix yaml config key and pre-commit formatting issues ([672bc7d](https://github.com/ambicuity/New-Grad-Jobs/commit/672bc7d552347556a8c3ea4c1e35127b5de7f20b))
* **ci:** grant trivy workflow security-events write permission and bump upload-sarif to v4 ([fc9515a](https://github.com/ambicuity/New-Grad-Jobs/commit/fc9515a396f776134721d176dc359d01005b11cd))
* replace bare except with Exception and add logging for date parsing ([#39](https://github.com/ambicuity/New-Grad-Jobs/issues/39)) ([10faa04](https://github.com/ambicuity/New-Grad-Jobs/commit/10faa04e97bf0ac0952ec445622db2eeabe87b1c))
* **security:** resolve CodeQL alerts ([c23105e](https://github.com/ambicuity/New-Grad-Jobs/commit/c23105e8ec3d0c0c52516d741b69a30c4b187086))
* **tests:** resolve failing test suite ([e1ad340](https://github.com/ambicuity/New-Grad-Jobs/commit/e1ad340bff08206e4747cf900b1a1e2b50cb2e44))


### Documentation

* add AI review tooling strategy to wiki and decision log ([0481c82](https://github.com/ambicuity/New-Grad-Jobs/commit/0481c82bf8870e0f714b0e68ce615f17365cbf34))
* add all-contributors specification and cheerleading bot config ([df5fff8](https://github.com/ambicuity/New-Grad-Jobs/commit/df5fff80592f4811e4b96e4809766872b0244e96))
* add CI monitoring guide to Operator Manual ([88fe377](https://github.com/ambicuity/New-Grad-Jobs/commit/88fe377c859b55715a28d68c47f69e1529f4c7d1))
* add repository ruleset documentation and update wiki sidebar ([522aef2](https://github.com/ambicuity/New-Grad-Jobs/commit/522aef2b3a2bda3c2e9f76687674451dc2b5371f))
* add strict PR template and update CONTRIBUTING for AI workflow ([1ba3f83](https://github.com/ambicuity/New-Grad-Jobs/commit/1ba3f83cc42b660cd027922b72f31a93c62e1119))
* **architecture:** add in-depth mermaid flow diagram of system pipeline ([714ecd7](https://github.com/ambicuity/New-Grad-Jobs/commit/714ecd7949e81ea116765c87bf9bf32ca2fbef57))
* gold-standard rewrite of copilot-instructions.md and create GEMINI.md ([7a1c28e](https://github.com/ambicuity/New-Grad-Jobs/commit/7a1c28e1b64e0f3b28dc1582960e6f7e8915a299))
* rewrite ruleset from solo-maintainer perspective ([c21eb12](https://github.com/ambicuity/New-Grad-Jobs/commit/c21eb120a389b6f0cc2ed842b2cb0f7912732445))
* **wiki:** enhance professionalism with absolute URLs and alerts ([20ed45d](https://github.com/ambicuity/New-Grad-Jobs/commit/20ed45dfe6da05dad110749be73413fd503a37e1))
* **wiki:** init local project wiki structure (home, roadmap, sidebar) ([f08fbf2](https://github.com/ambicuity/New-Grad-Jobs/commit/f08fbf25116ba0dae837a72be745b1d46364b4df))
* **wiki:** upgrade to gold-standard solo-maintainer framework ([756e758](https://github.com/ambicuity/New-Grad-Jobs/commit/756e758fe201f5398f6ad6d3c3a88424124fef5a))

[Unreleased]: https://github.com/ambicuity/New-Grad-Jobs/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/ambicuity/New-Grad-Jobs/compare/v1.0.0...v1.0.1

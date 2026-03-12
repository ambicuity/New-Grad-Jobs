# Changelog

All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org).
This changelog is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Bug Fixes

* **scraper:** handle `math.inf` and `-math.inf` in `get_job_key` `safe_str` helper to prevent unpredictable deduplication behavior ([#81](https://github.com/ambicuity/New-Grad-Jobs/issues/81))

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

## [Unreleased]

### Fixed

- add `'developer advocate'` and `'devrel'` to `software_engineering` keyword list in `categorize_job()` so DevRel roles are no longer classified as `other` ([#87](https://github.com/ambicuity/New-Grad-Jobs/issues/87))
- add domain-aware concurrency limiter for scraper HTTP calls, capping `api.greenhouse.io` concurrency while preserving high parallelism for other domains
- normalize timezone-aware date handling in `is_recent_job` by standardizing parsed values to UTC before recency comparison; add explicit guards/tests for `None`, `NaN`, UTC-offset strings, aware datetimes, and boundary windows
- stabilize CI workflow reliability: fix duplicate key in `.github/labeler.yml` and update Trivy action reference to a valid release
- calibrate config sanity threshold in `test_config.py` to match current source volume baseline
- scope `update-jobs` workflow push trigger to scraper inputs and generated docs behavior to prevent recursive self-trigger loops on `main`

### Added

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

## [1.0.0] - 2026-01-17

### Added

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

### Changed

- `README.md` replaced with auto-generated job board index (generated by scraper)

---

[Unreleased]: https://github.com/ambicuity/New-Grad-Jobs/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/ambicuity/New-Grad-Jobs/releases/tag/v1.0.0

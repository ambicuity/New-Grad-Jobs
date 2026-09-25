# AGENTS.md

Instructions for AI coding agents (Codex, Copilot, Claude, Cursor, …) working in this repo.
Humans should read [CONTRIBUTING.md](CONTRIBUTING.md). Operators should read
[docs/operations.md](docs/operations.md).

## What this is

New Grad Jobs is an automated board of entry-level tech jobs in the US, Canada and India.
A Python scraper pulls public ATS APIs (Greenhouse, Lever, Ashby, Workday) plus JobSpy
(Indeed) about every 30 minutes in GitHub Actions. It filters for new-grad roles and
publishes static JSON/RSS. A Vite + React site at <https://jobs.riteshrana.engineer> is
built from that data and deployed to GitHub Pages. There is no server and no database.

## Repo map

```
config.yml                 companies per ATS, filter signals, source knobs (validated by scripts/validate_config.py)
scripts/update_jobs.py     CLI entrypoint → ngj.pipeline.main
scripts/ngj/               the scraper package
  pipeline.py              fetch → dedup → filter → enrich → URL gate → collapse guard → publish
  settings.py              frozen Settings built from config.yml + env (NGJ_OUTPUT_DIR, NGJ_SITE_URL)
  models.py                SourceResult / SourceError (per-company errors travel with the jobs)
  registry.py              which sources are enabled (shared by pipeline, health.json, validate_config)
  http.py                  shared requests session, per-domain concurrency limits, 403 cooldown hooks
  sources/                 one adapter per source; each returns a SourceResult
  filters.py locations.py  inclusion gate: exclusions, level III+, new-grad/track signals, recency, US/CA/IN
  dedup.py                 same-posting (job_id) + cross-source dedup
  taxonomy.py enrich.py    CATEGORY_PATTERNS, company tiers, sponsorship/closed flags
  outputs/                 jobs_json, rss, health, market_history, previous (last published run)
scripts/contracts.py       jobs.json schema (1.1), canonical_url, compute_job_id
scripts/publish.py         jobs-index.json + descriptions/<0-f>.json shards
scripts/quality.py         cross-artifact integrity checks (run by scripts/check_integrity.py)
scripts/url_safety.py      publish-time URL gate (public http(s) only)
scripts/sync_readme_*.py   rewrite README COUNT markers / CATEGORY-LISTINGS / COMPANY-LISTINGS blocks
tests/                     pytest; network blocked by tests/conftest.py
site/                      Vite + React 18 app (src/components, src/lib, src/hooks, src/data)
site/scripts/seo/          Vite plugin: CSP, /job/<job_id>/ pages with JobPosting JSON-LD, sitemap, robots, prerender
data/market-history.json   daily snapshots (committed by CI, 90-day retention)
docs/                      architecture.md, operations.md, adr/, removed-companies.md
```

## Setup

```bash
make setup                 # .venv + hash-locked runtime/dev deps + pre-commit hook (Python 3.11+)
make install               # re-install deps into an existing .venv
cd site && npm ci          # Node >= 20.19 (CI uses 22)
```

## Commands

```bash
make test                  # pytest; coverage floor 75% (pyproject.toml)
make lint                  # ruff + pre-commit --all-files
make format                # ruff --fix
make typecheck             # mypy (CI job is non-blocking for now)
.venv/bin/python scripts/validate_config.py          # after any config.yml edit
NGJ_OUTPUT_DIR=/tmp/ngj make run                     # real scrape (network, minutes)
.venv/bin/python scripts/check_integrity.py /tmp/ngj # validate that output

cd site
npm run fetch-data         # download live jobs/health/feed/descriptions into public/ (gitignored)
npm run dev                # dev server
npm test                   # vitest (src/lib coverage threshold 80% lines)
npm run lint               # eslint
npm run build              # dist/ incl. SEO pages; tolerates missing data
npm run build:fixtures     # build against site/test/fixtures
```

After `make run`, restore the two files that a local scrape rewrites:
`git checkout -- README.md data/market-history.json`.

## Architecture in brief

- **Pipeline** (`ngj.pipeline.run`): `plan_sources` binds one fetcher per enabled source
  (from `ngj.registry`) to `Settings`, and `fetch_all_sources` runs them concurrently.
  Then `deduplicate_jobs` → `filter_jobs` → `enrich_jobs` → `filter_safe_jobs` →
  `generate_jobs_json` → partial-collapse guard → `_publish` (history, jobs artifacts,
  feed, health, README sync). The run exits 1 on any write failure or a guard trip.
- **Errors are data:** adapters never raise for a single company. They return
  `SourceResult(jobs, errors=(SourceError(company, source, kind, status, message), ...))`.
  `health.json` summarizes them per source (status, failure ratio, failed companies).
- **Identity:** `job_id = "job_" + sha256(source + canonical URL)[:20]`. Tracking params
  are stripped, and there is a company/title/location fallback when a job has no URL.
  `id == job_id`. `first_seen` carries forward from the previous published run.
- **Collapse guard:** refuses to publish if the total drops more than 40% versus the
  previous run, or if a source that had more than 100 jobs returns 0. Override with
  `NGJ_ALLOW_DROP=1`.
- **Site data flow:** the scraper writes to `site/public/`. `vite build` copies it into
  `dist/` and generates SEO pages from it. The browser loads `jobs-index.json`, and fetches
  one `descriptions/<shard>.json` when a detail pane opens. Data URLs are relative
  (`base: './'`).

## Conventions

- **Tests first.** Add or adjust a pytest/vitest test that fails, then fix. Tests must be
  deterministic: network is blocked (mark `@pytest.mark.network` only with a real reason),
  `time.sleep` > 0.1 s is a no-op unless marked `real_sleep`, and inject `now`.
- **Immutability.** Pipeline stages return new lists/dicts and never mutate their input.
  `Settings`, `SourceResult` and `SourceError` are frozen dataclasses. Pass `Settings`
  explicitly and add no module globals.
- **Python style:** type hints on every signature, `logging` (never `print`, except CLI
  JSON output), specific exceptions, named constants. Ruff config is in `pyproject.toml`
  (line length 120).
- **HTTP** goes through `ngj.http` (`limited_get` / `limited_post` / `get_session`) so
  retries, pooling, domain limits and the 403 cooldown apply.
- **Site:** keep data logic in `site/src/lib/` as pure, unit-tested functions. Components
  use inline styles and the `useIsMobile` hook for responsiveness.

### Where to add things

- **A company:** add `{name, url}` under `apis.greenhouse|lever|ashby.companies`
  (`https://boards-api.greenhouse.io/v1/boards/<slug>/jobs`,
  `https://api.lever.co/v0/postings/<slug>`,
  `https://api.ashbyhq.com/posting-api/job-board/<slug>`) or `{name, workday_url}` under
  `apis.workday.companies` (`https://<tenant>.wd<N>.myworkdayjobs.com/<site>`). Then run
  `validate_config.py`. Record removals in `docs/removed-companies.md`.
- **A new ATS source:** add `scripts/ngj/sources/<name>.py` returning `SourceResult`. Then
  register it in `ngj/registry.py` (`SOURCE_ORDER` + enable rule), wire it in
  `pipeline.plan_sources`, add knobs to `Settings` and schema checks to
  `validate_config.py`, and add tests with mocked HTTP.
- **A category:** `CATEGORY_PATTERNS` in `scripts/ngj/taxonomy.py` is canonical.
  `tests/test_category_taxonomy_sync.py` fails until you also add the id to
  `site/src/lib/taxonomy.js` (`CATEGORY_TYPE` and friends) and add a
  `<!-- COUNT:<id> -->0<!-- /COUNT -->` row to the README table.
- **A filter signal:** edit `filtering.*` in `config.yml`. Matching is token-boundary,
  never substring.

## Hard rules

1. **Honesty.** Never show invented, estimated or placeholder numbers on the site or in the
   README. Every count and stat must come from the published data.
2. **Never commit generated data:** `site/public/{jobs.json, jobs-index.json, descriptions/,
   feed.xml, health.json}` are gitignored and exist only in the Pages deployment.
3. **README:** edit only outside `<!-- COUNT:* -->…<!-- /COUNT -->` and the
   `<!-- CATEGORY-LISTINGS:START … -->`…`<!-- CATEGORY-LISTINGS:END -->` and
   `<!-- COMPANY-LISTINGS:START … -->`…`<!-- COMPANY-LISTINGS:END -->` blocks, which the
   scraper owns (the latter, and the `boards_*` counts, come from `config.yml`). Do not touch the sponsor blocks: the Zapply CTA copy is verbatim-locked,
   and the root-level `apply-faster-banner.png` and `get-started-button.png` must stay
   where they are. Leave the Tailr block as is too.
4. **Dependencies:** ranges live in `pyproject.toml`, and exact hash-locked versions in
   `requirements*.txt`. After changing dependencies, run `make lock` (needs `uv`) and
   commit both files. Keep the ruff pin in step with `.pre-commit-config.yaml`. For the
   site, commit `package-lock.json`.
5. **Conventional commits** (`feat|fix|docs|test|chore|refactor|perf|ci: …`). PRs are
   squash-merged.
6. **Required CI must pass:** `lint` (ruff, actionlint, validate_config), `typecheck` (mypy),
   `test (3.11)`, `test (3.13)`, `site` (eslint, vitest, build, Playwright e2e + axe) and pre-commit. Do not rename these jobs:
   they are required status checks.
7. **Do not** edit `CHANGELOG.md` (the maintainer writes it), add secrets, loosen workflow
   `permissions`, or add a server, database or external scheduler.

## Deploy

`update-jobs.yml` runs on the `7,37 * * * *` cron, on dispatch, and on pushes to `main`
that touch `scripts/`, `config.yml`, `requirements.txt`, `site/` or the workflow. It
scrapes, runs `check_integrity.py`, runs `vite build` and uploads the Pages artifact. The
`deploy` job (deploy-pages) and the `persist` job (commits `README.md` +
`data/market-history.json`) then run on `main` only. `scraper-watchdog.yml` re-dispatches
the scrape when the live `health.json` is more than 3 h old. Rollback and troubleshooting
are in [docs/operations.md](docs/operations.md).

## Gotchas

- `pre-commit` in CI runs `--all-files`, so an untouched file with trailing whitespace can
  fail your PR.
- Imports inside `scripts/` are top-level (`from ngj...`, `from contracts import ...`),
  because `scripts/` is on `sys.path` (tests insert it in `conftest.py`).
- A local `make run` hits real APIs, reads the previous run from the live site, and
  rewrites `README.md` and `data/market-history.json`.
- The site's `public/` data is absent in a fresh clone. Run `npm run fetch-data` or
  `build:fixtures` before expecting a populated UI.
- Workday tenants fail in cohorts. Per-company errors are captured and reported in
  `health.json`, so a partial Workday result is not a pipeline bug.
- `docs/superpowers/` is gitignored local planning and is not project docs.

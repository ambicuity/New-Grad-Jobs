# ADR-0005: Vite-built Site, Deployed from the Scraper Job, No Committed Data

**Date:** 2026-09 (v1.0.1)
**Status:** Accepted. Supersedes [ADR-0002](0002-github-pages-deployment.md).
**Deciders:** Ritesh Rana (maintainer)

---

## Context

[ADR-0002](0002-github-pages-deployment.md) chose a no-build static site served by GitHub
Pages from `docs/` on `main`. The scraper committed its output (`jobs.json`,
descriptions, feed, health) into `docs/` on every run. By v1.0 that design had costs no
one had chosen deliberately:

- **Page weight.** The "terminal" UI had moved to React, still with no build step. It
  shipped the development builds of React and Babel Standalone and transpiled JSX in the
  browser: about **916 KB gzipped** of JavaScript before any data, plus slow startup on
  mobile.
- **Data size.** `jobs.json` had grown to about **30 MB**, and it was committed on every
  refresh.
- **Repository bloat.** Committed generated data had pushed the repository to about
  **285 MB**. About **97% of commits** were bot data commits, which buried human history
  and made clones and blame slow.
- **Fragile publishing.** The data commits raced with human pushes (autostash and rebase
  conflicts), and a failed push meant a failed deploy.
- **No SEO surface.** A single client-rendered page gave search engines nothing per job.

## Decision

1. **Build the site with Vite** (React 18, ES modules) under `site/`. The production
   bundle has no runtime transpiler and no development React. Data logic lives in
   `site/src/lib/` as pure, unit-tested functions. A build-time plugin
   (`site/scripts/seo/`) emits the CSP, per-job pages `/job/<job_id>/` with `JobPosting`
   JSON-LD, `sitemap.xml`, `robots.txt` and a prerendered list.
2. **Deploy from the scraper workflow.** `update-jobs.yml` scrapes into `site/public/`,
   runs `check_integrity.py`, runs `vite build` and uploads the Pages artifact. A separate
   `deploy` job publishes it with `actions/deploy-pages`. Pages source = **GitHub
   Actions**. That workflow is the only deployer, and site-only pushes to `main` trigger
   it too.
3. **Stop committing generated data.** `jobs.json`, `jobs-index.json`, `descriptions/`,
   `feed.xml` and `health.json` are gitignored and exist only in the deployment. They are
   served at the site root (`https://jobs.riteshrana.engineer/jobs.json`). Only small
   persistent state is committed back, by a separate `persist` job: `README.md` (counts
   and category tables) and `data/market-history.json`. Anything that needs the previous
   run (collapse guard, `first_seen`) reads it from the live site.
4. **Do not rewrite history** to reclaim the 285 MB. A rewrite is irreversible, would
   break every existing fork, clone and PR branch, and would invalidate commit links in
   issues and the changelog. The repository stops growing from data. Old blobs stay.

## Consequences

**Positive**
- Much smaller, faster first load: an optimized bundle plus `jobs-index.json` without
  descriptions. Descriptions load per shard on demand.
- Repository growth from data stops, and `main` history is human-readable again.
- A deploy no longer depends on winning a push race. `deploy` and `persist` are
  independent, so a persist failure does not block the site update.
- Crawlable per-job pages and structured data.
- A run that fails its integrity check or the collapse guard deploys nothing, and the
  last good site stays up.

**Negative**
- The site now needs Node and a build (`npm ci && npm run build`). Contributors working on
  the site need Node 20.19+.
- Generated data is no longer in git. Local site work needs `npm run fetch-data` (or the
  test fixtures), and there is no git history of past `jobs.json` snapshots.
- Rolling back means re-running a previous deploy while its artifact still exists, or
  reverting code and redeploying. `git revert` of a data commit no longer does anything.
  See [operations.md](../operations.md).
- The repository stays large on disk because of pre-v1.0.1 history (accepted; see
  decision 4).

## Review Trigger

Revisit when:
- GitHub Pages limits (artifact size, deploy frequency, bandwidth) are approached;
- features need server-side state or APIs beyond static files;
- repository size causes real problems for contributors. At that point, weigh a
  coordinated history rewrite, announced in advance, against its costs.

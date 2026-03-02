# ADR-0001: Python Single-Script Scraper Architecture

**Date:** 2026-01-17
**Status:** Accepted
**Deciders:** Ritesh Rana (maintainer)

---

## Context

The New Grad Jobs aggregator needs to fetch job listings from multiple company ATSs (Greenhouse, Lever, Google Careers, JobSpy), filter them for new-grad relevance, and write the results to `jobs.json` and `README.md` on a 5-minute cycle via GitHub Actions.

The core architectural question was: **how to structure the Python backend.**

Options considered:
1. **Single-script architecture** — One large `scripts/update_jobs.py` file handling all logic.
2. **Multi-module package** — Separate `scraper/`, `filter/`, `config/`, `output/` packages.
3. **Web App with Database** — Full web application using PostgreSQL/Redis and an API layer.

## Decision

**Option 1 — Single-script architecture** was chosen without an external database.

All scraping, filtering, categorization, deduplication, and output generation live in `scripts/update_jobs.py`. State is managed entirely through static files (`jobs.json` and `README.md`).

## Consequences

**Positive**:
- **Zero Hosting Costs**: GitHub Actions provides compute; GitHub Pages provides hosting. No database fees.
- **Unbreakable Uptime**: No database to go down or web server to crash under load.
- **Easy Onboarding**: Contributors only need Python 3.11. There's no complex Docker Compose setup for databases required.

**Negative**:
- **Git Bloat**: Generating the README every 5 minutes results in a massive number of commits.
- **Modularity Limits**: As the file grows beyond ~2,000 lines, it will need to be split (See ADR-0003).

## Review Trigger

This decision should be revisited when:
- The script exceeds 3,000 lines.
- We add a new source type requiring fundamentally different auth (e.g., OAuth flows).
- GitHub limits action execution frequency prohibiting our 5-minute cycle.

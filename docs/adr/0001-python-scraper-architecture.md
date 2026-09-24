# ADR-0001: Python Scraper Architecture

**Date:** 2026-01-17 (revised 2026-09 for v1.0.1)
**Status:** Accepted (amended: the single script became the `ngj` package)
**Deciders:** Ritesh Rana (maintainer)

---

## Context

The aggregator fetches job listings from many company ATSs (Greenhouse, Lever, Ashby,
Workday) and JobSpy, filters them for new-grad relevance and publishes static artifacts.
It runs every 30 minutes in GitHub Actions.

The original question was how to structure the Python backend:

1. **Single script:** one `scripts/update_jobs.py` handling everything.
2. **Multi-module package:** separate modules for sources, filtering, outputs and config.
3. **Web app with a database:** PostgreSQL/Redis behind an API.

## Decision

**No database, no server.** State lives in static files produced on every run. Option 3 is
still rejected.

The code started as **option 1**, a single script, to keep onboarding simple. By 2026 it
had grown past 2,000 lines of shared globals, and changes in one area kept breaking
another. For v1.0.1 it was split into **option 2**, the `ngj` package under
`scripts/ngj/`:

- `scripts/update_jobs.py` is a 16-line entrypoint that calls `ngj.pipeline.main`.
- `settings.py` builds a frozen `Settings` from `config.yml` + env, passed explicitly
  instead of module globals.
- `sources/` holds one adapter per source, each returning a `SourceResult` whose
  per-company `SourceError`s travel with the jobs.
- `registry.py` is the single place that decides which sources are enabled.
- `dedup.py`, `filters.py`, `locations.py`, `taxonomy.py` and `enrich.py` are pure
  stages that never mutate their input.
- `outputs/` holds `jobs_json`, `rss`, `health`, `market_history` and `previous`.

## Consequences

**Positive**
- Zero hosting cost: Actions provides compute and Pages provides hosting.
- Nothing to go down: no database or web server.
- Each stage is independently testable. The pytest suite enforces a 75% coverage floor
  with the network blocked.
- Per-company failures are visible in `health.json` instead of disappearing into logs.

**Negative**
- Contributors need to learn a package layout instead of one file. The module map in
  [architecture.md](../architecture.md) mitigates this.
- Data only lives as long as the last deploy. There is no history beyond
  `data/market-history.json`.

## Review Trigger

Revisit when:
- A source needs authenticated access (OAuth, API keys), which would force secrets into CI.
- A run no longer fits comfortably in the 25-minute job timeout.
- Features need server-side state (accounts, alerts) that static files cannot provide.

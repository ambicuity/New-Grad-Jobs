# ADR-0001: Python Single-Script Scraper Architecture

**Date:** 2026-01-17
**Status:** Accepted
**Deciders:** Ritesh Rana (maintainer)

---

## Context

The New Grad Jobs aggregator needs to fetch job listings from multiple company ATSs (Greenhouse, Lever, Google Careers, JobSpy), filter them for new-grad relevance, and write the results to `jobs.json` and `README.md` on a 5-minute cycle via GitHub Actions.

The core architectural question was: **how to structure the Python backend.**

Options considered:

1. **Single-script architecture** — One large `scripts/update_jobs.py` file handling all logic
2. **Multi-module package** — Separate `scraper/`, `filter/`, `config/`, `output/` packages
3. **Microservices / separate workers** — One process per ATS, coordinated via a queue

---

## Decision

**Option 1 — Single-script architecture** was chosen.

All scraping, filtering, categorization, deduplication, and output generation live in `scripts/update_jobs.py`, driven by `config.yml`.

---

## Rationale

| Criterion | Single-script | Multi-module | Microservices |
|-----------|--------------|--------------|---------------|
| Setup complexity | Low | Medium | High |
| GitHub Actions simplicity | `python update_jobs.py` | Requires packaging | Requires orchestration |
| Contributor on-boarding | New contributors read one file | Must navigate multiple modules | Must understand distributed system |
| State sharing (dedup sets, caches) | Trivial (in-memory) | Shared state is complex | Requires external store (Redis etc.) |
| CI/CD footprint | 1 process, 1 step | 1 process, multiple steps | Multiple processes |

At the current scale of ~150 companies and a 5-minute cycle, the overhead of inter-process communication and package management is not justified.

Internal parallelism (50+ concurrent workers via `ThreadPoolExecutor`) is sufficient to handle throughput without process-level distribution.

---

## Consequences

- **Positive**: Zero-dependency runner. `python update_jobs.py` is all any contributor needs to know.
- **Positive**: Easy to understand the full data flow end-to-end in a single read.
- **Negative**: As the file grows beyond ~2,000 lines, it will need to be split. See ADR-0003 (future) for the planned modularization strategy.
- **Negative**: Mixing I/O-bound (HTTP) and CPU-bound (string matching, categorization) work in one thread pool is suboptimal at very large scale.

---

## Review Trigger

This decision should be revisited when:
- The script exceeds 3,000 lines
- We add a new source type requiring fundamentally different auth (e.g., OAuth flows)
- We need to run scrapers on different schedules (e.g., Workday every 15 minutes vs Google every 5)

# ADR-0003: Job Filtering Algorithm Design

**Date:** 2026-03-02
**Status:** Accepted
**Deciders:** Ritesh Rana (maintainer)

---

## Context

The scraper retrieves hundreds of raw job postings from Greenhouse, Lever, Google Careers, and JobSpy (LinkedIn/Indeed). Not all postings are appropriate for new graduates. The filtering step needs to:

1. Narrow listings to recent postings (within the last N days, configurable)
2. Include only titles that signal "entry-level" or "new grad" intent
3. Exclude titles that indicate seniority (Manager, Director, Senior, Staff, Principal)
4. Restrict to US/Remote locations (configurable)
5. Deduplicate by URL across all sources

The approach must be performant enough to run on every 5-minute cycle without adding latency.

---

## Decision

All filtering logic is centralized in the `filter_jobs()` function in `scripts/update_jobs.py`. The algorithm is:

1. **Date filter** — Accepts `max_days_old` from `config.yml`. Jobs older than this threshold are dropped. If a date cannot be parsed, the job is kept (safe default).
2. **Title keyword require filter** — The job title must contain at least one of the `title_keywords` list. Case-insensitive substring match.
3. **Title exclude filter** — The job title must not contain any of the `exclude_keywords` list. Case-insensitive substring match.
4. **Location filter** — At least one of the user-configured location strings must appear in the job's location field.
5. **Deduplication** — A `seen_urls` set is maintained per run; duplicate URLs are discarded in iteration order (first-seen wins).

All configuration lives in `config.yml` under the `filtering` key, allowing maintainers to tune behavior without code changes.

---

## Rationale

| Criterion | Decision |
|---|---|
| Keyword-based filtering | Simple, fast, maintainable — no ML overhead for a 5-minute pipeline |
| Configurable threshold (N days) | Allows community tuning based on job market seasonality |
| Case-insensitive match | Correct for job boards that use inconsistent casing |
| First-seen deduplication | Preserves earliest/best-quality record from the primary source |
| No false-positive protection | Acceptable miss rate; users prefer completeness over strict precision |

---

## Consequences

- **Positive**: Simple to test thoroughly with unit tests.
- **Positive**: Fully configurable via `config.yml` without deploys.
- **Negative**: Keyword matching means a role titled "New Grad Software Engineer (Senior Track at Company)" would still be included — this is an edge case and acceptable.
- **Negative**: No semantic understanding — cannot distinguish between "entry-level" for FAANG vs. true new-grad targeted roles.

---

## Review Trigger

Revisit when:
- False-positive rate exceeds 10% of listed jobs (measured via community reports)
- We introduce ML/AI classification capability
- A new ATS source provides structured seniority metadata directly

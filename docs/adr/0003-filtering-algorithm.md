# ADR-0003: Job Filtering Algorithm Design

**Date:** 2026-03-02 (revised 2026-09 for v1.0.1)
**Status:** Accepted
**Deciders:** Ritesh Rana (maintainer)

---

## Context

The scraper retrieves thousands of raw postings from Greenhouse, Lever, Ashby, Workday and
JobSpy. Most are not appropriate for new graduates. The filter has to:

1. keep only recent postings;
2. keep titles that signal entry-level / new-grad intent;
3. drop senior, staff, lead, manager, intern and level III+ titles;
4. keep only locations in the target countries;
5. stay configurable without code changes, and be fast enough to run every 30 minutes.

The first version used case-insensitive **substring** matching. It produced systematic
false positives and false negatives: `ai` matched "Maint**ai**nance", `I` matched a
middle initial, `2026` matched a requisition id, and `intern` missed "Internship".

## Decision

`filter_jobs()` in `scripts/ngj/filters.py` is the single inclusion gate, applied after
deduplication ([ADR-0004](0004-deduplication-strategy.md)). Signals come from
`config.yml` → `filtering`, with defaults in code. For each job:

1. **Exclusions first.** The job is dropped if its title contains an
   `exclusion_signals` word (senior, staff, principal, lead, manager, director, intern,
   …) or a **level III+ marker** ("Engineer III", "Engineer 3", "Level 4", "L5").
   Titles that also name level I/II ("Software Engineer II/III") are kept. So are
   entry-level titles that merely contain an exclusion word ("Associate Product
   Manager").
2. **A new-grad signal is required:** one of `new_grad_signals` or a standalone
   entry-level token from `level_signals` ("Engineer I", "SDE II", "(L3)").
3. **Then either** a `strong_new_grad_signals` phrase (new grad, campus, early career,
   cohort years) **or** a `track_signals` word (software, data, ML, SRE, …). The ambiguous
   `network` track only counts on engineering-focused titles.
4. **Recency:** `posted_at` within `filtering.max_age_days` (60).
5. **Location:** the target countries are the **United States, Canada and India**,
   including remote roles there and locations with no country at all. A location that
   names only foreign places is dropped.

Every signal matches at **token boundaries**, never as a raw substring. Level tokens only
count in level positions, so "L3Harris", "I/O" and "Alvin I. Goodman" are not levels.
Common inflections match ("Engineering", "Developers", "Interns", "Internship").

Categorization is not part of the gate. It runs afterwards in enrichment, and it is
**title first**: the first `CATEGORY_PATTERNS` category whose keywords appear in the title
wins. The description is only consulted when the title matches nothing, and never for the
title-only specialty buckets (frontend, backend, mobile, security).

## Rationale

| Criterion | Decision |
|---|---|
| Keyword signals, not ML | Deterministic, explainable, testable and free to run every 30 min |
| Token-boundary matching | Removes the substring false positives without losing inflections |
| Explicit level III+ rule | Seniority often only appears as a numeral |
| Broad gate (owner decision) | An unlevelled "Software Engineer" passes on signals, because users prefer completeness to strict precision |
| Config-driven | Maintainers tune `filtering.*` without code changes |

## Consequences

- **Positive:** each rule has focused unit tests (`tests/test_filter.py`,
  `tests/test_location.py`, `tests/test_signal_detection.py`).
- **Positive:** adding a signal is a one-line `config.yml` change, and
  `validate_config.py` checks the shape.
- **Negative:** still no semantic understanding. A genuinely senior role with no
  seniority word in its title can pass.
- **Negative:** the cohort years in the strong signals must be moved forward each hiring
  cycle.

## Review Trigger

Revisit when:
- community reports show more than 10% false positives among listed jobs;
- a source starts providing structured seniority metadata;
- the target country set changes.

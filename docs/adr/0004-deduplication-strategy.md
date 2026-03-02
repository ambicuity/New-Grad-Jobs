# ADR-0004: Multi-Source Deduplication Strategy

**Date:** 2026-03-02
**Status:** Accepted
**Deciders:** Ritesh Rana (maintainer)

---

## Context

The scraper aggregates jobs from multiple sources (Greenhouse, Lever, Google Careers, JobSpy/LinkedIn/Indeed). The same job at the same company frequently appears across multiple sources with:

- Different URLs (e.g., the company's own Greenhouse URL vs. the LinkedIn repost)
- Slightly different titles (typos, formatting)
- Different metadata (location string, posted_at timestamp)

Without deduplication, the README and `jobs.json` contain duplicates that harm user trust and inflate counts.

---

## Decision

Deduplication is **URL-based**, not title-based:

1. **Primary key**: The job's `url` field, after stripping query parameters and trailing slashes.
2. **Implementation**: A `seen_urls: set[str]` is maintained within each `filter_jobs()` call. On each candidate job, the normalized URL is checked against this set. If already present, the job is dropped.
3. **First-seen wins**: Among duplicates, the first occurrence in the processing pipeline is preserved. Source priority order: Greenhouse → Lever → Google Careers → JobSpy.
4. **Cross-session behavior**: The set is not persisted between runs. Each 5-minute cycle re-evaluates all jobs from scratch.

---

## Alternatives Considered

### Option A: Title + Company fuzzy deduplication
- Compare normalized `(title, company)` pairs using fuzzy string matching (e.g., Levenshtein distance).
- **Rejected**: High false-positive rate. "Software Engineer" and "Software Engineer, New Grad" at the same company are different roles.

### Option B: Job ID-based deduplication
- Use the ATS's internal job ID (available from Greenhouse and Lever APIs).
- **Rejected**: IDs are source-specific. Cross-source deduplication still requires a secondary signal.

### Option C: URL normalization + Title similarity hybrid
- Combine URL deduplication with title fuzzy matching for cases where the same job is posted at different URLs.
- **Future consideration**: Feasible once we see a measurable duplicate rate from non-URL-normalized sources.

---

## Consequences

- **Positive**: Simple, deterministic, zero false positives.
- **Positive**: No external dependencies (no fuzzy matching library needed).
- **Negative**: Two listings of the same job at genuinely different URLs are not deduplicated. Accepted trade-off for simplicity.
- **Negative**: URL normalization does not strip all UTM parameters — minor issue since ATS URLs rarely include them.

---

## Review Trigger

Revisit when:
- Community reports show >5% visible duplicate jobs in the README
- We add sources where the same job appears at structurally different URLs (e.g., LinkedIn Easy Apply vs. Direct Apply)

# ADR-0004: Job Identity and Multi-Source Deduplication

**Date:** 2026-03-02 (revised 2026-09 for v1.0.1)
**Status:** Accepted
**Deciders:** Ritesh Rana (maintainer)

---

## Context

The same role often reaches the scraper more than once:

- the same posting URL, repeated or decorated with tracking parameters (`utm_*`, `gh_src`);
- a company whose board exists on two ATSs (for example Greenhouse and Ashby during a
  migration);
- an ATS posting re-listed on Indeed through JobSpy, under a different URL.

Duplicates inflate counts and erode trust. Separately, the site, the RSS feed and the
per-job pages (`/job/<job_id>/`) need an identifier that stays **stable across runs**. The
old `id` was a `company-title-location` slug, and it changed whenever a title or location
was edited.

## Decision

**Identity.** `job_id = "job_" + sha256(identity)[:20]`, where the identity is the job's
`source` plus its **canonical URL** (`scripts/contracts.py`). The canonical URL uses a
lowercased host, drops the default port and trailing slash, keeps only posting-id query
params (`gh_jid`, `jk`, `jobid`, …), and drops fragments. Jobs without a usable URL fall
back to source + company + title + location. `id` is kept in jobs.json for compatibility
and always equals `job_id` (schema 1.1).

**Deduplication** (`scripts/ngj/dedup.py`, before filtering) runs two order-preserving,
non-mutating passes:

1. **Same posting:** jobs with the same `job_id` collapse to the first one. Because the
   published id is that same hash, this pass is what guarantees unique `job_id`s. The
   integrity check verifies it.
2. **Cross-source:** jobs from **different** sources with the same normalized company
   (legal suffixes dropped) and normalized title, and a **compatible location**, are one
   role. The preferred source wins: **ATS-direct beats aggregators** (JobSpy / Indeed /
   LinkedIn). Among ATSs, the one carrying more data (description, date, location, pay)
   wins, and ties go to the first seen. Locations are compared by their place-name words,
   ignoring country/state codes and "remote". A location with no place-name words is
   compatible with anything.

Jobs from the **same** source are never merged by the cross-source pass. Distinct
requisitions often share a title and location.

## Alternatives considered

- **Fuzzy title matching (Levenshtein):** rejected. "Software Engineer" and "Software
  Engineer, New Grad" at the same company are different roles.
- **ATS-native job ids:** rejected as the primary key. They are source-specific and still
  need a cross-source signal. The canonical URL keeps them anyway (`gh_jid`, `jk`).
- **URL-only dedup (the original design):** kept as pass 1, but it cannot catch the same
  role at structurally different URLs, which pass 2 now handles.

## Consequences

- **Positive:** stable ids power `first_seen` carry-forward, RSS guids, description shards
  and per-job pages.
- **Positive:** aggregator re-posts no longer duplicate ATS listings, and the richer ATS
  record is kept.
- **Negative:** an employer that changes a posting's URL gets a new `job_id`. It looks
  like a new job, with a fresh `first_seen`.
- **Negative:** two genuinely different same-titled roles at the same company, listed on
  different sources in compatible locations, would be merged. This is accepted as rare.

## Review Trigger

Revisit when:
- community reports show more than 5% visible duplicates;
- a new source formats URLs so that canonicalization splits one posting into several ids.

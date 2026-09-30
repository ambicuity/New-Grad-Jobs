---
title: Job freshness
description: What "posted", "first seen" and the LIVE stamp mean, how new roles are marked, and how to tell whether the board itself is current.
updated: 2026-09-30
section: NGJ data
order: 5
---

Freshness is two different questions: how new is this job, and how current is the board showing it. The board answers both with data it actually has, and this page says what each figure means.

## Posted date

The board shows the posted date supplied by the source and uses it for the default newest-first sort. Sources differ: some provide the original publication time, some a last edit, and some no date. An unknown posted date is shown as a dash and is not included in NEW 24H; the site does not substitute first seen for it. NEW 24H and the corresponding row marker use the posted timestamp.

## First seen

Separately, the board carries forward a first-seen timestamp for each stable job id from the previous published run. When previous records are available, a newly encountered job gets the current run time. During a bootstrap run without previous records, the scraper uses the source's posted date when available, otherwise the run time. The [new this week](../../jobs/new-this-week/) page and discovery filters use first seen, so the bootstrap fallback means it is not always the literal first observation. Jobs absent from the previous run can also receive a new first-seen value when they reappear.

## The LIVE stamp

The word in the top bar reports the board's own currency. It reads LIVE when the last completed scrape finished within the last 24 hours, STALE when it is older, and OFFLINE when the health file could not be loaded. Hover over it for the exact age. Runs happen about every 30 minutes, so LIVE normally means less than an hour old. The [about page](../../about/) shows when the data was generated.

## Why the board can be a little behind

- A run is refused by the collapse guard when a source fails badly, so the previous data stays up until the next good run. [How job data is collected](../how-job-data-is-collected/) explains.
- Pages are cached at the edge for a few minutes, so two people can see runs a few minutes apart.
- Employers do not always remove closed roles promptly. [Expired jobs](../expired-jobs/) covers that.

None of these produce invented dates. If the board does not know when something happened, it shows nothing rather than an estimate.

## Using freshness

- Apply promptly when you can, while checking eligibility and application quality. Rolling review can close before a stated deadline; early submission does not guarantee review.
- Subscribe to a feed; entries appear the run they are first seen, which is as early as the board knows.
- Treat an old posted date with a recent first-seen as a reposted or newly discovered role, and read it with that in mind.
- If the stamp reads STALE, the board is not currently updating; the data is still the last good run and the feeds will resume when the scrape does.

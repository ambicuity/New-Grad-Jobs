---
title: Job freshness
description: What "posted", "first seen" and the LIVE stamp mean, how new roles are marked, and how to tell whether the board itself is current.
updated: 2026-09-25
section: NGJ data
order: 5
---

Freshness is two different questions: how new is this job, and how current is the board showing it. The board answers both with data it actually has, and this page says what each figure means.

## Posted date

Each source reports when the employer published the posting, and the board shows that date on the row and uses it for the default newest-first sort. Sources differ in how they report it: some give the original publication time, some give the last edit, and a few give nothing. When a posting has no date, the board uses the time it first saw it instead. The NEW 24H count in the status bar and the marker on a row are based on this posted date.

## First seen

Separately, the board records the first run in which it saw each job, using the job's stable id. That timestamp is carried forward from run to run, so it does not reset when an employer edits a posting. It drives the [new this week](../../jobs/new-this-week/) page and the "new" link on the board, which list everything first seen in the last seven days. First seen is the board's own observation and does not depend on how a source reports dates, which is why it is used for those views.

## The LIVE stamp

The word in the top bar reports the board's own currency. It reads LIVE when the last completed scrape finished within the last 24 hours, STALE when it is older, and OFFLINE when the health file could not be loaded. Hover over it for the exact age. Runs happen about every 30 minutes, so LIVE normally means less than an hour old. The [about page](../../about/) shows when the data was generated.

## Why the board can be a little behind

- A run is refused by the collapse guard when a source fails badly, so the previous data stays up until the next good run. [How job data is collected](../how-job-data-is-collected/) explains.
- Pages are cached at the edge for a few minutes, so two people can see runs a few minutes apart.
- Employers do not always remove closed roles promptly. [Expired jobs](../expired-jobs/) covers that.

None of these produce invented dates. If the board does not know when something happened, it shows nothing rather than an estimate.

## Using freshness

- Apply within days of first seen when you can. Rolling review means early applications are read against a smaller pile.
- Subscribe to a feed; entries appear the run they are first seen, which is as early as the board knows.
- Treat an old posted date with a recent first-seen as a reposted or newly discovered role, and read it with that in mind.
- If the stamp reads STALE, the board is not currently updating; the data is still the last good run and the feeds will resume when the scrape does.

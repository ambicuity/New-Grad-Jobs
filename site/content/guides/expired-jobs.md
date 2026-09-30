---
title: Expired and closed jobs
description: How the board notices a job has closed, why some closed jobs linger for a run, and what the closed marker means.
updated: 2026-09-30
section: NGJ data
order: 4
---

A job board is only as useful as its closed jobs are rare. This board handles closure in two ways: it drops postings that disappear from their source, and it marks postings that say they are closed while still being published. Neither is perfect, and the imperfections are described here.

## Disappearance

The main mechanism is the simplest one. Every run refetches every board, and a posting that is no longer returned by its source is no longer on the board. With runs about every 30 minutes, a job that an employer takes down is gone from here within an hour in the normal case.

## Closed markers

Some employers leave a posting up but edit it: "[Closed]" in the title, "this position has been filled" or "no longer accepting applications" in the description. The scraper looks for a short list of such phrases and title markers and sets a closed flag. The board shows those rows dimmed with a CLOSED tag rather than removing them, because the employer has not removed them either and the text is the only evidence. Their stable pages stay up, marked closed and hidden from search engines, so a shared link explains itself instead of failing.

The phrase list is deliberately strict. Early versions matched the bare words "closed" and "expired" and produced false positives on ordinary descriptions ("closed-loop control", "until the requisition is closed"). The current rules match whole phrases that indicate closure, and "position is filled" alone is not matched because "reviewed on a rolling basis until the position is filled" can appear in open postings. Unusual wording can still be missed, and false positives remain possible; verify the employer's current page.

## The 60-day window

Independently of either mechanism, a posting with a known date older than 60 days leaves the curated set, and one older than 120 days leaves the near-miss tier. This is a freshness rule, not evidence that the employer has stopped hiring. Missing or unparseable dates pass the recency check. The WIDEN SCOPE toggle for "posted 60–120 days ago" brings back eligible older postings; enable any other recorded reasons too.

## When a source is down

The run records source failures and checks the resulting drop before publishing. It refuses publication when the overall count falls by more than 40%, or a source that previously had more than 100 jobs returns none. Smaller losses can still be published: failed-company jobs are not automatically carried forward. Disappearance therefore does not by itself prove closure. [How job data is collected](../how-job-data-is-collected/) explains the guards.

## What you can do

- Sort newest first (the default) and use the "new this week" page to prioritize recent discoveries, then check whether the employer still accepts applications.
- If a job page says the role is closed but the employer's site still accepts applications, apply anyway; the employer's site is the source of truth.
- Report a pattern of missed closures on [GitHub](https://github.com/ambicuity/New-Grad-Jobs) with the job link; a new phrase is a one-line change with a test.

[Job freshness](../job-freshness/) covers the other side: how you can tell how new a posting is.

---
title: Duplicate jobs
description: Why the same role appears on several sites, how the board decides two postings are one, and why a few duplicates remain.
updated: 2026-09-25
section: NGJ data
order: 3
---

The same job is often published in several places: on the employer's Greenhouse board, on Indeed, and sometimes on a second career site after a migration. Left alone, a board built from many sources would list one opening three times and its counts would be wrong. Two passes remove most of the repetition without merging distinct jobs.

## Pass one: the same posting

Every posting gets an identity computed from its source and its URL, after tracking parameters are stripped. Two fetches of the same page are the same posting, and only the first is kept. This identity is also the job's published id, which is why each job has a stable page and why the id survives between runs. A posting with no URL gets an identity from company, title and location instead.

## Pass two: the same role on two sources

Jobs from different sources with the same normalized company, the same title and a compatible location are treated as one role listed twice. Locations are compared by their place names, ignoring country codes and words like "remote", because every source formats them differently. When two match, the better source wins: an employer's own board beats an aggregator such as Indeed, and among employer boards the one carrying more data wins, with ties going to the source seen first.

Jobs from the same source are never merged in this pass. Employers routinely post several distinct requisitions with the same title and location, one per team, and collapsing them would hide real openings.

## What still gets through

- The same role with different titles on two sites ("Software Engineer I" and "Software Engineer, New Grad")
- The same role at two locations that share no place-name words
- A requisition reposted with a new URL after it was closed and reopened

These show as separate rows. They are a small fraction, and the board would rather show an occasional duplicate than drop a real job by guessing.

## Applicant side

If you see a role twice, apply through the employer's own site. It is the version the board prefers, it is the one the employer maintains, and applying twice through two channels can create two candidate records for the same person, which recruiters find confusing. Mark the job applied on the board (`a`) and it stays marked across runs because the id is stable.

## Reporting a duplicate

Duplicates that follow a pattern are worth an issue on [GitHub](https://github.com/ambicuity/New-Grad-Jobs) with the two job links. The comparison rules live in one file and are tested, so a clean example usually turns into a small fix. [How job data is collected](../how-job-data-is-collected/) explains where the postings come from in the first place.

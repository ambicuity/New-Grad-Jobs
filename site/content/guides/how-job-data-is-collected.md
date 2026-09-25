---
title: How job data is collected
description: Where every posting on this board comes from, how often the scraper runs, and what happens when a source fails.
updated: 2026-09-25
section: NGJ data
order: 1
---

Every job on this board was fetched by a program from a company's own career site or from Indeed, within the last few hours. Nobody submits postings, nobody edits them, and nothing is stored anywhere except as published files. This page describes that pipeline; the code is open source on [GitHub](https://github.com/ambicuity/New-Grad-Jobs) and the [about page](../../about/) shows the live figures.

## Sources

Four applicant tracking systems publish public job APIs, and most employers with a serious campus program use one of them:

- **Greenhouse**, **Lever** and **Ashby** expose a JSON list of open jobs per company board.
- **Workday** exposes a search endpoint per tenant, queried page by page.

A list of company boards, several hundred of them across every field, is kept in the repository's configuration file, and anyone can propose an addition by opening an issue. Indeed is queried too, through the JobSpy library, with a set of entry-level search terms, to catch employers that do not use one of the four systems. Each source is an adapter that returns jobs plus any errors it met.

## Schedule

A GitHub Actions workflow runs the scraper about every 30 minutes, around the clock. Each run fetches every configured board, deduplicates the result ([Duplicate jobs](../duplicate-jobs/)), applies the rules ([How NGJ classifies jobs](../how-ngj-classifies-jobs/)), and publishes static files that the site is built from. A separate watchdog re-runs the scrape if the published data is more than three hours old. There is no server and no database; the whole board is files on a content delivery network.

## When a source fails

Career-site APIs go down, rate-limit, or change shape. The scraper never lets one company's failure stop a run: errors are recorded per company and per source and published in the health file, and the run continues with what it got. Workday tenants in particular fail in groups, so a partial Workday result is normal and visible.

Two guards protect the board from a bad run. If the total number of jobs would drop by more than 40% compared with the previous run, or if a source that had more than a hundred jobs suddenly returns none, the run refuses to publish and the previous data stays live. That is why a source outage usually shows up as slightly stale data rather than as an empty board.

## What is published

- **jobs.json**: every open role that passed the rules, with a documented schema
- **jobs-index.json** and per-shard description files, which the site loads
- **feed.xml** and one feed per category, plus remote and "no restriction stated"
- **health.json**: run time, per-source counts and errors, failed companies
- **jobs-extended.json**: the near misses behind WIDEN SCOPE
- **corpus-index.json**: a compact row per unique posting seen, behind EXPLORE

All of it is public and reusable. If you build something with it, the [about page](../../about/) links the schema.

## What is not collected

No personal data: there are no accounts, and the saved and applied lists live only in your browser. The scraper reads public job pages and nothing else.

---
title: How to use this board
description: Filters, alerts, saved and applied lists, keyboard shortcuts and the data behind every count.
updated: 2026-09-25
section: Getting started
order: 1
---

NGJ is a live list of new grad and entry-level jobs pulled straight from company career sites. It refreshes about every 30 minutes, and every number on it is computed from the published data. This guide is the two-minute tour.

## Filtering

The left rail holds the facets: ROLE (thirty categories from software engineering to healthcare), REMOTE, COUNTRY, VISA / CITIZENSHIP, COMPANY TIER, LOCATION (the busiest metros) and HIRING NOW (every company with open roles). Chips combine: pick a role and a metro and you see only that intersection. The search box matches company, title and location, and every word you type must appear.

Everything you set lives in the URL, so a filtered view is a link you can share or bookmark. Esc clears the whole thing.

## Alerts

Every category, plus remote and "no visa restriction stated", has its own RSS feed. The status bar shows the feed that matches your current view; the [browse pages](../../jobs/) link the feed for each page. Paste a feed into your reader, or into an RSS-to-email service, and you get new roles the moment the scraper sees them.

## Saved and applied

The star saves a job in your browser; the APPLIED button (or the `a` key) marks it as applied. Both lists stay in this browser only, and there is no account. The LINK button copies a stable page for the job that you can send to someone.

## Keyboard

- `/` focuses search, `Esc` leaves it or clears filters
- `j` `k` or the arrow keys move through jobs, `Enter` opens the application
- `s` saves, `a` marks applied, `F2` cycles the sort
- `?` shows the full list

## What "no restriction stated" means

The scraper reads each posting for two things: a statement that the employer will not sponsor a visa, and a requirement for citizenship or a security clearance. A job with neither is shown as "no restriction stated". That is not a promise of sponsorship, only the absence of a stated restriction. Read the posting before you apply.

## The data

Everything the site shows is also published as files: [jobs.json](../../jobs.json) (every open role, documented schema), [feed.xml](../../feed.xml) and [health.json](../../health.json) (the scraper's own telemetry). The [about page](../../about/) explains the sources and the rules in full.

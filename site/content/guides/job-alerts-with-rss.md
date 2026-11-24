---
title: Job alerts with RSS and email
description: How to follow new-grad postings with NGJ's RSS feeds and get updates by email without missing the application window.
updated: 2026-11-24
published: 2026-11-24
section: NGJ data
order: 7
format: checklist
use_when: Read this when you want new postings delivered to a feed reader or your inbox instead of checking the board by hand.
you_get: You get the feed URLs to use, how to narrow them to your field, and how to turn a feed into email alerts.
---

The board refreshes throughout the day, and the fastest way to apply early is to let a feed reader or an email tool watch it for you. NGJ publishes RSS feeds but does not send email itself; the email part comes from a reader or automation tool you choose. This checklist takes you from a feed URL to alerts you will actually read.

## Pick the feed that matches your search

- **Everything:** [feed.xml](../../feed.xml), ordered by when NGJ first saw each posting rather than by the employer's posted date.
- **One field:** a per-category file under `feeds/`, such as [feeds/software-engineering.xml](../../feeds/software-engineering.xml). Category names match the ones used on the board.
- **Location and visa filters:** [feeds/remote.xml](../../feeds/remote.xml) and [feeds/no-visa-restriction.xml](../../feeds/no-visa-restriction.xml).

All of these are generated from the same [jobs.json](../../jobs.json) data, so a posting in a narrow feed is also in the main one. For what the underlying fields mean, see [How job data is collected](../how-job-data-is-collected/).

## Subscribe in a feed reader

1. Copy the URL of the feed you picked from the links above.
2. In a feed reader you already use, or one you install for this, add the URL as a new feed, often labelled "Subscribe to feed" or "Add RSS".
3. Name the feed something you will recognise, such as "NGJ — remote data roles", so new items are easy to scan.
4. Set the reader to check every few hours. NGJ publishes new postings all day, so checking only once a day can cost you a head start.
5. Open a couple of items and confirm the link goes to the employer's own posting. NGJ links out to the original job page.

A reader also keeps a history of what you have read, which makes genuinely new postings easier to spot on your next visit.

## Turn the feed into email

NGJ does not run a mailing list. To get messages in your inbox:

1. Choose a feed-to-email tool or an automation service that watches an RSS URL and sends a message when a new item appears.
2. Paste the same feed URL you used in your reader.
3. Choose delivery: instant, a digest once or twice a day, or a daily summary. A digest is usually easier to keep up with than one email per posting.
4. Send a test item to yourself and check that the message includes the job title, company and a working link to the posting.
5. Add a filter or label in your mail client so alerts do not bury other messages.

Keep only one email rule per feed. Two tools watching the same URL will send you duplicates.

## Tune the alerts so you keep reading them

- **Start narrow.** One category plus one location filter is usually enough. A feed with everything can produce more items than you can apply to.
- **Act fast.** Alerts help only if you apply within a few days; [Job freshness](../job-freshness/) explains why older postings are a poor bet.
- **Check the source before applying.** A feed item is a copy of the posting. Follow its link and read the employer's page, then use [How NGJ classifies jobs](../how-ngj-classifies-jobs/) if the role or level looks odd.
- **Prune feeds you ignore.** If a feed keeps sending items you never open, remove it rather than training yourself to ignore the alerts.

When a posting is wrong or already closed, report it in the [repository](https://github.com/ambicuity/New-Grad-Jobs/issues) with the job link.

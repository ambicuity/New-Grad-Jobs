---
title: Data Sources
description: Where every NGJ (New Grad Jobs) listing comes from, how and how often it is collected, what is stored and published, and how employers can correct or remove their listings.
effective: 2026-10-15
updated: 2026-10-15
---

This page lists every place NGJ (New Grad Jobs) collects job postings from, and explains how they are collected, stored and published. The [about page](../about/) shows live figures for the latest run: how many postings each source returned, how many boards are configured and which ones failed. The full list of employers and their board addresses is in [config.yml](https://github.com/ambicuity/New-Grad-Jobs/blob/main/config.yml).

## 1. How collection works

- **Schedule.** A program in GitHub Actions runs at 7 and 37 minutes past every hour, and also when the code changes. A run that fails publishes nothing, and the previous data stays live.
- **Method.** For each configured employer, the program requests the public job list from the employer's own careers system, using the same address that the employer's careers page uses. It does not log in, solve CAPTCHAs, or use credentials. It identifies itself with the user agent `NewGradJobs-Aggregator/3.0`, except for two sources that send a browser-style user agent: Workday, whose job sites expect one (NGJ also reads the session token the Workday careers page itself issues), and Indeed, read through JobSpy.
- **Politeness.** Requests are limited per domain, retried with back-off after temporary errors, and paused for a while when a site answers "forbidden" (HTTP 403). Where a source needs a separate request for a job's details, that request is made only for postings that pass the title rules.
- **Filtering.** Only postings that look like new grad or entry-level roles in the United States, Canada or India, and that were posted in the last 60 days, are published. The [about page](../about/) states the rules.

## 2. Sources

| Source | What NGJ reads | Notes |
| --- | --- | --- |
| Greenhouse | each employer's public job board API (`boards-api.greenhouse.io`) | descriptions fetched after filtering |
| Lever | each employer's public postings API (`api.lever.co`) | |
| Ashby | each employer's public job board API (`api.ashbyhq.com`) | |
| SmartRecruiters | each employer's public postings API (`api.smartrecruiters.com`) | |
| Oracle HCM (Oracle Recruiting Cloud) | the public candidate-experience API behind each employer's careers site | |
| Rippling | each employer's public job board API (`ats.rippling.com`) | |
| UKG Pro Recruiting | each employer's public job board (`recruiting.ultipro.com`) | |
| ADP Workforce Now | each employer's public career center (`workforcenow.adp.com`) | |
| Workable | each employer's public job widget (`apply.workable.com`) | direct employers only, no recruiting agencies |
| Paylocity | each employer's public job board page (`recruiting.paylocity.com`) | |
| SAP SuccessFactors | the public search and job pages of each employer's careers site | posting dates read from the job page |
| iCIMS | each employer's careers-site job API, or the public iCIMS job portal and job pages | posting dates read from the job page |
| Workday | each employer's public Workday job site (`*.myworkdayjobs.com`) | some postings' locations are looked up on the job's own page |
| Indeed | Indeed's public job search results, read with the open-source [JobSpy](https://github.com/speedyapply/JobSpy) library, for a set of entry-level search terms in the US, Canada and India | dropped when an employer source has the same role; LinkedIn is not used |

Other adapters exist in the code (Google Careers and a generic GraphQL source), but they are switched off and contribute nothing.

## 3. What is stored and published

From each posting NGJ keeps the title, employer name, location, posting date, salary range when stated, the description converted to plain text, and the link to the original posting. `jobs.json` carries a description excerpt of at most 3,000 characters (empty for some sources, such as Workday); the `descriptions/` files, the board's detail pane and the job pages carry the cleaned description in full, up to 50,000 characters. It adds its own fields: an ID, a category, a company tier, and flags for stated visa or citizenship restrictions.

NGJ has no database. Each run writes static files, which GitHub Pages serves:

- [jobs.json](../jobs.json): every open listing, with a [documented schema](https://github.com/ambicuity/New-Grad-Jobs#jobsjson-schema). The board itself loads `jobs-index.json` (the same data without descriptions) and fetches descriptions from `descriptions/<shard>.json` when you open a job;
- `jobs-extended.json`: "near misses" that pass every hard rule but fail a soft one, shown only when you widen the scope;
- `corpus-index.json`: every unique posting the run saw, used by the EXPLORE tab;
- [feed.xml](../feed.xml) and per-category RSS feeds in `feeds/`;
- [health.json](../health.json): the run's own telemetry;
- static pages for each job, landing pages, the [sitemap](../sitemap.xml) and [llms.txt](../llms.txt).

The repository also stores two files, committed after each run: `README.md`, whose job tables show title, employer, location and link, and `data/market-history.json`, daily aggregate counts kept for 90 days. Because these are committed to git, earlier versions stay in the repository's history.

## 4. Attribution

Every listing names its employer, links to the original posting, and, on its job page, names the source system and the date NGJ last confirmed it open. NGJ is not affiliated with, or endorsed by, any employer or job-system provider listed here. See the [copyright and attribution policy](../copyright/) for what that means for reuse.

## 5. For employers

- **To add your company**, open a pull request that adds your public job board to `config.yml` (the [contributing guide](https://github.com/ambicuity/New-Grad-Jobs/blob/main/CONTRIBUTING.md) explains how), or open an issue.
- **To correct or remove your listings**, email contact@riteshrana.engineer with the subject "Listing correction" or "Listing removal". A removal is made in NGJ's configuration, so later runs do not bring the listings back.
- **If NGJ's requests cause you a problem**, email the same address. The board can be removed, or its request rate reduced.

## 6. Known limits, kept under review

- A source's terms of use, API terms, rate limits and `robots.txt` can change. NGJ reads public endpoints at low volume and stops when asked, but it does not check each source's `robots.txt` automatically. A `robots.txt` file does not decide copyright questions either way.
- Indeed's results are read through JobSpy rather than an official API, so that source is the most likely to change or stop working.
- A role that closes between runs can stay listed for up to one run.

## 7. Changes

This page is updated when a source is added, removed or changes how it is read. Earlier versions are in the [file history on GitHub](https://github.com/ambicuity/New-Grad-Jobs/commits/main/site/content/legal/data-sources.md).

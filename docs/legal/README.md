# Legal pages: sources, audit and maintenance

The site's policy pages are built from Markdown in [`site/content/legal/`](../../site/content/legal/). Those files are the single source of truth. Do not copy their text into other files.

| Page | Source | URL |
| --- | --- | --- |
| Terms of Service | `terms.md` | <https://jobs.riteshrana.engineer/terms/> |
| Privacy Policy | `privacy.md` | <https://jobs.riteshrana.engineer/privacy/> |
| Copyright, Attribution and Third-Party Content | `copyright.md` | <https://jobs.riteshrana.engineer/copyright/> |
| Data Sources | `data-sources.md` | <https://jobs.riteshrana.engineer/data-sources/> |

`site/scripts/seo/legal.mjs` renders each page to `/<slug>/index.html`, with a plain copy at `/<slug>/index.md`, and lists it in the sitemap, in every static page footer and in the board's footer. `site/scripts/seo/llms.mjs` writes `/llms.txt`. `site/scripts/seo/licenses.mjs` writes `/third-party-licenses.txt`. The test `site/test/legal-llms.test.js` checks the front matter and the internal links, and fails on placeholder text.

**To change a policy:** edit the Markdown, set `updated:` to the date, and describe material changes in the commit message. Git history is the version record, and each page links to it. If a data practice changes (for example a new analytics provider, a form, or a new third-party request from the browser), update `privacy.md` in the same pull request.

These documents are legal information drafted from the code. They are not legal advice. The items marked for review below should be checked by a qualified lawyer.

## Audit, 2026-10-15

V marks a fact verified from code, configuration or the live site. I marks a reasonable inference. Q marks an open question for the maintainer.

### 1. Identity and operator

- V: `LICENSE` reads "Copyright (c) 2026 Ritesh Rana". The GitHub owner is `ambicuity`.
- V: `contact@riteshrana.engineer` is already published in `SECURITY.md` and `CODE_OF_CONDUCT.md`.
- V: the site brands itself "NGJ · New Grad Jobs" (`site/index.html`), so the policies use that name.
- V (confirmed by the maintainer, 2026-10-15): NGJ is operated by Ritesh Rana, contact contact@riteshrana.engineer. No postal address is published.

### 2. What the site does

- V: it is static. GitHub Actions scrapes on the `7,37 * * * *` cron (`.github/workflows/update-jobs.yml`), and GitHub Pages serves the result. There is no server, database, account system, form, newsletter, payment or advertising. `APP_CSP` sets `form-action 'none'`.
- V: the only user-generated content is GitHub issues and pull requests, which GitHub hosts.

### 3. Personal data

- V: no data is collected directly through the site.
- V: GitHub Pages logs visitor IP addresses for security, per GitHub's documentation ("What is GitHub Pages?").
- V: GoatCounter is loaded only by the interactive board (`site/src/analytics.js`, imported from `index.html`), three seconds after load. The static pages' CSP is `default-src 'none'` with no script source. GoatCounter's `count.js` sends the path (resolved from the canonical link, so always `/`), the title, the referrer, the screen width, a bot flag and **`location.search`**. The board writes its filters and search text into the query string (`site/src/lib/url-state.js`).
- V: browser storage keys are `ngj:saved-jobs:v1`, `ngj:applied-jobs:v1` (`src/lib/saved.js`), `ng-terminal:gh-v2` (`src/data/contributors-source.js`) and `ng-terminal:gh-commits-v1:<username>` (`src/data/recent-commits.js`). `site/test/legal-llms.test.js` fails if a key in the code is missing from the privacy policy. No cookies are set (no `document.cookie` anywhere in `site/src`).
- V: the browser calls `api.github.com` from the CONTRIBUTORS tab, and avatars load from `avatars.githubusercontent.com` (`APP_CSP` `connect-src` and `img-src`).
- V: postings can contain recruiters' names and work emails. Descriptions are republished in full, up to 50,000 characters, in `descriptions/` and on job pages (`FULL_DESCRIPTION_CHARS` in `scripts/ngj/outputs/jobs_json.py`), with a 3,000-character excerpt in `jobs.json` (`DEFAULT_DESCRIPTION_CHARS` in `scripts/ngj/text.py`).
- V: `README.md` job tables are committed after each run, so past listings stay in git history. `data/market-history.json` keeps 90 days (`RETENTION_DAYS`).
- I: GitHub Pages gives site owners no access to visitor logs (no such feature is documented).
- Q: is "individual pageview" collection on or off in the GoatCounter dashboard, and how long are counts kept?

### 4. Cookies, analytics and tracking

- V: there is no advertising, pixel, fingerprinting or outbound-click instrumentation. `goatcounter` appears only in `analytics.js`.
- V: apply links use `rel="noopener noreferrer"` (`JobDetail.jsx`, static job pages) or `window.open(..., 'noopener,noreferrer')` (`DashboardView.jsx`).
- Review: the site has no consent banner. GoatCounter stores nothing on the device, but EDPB Guidelines 2/2023 read ePrivacy Art. 5(3) broadly, so whether script-triggered transmission needs consent for EU visitors should be checked.

### 5. Hosting and processors

- V: Cloudflare proxies the domain in front of GitHub Pages (`server: cloudflare`, `cf-ray` and `cf-cache-status` headers; DNS resolves to Cloudflare addresses; checked with curl on 2026-10-15). No `Set-Cookie` header is sent. Responses carry Cloudflare's `Report-To` / `NEL` headers (Network Error Logging to `a.nel.cloudflare.com`). Cloudflare Web Analytics auto-injects `static.cloudflareinsights.com/beacon.min.js`, which every page's CSP blocks (seen as a CSP violation in the browser console). Recommended: turn off Web Analytics automatic setup in the Cloudflare dashboard.
- V: GitHub (Pages, Actions, API) and GoatCounter. Fonts are self-hosted (`@fontsource/jetbrains-mono`, CSP `font-src 'self'`). HTTP redirects to HTTPS (checked with curl, 301).

### 6. Job sources

- V: 14 sources are enabled (live `health.json`). Adapters are in `scripts/ngj/sources/`, and boards are listed in `config.yml`. Google and GraphQL are disabled.
- V: the scraper's user agent is `NewGradJobs-Aggregator/3.0` (`scripts/ngj/http.py`), except Workday (`_BROWSER_USER_AGENT`, a Chrome string, plus the careers page's CSRF token) and JobSpy. Requests have per-domain limits, retries and a 403 cooldown. The scraper does not check `robots.txt`.
- V: Indeed is read through JobSpy (`apis.jobspy` in `config.yml`). LinkedIn is disabled.
- Review: Workday requests use a browser user agent rather than the NGJ one. Consider an identifying user agent if Workday tenants accept it.
- Review: Indeed's terms restrict automated access. Scraping job systems' public endpoints may conflict with their terms of service. Check each source's terms and decide whether to keep JobSpy.

### 7. Copyright and redistribution

- V: listings link back to the employer, and job pages name the source system and the "confirmed open" date (`site/scripts/seo/render.mjs`). No employer logos are shown.
- Risk, high: full descriptions (up to 50,000 characters) are republished on job pages and in `descriptions/`, plus 3,000-character excerpts in `jobs.json`, without permission from the employers. This is NGJ's own act of copying, so DMCA notice-and-takedown safe harbours (which cover user-stored content and links) would not clearly protect it. One way to reduce the risk is to publish shorter excerpts, or metadata only, and rely on the link. This is a product decision for the maintainer.
- V: a per-listing takedown has no blocklist. Removal means editing `config.yml` (dropping a board) or adding a code rule.

### 8. Privacy obligations

- Review: whether GDPR or UK GDPR applies under Art. 3(2) is uncertain. The service targets US, Canadian and Indian jobs, but it is reachable from the EU and UK. The policy states legal bases on an "if it applies" basis.
- Review: CCPA thresholds ($26,625,000 revenue from 2025-01-01, per the CPPA), and the Texas TDPSA (small-business carve-out). The policy claims neither coverage nor exemption, and offers the rights to everyone.

### 9. Security and retention

- V: CSPs are set (`vite-plugin.mjs`, `render.mjs`). The URL safety gate is in `scripts/url_safety.py`. Dependencies are hash-locked, actions are SHA-pinned, CodeQL runs, and `SECURITY.md` exists.

### 10. Repository licensing

- V: there is one licence (MIT, `LICENSE`), and it is preserved. `THIRD_PARTY_NOTICES.md` was added. The website bundle's licence texts ship at `/third-party-licenses.txt`, which matters because the OFL font requires its notice to travel with the font.
- Review: `tls-client` bundles compiled Go libraries whose licence was not reviewed. These are not redistributed by NGJ.

## Decisions for the maintainer

1. ~~Confirm the operator~~: confirmed 2026-10-15, Ritesh Rana, contact@riteshrana.engineer.
2. Choose a governing law and venue, or keep the current "none chosen" clause in Terms section 15.
3. Register a DMCA designated agent with the US Copyright Office (<https://www.copyright.gov/dmca-directory/>) if you want the section 512 safe harbours. Agent details must also be published on the site.
4. Decide how much description text to republish (section 7 risk): full text, a short excerpt, or metadata only.
5. Decide on JobSpy/Indeed, given Indeed's terms.
6. Check the GoatCounter settings (individual pageviews, retention). Optionally, strip the query string from counts by counting with a fixed path through a no-JS pixel, so filters and search text never reach GoatCounter.
7. Optionally, add a per-listing blocklist (job_id or URL) to `config.yml`, so takedowns don't require dropping a whole board.

## Pre-publication checklist

- [x] Decision 1 (operator) confirmed
- [ ] Decisions 2 and 3 made, and the Terms and Privacy pages updated to match
- [ ] A lawyer has reviewed the items marked "Review"
- [ ] The `contact@riteshrana.engineer` mailbox is monitored for the subject lines the policies list
- [ ] The GoatCounter dashboard settings match privacy section 3.3
- [ ] After deploy, `/terms/`, `/privacy/`, `/copyright/`, `/data-sources/`, `/llms.txt` and `/third-party-licenses.txt` return 200, and the board footer links to them

// /about/: how the board works, where the data comes from and what it
// deliberately does not do. Every number is read from health.json and the
// jobs data at build time; nothing is typed in by hand.

import { JOB_PAGE_CSP, JOB_PAGE_CSS, REPO_URL } from './render.mjs';
import { escapeHtml } from './text.mjs';

export const ABOUT_PATH = 'about/';
const SOURCE_LABEL = { greenhouse: 'Greenhouse', lever: 'Lever', ashby: 'Ashby', workday: 'Workday', jobspy: 'Indeed (via JobSpy)', graphql: 'GraphQL', google: 'Google Jobs' };

const num = (n) => (typeof n === 'number' && Number.isFinite(n) ? n.toLocaleString('en-US') : null);

/** Facts for the page, all from health.json; missing fields render as "not reported". */
export function aboutFacts(health, { totalJobs, generatedAt }) {
  const h = health && typeof health === 'object' ? health : {};
  const sources = h.sources && typeof h.sources === 'object' ? h.sources : {};
  const counts = h.source_counts && typeof h.source_counts === 'object' ? h.source_counts : {};
  const rows = Object.keys({ ...counts, ...sources }).map((key) => {
    const s = sources[key] && typeof sources[key] === 'object' ? sources[key] : {};
    const errors = s.errors && typeof s.errors === 'object' ? s.errors : {};
    return {
      key,
      label: SOURCE_LABEL[key] || key,
      raw: num(s.raw_count ?? counts[key]),
      configured: num(s.configured_units),
      status: typeof s.status === 'string' ? s.status : '',
      failed: Array.isArray(errors.failed_companies) ? errors.failed_companies.filter((c) => typeof c === 'string') : [],
    };
  });
  return {
    totalJobs: num(totalJobs),
    generatedAt: generatedAt ? generatedAt.toISOString().replace(/\.\d{3}Z$/, 'Z') : '',
    lastRun: typeof h.last_run === 'string' ? h.last_run : '',
    status: typeof h.status === 'string' ? h.status : '',
    configuredCompanyApis: num(h.configured_company_apis),
    activeHiringCompanies: num(h.active_hiring_companies),
    enabledSources: num(h.enabled_sources),
    runDurationSeconds: num(h.run_duration_seconds),
    urlSafetyBlocked: num(h.url_safety_blocked),
    rows,
  };
}

const cell = (v) => (v == null || v === '' ? '<span class="dim">not reported</span>' : escapeHtml(String(v)));

export function renderAboutPage(facts, { siteUrl }) {
  const root = '../';
  const canonical = `${siteUrl}/${ABOUT_PATH}`;
  const description = `How NGJ works: ${facts.totalJobs || 'the'} open new grad roles pulled straight from ${facts.configuredCompanyApis || 'company'} career-site APIs and Indeed, filtered by rule, refreshed about every 30 minutes, with every number published as data.`;
  const rows = facts.rows.map((r) => (
    `<tr><td>${escapeHtml(r.label)}</td><td>${cell(r.raw)}</td><td>${cell(r.configured)}</td><td>${cell(r.status)}</td><td>${r.failed.length ? escapeHtml(r.failed.join(', ')) : '—'}</td></tr>`
  ));
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="${escapeHtml(JOB_PAGE_CSP)}">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>How NGJ works: sources, filters and honesty · NGJ</title>
<meta name="description" content="${escapeHtml(description)}">
<link rel="canonical" href="${escapeHtml(canonical)}">
<link rel="icon" type="image/svg+xml" href="${root}favicon.svg">
<link rel="alternate" type="application/rss+xml" title="New Grad Jobs RSS Feed" href="${root}feed.xml">
<meta property="og:type" content="website">
<meta property="og:site_name" content="NGJ · New Grad Jobs">
<meta property="og:title" content="How NGJ works">
<meta property="og:description" content="${escapeHtml(description)}">
<meta property="og:url" content="${escapeHtml(canonical)}">
<meta property="og:image" content="${escapeHtml(`${siteUrl}/og-image.png`)}">
<meta name="twitter:card" content="summary_large_image">
<style>${JOB_PAGE_CSS}</style>
</head>
<body>
<main>
<nav class="crumb" aria-label="Breadcrumb"><a href="${root}">NGJ</a> › about</nav>
<h1>How this board works</h1>
<p>NGJ is a fully automated board of new grad and entry-level jobs in every field. A scraper in GitHub Actions pulls postings straight from company career-site APIs (Greenhouse, Lever, Ashby, Workday) and Indeed about every 30 minutes, keeps only the roles that pass the rules below, and publishes the result as static files. There is no server, no database and no account.</p>

<h2>THIS RUN</h2>
<dl>
<dt>open roles</dt><dd>${cell(facts.totalJobs)}</dd>
<dt>data generated</dt><dd>${cell(facts.generatedAt || facts.lastRun)}</dd>
<dt>scraper status</dt><dd>${cell(facts.status)}</dd>
<dt>company APIs configured</dt><dd>${cell(facts.configuredCompanyApis)}</dd>
<dt>companies hiring now</dt><dd>${cell(facts.activeHiringCompanies)}</dd>
<dt>sources enabled</dt><dd>${cell(facts.enabledSources)}</dd>
<dt>run duration</dt><dd>${facts.runDurationSeconds ? `${escapeHtml(facts.runDurationSeconds)} s` : '<span class="dim">not reported</span>'}</dd>
<dt>links blocked by the URL gate</dt><dd>${cell(facts.urlSafetyBlocked)}</dd>
</dl>

<h2>SOURCES</h2>
<div class="list">
<table>
<thead><tr><th>Source</th><th>Postings fetched</th><th>Boards configured</th><th>Status</th><th>Failed boards</th></tr></thead>
<tbody>
${rows.join('\n')}
</tbody>
</table>
</div>
<p class="dim">"Postings fetched" is every posting a source returned before filtering; the open-roles figure above is what survived. Per-board failures are normal for Workday tenants and are reported rather than hidden.</p>

<h2>WHAT GETS IN</h2>
<ul class="list">
<li>The title carries a new-grad signal (new grad, graduate, entry level, junior, associate, early career, a cohort year, a level I/II marker) and names a role.</li>
<li>Senior, staff, principal, lead, manager, director, level III+, intern, co-op, student and summer-analyst titles are excluded.</li>
<li>Posted within the last 60 days, located in the United States, Canada or India (remote counts).</li>
<li>Duplicates across sources collapse to one listing; the employer's own posting wins over an Indeed copy.</li>
</ul>

<h2>WHAT WE DELIBERATELY DO NOT DO</h2>
<ul class="list">
<li>No invented, estimated or placeholder numbers, anywhere. Every count on this site is computed from the published data.</li>
<li>No scraping of LinkedIn, and no reselling of your clicks: APPLY goes to the employer's own page.</li>
<li>No guessing whether a role sponsors visas. We only report what the posting states, so "no restriction stated" means exactly that.</li>
<li>No accounts, tracking pixels or third-party scripts beyond a privacy-preserving page counter.</li>
</ul>

<h2>USE THE DATA</h2>
<ul class="list">
<li><a href="${root}jobs.json">jobs.json</a> — every open role, with a documented schema in the <a href="${REPO_URL}#readme" rel="noopener noreferrer">README</a>.</li>
<li><a href="${root}feed.xml">feed.xml</a> — RSS of newly discovered roles, plus per-category, remote and no-visa-restriction slices under <code>feeds/</code>.</li>
<li><a href="${root}health.json">health.json</a> — the run telemetry this page is built from.</li>
<li><a href="${REPO_URL}" rel="noopener noreferrer">Source code</a> — MIT licensed; add a company by opening a pull request.</li>
</ul>
<footer>
<a href="${root}">← all new grad jobs</a> · <a href="${root}jobs/">browse</a> · <a href="${root}guides/">guides</a> · <a href="${root}feed.xml">RSS</a> · <a href="${REPO_URL}">GitHub</a>
</footer>
</main>
</body>
</html>
`;
}

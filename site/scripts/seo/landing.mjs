// Build-time landing pages: one static, script-free page per category, top
// company, top metro, country, plus remote / no-visa-restriction / new-this-week
// and a /jobs/ hub. They target the queries people actually type ("entry level
// software engineer jobs new york") with real, live counts — every number on a
// page is derived from the job data handed in (hard rule: nothing invented).
//
// Paths (all under LANDING_ROOT):
//   jobs/                       hub
//   jobs/<category-slug>/       e.g. jobs/software-engineering/
//   jobs/at/<company-slug>/     e.g. jobs/at/spacex/
//   jobs/in/<metro-slug>/       e.g. jobs/in/new-york-ny/
//   jobs/in/canada/, jobs/in/india/
//   jobs/remote/, jobs/no-visa-restriction/, jobs/new-this-week/

import { CATEGORY_TYPE } from '../../src/lib/taxonomy.js';
import { deriveRmt } from '../../src/lib/jobs.js';
import { parsePostedAt } from './jobposting.mjs';
import { COUNTRY_NAME, metroOf, parseLocation } from './location.mjs';
import { JOB_PAGE_CSP, JOB_PAGE_CSS, REPO_URL, jobPageUrl, jobPath } from './render.mjs';
import { MAIN_FEED, categoryFeedPath, feedlyUrl } from '../../src/lib/feeds.js';
import { escapeHtml, jsonForScript, truncate } from './text.mjs';

export const LANDING_ROOT = 'jobs';
export const DEFAULT_MAX_COMPANIES = 30;
export const DEFAULT_MAX_LOCATIONS = 20;
export const DEFAULT_MIN_COMPANY_JOBS = 3;
export const DEFAULT_MIN_LOCATION_JOBS = 5;
export const DEFAULT_MIN_COUNTRY_JOBS = 1;
export const DEFAULT_LIST_LIMIT = 300;
const ITEMLIST_LIMIT = 100;
const NEW_WINDOW_HOURS = 168;
const META_DESCRIPTION_CHARS = 155;
const SLUG_MAX = 60;
const TOP_COMPANIES_IN_INTRO = 5;
const COUNTRY_PAGES = ['CA', 'IN'];
const RESERVED_SLUGS = new Set(['at', 'in', 'remote', 'no-visa-restriction', 'new-this-week']);

/** URL slug: ASCII lower-case words joined by single dashes, '' when nothing usable remains. */
export function slugify(text) {
  return String(text ?? '')
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, SLUG_MAX)
    .replace(/-+$/g, '');
}

export const landingPageUrl = (siteUrl, path) => `${siteUrl}/${path}`;

const newestFirst = (a, b) => (b.posted ? b.posted.getTime() : 0) - (a.posted ? a.posted.getTime() : 0);
const countBy = (items, key) => {
  const counts = new Map();
  for (const item of items) {
    const k = key(item);
    if (k) counts.set(k, (counts.get(k) || 0) + 1);
  }
  return counts;
};

function firstSeen(entry) {
  return parsePostedAt(entry.job.first_seen) || entry.posted;
}

function isVisaUnrestricted(job) {
  const flags = job.flags;
  return Boolean(flags && typeof flags === 'object' && flags.no_sponsorship === false && flags.us_citizenship_required === false);
}

function countriesOf(location) {
  const { places, remoteCountries } = parseLocation(location);
  return new Set([...places.map((p) => p.country), ...remoteCountries].filter(Boolean));
}

const boardQueryFor = (params) => new URLSearchParams(params).toString();

function describePage(kind, name, entries, generatedAt) {
  const n = entries.length;
  const companies = countBy(entries, (e) => e.job.company).size;
  const remote = entries.filter((e) => deriveRmt(e.job) === 'remote').length;
  const when = generatedAt ? ` Updated ${generatedAt.toISOString().slice(0, 10)}.` : '';
  const what = {
    category: `entry-level ${name} roles`,
    company: `new grad and entry-level roles at ${name}`,
    location: `new grad roles in ${name}`,
    country: `new grad roles in ${name}`,
    remote: 'remote new grad roles',
    visa: 'new grad roles whose posting states no visa sponsorship or citizenship restriction',
    new: 'new grad roles added in the last 7 days',
  }[kind];
  const at = kind === 'company' ? '' : ` at ${companies} ${companies === 1 ? 'company' : 'companies'}`;
  const remoteNote = kind === 'remote' || remote === 0 ? '' : `, ${remote} remote`;
  return `${n} ${what}${at}${remoteNote}. Direct from company career sites, refreshed every 30 minutes.${when}`;
}

const TITLES = {
  category: (name, n) => [`New Grad ${name} Jobs (${n} open) · NGJ`, `New grad ${name} jobs`],
  company: (name, n) => [`New Grad Jobs at ${name} (${n} open) · NGJ`, `New grad jobs at ${name}`],
  location: (name, n) => [`New Grad Jobs in ${name} (${n} open) · NGJ`, `New grad jobs in ${name}`],
  country: (name, n) => [`New Grad Jobs in ${name} (${n} open) · NGJ`, `New grad jobs in ${name}`],
  remote: (name, n) => [`Remote New Grad Jobs (${n} open) · NGJ`, 'Remote new grad jobs'],
  visa: (name, n) => [`New Grad Jobs With No Visa Restriction Stated (${n} open) · NGJ`, 'New grad jobs with no visa or citizenship restriction stated'],
  new: (name, n) => [`New Grad Jobs Added This Week (${n} open) · NGJ`, 'New grad jobs added this week'],
};

function makePage(kind, name, path, boardQuery, entries, generatedAt) {
  const sorted = [...entries].sort(newestFirst);
  const [title, h1] = TITLES[kind](name, sorted.length);
  return {
    kind, name, path, title, h1, boardQuery, entries: sorted,
    description: describePage(kind, name, sorted, generatedAt),
  };
}

function categoryPages(entries, generatedAt) {
  const groups = new Map();
  for (const entry of entries) {
    const category = entry.job.category;
    const id = category && typeof category.id === 'string' ? category.id : '';
    if (!id || id === 'other' || !CATEGORY_TYPE[id]) continue;
    if (!groups.has(id)) groups.set(id, { name: typeof category.name === 'string' && category.name ? category.name : id, entries: [] });
    groups.get(id).entries.push(entry);
  }
  return [...groups].map(([id, { name, entries: list }]) => {
    const slug = slugify(id);
    if (!slug || RESERVED_SLUGS.has(slug)) return null;
    const page = makePage('category', name, `${LANDING_ROOT}/${slug}/`, boardQueryFor({ role: CATEGORY_TYPE[id] }), list, generatedAt);
    return { ...page, categoryId: id };
  }).filter(Boolean);
}

function companyPages(entries, generatedAt, { minCompanyJobs, maxCompanies }) {
  const groups = new Map();
  for (const entry of entries) {
    const name = typeof entry.job.company === 'string' ? entry.job.company.trim() : '';
    if (!name) continue;
    if (!groups.has(name)) groups.set(name, []);
    groups.get(name).push(entry);
  }
  const used = new Set();
  return [...groups]
    .filter(([, list]) => list.length >= minCompanyJobs)
    .sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]))
    .slice(0, maxCompanies)
    .map(([name, list]) => {
      const slug = slugify(name);
      if (!slug || used.has(slug)) return null;
      used.add(slug);
      return makePage('company', name, `${LANDING_ROOT}/at/${slug}/`, boardQueryFor({ co: name }), list, generatedAt);
    })
    .filter(Boolean);
}

function locationPages(entries, generatedAt, { minLocationJobs, maxLocations }) {
  const groups = new Map();
  for (const entry of entries) {
    const metro = metroOf(entry.job.location);
    if (!metro) continue;
    const key = `${metro.locality.toLowerCase()}|${metro.code}`;
    if (!groups.has(key)) groups.set(key, { spellings: new Map(), code: metro.code, entries: [] });
    const group = groups.get(key);
    group.spellings.set(metro.locality, (group.spellings.get(metro.locality) || 0) + 1);
    group.entries.push(entry);
  }
  const used = new Set(COUNTRY_PAGES.map((code) => slugify(COUNTRY_NAME[code])));
  return [...groups.values()]
    .filter((g) => g.entries.length >= minLocationJobs)
    .sort((a, b) => b.entries.length - a.entries.length || a.code.localeCompare(b.code))
    .slice(0, maxLocations)
    .map((g) => {
      const locality = [...g.spellings].sort((a, b) => b[1] - a[1])[0][0];
      const name = `${locality}, ${g.code}`;
      const slug = slugify(name);
      if (!slug || used.has(slug)) return null;
      used.add(slug);
      return makePage('location', name, `${LANDING_ROOT}/in/${slug}/`, boardQueryFor({ metro: name }), g.entries, generatedAt);
    })
    .filter(Boolean);
}

function countryPages(entries, generatedAt, { minCountryJobs }) {
  return COUNTRY_PAGES.map((code) => {
    const list = entries.filter((e) => countriesOf(e.job.location).has(code));
    if (list.length < minCountryJobs) return null;
    const name = COUNTRY_NAME[code];
    return makePage('country', name, `${LANDING_ROOT}/in/${slugify(name)}/`, boardQueryFor({ country: code }), list, generatedAt);
  }).filter(Boolean);
}

function facetPages(entries, generatedAt) {
  const pages = [];
  const remote = entries.filter((e) => deriveRmt(e.job) === 'remote');
  if (remote.length) pages.push(makePage('remote', 'Remote', `${LANDING_ROOT}/remote/`, boardQueryFor({ remote: 'remote' }), remote, generatedAt));
  const visa = entries.filter((e) => isVisaUnrestricted(e.job));
  if (visa.length) pages.push(makePage('visa', 'No visa restriction', `${LANDING_ROOT}/no-visa-restriction/`, boardQueryFor({ visa: 'none' }), visa, generatedAt));
  if (generatedAt) {
    const cutoff = generatedAt.getTime() - NEW_WINDOW_HOURS * 3600 * 1000;
    const fresh = entries.filter((e) => {
      const seen = firstSeen(e);
      return seen && seen.getTime() >= cutoff;
    });
    if (fresh.length) pages.push(makePage('new', 'New this week', `${LANDING_ROOT}/new-this-week/`, boardQueryFor({ new: String(NEW_WINDOW_HOURS) }), fresh, generatedAt));
  }
  return pages;
}

/**
 * @param {{job: object, posted: Date|null}[]} entries  open jobs (as prepared by generate.mjs)
 * @param {{generatedAt?: Date|null, minCompanyJobs?: number, maxCompanies?: number, minLocationJobs?: number, maxLocations?: number, minCountryJobs?: number}} opts
 * @returns {{hub: {path: string, pages: object[]}|null, pages: object[]}}
 */
export function buildLandingPages(entries, {
  generatedAt = null,
  minCompanyJobs = DEFAULT_MIN_COMPANY_JOBS,
  maxCompanies = DEFAULT_MAX_COMPANIES,
  minLocationJobs = DEFAULT_MIN_LOCATION_JOBS,
  maxLocations = DEFAULT_MAX_LOCATIONS,
  minCountryJobs = DEFAULT_MIN_COUNTRY_JOBS,
} = {}) {
  if (!Array.isArray(entries) || !entries.length) return { hub: null, pages: [] };
  const opts = { minCompanyJobs, maxCompanies, minLocationJobs, maxLocations, minCountryJobs };
  const pages = [
    ...categoryPages(entries, generatedAt),
    ...facetPages(entries, generatedAt),
    ...companyPages(entries, generatedAt, opts),
    ...locationPages(entries, generatedAt, opts),
    ...countryPages(entries, generatedAt, opts),
  ];
  if (!pages.length) return { hub: null, pages: [] };
  return { hub: { path: `${LANDING_ROOT}/`, pages }, pages };
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

const depthOf = (path) => path.split('/').filter(Boolean).length;
const rootFrom = (path) => '../'.repeat(depthOf(path));
const formatDate = (date) => (date ? date.toISOString().slice(0, 10) : '');

function head({ title, description, canonical, siteUrl, root, jsonLd }) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="${escapeHtml(JOB_PAGE_CSP)}">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${escapeHtml(title)}</title>
<meta name="description" content="${escapeHtml(description)}">
<link rel="canonical" href="${escapeHtml(canonical)}">
<link rel="icon" type="image/svg+xml" href="${root}favicon.svg">
<link rel="alternate" type="application/rss+xml" title="New Grad Jobs RSS Feed" href="${root}feed.xml">
<meta property="og:type" content="website">
<meta property="og:site_name" content="NGJ · New Grad Jobs">
<meta property="og:title" content="${escapeHtml(title)}">
<meta property="og:description" content="${escapeHtml(description)}">
<meta property="og:url" content="${escapeHtml(canonical)}">
<meta property="og:image" content="${escapeHtml(`${siteUrl}/og-image.png`)}">
<meta name="twitter:card" content="summary_large_image">
<style>${JOB_PAGE_CSS}</style>
${jsonLd ? `<script type="application/ld+json">${jsonForScript(jsonLd)}</script>\n` : ''}</head>`;
}

function jobListItems(entries, root) {
  return entries.map(({ job, posted }) => (
    `<li><a href="${root}${jobPath(job.job_id)}">${escapeHtml(job.title)}</a>`
    + ` <span class="co">${escapeHtml(job.company)}</span>`
    + (job.location ? ` <span class="dim">· ${escapeHtml(job.location)}</span>` : '')
    + (posted ? ` <time datetime="${posted.toISOString()}" class="dim">· ${formatDate(posted)}</time>` : '')
    + '</li>'
  )).join('\n');
}

/** RSS slice for a page: category / remote / visa pages have their own feed, the rest use feed.xml. */
export function feedPathForPage(page) {
  if (page.kind === 'category') return categoryFeedPath(page.categoryId);
  if (page.kind === 'remote') return 'feeds/remote.xml';
  if (page.kind === 'visa') return 'feeds/no-visa-restriction.xml';
  return MAIN_FEED;
}

function subscribeLine(page, root, siteUrl) {
  const path = feedPathForPage(page);
  const absolute = `${siteUrl}/${path}`;
  const scope = path === MAIN_FEED ? 'every new role' : 'new roles on this page';
  return `<p class="subscribe">Get alerts for ${scope}: <a href="${root}${escapeHtml(path)}">RSS feed</a> · <a href="${escapeHtml(feedlyUrl(absolute))}" rel="nofollow noopener noreferrer">open in Feedly</a> · paste the feed URL into any RSS-to-email service (Blogtrottr, Feedrabbit, …) for email alerts.</p>`;
}

function browseNav(siblings, current, root) {
  const featured = siblings.filter((p) => p !== current && ['category', 'remote', 'visa', 'new'].includes(p.kind));
  const links = featured.map((p) => `<a href="${root}${p.path}">${escapeHtml(p.name)}</a> <span class="dim">${p.entries.length}</span>`);
  return `<nav class="browse" aria-label="Browse new grad jobs"><a href="${root}${LANDING_ROOT}/">All pages</a>${links.length ? ' · ' : ''}${links.join(' · ')}</nav>`;
}

function topCompanies(entries) {
  const counts = countBy(entries, (e) => e.job.company);
  return [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, TOP_COMPANIES_IN_INTRO);
}

function itemList(page, siteUrl) {
  return {
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    name: page.h1,
    numberOfItems: page.entries.length,
    itemListElement: page.entries.slice(0, ITEMLIST_LIMIT).map(({ job }, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      url: jobPageUrl(siteUrl, job.job_id),
      name: `${job.title} at ${job.company}`,
    })),
  };
}

/**
 * @param {object} page                one entry of buildLandingPages().pages
 * @param {{siteUrl: string, generatedAt?: Date|null, siblings?: object[], listLimit?: number}} opts
 */
export function renderLandingPage(page, { siteUrl, generatedAt = null, siblings = [], listLimit = DEFAULT_LIST_LIMIT }) {
  const root = rootFrom(page.path);
  const canonical = landingPageUrl(siteUrl, page.path);
  const shown = page.entries.slice(0, listLimit);
  const total = page.entries.length;
  const top = topCompanies(page.entries);
  const companiesLine = page.kind === 'company' || !top.length
    ? ''
    : `<p>Hiring most: ${top.map(([name, n]) => `<span class="co">${escapeHtml(name)}</span> (${n})`).join(', ')}.</p>`;
  const honesty = page.kind === 'visa'
    ? '<p class="dim">"No restriction stated" means the posting text names neither a sponsorship exclusion nor a citizenship requirement. It does not guarantee sponsorship; check with the employer.</p>'
    : '';
  const capNote = total > shown.length
    ? `<p class="dim">Showing the newest ${shown.length} of ${total}. The job board lists all of them.</p>`
    : '';
  return `${head({ title: page.title, description: truncate(page.description, META_DESCRIPTION_CHARS), canonical, siteUrl, root, jsonLd: itemList(page, siteUrl) })}
<body>
<main>
<nav class="crumb" aria-label="Breadcrumb"><a class="brand" href="${root}" aria-label="NGJ, New Grad Jobs, home">NGJ</a> › <a href="${root}${LANDING_ROOT}/">browse</a> › ${escapeHtml(page.name)}</nav>
<h1>${escapeHtml(page.h1)}</h1>
<p>${escapeHtml(page.description)}</p>
${companiesLine}
${honesty}
<div class="actions">
<a class="btn primary" href="${root}?${escapeHtml(page.boardQuery)}">OPEN IN JOB BOARD</a>
</div>
${subscribeLine(page, root, siteUrl)}
${browseNav(siblings, page, root)}
<h2>OPEN ROLES${generatedAt ? ` · UPDATED ${formatDate(generatedAt)}` : ''}</h2>
${capNote}
<div class="list">
<ol>
${jobListItems(shown, root)}
</ol>
</div>
<footer>
<a href="${root}">← all new grad jobs</a> · <a href="${root}feed.xml">RSS</a> · <a href="${REPO_URL}">GitHub</a>
</footer>
</main>
</body>
</html>
`;
}

const HUB_SECTIONS = [
  ['category', 'By role'],
  ['facet', 'By work setup'],
  ['company', 'By company'],
  ['location', 'By city'],
  ['country', 'By country'],
];
const sectionOf = (page) => (['remote', 'visa', 'new'].includes(page.kind) ? 'facet' : page.kind);

/**
 * @param {{path: string, pages: object[]}} hub
 * @param {{siteUrl: string, generatedAt?: Date|null, totalJobs: number}} opts
 */
export function renderLandingHub(hub, { siteUrl, generatedAt = null, totalJobs, guides = [] }) {
  const root = rootFrom(hub.path);
  const canonical = landingPageUrl(siteUrl, hub.path);
  const title = `Browse New Grad Jobs by Role, Company and City (${totalJobs} open) · NGJ`;
  const description = `${totalJobs} new grad and entry-level roles, grouped by role, company, city and work setup. Every count is live from company career-site APIs, refreshed about every 30 minutes.${generatedAt ? ` Updated ${formatDate(generatedAt)}.` : ''}`;
  const sections = HUB_SECTIONS.map(([key, label]) => {
    const pages = hub.pages.filter((p) => sectionOf(p) === key);
    if (!pages.length) return '';
    const items = pages.map((p) => `<li><a href="${root}${p.path}">${escapeHtml(p.name)}</a> <span class="dim">${p.entries.length} open</span></li>`);
    return `<h2>${escapeHtml(label.toUpperCase())}</h2>\n<div class="list"><ul>\n${items.join('\n')}\n</ul></div>`;
  }).filter(Boolean).join('\n');
  const guideLinks = guides.length
    ? `<h2>GUIDES</h2>\n<div class="list"><ul>\n${guides.map((g) => `<li><a href="${root}guides/${escapeHtml(g.slug)}/">${escapeHtml(g.title)}</a></li>`).join('\n')}\n</ul></div>`
    : '';
  return `${head({ title, description: truncate(description, META_DESCRIPTION_CHARS), canonical, siteUrl, root, jsonLd: null })}
<body>
<main>
<nav class="crumb" aria-label="Breadcrumb"><a class="brand" href="${root}" aria-label="NGJ, New Grad Jobs, home">NGJ</a> › browse</nav>
<h1>Browse new grad jobs</h1>
<p>${escapeHtml(description)}</p>
<div class="actions">
<a class="btn primary" href="${root}?">OPEN THE JOB BOARD</a>
</div>
${subscribeLine({ kind: 'hub' }, root, siteUrl)}
${sections}
${guideLinks}
<h2>HOW IT WORKS</h2>
<p><a href="${root}about/">Sources, filter rules and this run's numbers</a>.</p>
<footer>
<a href="${root}">← all new grad jobs</a> · <a href="${root}feed.xml">RSS</a> · <a href="${REPO_URL}">GitHub</a>
</footer>
</main>
</body>
</html>
`;
}

// Build-time SEO generation. Reads the scraper output from public/ (jobs.json
// or jobs-index.json + descriptions/<shard>.json) and writes into dist/:
//   - job/<job_id>/index.html   static page + JobPosting JSON-LD per open job
//   - jobs/…/index.html         landing pages by category, company, metro,
//                               country, remote, visa, new-this-week + hub (landing.mjs)
//   - guides/<slug>/index.html  evergreen guides from site/content/guides/*.md (guides.mjs)
//   - about/index.html          sources, rules and this run's numbers from health.json (about.mjs)
//   - index.html                crawlable list of the newest jobs inside #root
//   - sitemap.xml, robots.txt
// Missing or malformed data never fails the build: generation is skipped with
// a warning and only robots.txt + a home-only sitemap are written.

import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { ABOUT_PATH, aboutFacts, renderAboutPage } from './about.mjs';
import { GUIDES_ROOT, guidePath, loadGuides, renderGuidePage, renderGuidesIndex } from './guides.mjs';
import { descriptionShard, lookupDescription } from '../../src/lib/descriptions.js';
import { buildJobPosting, isSafeJobId, parsePostedAt } from './jobposting.mjs';
import { buildLandingPages, landingPageUrl, renderLandingHub, renderLandingPage } from './landing.mjs';
import {
  injectPrerender, jobPageUrl, renderJobPage, renderPrerenderList, renderRobots, renderSitemap,
} from './render.mjs';

export const DEFAULT_SITE_URL = 'https://jobs.riteshrana.engineer';
export const DEFAULT_PRERENDER_LIMIT = 200;
const WRITE_BATCH = 64;

async function readJson(path, log) {
  let raw;
  try {
    raw = await readFile(path, 'utf8');
  } catch (err) {
    if (err && err.code !== 'ENOENT') log.warn(`[seo] could not read ${path}: ${err.message}`);
    return null;
  }
  try {
    return JSON.parse(raw);
  } catch (err) {
    log.warn(`[seo] malformed JSON in ${path}: ${err.message}`);
    return null;
  }
}

/**
 * Well-formed jobs from the first data file that has any: `jobs` are open,
 * `closed` are the ones the scraper marked is_closed (they still get a
 * noindex page so shared links explain themselves).
 */
export async function loadJobs(publicDir, log = console) {
  for (const name of ['jobs.json', 'jobs-index.json']) {
    const data = await readJson(join(publicDir, name), log);
    if (!data || !Array.isArray(data.jobs)) continue;
    const seen = new Set();
    const wellFormed = data.jobs.filter((j) => {
      if (!j || typeof j !== 'object') return false;
      if (!isSafeJobId(j.job_id) || seen.has(j.job_id)) return false;
      if (typeof j.title !== 'string' || !j.title.trim() || typeof j.company !== 'string' || !j.company.trim()) return false;
      seen.add(j.job_id);
      return true;
    });
    return {
      jobs: wellFormed.filter((j) => !j.is_closed),
      closed: wellFormed.filter((j) => j.is_closed),
      meta: (data.meta && typeof data.meta === 'object') ? data.meta : {},
      source: name,
    };
  }
  return null;
}

function createDescriptionLookup(publicDir, log) {
  const shards = new Map();
  return async function describe(job) {
    const key = descriptionShard(job.job_id);
    if (key) {
      if (!shards.has(key)) shards.set(key, readJson(join(publicDir, 'descriptions', `${key}.json`), log));
      const text = lookupDescription(await shards.get(key), job.job_id);
      if (text) return text;
    }
    return typeof job.description === 'string' ? job.description : '';
  };
}

async function writeInBatches(tasks) {
  for (let i = 0; i < tasks.length; i += WRITE_BATCH) {
    await Promise.all(tasks.slice(i, i + WRITE_BATCH).map((t) => t()));
  }
}

const newestFirst = (a, b) => (b.posted ? b.posted.getTime() : 0) - (a.posted ? a.posted.getTime() : 0);

async function writeGuides(distDir, guides, site) {
  if (!guides.length) return [];
  await mkdir(join(distDir, GUIDES_ROOT), { recursive: true });
  await writeFile(join(distDir, GUIDES_ROOT, 'index.html'), renderGuidesIndex(guides, { siteUrl: site }));
  await writeInBatches(guides.map((guide) => async () => {
    const dir = join(distDir, guidePath(guide.slug));
    await mkdir(dir, { recursive: true });
    await writeFile(join(dir, 'index.html'), renderGuidePage(guide, { siteUrl: site, siblings: guides }));
  }));
  return [`${GUIDES_ROOT}/`, ...guides.map((g) => guidePath(g.slug))];
}

/**
 * @param {{publicDir: string, distDir: string, siteUrl?: string, prerenderLimit?: number, guidesDir?: string, log?: Pick<Console, 'log'|'warn'>}} opts
 */
export async function generateSeo({
  publicDir, distDir, siteUrl = DEFAULT_SITE_URL, prerenderLimit = DEFAULT_PRERENDER_LIMIT,
  guidesDir = resolve(publicDir, '..', 'content', 'guides'), log = console,
}) {
  const site = siteUrl.replace(/\/+$/, '');
  const stats = {
    jobPages: 0, closedPages: 0, jsonLd: 0, jsonLdSkipped: {}, landingPages: 0, guidePages: 0, aboutPage: false,
    sitemapUrls: 1, prerendered: 0, source: null,
  };
  await mkdir(distDir, { recursive: true });
  await writeFile(join(distDir, 'robots.txt'), renderRobots(site));

  const data = await loadJobs(publicDir, log);
  const indexPath = join(distDir, 'index.html');
  const indexHtml = await readFile(indexPath, 'utf8').catch(() => null);
  const guides = await loadGuides(guidesDir, log);

  if (!data || !data.jobs.length) {
    log.warn('[seo] no job data in public/ (jobs.json / jobs-index.json) — skipping job pages and prerender');
    const guidePaths = await writeGuides(distDir, guides, site);
    stats.guidePages = guides.length;
    await writeFile(join(distDir, 'sitemap.xml'), renderSitemap(site, null, [], guidePaths.map((p) => ({ loc: `${site}/${p}`, lastmod: null }))));
    stats.sitemapUrls = 1 + guidePaths.length;
    if (indexHtml) await writeFile(indexPath, injectPrerender(indexHtml, '').html);
    return stats;
  }
  stats.source = data.source;

  const describe = createDescriptionLookup(publicDir, log);
  const entries = [];
  for (const job of data.jobs) {
    const description = await describe(job);
    const posted = parsePostedAt(job.posted_at);
    const { posting, reason } = buildJobPosting(job, description, jobPageUrl(site, job.job_id));
    if (posting) stats.jsonLd += 1;
    else stats.jsonLdSkipped[reason] = (stats.jsonLdSkipped[reason] || 0) + 1;
    entries.push({ job, description, posted, posting });
  }
  entries.sort(newestFirst);

  const generatedAt = parsePostedAt(data.meta.generated_at) || (entries[0] && entries[0].posted) || null;
  await writeInBatches(entries.map((entry) => async () => {
    const dir = join(distDir, 'job', entry.job.job_id);
    await mkdir(dir, { recursive: true });
    await writeFile(join(dir, 'index.html'), renderJobPage({ ...entry, siteUrl: site, generatedAt }));
  }));
  stats.jobPages = entries.length;

  // Closed jobs keep a noindex page (no JSON-LD, not in the sitemap or any list).
  await writeInBatches(data.closed.map((job) => async () => {
    const dir = join(distDir, 'job', job.job_id);
    await mkdir(dir, { recursive: true });
    const description = await describe(job);
    await writeFile(join(dir, 'index.html'), renderJobPage({
      job, description, posted: parsePostedAt(job.posted_at), posting: null, siteUrl: site, generatedAt, closed: true,
    }));
  }));
  stats.closedPages = data.closed.length;
  const { hub, pages } = buildLandingPages(entries, { generatedAt });
  await writeInBatches(pages.map((page) => async () => {
    const dir = join(distDir, page.path);
    await mkdir(dir, { recursive: true });
    await writeFile(join(dir, 'index.html'), renderLandingPage(page, { siteUrl: site, generatedAt, siblings: pages }));
  }));
  if (hub) {
    await mkdir(join(distDir, hub.path), { recursive: true });
    await writeFile(join(distDir, hub.path, 'index.html'), renderLandingHub(hub, { siteUrl: site, generatedAt, totalJobs: entries.length, guides }));
  }
  const landing = hub ? [hub, ...pages] : [];
  stats.landingPages = landing.length;

  const health = await readJson(join(publicDir, 'health.json'), log);
  await mkdir(join(distDir, ABOUT_PATH), { recursive: true });
  await writeFile(join(distDir, ABOUT_PATH, 'index.html'), renderAboutPage(aboutFacts(health, { totalJobs: entries.length, generatedAt }), { siteUrl: site }));
  stats.aboutPage = true;

  const guidePaths = await writeGuides(distDir, guides, site);
  stats.guidePages = guides.length;

  const extraUrls = [
    ...landing.map((page) => ({ loc: landingPageUrl(site, page.path), lastmod: generatedAt })),
    { loc: `${site}/${ABOUT_PATH}`, lastmod: generatedAt },
    ...guidePaths.map((p) => ({ loc: `${site}/${p}`, lastmod: null })),
  ];
  await writeFile(join(distDir, 'sitemap.xml'), renderSitemap(site, generatedAt, entries, extraUrls));
  stats.sitemapUrls = 1 + extraUrls.length + entries.length;

  if (indexHtml) {
    const top = entries.slice(0, prerenderLimit);
    const browse = pages
      .filter((p) => ['category', 'remote', 'visa', 'new'].includes(p.kind))
      .map((p) => ({ path: p.path, label: p.name, count: p.entries.length }));
    const { html, injected } = injectPrerender(indexHtml, renderPrerenderList(top, entries.length, browse));
    if (!injected) log.warn('[seo] prerender marker missing from dist/index.html — crawlable list not injected');
    else stats.prerendered = top.length;
    await writeFile(indexPath, html);
  } else {
    log.warn('[seo] dist/index.html not found — crawlable list not injected');
  }
  return stats;
}

// Build-time SEO generation. Reads the scraper output from public/ (jobs.json
// or jobs-index.json + descriptions/<shard>.json) and writes into dist/:
//   - job/<job_id>/index.html   static page + JobPosting JSON-LD per open job
//   - index.html                crawlable list of the newest jobs inside #root
//   - sitemap.xml, robots.txt
// Missing or malformed data never fails the build: generation is skipped with
// a warning and only robots.txt + a home-only sitemap are written.

import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { descriptionShard, lookupDescription } from '../../src/lib/descriptions.js';
import { buildJobPosting, isSafeJobId, parsePostedAt } from './jobposting.mjs';
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

/** Open, well-formed jobs from the first data file that has any. */
export async function loadJobs(publicDir, log = console) {
  for (const name of ['jobs.json', 'jobs-index.json']) {
    const data = await readJson(join(publicDir, name), log);
    if (!data || !Array.isArray(data.jobs)) continue;
    const seen = new Set();
    const jobs = data.jobs.filter((j) => {
      if (!j || typeof j !== 'object' || j.is_closed) return false;
      if (!isSafeJobId(j.job_id) || seen.has(j.job_id)) return false;
      if (typeof j.title !== 'string' || !j.title.trim() || typeof j.company !== 'string' || !j.company.trim()) return false;
      seen.add(j.job_id);
      return true;
    });
    return { jobs, meta: (data.meta && typeof data.meta === 'object') ? data.meta : {}, source: name };
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

/**
 * @param {{publicDir: string, distDir: string, siteUrl?: string, prerenderLimit?: number, log?: Pick<Console, 'log'|'warn'>}} opts
 */
export async function generateSeo({
  publicDir, distDir, siteUrl = DEFAULT_SITE_URL, prerenderLimit = DEFAULT_PRERENDER_LIMIT, log = console,
}) {
  const site = siteUrl.replace(/\/+$/, '');
  const stats = { jobPages: 0, jsonLd: 0, jsonLdSkipped: {}, sitemapUrls: 1, prerendered: 0, source: null };
  await mkdir(distDir, { recursive: true });
  await writeFile(join(distDir, 'robots.txt'), renderRobots(site));

  const data = await loadJobs(publicDir, log);
  const indexPath = join(distDir, 'index.html');
  const indexHtml = await readFile(indexPath, 'utf8').catch(() => null);

  if (!data || !data.jobs.length) {
    log.warn('[seo] no job data in public/ (jobs.json / jobs-index.json) — skipping job pages and prerender');
    await writeFile(join(distDir, 'sitemap.xml'), renderSitemap(site, null, []));
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

  await writeInBatches(entries.map((entry) => async () => {
    const dir = join(distDir, 'job', entry.job.job_id);
    await mkdir(dir, { recursive: true });
    await writeFile(join(dir, 'index.html'), renderJobPage({ ...entry, siteUrl: site }));
  }));
  stats.jobPages = entries.length;

  const generatedAt = parsePostedAt(data.meta.generated_at) || (entries[0] && entries[0].posted) || null;
  await writeFile(join(distDir, 'sitemap.xml'), renderSitemap(site, generatedAt, entries));
  stats.sitemapUrls = entries.length + 1;

  if (indexHtml) {
    const top = entries.slice(0, prerenderLimit);
    const { html, injected } = injectPrerender(indexHtml, renderPrerenderList(top, entries.length));
    if (!injected) log.warn('[seo] prerender marker missing from dist/index.html — crawlable list not injected');
    else stats.prerendered = top.length;
    await writeFile(indexPath, html);
  } else {
    log.warn('[seo] dist/index.html not found — crawlable list not injected');
  }
  return stats;
}

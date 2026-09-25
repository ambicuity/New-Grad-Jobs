// HTML / XML templates for the build-time SEO output: per-job static pages,
// the crawlable job list injected into index.html, sitemap.xml and robots.txt.
// All interpolated data goes through escapeHtml / jsonForScript / safeHttpUrl.

import { createHash } from 'node:crypto';
import { safeHttpUrl } from '../../src/lib/safe-url.js';
import { descriptionHtml, fallbackDescription } from './jobposting.mjs';
import { escapeHtml, jsonForScript, toParagraphs, truncate } from './text.mjs';

export const PRERENDER_MARKER = '<!--ngj:prerender-->';
const META_DESCRIPTION_CHARS = 155;
export const REPO_URL = 'https://github.com/ambicuity/New-Grad-Jobs';

// Terminal look without web fonts or scripts: system monospace, black canvas.
// Shared by the per-job pages and the landing pages (landing.mjs).
export const JOB_PAGE_CSS = [
  ':root{color-scheme:dark}',
  '*{box-sizing:border-box}',
  'body{margin:0;background:#000;color:#e8e8e8;font:14px/1.6 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;-webkit-font-smoothing:antialiased}',
  'main{max-width:820px;margin:0 auto;padding:24px 16px 48px}',
  'a{color:#ff9d3d}',
  'a:focus-visible{outline:1px solid #ff9d3d;outline-offset:2px}',
  '.crumb{font-size:12px;color:#8a8a8a;letter-spacing:.6px;margin-bottom:18px}',
  // Underlined: inside a text line a link must not be told apart by colour alone (WCAG 1.4.1).
  '.crumb a{color:#ff9d3d}',
  'h1{font-size:22px;line-height:1.3;margin:0 0 6px;color:#fff}',
  '.co{color:#ff9d3d;font-weight:700;letter-spacing:.4px}',
  'dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;margin:16px 0;padding:12px 14px;border:1px solid #2a2a2a;background:#0a0a0a;font-size:13px}',
  'dt{color:#8a8a8a}dd{margin:0;overflow-wrap:anywhere}',
  '.actions{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0 22px}',
  '.btn{display:inline-block;padding:9px 14px;font-weight:700;text-decoration:none;letter-spacing:.5px;border:1px solid #ff9d3d}',
  '.btn.primary{background:#ff9d3d;color:#000}',
  '.btn.ghost{color:#e8e8e8;border-color:#3a3a3a}',
  'h2{font-size:12px;color:#8a8a8a;letter-spacing:.8px;font-weight:600;margin:24px 0 8px;border-bottom:1px solid #2a2a2a;padding-bottom:4px}',
  '.desc p{margin:0 0 12px;overflow-wrap:anywhere}',
  '.dim{color:#8a8a8a}',
  '.browse{font-size:12px;line-height:2;margin:0 0 8px}',
  '.subscribe{font-size:12px;color:#8a8a8a;margin:0 0 12px}',
  '.list ol,.list ul{margin:0;padding-left:22px}',
  '.list li{margin:0 0 8px;overflow-wrap:anywhere}',
  '.notice{border:1px solid #ff9d3d;padding:10px 12px;margin:0 0 16px}',
  'table{border-collapse:collapse;width:100%;font-size:12px}',
  'th,td{text-align:left;padding:6px 8px;border-bottom:1px solid #2a2a2a;vertical-align:top}',
  'th{color:#8a8a8a;font-weight:600}',
  '.desc h2,.desc h3{font-size:15px;color:#fff;letter-spacing:0;border-bottom:none;padding:0;margin:22px 0 8px;font-weight:600}',
  '.desc h3{font-size:14px}',
  '.desc ul,.desc ol{padding-left:22px;margin:0 0 12px}',
  '.desc li{margin:0 0 6px}',
  'blockquote{border-left:2px solid #ff9d3d;margin:0 0 12px;padding:0 0 0 12px;color:#8a8a8a}',
  'code{background:#0a0a0a;border:1px solid #2a2a2a;padding:0 4px}',
  'footer{margin-top:32px;font-size:12px;color:#8a8a8a;border-top:1px solid #2a2a2a;padding-top:12px}',
].join('');

const cspHash = (text) => `'sha256-${createHash('sha256').update(text, 'utf8').digest('base64')}'`;

/**
 * Strict CSP for static job pages: no scripts at all (the JSON-LD block is a
 * data block, never executed), only the one hashed inline stylesheet.
 */
export const JOB_PAGE_CSP = [
  "default-src 'none'",
  `style-src ${cspHash(JOB_PAGE_CSS)}`,
  "img-src 'self'",
  // Same-origin fetches only (no scripts run, but Lighthouse reads robots.txt from the page context).
  "connect-src 'self'",
  "base-uri 'none'",
  "form-action 'none'",
  "object-src 'none'",
].join('; ');

export const jobPath = (jobId) => `job/${jobId}/`;
export const jobPageUrl = (siteUrl, jobId) => `${siteUrl}/${jobPath(jobId)}`;

function formatDate(date) {
  return date ? date.toISOString().slice(0, 10) : '';
}

function formatComp(comp) {
  if (!comp || typeof comp.currency !== 'string') return '';
  const fmt = (n) => (typeof n === 'number' && Number.isFinite(n) ? n.toLocaleString('en-US') : null);
  const lo = fmt(comp.min);
  const hi = fmt(comp.max);
  if (!lo && !hi) return '';
  return `${comp.currency} ${lo && hi && lo !== hi ? `${lo} – ${hi}` : lo || hi}`;
}

/**
 * Full static page for one job. A closed job keeps its page (so shared links
 * explain themselves instead of 404ing) but is noindex, carries no JobPosting
 * JSON-LD and labels the employer link as closed.
 * @param {{job: object, description: string, posted: Date|null, posting: object|null, siteUrl: string, generatedAt?: Date|null, closed?: boolean}} args
 */
export function renderJobPage({ job, description, posted, posting, siteUrl, generatedAt = null, closed = false }) {
  const canonical = jobPageUrl(siteUrl, job.job_id);
  const applyUrl = safeHttpUrl(job.url);
  const paragraphs = toParagraphs(description);
  const bodyHtml = descriptionHtml(paragraphs.length ? paragraphs : [fallbackDescription(job)]);
  const where = job.location ? ` — ${job.location}` : '';
  const title = `${job.title} at ${job.company}${where} · NGJ`;
  const metaDesc = truncate(description || fallbackDescription(job), META_DESCRIPTION_CHARS);
  const category = job.category && typeof job.category.name === 'string' ? job.category.name : '';
  const comp = formatComp(job.comp);
  const rows = [
    ['company', job.company],
    ['location', job.location],
    ['posted', formatDate(posted)],
    ['category', category],
    ['salary', comp],
    ['source', job.source],
    ['verified', generatedAt ? `confirmed open at the employer on ${formatDate(generatedAt)}` : ''],
  ].filter(([, v]) => typeof v === 'string' && v.trim());

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="${escapeHtml(JOB_PAGE_CSP)}">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${escapeHtml(closed ? `[Closed] ${title}` : title)}</title>
<meta name="description" content="${escapeHtml(metaDesc)}">
${closed ? '<meta name="robots" content="noindex">\n' : ''}<link rel="canonical" href="${escapeHtml(canonical)}">
<link rel="icon" type="image/svg+xml" href="../../favicon.svg">
<link rel="alternate" type="application/rss+xml" title="New Grad Jobs RSS Feed" href="../../feed.xml">
<meta property="og:type" content="website">
<meta property="og:site_name" content="NGJ · New Grad Jobs">
<meta property="og:title" content="${escapeHtml(`${job.title} at ${job.company}`)}">
<meta property="og:description" content="${escapeHtml(metaDesc)}">
<meta property="og:url" content="${escapeHtml(canonical)}">
<meta property="og:image" content="${escapeHtml(`${siteUrl}/og-image.png`)}">
<meta name="twitter:card" content="summary_large_image">
<style>${JOB_PAGE_CSS}</style>
${posting && !closed ? `<script type="application/ld+json">${jsonForScript(posting)}</script>\n` : ''}</head>
<body>
<main>
<nav class="crumb" aria-label="Breadcrumb"><a href="../../">NGJ</a> › jobs › ${escapeHtml(job.company)}</nav>
${closed ? '<p class="notice" role="note">This role is marked CLOSED: the employer\'s page says applications are no longer accepted. It stays here so shared links still explain themselves. <a href="../../">See open roles instead.</a></p>\n' : ''}<h1>${escapeHtml(job.title)}</h1>
<div class="co">${escapeHtml(job.company)}</div>
<dl>
${rows.map(([k, v]) => `<dt>${k}</dt><dd>${escapeHtml(v)}</dd>`).join('\n')}
</dl>
<div class="actions">
${applyUrl ? `<a class="btn ${closed ? 'ghost' : 'primary'}" href="${escapeHtml(applyUrl)}" rel="nofollow noopener noreferrer" target="_blank">${closed ? 'VIEW CLOSED LISTING ↗' : 'APPLY ON EMPLOYER SITE ↗'}</a>` : ''}
<a class="btn ghost" href="../../?job=${encodeURIComponent(job.job_id)}">OPEN IN JOB BOARD</a>
</div>
<h2>ABOUT THE ROLE</h2>
<div class="desc">
${bodyHtml}
</div>
<footer>
<a href="../../">← all new grad jobs</a> · <a href="../../feed.xml">RSS</a> · <a href="${REPO_URL}">GitHub</a>
</footer>
</main>
</body>
</html>
`;
}

/**
 * Crawlable list of the most recent jobs, injected into #root of index.html.
 * `browse` ({path, label, count}[]) links the landing pages so crawlers reach
 * them from the home page.
 */
export function renderPrerenderList(entries, totalJobs, browse = []) {
  if (!entries.length) return '';
  const browseLine = browse.length
    ? `<p class="dim">Browse: <a href="./jobs/">all pages</a> · ${browse.map((b) => `<a href="./${escapeHtml(b.path)}">${escapeHtml(b.label)}</a> (${b.count})`).join(' · ')} · <a href="./guides/">guides</a> · <a href="./about/">how it works</a></p>\n`
    : '';
  const items = entries.map(({ job, posted }) => (
    `<li><a href="./${jobPath(job.job_id)}">${escapeHtml(job.title)}</a>`
    + ` <span class="co">${escapeHtml(job.company)}</span>`
    + (job.location ? ` <span class="dim">· ${escapeHtml(job.location)}</span>` : '')
    + (posted ? ` <time datetime="${posted.toISOString()}" class="dim">· ${formatDate(posted)}</time>` : '')
    + '</li>'
  ));
  return `<section class="ng-static" aria-labelledby="ng-static-h">
<h1 id="ng-static-h">New grad &amp; entry-level jobs — latest ${entries.length} of ${totalJobs}</h1>
<ol>
${items.join('\n')}
</ol>
${browseLine}<p class="dim">Full data: <a href="./jobs.json">jobs.json</a> · <a href="./feed.xml">RSS feed</a> · <a href="${REPO_URL}#readme">README job tables</a></p>
</section>`;
}

/** Replace the marker (or nothing) in index.html with the prerendered list. */
export function injectPrerender(indexHtml, snippet) {
  if (!indexHtml.includes(PRERENDER_MARKER)) return { html: indexHtml, injected: false };
  return { html: indexHtml.replace(PRERENDER_MARKER, () => snippet), injected: Boolean(snippet) };
}

/**
 * sitemap.xml for the home page, the landing pages (`extra`: {loc, lastmod}[])
 * and every job page.
 */
export function renderSitemap(siteUrl, homeLastmod, jobEntries, extra = []) {
  const url = (loc, lastmod) => `  <url><loc>${escapeHtml(loc)}</loc>${lastmod ? `<lastmod>${lastmod}</lastmod>` : ''}</url>`;
  const lines = [
    url(`${siteUrl}/`, homeLastmod ? homeLastmod.toISOString() : ''),
    ...extra.map(({ loc, lastmod }) => url(loc, lastmod ? lastmod.toISOString() : '')),
    ...jobEntries.map(({ job, posted }) => url(jobPageUrl(siteUrl, job.job_id), posted ? posted.toISOString() : '')),
  ];
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${lines.join('\n')}
</urlset>
`;
}

export function renderRobots(siteUrl) {
  return `User-agent: *\nAllow: /\n\nSitemap: ${siteUrl}/sitemap.xml\n`;
}

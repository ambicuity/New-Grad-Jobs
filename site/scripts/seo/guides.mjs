// Evergreen guides: Markdown files in site/content/guides/ rendered to
// /guides/<slug>/ plus a /guides/ index at build time. Script-free, same CSS
// and CSP as the other static pages, with Article JSON-LD. Their job is to
// answer the questions new grads search for and to link into the live board
// and the landing pages.

import { readFile, readdir } from 'node:fs/promises';
import { join } from 'node:path';
import { parseFrontMatter, renderMarkdown } from './markdown.mjs';
import { JOB_PAGE_CSP, JOB_PAGE_CSS, REPO_URL } from './render.mjs';
import { escapeHtml, jsonForScript, truncate } from './text.mjs';

export const GUIDES_ROOT = 'guides';
const META_DESCRIPTION_CHARS = 155;
const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

/**
 * Load every guide. A file is skipped (with a warning) when its name is not a
 * slug or its front matter lacks a title — never fail the build over content.
 * @returns {Promise<{slug: string, title: string, description: string, updated: string, html: string, headings: object[]}[]>}
 */
export async function loadGuides(contentDir, log = console) {
  let names;
  try {
    names = (await readdir(contentDir)).filter((n) => n.endsWith('.md')).sort();
  } catch (err) {
    if (err && err.code !== 'ENOENT') log.warn(`[seo] could not read guides in ${contentDir}: ${err.message}`);
    return [];
  }
  const guides = [];
  for (const name of names) {
    const slug = name.slice(0, -3);
    if (!SLUG_RE.test(slug)) { log.warn(`[seo] guide skipped, bad slug: ${name}`); continue; }
    const { meta, body } = parseFrontMatter(await readFile(join(contentDir, name), 'utf8'));
    if (!meta.title) { log.warn(`[seo] guide skipped, no title: ${name}`); continue; }
    const { html, headings } = renderMarkdown(body);
    guides.push({
      slug,
      title: meta.title,
      description: meta.description || '',
      updated: DATE_RE.test(meta.updated || '') ? meta.updated : '',
      html,
      headings,
    });
  }
  return guides;
}

export const guidePath = (slug) => `${GUIDES_ROOT}/${slug}/`;
export const guideUrl = (siteUrl, slug) => `${siteUrl}/${guidePath(slug)}`;

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
<meta property="og:type" content="article">
<meta property="og:site_name" content="NGJ · New Grad Jobs">
<meta property="og:title" content="${escapeHtml(title)}">
<meta property="og:description" content="${escapeHtml(description)}">
<meta property="og:url" content="${escapeHtml(canonical)}">
<meta property="og:image" content="${escapeHtml(`${siteUrl}/og-image.png`)}">
<meta name="twitter:card" content="summary_large_image">
<style>${JOB_PAGE_CSS}</style>
${jsonLd ? `<script type="application/ld+json">${jsonForScript(jsonLd)}</script>\n` : ''}</head>`;
}

const footer = (root) => `<footer>
<a href="${root}">← all new grad jobs</a> · <a href="${root}guides/">guides</a> · <a href="${root}jobs/">browse</a> · <a href="${root}feed.xml">RSS</a> · <a href="${REPO_URL}">GitHub</a>
</footer>`;

/** One guide page. `siblings` are the other guides, for the "more guides" list. */
export function renderGuidePage(guide, { siteUrl, siblings = [] }) {
  const root = '../../';
  const canonical = guideUrl(siteUrl, guide.slug);
  const description = truncate(guide.description || guide.title, META_DESCRIPTION_CHARS);
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: guide.title,
    description,
    url: canonical,
    ...(guide.updated ? { dateModified: guide.updated } : {}),
    author: { '@type': 'Organization', name: 'NGJ · New Grad Jobs', url: `${siteUrl}/` },
  };
  const more = siblings.filter((g) => g.slug !== guide.slug);
  return `${head({ title: `${guide.title} · NGJ`, description, canonical, siteUrl, root, jsonLd })}
<body>
<main>
<nav class="crumb" aria-label="Breadcrumb"><a class="brand" href="${root}" aria-label="NGJ, New Grad Jobs, home">NGJ</a> › <a href="${root}guides/">guides</a> › ${escapeHtml(guide.title)}</nav>
<article class="desc">
<h1>${escapeHtml(guide.title)}</h1>
${guide.updated ? `<p class="dim">Updated ${escapeHtml(guide.updated)}</p>` : ''}
${guide.html}
</article>
<div class="actions">
<a class="btn primary" href="${root}?">OPEN THE JOB BOARD</a>
<a class="btn ghost" href="${root}jobs/">BROWSE BY ROLE, COMPANY, CITY</a>
</div>
${more.length ? `<h2>MORE GUIDES</h2>\n<div class="list"><ul>\n${more.map((g) => `<li><a href="${root}${guidePath(g.slug)}">${escapeHtml(g.title)}</a></li>`).join('\n')}\n</ul></div>` : ''}
${footer(root)}
</main>
</body>
</html>
`;
}

/** The /guides/ index. */
export function renderGuidesIndex(guides, { siteUrl }) {
  const root = '../';
  const canonical = `${siteUrl}/${GUIDES_ROOT}/`;
  const description = 'Short, practical guides for the new grad job search: reading a posting, visa and citizenship flags, ATS-friendly résumés, hiring timelines and how to work this board.';
  const items = guides.map((g) => (
    `<li><a href="${root}${guidePath(g.slug)}">${escapeHtml(g.title)}</a>${g.description ? ` <span class="dim">— ${escapeHtml(g.description)}</span>` : ''}</li>`
  ));
  return `${head({ title: 'New Grad Job Search Guides · NGJ', description, canonical, siteUrl, root, jsonLd: null })}
<body>
<main>
<nav class="crumb" aria-label="Breadcrumb"><a class="brand" href="${root}" aria-label="NGJ, New Grad Jobs, home">NGJ</a> › guides</nav>
<h1>New grad job search guides</h1>
<p>${escapeHtml(description)}</p>
<div class="list"><ul>
${items.join('\n')}
</ul></div>
${footer(root)}
</main>
</body>
</html>
`;
}

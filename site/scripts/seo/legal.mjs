// Policy pages: site/content/legal/<slug>.md rendered to /<slug>/ (terms,
// privacy, copyright, data-sources) at build time, plus a plain Markdown copy
// at /<slug>/index.md for readers and LLMs. Script-free, same CSS and CSP as
// the other static pages. The Markdown files are the single source of truth;
// edit them and bump `updated` to change a policy.

import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { parseFrontMatter, renderMarkdown, slugifyHeading } from './markdown.mjs';
import { JOB_PAGE_CSP, JOB_PAGE_CSS, LEGAL_LINKS, REPO_URL, legalLinksHtml } from './render.mjs';
import { escapeHtml, truncate } from './text.mjs';

const META_DESCRIPTION_CHARS = 155;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const isDate = (value) => DATE_RE.test(value || '') && new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value;

/** Policy slugs, in display order. Each needs a matching site/content/legal/<slug>.md. */
export const LEGAL_PAGES = LEGAL_LINKS;

export const legalPath = (slug) => `${slug}/`;

/**
 * Load every policy page in LEGAL_PAGES order. A missing file, or one without
 * a title and valid `effective` / `updated` dates, is skipped with a warning:
 * content problems never fail the build (the content test catches them).
 * @returns {Promise<{slug: string, title: string, description: string, effective: string, updated: string, html: string, headings: object[], markdown: string}[]>}
 */
export async function loadLegalPages(contentDir, log = console) {
  const pages = [];
  for (const { slug } of LEGAL_PAGES) {
    let source;
    try {
      source = await readFile(join(contentDir, `${slug}.md`), 'utf8');
    } catch (err) {
      log.warn(`[seo] policy page skipped, cannot read ${slug}.md${err && err.code !== 'ENOENT' ? `: ${err.message}` : ''}`);
      continue;
    }
    const { meta, body } = parseFrontMatter(source);
    if (!meta.title || !isDate(meta.effective) || !isDate(meta.updated)) {
      log.warn(`[seo] policy page skipped, ${slug}.md needs title, effective and updated (YYYY-MM-DD)`);
      continue;
    }
    const { html, headings } = renderMarkdown(body);
    pages.push({
      slug,
      title: meta.title,
      description: meta.description || '',
      effective: meta.effective,
      updated: meta.updated,
      html,
      headings,
      markdown: body.trim(),
    });
  }
  return pages;
}

/** The Markdown companion served at /<slug>/index.md. */
export function legalMarkdown(page) {
  return `# ${page.title}\n\nEffective: ${page.effective}\nLast updated: ${page.updated}\n\n${page.markdown}\n`;
}

/** One policy page. `siblings` are all loaded policy pages, for the related list. */
export function renderLegalPage(page, { siteUrl, siblings = [] }) {
  const root = '../';
  const canonical = `${siteUrl}/${legalPath(page.slug)}`;
  const description = truncate(page.description || page.title, META_DESCRIPTION_CHARS);
  const sections = page.headings.filter((h) => h.level === 2);
  const toc = sections.length
    ? `<nav class="toc" aria-label="On this page"><span class="dim">ON THIS PAGE</span>\n<ul>\n${sections.map((h) => `<li><a href="#${escapeHtml(slugifyHeading(h.text))}">${escapeHtml(h.text)}</a></li>`).join('\n')}\n</ul>\n</nav>`
    : '';
  const related = siblings.length > 1
    ? `<h2>POLICIES</h2>\n<ul class="list related">\n${siblings.map((p) => (p.slug === page.slug
      ? `<li><a href="${root}${legalPath(p.slug)}" aria-current="page">${escapeHtml(p.title)}</a></li>`
      : `<li><a href="${root}${legalPath(p.slug)}">${escapeHtml(p.title)}</a></li>`)).join('\n')}\n</ul>`
    : '';
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="${escapeHtml(JOB_PAGE_CSP)}">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${escapeHtml(page.title)} · NGJ</title>
<meta name="description" content="${escapeHtml(description)}">
<link rel="canonical" href="${escapeHtml(canonical)}">
<link rel="alternate" type="text/markdown" href="index.md">
<link rel="icon" type="image/svg+xml" href="${root}favicon.svg">
<meta property="og:type" content="website">
<meta property="og:site_name" content="NGJ · New Grad Jobs">
<meta property="og:title" content="${escapeHtml(page.title)}">
<meta property="og:description" content="${escapeHtml(description)}">
<meta property="og:url" content="${escapeHtml(canonical)}">
<meta property="og:image" content="${escapeHtml(`${siteUrl}/og-image.png`)}">
<style>${JOB_PAGE_CSS}</style>
</head>
<body>
<main>
<nav class="crumb" aria-label="Breadcrumb"><a class="brand" href="${root}" aria-label="NGJ, New Grad Jobs, home">NGJ</a> › ${escapeHtml(page.title.toLowerCase())}</nav>
<article class="desc">
<h1>${escapeHtml(page.title)}</h1>
<p class="dim">Effective <time datetime="${page.effective}">${page.effective}</time> · Last updated <time datetime="${page.updated}">${page.updated}</time> · <a href="index.md">Markdown</a> · <a href="${REPO_URL}/commits/main/site/content/legal/${page.slug}.md" rel="noopener noreferrer">history</a></p>
${toc}
${page.html}
</article>
${related}
<footer>
<a href="${root}">← all new grad jobs</a> · <a href="${root}about/">about</a> · <a href="${root}guides/">guides</a> · <a href="${REPO_URL}">GitHub</a>
${legalLinksHtml(root)}
</footer>
</main>
</body>
</html>
`;
}

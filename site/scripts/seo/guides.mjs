// Evergreen guides: Markdown files in site/content/guides/ rendered to
// /guides/<slug>/ plus a /guides/ index at build time, with Article JSON-LD.
// Every page is complete static HTML: cards, reading paths, the 30-second
// brief and "On this page" all work without JavaScript. One same-origin
// script (guides.js, from src/lib/guides-client.js) adds search, filters and
// read/saved marks on top. Their job is to answer the questions new grads
// search for and to link into the live board and the landing pages.

import { readFile, readdir } from 'node:fs/promises';
import { join } from 'node:path';
import { READING_PATHS } from './guide-paths.mjs';
import { GUIDE_PAGE_CSP, GUIDE_PAGE_CSS } from './guides-style.mjs';
import { parseFrontMatter, portableMarkdown, renderMarkdown, slugifyHeading } from './markdown.mjs';
import { REPO_URL, legalLinksHtml } from './render.mjs';
import { escapeHtml, jsonForScript, truncate } from './text.mjs';

export { GUIDE_PAGE_CSP, READING_PATHS };
export const GUIDES_ROOT = 'guides';
/** The enhancement script, written to /guides/guides.js (it imports ./saved.js beside it). */
export const GUIDES_SCRIPT = 'guides.js';
const META_DESCRIPTION_CHARS = 155;
const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const DEFAULT_ORDER = 999;
const WORDS_PER_MINUTE = 230;
const MIN_TOC_HEADINGS = 3;

/** What a guide mostly is. `format:` front matter takes one or two ids; `explainer` is the default. */
export const GUIDE_FORMATS = Object.freeze([
  { id: 'checklist', label: 'CHECKLIST', description: 'steps to work through in order' },
  { id: 'script', label: 'SCRIPT', description: 'copy-ready emails, messages or answers' },
  { id: 'diagnostic', label: 'DIAGNOSTIC', description: 'work out why something is going wrong' },
  { id: 'official', label: 'OFFICIAL', description: 'government rules and official sources' },
  { id: 'worksheet', label: 'WORKSHEET', description: 'a table or template to fill in' },
  { id: 'explainer', label: 'EXPLAINER', description: 'how something works' },
].map(Object.freeze));
const FORMAT_LABEL = new Map(GUIDE_FORMATS.map((f) => [f.id, f.label]));
const DEFAULT_FORMATS = Object.freeze(['explainer']);

/** Whole minutes at a steady reading pace, never zero. */
export const readingMinutes = (words) => Math.max(1, Math.round(words / WORDS_PER_MINUTE));

/** Words a reader sees: Markdown syntax, link targets and evidence fences removed. */
function countWords(markdown) {
  const text = String(markdown)
    .replace(/^:::.*$/gm, ' ')
    .replace(/\]\([^)]*\)/g, ']')
    .replace(/[#>*_`|[\]-]+/g, ' ');
  return (text.match(/[\p{L}\p{N}][\p{L}\p{N}'’.,%/]*/gu) || []).length;
}

/** A real calendar date in YYYY-MM-DD form, or ''. */
function validDate(raw) {
  const v = String(raw || '');
  return DATE_RE.test(v) && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0, 10) === v ? v : '';
}

function parseFormats(raw, name, log) {
  const ids = String(raw || '').split(',').map((s) => s.trim()).filter(Boolean);
  for (const id of ids) if (!FORMAT_LABEL.has(id)) log.warn(`[seo] guide ${name}: unknown format "${id}" ignored`);
  const known = [...new Set(ids.filter((id) => FORMAT_LABEL.has(id)))];
  return known.length ? known : [...DEFAULT_FORMATS];
}

/** Index sections, in display order. A guide's `section` front matter must be one of these to be grouped. */
export const SECTION_ORDER = Object.freeze([
  'Getting started',
  'Job search strategy',
  'Understanding jobs',
  'Résumé and applications',
  'LinkedIn and networking',
  'GitHub and portfolio',
  'International students',
  'Interviews',
  'Technical preparation',
  'AI and job search',
  'Rejections and recovery',
  'Offers',
  'Starting your job',
  'NGJ data',
]);
const OTHER_SECTION = 'More';

/**
 * Sections whose guides auto-append an "educational, not legal advice"
 * disclaimer and a list of official sources. The list is built from US
 * government immigration / labor / consumer-protection sites that the guides
 * link to throughout; extend it as new authoritative sources are added.
 */
const LEGAL_DISCLAIMER_SECTIONS = new Set(['International students']);
const LEGAL_DISCLAIMER_NOTICE = '<strong>Important:</strong> This guide is educational information, not legal advice. Immigration rules, processing times and employer policies change. Verify current requirements with the official sources below, your Designated School Official (DSO), or a qualified immigration attorney.';
const LEGAL_DISCLAIMER_SOURCES = [
  { href: 'https://www.uscis.gov/working-in-the-united-states', label: 'USCIS — Working in the United States' },
  { href: 'https://studyinthestates.dhs.gov/', label: 'DHS — Study in the States (F-1 students)' },
  { href: 'https://www.uscis.gov/policy-manual', label: 'USCIS Policy Manual' },
  { href: 'https://www.e-verify.gov/', label: 'E-Verify' },
  { href: 'https://www.bls.gov/', label: 'Bureau of Labor Statistics — Occupational Employment and Wage Statistics' },
];

/**
 * The disclaimer footer for guides whose section needs an authoritative-sources
 * footer. Sources are rendered as a small `<ul>` of inline links so the page
 * keeps working with JavaScript off.
 */
export function legalDisclaimerHtml() {
  const links = LEGAL_DISCLAIMER_SOURCES
    .map((s) => `<li><a href="${s.href}" rel="noopener noreferrer">${s.label}</a></li>`)
    .join('\n');
  return `<aside class="legal-notice" role="note" aria-label="Educational disclaimer and official sources">
<p>${LEGAL_DISCLAIMER_NOTICE}</p>
<p>Official sources:</p>
<ul>
${links}
</ul>
</aside>`;
}

/** Sort key inside a section: explicit `order`, then title. */
const byOrderThenTitle = (a, b) => (a.order - b.order) || a.title.localeCompare(b.title);

/** Group guides by section in SECTION_ORDER; unknown or missing sections go last under "More". */
export function groupGuides(guides) {
  const known = new Set(SECTION_ORDER);
  const sections = [...SECTION_ORDER, OTHER_SECTION].map((name) => ({
    name,
    guides: guides.filter((g) => (known.has(g.section) ? g.section : OTHER_SECTION) === name).sort(byOrderThenTitle),
  }));
  return sections.filter((s) => s.guides.length);
}

/**
 * Load every guide. A file is skipped (with a warning) when its name is not a
 * slug or its front matter lacks a title — never fail the build over content.
 * @returns {Promise<{slug: string, title: string, description: string, updated: string, section: string, order: number, html: string, headings: object[]}[]>}
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
    const words = countWords(body);
    guides.push({
      slug,
      title: meta.title,
      description: meta.description || '',
      updated: validDate(meta.updated),
      published: validDate(meta.published),
      section: meta.section || '',
      order: /^\d+$/.test(meta.order || '') ? Number(meta.order) : DEFAULT_ORDER,
      formats: parseFormats(meta.format, name, log),
      useWhen: meta.use_when || '',
      youGet: meta.you_get || '',
      words,
      readMinutes: readingMinutes(words),
      html,
      headings,
      markdown: body.trim(),
    });
  }
  return guides;
}

export const guidePath = (slug) => `${GUIDES_ROOT}/${slug}/`;

/** The Markdown companion served at /guides/<slug>/index.md. */
export function guideMarkdown(guide) {
  const brief = [guide.useWhen, guide.youGet].filter(Boolean).join(' ');
  const lead = [`# ${guide.title}`, guide.description ? `> ${guide.description}` : '', brief, guide.updated ? `Updated: ${guide.updated}` : '']
    .filter(Boolean).join('\n\n');
  return `${lead}\n\n${portableMarkdown(guide.markdown || '')}\n`;
}
export const guideUrl = (siteUrl, slug) => `${siteUrl}/${guidePath(slug)}`;

/** Resolve reading-path steps to guides, in path order; unknown slugs and empty paths drop out. */
export function readingPaths(guides, paths = READING_PATHS) {
  const bySlug = new Map(guides.map((g) => [g.slug, g]));
  return paths
    .map((p) => ({ ...p, guides: p.steps.map((s) => bySlug.get(s)).filter(Boolean) }))
    .filter((p) => p.guides.length);
}

const sectionId = (name) => `sec-${slugifyHeading(name) || 'more'}`;
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
const formatTags = (formats) => formats.map((f) => `<span class="tag">${escapeHtml(FORMAT_LABEL.get(f) || f.toUpperCase())}</span>`).join(' ');
const minutes = (g) => `<span>${g.readMinutes} min read</span>`;
/** Bold the fixed lead words ("Read this when", "You get") of a brief sentence. */
const briefLine = (text, lead) => (text.startsWith(lead)
  ? `<p><strong>${escapeHtml(lead)}</strong>${escapeHtml(text.slice(lead.length))}</p>`
  : `<p>${escapeHtml(text)}</p>`);

function head({ title, description, canonical, siteUrl, root, jsonLd, markdown = false }) {
  return `<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="${escapeHtml(GUIDE_PAGE_CSP)}">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${escapeHtml(title)}</title>
<meta name="description" content="${escapeHtml(description)}">
<link rel="canonical" href="${escapeHtml(canonical)}">
${markdown ? '<link rel="alternate" type="text/markdown" href="index.md">\n' : ''}<link rel="icon" type="image/svg+xml" href="${root}favicon.svg">
<link rel="alternate" type="application/rss+xml" title="New Grad Jobs RSS Feed" href="${root}feed.xml">
<meta property="og:type" content="article">
<meta property="og:site_name" content="NGJ · New Grad Jobs">
<meta property="og:title" content="${escapeHtml(title)}">
<meta property="og:description" content="${escapeHtml(description)}">
<meta property="og:url" content="${escapeHtml(canonical)}">
<meta property="og:image" content="${escapeHtml(`${siteUrl}/og-image.png`)}">
<meta name="twitter:card" content="summary_large_image">
<style>${GUIDE_PAGE_CSS}</style>
${jsonLd ? `<script type="application/ld+json">${jsonForScript(jsonLd)}</script>\n` : ''}</head>`;
}

const footer = (root) => `<footer>
<a href="${root}">← all new grad jobs</a> · <a href="${root}guides/">guides</a> · <a href="${root}jobs/">browse</a> · <a href="${root}feed.xml">RSS</a> · <a href="${REPO_URL}">GitHub</a>
${legalLinksHtml(root)}
</footer>`;

/** "On this page": the guide's second-level headings, linked to the ids renderMarkdown gives them. */
function tocItems(guide) {
  const items = (guide.headings || []).filter((h) => h.level === 2).map((h) => ({ text: h.text, id: slugifyHeading(h.text) })).filter((h) => h.id);
  if (items.length < MIN_TOC_HEADINGS) return '';
  return `<ol>\n${items.map((h) => `<li><a href="#${escapeHtml(h.id)}">${escapeHtml(h.text)}</a></li>`).join('\n')}\n</ol>`;
}

function pager(guide, ordered, root) {
  const i = ordered.findIndex((g) => g.slug === guide.slug);
  if (i < 0) return '';
  const link = (g, rel, dir) => (g
    ? `<a rel="${rel}" href="${root}${guidePath(g.slug)}"><span class="dir">${dir}</span>${escapeHtml(g.title)}</a>`
    : '');
  const prev = link(ordered[i - 1], 'prev', '← PREVIOUS');
  const next = link(ordered[i + 1], 'next', 'NEXT →');
  return prev || next ? `<nav class="pager" aria-label="Previous and next guide">\n${prev}\n${next}\n</nav>` : '';
}

/** One guide page. `siblings` are all guides (this one included), for prev/next and "more in section". */
export function renderGuidePage(guide, { siteUrl, siblings = [] }) {
  const root = '../../';
  const canonical = guideUrl(siteUrl, guide.slug);
  const description = truncate(guide.description || guide.title, META_DESCRIPTION_CHARS);
  const formats = guide.formats?.length ? guide.formats : DEFAULT_FORMATS;
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: guide.title,
    description,
    url: canonical,
    inLanguage: 'en',
    ...(guide.published ? { datePublished: guide.published } : {}),
    ...(guide.updated ? { dateModified: guide.updated } : {}),
    ...(guide.section ? { articleSection: guide.section } : {}),
    ...(guide.words ? { wordCount: guide.words } : {}),
    author: { '@type': 'Organization', name: 'NGJ · New Grad Jobs', url: `${siteUrl}/` },
    publisher: { '@type': 'Organization', name: 'NGJ · New Grad Jobs', url: `${siteUrl}/` },
  };
  const ordered = groupGuides(siblings.some((g) => g.slug === guide.slug) ? siblings : [...siblings, guide]).flatMap((s) => s.guides);
  const others = siblings.filter((g) => g.slug !== guide.slug);
  const sameSection = guide.section ? others.filter((g) => g.section === guide.section).sort(byOrderThenTitle) : [];
  const more = sameSection.length ? sameSection : others;
  const moreTitle = sameSection.length ? `MORE IN ${escapeHtml(guide.section.toUpperCase())}` : 'MORE GUIDES';
  // Auto-append the legal disclaimer for guides in sections whose content
  // (immigration, employment authorisation) carries legal consequences.
  const legalFooter = LEGAL_DISCLAIMER_SECTIONS.has(guide.section) ? legalDisclaimerHtml() : '';
  const toc = tocItems(guide);
  const brief = guide.useWhen || guide.youGet
    ? `<aside class="brief" aria-label="30-second brief">
<p class="brief-h">30-SECOND BRIEF</p>
${guide.useWhen ? briefLine(guide.useWhen, 'Read this when') : ''}
${guide.youGet ? briefLine(guide.youGet, 'You get') : ''}
</aside>`
    : '';
  const sectionCrumb = SECTION_ORDER.includes(guide.section)
    ? ` › <a href="${root}${GUIDES_ROOT}/#${sectionId(guide.section)}">${escapeHtml(guide.section)}</a>`
    : '';
  return `<!DOCTYPE html>
<html lang="en" data-ngj-guides="page">
${head({ title: `${guide.title} · NGJ`, description, canonical, siteUrl, root, jsonLd, markdown: true })}
<body>
<main class="wide guide">
<nav class="crumb" aria-label="Breadcrumb"><a class="brand" href="${root}" aria-label="NGJ, New Grad Jobs, home">NGJ</a> › <a href="${root}guides/">guides</a>${sectionCrumb} › <span aria-current="page">${escapeHtml(guide.title)}</span></nav>
<div class="layout">
<article class="desc">
<header>
${guide.section ? `<p class="kicker">${escapeHtml(guide.section.toUpperCase())}</p>\n` : ''}<h1>${escapeHtml(guide.title)}</h1>
${guide.description ? `<p class="lede">${escapeHtml(guide.description)}</p>\n` : ''}<p class="meta">${formatTags(formats)} ${minutes(guide)}${guide.updated ? ` <span>· Updated <time datetime="${escapeHtml(guide.updated)}">${escapeHtml(guide.updated)}</time></span>` : ''}</p>
<div class="tools" data-guide-tools data-guide="${escapeHtml(guide.slug)}" hidden>
<button type="button" data-read aria-pressed="false"><span class="glyph" aria-hidden="true">○</span> Mark as read</button>
<button type="button" data-save aria-pressed="false"><span class="glyph" aria-hidden="true">☆</span> Save</button>
</div>
<p class="storage-note" data-guides-storage role="status" hidden>Browser storage is blocked, so this mark lasts only until you leave the page.</p>
</header>
${brief}
${toc ? `<details class="toc toc-inline">\n<summary>ON THIS PAGE</summary>\n<nav aria-label="On this page">\n${toc}\n</nav>\n</details>` : ''}
<div class="prose">
${guide.html}
</div>
${legalFooter}
</article>
${toc ? `<nav class="toc toc-side" aria-label="On this page">\n<p class="toc-h">ON THIS PAGE</p>\n${toc}\n</nav>` : ''}
</div>
${pager(guide, ordered, root)}
<div class="actions">
<a class="btn primary" href="${root}?">OPEN THE JOB BOARD</a>
<a class="btn ghost" href="${root}jobs/">BROWSE BY ROLE, COMPANY, CITY</a>
</div>
${more.length ? `<h2>${moreTitle}</h2>\n<div class="list"><ul>\n${more.map((g) => `<li><a href="${root}${guidePath(g.slug)}">${escapeHtml(g.title)}</a></li>`).join('\n')}\n</ul></div>` : ''}
${footer(root)}
</main>
<script type="module" src="../${GUIDES_SCRIPT}"></script>
</body>
</html>
`;
}

function card(g, root) {
  const formats = g.formats?.length ? g.formats : DEFAULT_FORMATS;
  const text = [g.title, g.description, g.section, ...formats.map((f) => FORMAT_LABEL.get(f) || f)].join(' ').toLowerCase();
  return `<li class="card" data-guide="${escapeHtml(g.slug)}" data-formats="${escapeHtml(formats.join(' '))}" data-text="${escapeHtml(text)}">
<h3><a href="${root}${guidePath(g.slug)}">${escapeHtml(g.title)}</a></h3>
<p class="meta">${formatTags(formats)} ${minutes(g)}</p>
${g.description ? `<p class="summary">${escapeHtml(g.description)}</p>\n` : ''}<button type="button" class="star" data-save aria-pressed="false" aria-label="Save ${escapeHtml(g.title)}" hidden>☆</button>
</li>`;
}

function pathsPanel(paths, root) {
  if (!paths.length) return '';
  const items = paths.map((p) => `<details class="path" name="path" id="path-${escapeHtml(p.id)}">
<summary>${escapeHtml(p.label)} <span class="n">${p.guides.length}</span></summary>
<div class="path-body">
<p>${escapeHtml(p.explain)}</p>
<ol>
${p.guides.map((g) => `<li><a href="${root}${guidePath(g.slug)}">${escapeHtml(g.title)}</a> <span class="dim">· ${g.readMinutes} min</span></li>`).join('\n')}
</ol>
</div>
</details>`);
  return `<section class="panel paths" aria-labelledby="paths-h">
<h2 class="panel-h" id="paths-h">PICK YOUR SITUATION</h2>
<div class="path-list">
${items.join('\n')}
</div>
</section>`;
}

function toolbar(guides) {
  const used = new Set(guides.flatMap((g) => (g.formats?.length ? g.formats : DEFAULT_FORMATS)));
  const options = GUIDE_FORMATS.filter((f) => used.has(f.id))
    .map((f) => `<option value="${f.id}">${f.label}</option>`).join('\n');
  return `<div class="toolbar" data-guides-toolbar hidden>
<div class="search"><label class="sr-only" for="guide-q">Search guides</label><input type="search" id="guide-q" placeholder="/ search ${guides.length} guides" autocomplete="off" spellcheck="false"></div>
<div class="views" role="group" aria-label="Show">
<button type="button" data-view="all" aria-pressed="true">All <span data-count="all">${guides.length}</span></button>
<button type="button" data-view="unread" aria-pressed="false">Unread <span data-count="unread">${guides.length}</span></button>
<button type="button" data-view="saved" aria-pressed="false">★ Saved <span data-count="saved">0</span></button>
</div>
<div><label class="sr-only" for="guide-format">Format</label><select id="guide-format">
<option value="">All formats</option>
${options}
</select></div>
</div>
<p class="progress" data-guides-progress hidden>Read <strong data-count="read">0</strong> of ${guides.length}</p>`;
}

/** The /guides/ index. `paths` defaults to READING_PATHS. */
export function renderGuidesIndex(guides, { siteUrl, paths = READING_PATHS }) {
  const root = '../';
  const canonical = `${siteUrl}/${GUIDES_ROOT}/`;
  const description = 'Short, practical guides for the new grad job search: what counts as a new grad job, reading postings, résumés, visas and OPT, interviews, offers, and how this board collects and classifies its data.';
  const groups = groupGuides(guides);
  const resolved = readingPaths(guides, paths);
  const lastUpdated = guides.map((g) => g.updated).filter(Boolean).sort().at(-1);
  const stats = [plural(guides.length, 'guide'), plural(groups.length, 'section'), plural(resolved.length, 'reading path'), ...(lastUpdated ? [`last updated ${lastUpdated}`] : [])].join(' · ');
  const chips = groups.map((s) => `<a href="#${sectionId(s.name)}">${escapeHtml(s.name)}<span class="n">${s.guides.length}</span></a>`).join('\n');
  const sections = groups.map((s) => `<section class="sec" id="${sectionId(s.name)}" data-section>
<h2>${escapeHtml(s.name.toUpperCase())} <span class="n" data-section-count>(${s.guides.length})</span></h2>
<ul class="cards">
${s.guides.map((g) => card(g, root)).join('\n')}
</ul>
</section>`);
  return `<!DOCTYPE html>
<html lang="en" data-ngj-guides="index">
${head({ title: 'New Grad Job Search Guides · NGJ', description, canonical, siteUrl, root, jsonLd: null })}
<body>
<main class="wide">
<nav class="crumb" aria-label="Breadcrumb"><a class="brand" href="${root}" aria-label="NGJ, New Grad Jobs, home">NGJ</a> › guides</nav>
<header class="hero">
<h1>New grad job search guides</h1>
<p>${escapeHtml(description)}</p>
<p class="stats">${stats}</p>
</header>
${pathsPanel(resolved, root)}
${toolbar(guides)}
<nav class="chips" aria-label="Guide sections">
${chips}
</nav>
<p class="count" data-guides-count aria-live="polite" hidden></p>
<p class="storage-note" data-guides-storage role="status" hidden>Browser storage is blocked, so saved and read marks last only until you leave the page.</p>
<div class="empty" data-guides-empty hidden><p>No guides match these filters.</p><button type="button" class="linkish" data-reset>Clear search and filters</button></div>
${sections.join('\n')}
${footer(root)}
</main>
<script type="module" src="${GUIDES_SCRIPT}"></script>
</body>
</html>
`;
}

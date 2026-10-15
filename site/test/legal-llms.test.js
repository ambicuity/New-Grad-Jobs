// Policy pages (Markdown → /terms/, /privacy/, /copyright/, /data-sources/),
// llms.txt, the Markdown companions and the bundled third-party licence file.
import { mkdir, mkdtemp, readdir, readFile, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { LEGAL_PAGES, legalMarkdown, loadLegalPages, renderLegalPage } from '../scripts/seo/legal.mjs';
import { renderLlmsTxt } from '../scripts/seo/llms.mjs';
import { BUNDLED_PACKAGES, renderThirdPartyLicenses } from '../scripts/seo/licenses.mjs';
import { JOB_PAGE_CSP, PRERENDER_MARKER, legalLinksHtml } from '../scripts/seo/render.mjs';
import { generateSeo } from '../scripts/seo/generate.mjs';
import { parseFrontMatter, portableMarkdown } from '../scripts/seo/markdown.mjs';
import { guideMarkdown } from '../scripts/seo/guides.mjs';

const SITE = 'https://jobs.example.test';
const quiet = { log: () => {}, warn: () => {} };
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const page = (slug, extra = '') => `---\ntitle: ${slug} <policy>\ndescription: About ${slug} & more\neffective: 2026-10-15\nupdated: 2026-10-16\n${extra}---\nIntro with a [link](../about/).\n\n## 1. First part\n\nText.\n\n## 2. Second part\n\n- item\n`;

describe('published policy content', () => {
  const dir = new URL('../content/legal/', import.meta.url);

  it('has exactly one file per policy page, with valid metadata', async () => {
    const names = (await readdir(dir)).filter((n) => n.endsWith('.md')).sort();
    expect(names).toEqual(LEGAL_PAGES.map((p) => `${p.slug}.md`).sort());
    for (const name of names) {
      const { meta } = parseFrontMatter(await readFile(new URL(name, dir), 'utf8'));
      expect(meta.title, name).toBeTruthy();
      expect(meta.description, name).toBeTruthy();
      expect(meta.effective, name).toMatch(DATE_RE);
      expect(meta.updated, name).toMatch(DATE_RE);
      expect(meta.updated >= meta.effective, name).toBe(true);
    }
  });

  it('links only to pages and files the build produces, and never to a placeholder', async () => {
    const produced = new Set([
      ...LEGAL_PAGES.map((p) => `/${p.slug}/`),
      '/', '/about/', '/jobs/', '/guides/', '/jobs.json', '/feed.xml', '/health.json', '/robots.txt',
      '/sitemap.xml', '/llms.txt', '/third-party-licenses.txt',
    ]);
    const problems = [];
    for (const { slug } of LEGAL_PAGES) {
      const text = await readFile(new URL(`${slug}.md`, dir), 'utf8');
      if (/\[(?:PLACEHOLDER|TODO|TBD)|lorem ipsum|\bXX+\b/i.test(text)) problems.push(`${slug}: placeholder text`);
      for (const [, target] of text.matchAll(/\]\(([^)\s]+)\)/g)) {
        if (/^https?:/.test(target)) continue;
        const url = new URL(target, `${SITE}/${slug}/`);
        if (url.origin !== SITE || !produced.has(url.pathname)) problems.push(`${slug}: ${target}`);
      }
    }
    expect(problems).toEqual([]);
  });

  it('lists every browser storage key the app writes', async () => {
    const privacy = await readFile(new URL('privacy.md', dir), 'utf8');
    const srcDir = new URL('../src/', import.meta.url);
    const files = (await readdir(srcDir, { recursive: true })).filter((f) => /\.jsx?$/.test(f) && !/\.test\./.test(f));
    const keys = new Set();
    for (const f of files) {
      for (const [, key] of (await readFile(new URL(f, srcDir), 'utf8')).matchAll(/'(ngj?(?:-terminal)?:[a-z0-9:.-]+)'/g)) keys.add(key);
    }
    expect(keys.size).toBeGreaterThanOrEqual(4);
    for (const key of keys) expect(privacy, key).toContain(`\`${key}`);
  });

  it('names the published contact address on every page', async () => {
    for (const { slug } of LEGAL_PAGES) {
      expect(await readFile(new URL(`${slug}.md`, dir), 'utf8'), slug).toContain('contact@riteshrana.engineer');
    }
  });
});

describe('loadLegalPages', () => {
  let dir;
  beforeEach(async () => { dir = await mkdtemp(join(tmpdir(), 'ngj-legal-')); });
  afterEach(() => rm(dir, { recursive: true, force: true }));

  it('loads pages in LEGAL_PAGES order and skips missing or incomplete ones with a warning', async () => {
    await writeFile(join(dir, 'privacy.md'), page('privacy'));
    await writeFile(join(dir, 'terms.md'), page('terms'));
    await writeFile(join(dir, 'copyright.md'), '---\ntitle: No dates\n---\nBody\n');
    await writeFile(join(dir, 'stray.md'), page('stray'));
    const warnings = [];
    const pages = await loadLegalPages(dir, { warn: (m) => warnings.push(m) });
    expect(pages.map((p) => p.slug)).toEqual(['terms', 'privacy']);
    expect(pages[0]).toMatchObject({ title: 'terms <policy>', description: 'About terms & more', effective: '2026-10-15', updated: '2026-10-16' });
    expect(pages[0].headings.map((h) => h.text)).toEqual(['1. First part', '2. Second part']);
    expect(pages[0].markdown).toContain('## 1. First part');
    expect(warnings.join('\n')).toMatch(/copyright\.md/);
    expect(warnings.join('\n')).toMatch(/data-sources\.md/);
  });

  it('returns nothing for a missing directory', async () => {
    expect(await loadLegalPages(join(dir, 'nope'), quiet)).toEqual([]);
  });
});

describe('renderLegalPage', () => {
  let pages;
  beforeEach(async () => {
    const dir = await mkdtemp(join(tmpdir(), 'ngj-legal-'));
    for (const { slug } of LEGAL_PAGES) await writeFile(join(dir, `${slug}.md`), page(slug));
    pages = await loadLegalPages(dir, quiet);
    await rm(dir, { recursive: true, force: true });
  });

  it('is a script-free page with escaped metadata, dates, a contents list and the Markdown alternate', () => {
    const html = renderLegalPage(pages[0], { siteUrl: SITE, siblings: pages });
    expect(html).toContain(`<meta http-equiv="Content-Security-Policy" content="${JOB_PAGE_CSP.replace(/'/g, '&#39;')}">`);
    expect(html).not.toMatch(/<script/);
    expect(html).toContain('<title>terms &lt;policy&gt; · NGJ</title>');
    expect(html).toContain(`<link rel="canonical" href="${SITE}/terms/">`);
    expect(html).toContain('<link rel="alternate" type="text/markdown" href="index.md">');
    expect(html).toContain('<h1>terms &lt;policy&gt;</h1>');
    expect(html).toMatch(/Effective <time datetime="2026-10-15">2026-10-15<\/time>/);
    expect(html).toMatch(/Last updated <time datetime="2026-10-16">2026-10-16<\/time>/);
    expect(html).toContain('<nav class="toc" aria-label="On this page">');
    expect(html).toContain('<a href="#1-first-part">1. First part</a>');
    expect(html).toContain('<h2 id="1-first-part">');
    // Other policies are linked; the current one is not linked to itself in the related list.
    expect(html).toContain('href="../privacy/"');
    expect(html).toContain('aria-current="page"');
  });

  it('legalMarkdown prefixes the title and dates to the source body', () => {
    const md = legalMarkdown(pages[1]);
    expect(md.startsWith('# privacy <policy>\n\nEffective: 2026-10-15\nLast updated: 2026-10-16\n\n')).toBe(true);
    expect(md).toContain('## 2. Second part');
  });
});

describe('Markdown companions', () => {
  it('turn evidence blocks into labelled blockquotes', () => {
    const md = portableMarkdown('Intro\n\n::: evidence official\nSee [USCIS](https://www.uscis.gov/).\n:::\n\nAfter');
    expect(md).toBe('Intro\n\n> **OFFICIAL**\n>\n> See [USCIS](https://www.uscis.gov/).\n\nAfter');
    expect(guideMarkdown({ title: 'T', description: 'D', updated: '2026-10-01', markdown: '::: evidence practical\nDo it.\n:::' }))
      .toBe('# T\n\n> D\n\nUpdated: 2026-10-01\n\n> **PRACTICAL ADVICE**\n>\n> Do it.\n');
  });

  it('llms.txt link text stays on one line without brackets', () => {
    const text = renderLlmsTxt({ siteUrl: SITE, generatedAt: null, totalJobs: null, guides: [{ slug: 'g', title: 'A [b]\nc', description: 'x\n y' }], legal: [], categories: [] });
    expect(text).toContain(`- [A b c](${SITE}/guides/g/index.md): x y`);
  });
});

describe('legalLinksHtml', () => {
  it('links every policy relative to the page root', () => {
    const html = legalLinksHtml('../../');
    for (const { slug } of LEGAL_PAGES) expect(html).toContain(`href="../../${slug}/"`);
    expect(html).toContain('href="../../llms.txt"');
    expect(html).toMatch(/^<nav class="legal" aria-label="Legal">/);
  });
});

describe('renderLlmsTxt', () => {
  const generatedAt = new Date('2026-10-15T18:00:00Z');
  const guides = [
    { slug: 'how-to-use-this-board', title: 'How to use this board', description: 'Filters & alerts.', section: 'Getting started' },
    { slug: 'opt', title: 'OPT basics', description: '', section: 'International students' },
  ];
  const legal = LEGAL_PAGES.map(({ slug }) => ({ slug, title: `${slug} title`, description: `${slug} summary` }));
  const categories = [{ path: 'jobs/software-engineering/', name: 'Software Engineering', count: 1234 }];

  it('follows the llmstxt.org layout: H1, blockquote, details, H2 link lists, Optional last', () => {
    const text = renderLlmsTxt({ siteUrl: SITE, generatedAt, totalJobs: 9003, guides, legal, categories });
    const lines = text.split('\n');
    expect(lines[0]).toBe('# NGJ · New Grad Jobs');
    expect(lines[2].startsWith('> ')).toBe(true);
    expect(text).toContain('9,003 open roles');
    expect(text).toContain('2026-10-15T18:00:00Z');
    const h2 = lines.filter((l) => l.startsWith('## '));
    expect(h2.at(-1)).toBe('## Optional');
    expect(h2).toEqual(expect.arrayContaining(['## Data files', '## About and policies', '## Guides', '## Browse']));
    // Nothing between the H1 and the first H2 is a heading (the spec allows none there).
    const firstH2 = lines.findIndex((l) => l.startsWith('## '));
    expect(lines.slice(1, firstH2).some((l) => /^#{1,6} /.test(l))).toBe(false);
    // Every list item under an H2 is a "- [name](url)" link with an absolute URL on the site or the repo.
    const items = lines.slice(firstH2).filter((l) => l.startsWith('- '));
    expect(items.length).toBeGreaterThan(10);
    for (const item of items) expect(item).toMatch(/^- \[[^\]]+\]\((?:https:\/\/jobs\.example\.test\/|https:\/\/github\.com\/ambicuity\/New-Grad-Jobs)[^)\s]*\)(: .+)?$/);
  });

  it('links Markdown versions of guides and policies and carries real counts only', () => {
    const text = renderLlmsTxt({ siteUrl: SITE, generatedAt, totalJobs: 9003, guides, legal, categories });
    expect(text).toContain(`- [How to use this board](${SITE}/guides/how-to-use-this-board/index.md): Filters & alerts.`);
    expect(text).toContain(`- [OPT basics](${SITE}/guides/opt/index.md)`);
    expect(text).toContain(`- [privacy title](${SITE}/privacy/index.md): privacy summary`);
    expect(text).toContain(`- [Software Engineering jobs](${SITE}/jobs/software-engineering/): 1,234 open roles`);
    expect(text).toContain(`- [jobs.json](${SITE}/jobs.json)`);
    expect(text).toMatch(/MIT/);
    expect(text).toMatch(/belong to the employers/);
  });

  it('omits counts and the browse section when there is no data', () => {
    const text = renderLlmsTxt({ siteUrl: SITE, generatedAt: null, totalJobs: null, guides: [], legal: [], categories: [] });
    expect(text).not.toMatch(/\d[\d,]* open roles/);
    expect(text).not.toContain('## Browse');
    expect(text).not.toContain('## Guides');
    expect(text.split('\n')[0]).toBe('# NGJ · New Grad Jobs');
  });
});

describe('third-party licences', () => {
  it('covers every runtime dependency in package.json', async () => {
    const pkg = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8'));
    for (const name of Object.keys(pkg.dependencies)) expect(BUNDLED_PACKAGES).toContain(name);
  });

  it('includes the full licence text of each bundled package', async () => {
    const text = await renderThirdPartyLicenses(new URL('../node_modules/', import.meta.url).pathname, quiet);
    for (const name of BUNDLED_PACKAGES) expect(text).toMatch(new RegExp(`^${name.replace(/[/@.]/g, '\\$&')} [\\d.]+ — `, 'm'));
    expect(text).toContain('Permission is hereby granted, free of charge');
    expect(text).toMatch(/SIL OPEN FONT LICENSE/i);
  });

  it('notes a package whose licence cannot be read instead of failing', async () => {
    const root = await mkdtemp(join(tmpdir(), 'ngj-lic-'));
    const warnings = [];
    const text = await renderThirdPartyLicenses(root, { warn: (m) => warnings.push(m) }, ['missing-pkg']);
    expect(text).toContain('missing-pkg — licence text not found');
    expect(warnings).toHaveLength(1);
    await rm(root, { recursive: true, force: true });
  });
});

describe('generateSeo writes policies, llms.txt and Markdown companions', () => {
  let root;
  let publicDir;
  let distDir;
  beforeEach(async () => {
    root = await mkdtemp(join(tmpdir(), 'ngj-legal-gen-'));
    publicDir = join(root, 'public');
    distDir = join(root, 'dist');
    await mkdir(publicDir, { recursive: true });
    await mkdir(distDir, { recursive: true });
    await mkdir(join(root, 'content', 'legal'), { recursive: true });
    await mkdir(join(root, 'content', 'guides'), { recursive: true });
    for (const { slug } of LEGAL_PAGES) await writeFile(join(root, 'content', 'legal', `${slug}.md`), page(slug));
    await writeFile(join(root, 'content', 'guides', 'a-guide.md'), '---\ntitle: A guide\ndescription: d\nupdated: 2026-10-01\n---\n## Part\n\nBody.\n');
    await writeFile(join(distDir, 'index.html'), `<html><body><div id="root">${PRERENDER_MARKER}</div></body></html>`);
  });
  afterEach(() => rm(root, { recursive: true, force: true }));

  const JOB = { job_id: 'job_a1b2c3', company: 'Acme', title: 'Software Engineer, New Grad', location: 'Austin, TX', url: 'https://boards.example.com/acme/1', posted_at: '2026-10-14T10:00:00Z', category: { id: 'software_engineering', name: 'Software Engineering' }, source: 'Greenhouse' };

  it('with data', async () => {
    await writeFile(join(publicDir, 'jobs.json'), JSON.stringify({ meta: { generated_at: '2026-10-15T00:00:00Z' }, jobs: [JOB] }));
    const stats = await generateSeo({ publicDir, distDir, siteUrl: SITE, log: quiet });
    expect(stats.legalPages).toBe(4);
    for (const { slug } of LEGAL_PAGES) {
      expect(existsSync(join(distDir, slug, 'index.html')), slug).toBe(true);
      expect(await readFile(join(distDir, slug, 'index.md'), 'utf8')).toMatch(/^# .+\n\nEffective: 2026-10-15/);
    }
    expect(await readFile(join(distDir, 'guides', 'a-guide', 'index.md'), 'utf8')).toMatch(/^# A guide\n/);
    const llms = await readFile(join(distDir, 'llms.txt'), 'utf8');
    expect(llms).toContain('1 open role');
    expect(llms).toContain(`${SITE}/guides/a-guide/index.md`);
    const sitemap = await readFile(join(distDir, 'sitemap.xml'), 'utf8');
    expect(sitemap).toContain(`<loc>${SITE}/privacy/</loc><lastmod>2026-10-16T00:00:00.000Z</lastmod>`);
    // Every static page footer links the policies.
    expect(await readFile(join(distDir, 'job', 'job_a1b2c3', 'index.html'), 'utf8')).toContain('href="../../privacy/"');
    expect(await readFile(join(distDir, 'about', 'index.html'), 'utf8')).toContain('href="../privacy/"');
  });

  it('without data', async () => {
    const stats = await generateSeo({ publicDir, distDir, siteUrl: SITE, log: quiet });
    expect(stats.legalPages).toBe(4);
    expect(existsSync(join(distDir, 'terms', 'index.html'))).toBe(true);
    expect(await readFile(join(distDir, 'llms.txt'), 'utf8')).not.toMatch(/open roles? as of/);
    const sitemap = await readFile(join(distDir, 'sitemap.xml'), 'utf8');
    expect(sitemap).toContain(`<loc>${SITE}/terms/</loc>`);
  });
});

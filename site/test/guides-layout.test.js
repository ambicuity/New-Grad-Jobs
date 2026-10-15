// The guides layout: front matter → cards, reading paths, the 30-second brief,
// "On this page", prev/next, and the same-origin enhancement script.
import { mkdtemp, readdir, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import {
  GUIDE_FORMATS, GUIDE_PAGE_CSP, READING_PATHS, loadGuides, readingMinutes, readingPaths, renderGuidePage, renderGuidesIndex,
} from '../scripts/seo/guides.mjs';
import { parseFrontMatter, renderMarkdown } from '../scripts/seo/markdown.mjs';

const SITE = 'https://jobs.example.test';
const quiet = { log: () => {}, warn: () => {} };
const FORMAT_IDS = GUIDE_FORMATS.map((f) => f.id);

const guide = (over = {}) => {
  const { html, headings } = renderMarkdown('## First part\n\nText.\n\n## Second part\n\nMore.\n\n## Third & last\n\nEnd.\n');
  return {
    slug: 'reading-a-posting', title: 'Reading a posting <carefully>', description: 'Levels & signals', updated: '2026-09-30',
    published: '2026-09-25', section: 'Understanding jobs', order: 1, formats: ['checklist'], useWhen: 'Read this when a posting <confuses> you.',
    youGet: 'You get the signals that matter.', words: 900, readMinutes: 4, html, headings, markdown: '',
    ...over,
  };
};

describe('published guide front matter for the layout', () => {
  it('every guide has a published date, formats and a 30-second brief that only repeats numbers from its body', async () => {
    const dir = new URL('../content/guides/', import.meta.url);
    const names = (await readdir(dir)).filter((n) => n.endsWith('.md'));
    const issues = [];
    for (const name of names) {
      const { meta, body } = parseFrontMatter(await readFile(new URL(name, dir), 'utf8'));
      if (!/^\d{4}-\d{2}-\d{2}$/.test(meta.published || '')) issues.push(`${name}: missing published`);
      else if (meta.published > meta.updated) issues.push(`${name}: published after updated`);
      const formats = String(meta.format || '').split(',').map((s) => s.trim()).filter(Boolean);
      if (formats.length < 1 || formats.length > 2) issues.push(`${name}: format needs 1 or 2 values`);
      for (const f of formats) if (!FORMAT_IDS.includes(f)) issues.push(`${name}: unknown format ${f}`);
      for (const [key, lead] of [['use_when', 'Read this when '], ['you_get', 'You get ']]) {
        const v = meta[key] || '';
        if (!v.startsWith(lead)) issues.push(`${name}: ${key} must start "${lead}"`);
        if (v.length > 140) issues.push(`${name}: ${key} longer than 140 characters`);
        if (!/[.?]$/.test(v)) issues.push(`${name}: ${key} must end with a full stop`);
        // Honesty: the brief may not introduce a figure the guide itself does not state.
        for (const [n] of v.matchAll(/\d[\d,.%]*/g)) {
          if (!body.includes(n.replace(/[.,]$/, ''))) issues.push(`${name}: ${key} number ${n} not in the body`);
        }
      }
    }
    expect(issues).toEqual([]);
  });

  it('every reading path step is a published guide, listed once', async () => {
    const dir = new URL('../content/guides/', import.meta.url);
    const slugs = new Set((await readdir(dir)).filter((n) => n.endsWith('.md')).map((n) => n.slice(0, -3)));
    expect(READING_PATHS.length).toBeGreaterThanOrEqual(5);
    for (const path of READING_PATHS) {
      expect(path.steps.length, path.id).toBeGreaterThanOrEqual(3);
      expect(new Set(path.steps).size, path.id).toBe(path.steps.length);
      for (const step of path.steps) expect(slugs.has(step), `${path.id}: ${step}`).toBe(true);
    }
  });

  it('reading paths repeat the start-here situations step for step', async () => {
    const { body } = parseFrontMatter(await readFile(new URL('../content/guides/start-here.md', import.meta.url), 'utf8'));
    const situations = body.split(/^## /m).slice(1)
      .map((s) => [...s.matchAll(/^\d+\.\s.*$/gm)].flatMap(([line]) => [...line.matchAll(/\]\(\.\.\/([a-z0-9-]+)\/\)/g)].map((m) => m[1])))
      .filter((steps) => steps.length);
    expect(READING_PATHS.map((p) => [...p.steps])).toEqual(situations);
  });
});

describe('loadGuides layout fields', () => {
  let dir;
  beforeEach(async () => { dir = await mkdtemp(join(tmpdir(), 'ngj-guides-layout-')); });
  afterEach(() => rm(dir, { recursive: true, force: true }));

  it('reads formats, the brief, published, and computes words and reading time', async () => {
    const body = `${'word '.repeat(460)}\n\n## A\n\nx\n`;
    await writeFile(join(dir, 'a-guide.md'), `---\ntitle: A\nupdated: 2026-09-30\npublished: 2026-09-25\nformat: script, nonsense, checklist\nuse_when: Read this when x.\nyou_get: You get y.\n---\n${body}`);
    const warnings = [];
    const [g] = await loadGuides(dir, { warn: (m) => warnings.push(m) });
    expect(g).toMatchObject({ published: '2026-09-25', formats: ['script', 'checklist'], useWhen: 'Read this when x.', youGet: 'You get y.' });
    expect(g.words).toBe(462); // 460 + the heading "A" + "x"
    expect(g.readMinutes).toBe(2);
    expect(warnings.join('\n')).toMatch(/unknown format "nonsense"/);
  });

  it('defaults to explainer, no brief and no published date', async () => {
    await writeFile(join(dir, 'plain.md'), '---\ntitle: Plain\npublished: 2026-13-40\n---\nbody\n');
    const [g] = await loadGuides(dir, quiet);
    expect(g).toMatchObject({ formats: ['explainer'], useWhen: '', youGet: '', published: '', readMinutes: 1 });
  });

  it('readingMinutes rounds to whole minutes and never shows zero', () => {
    expect(readingMinutes(0)).toBe(1);
    expect(readingMinutes(230)).toBe(1);
    expect(readingMinutes(2240)).toBe(10);
  });
});

describe('readingPaths', () => {
  it('resolves steps to guides in path order and drops unknown slugs and empty paths', () => {
    const a = guide({ slug: 'a' });
    const b = guide({ slug: 'b' });
    const paths = readingPaths([a, b], [
      { id: 'p1', label: 'P1', explain: 'e', steps: ['b', 'missing', 'a'] },
      { id: 'p2', label: 'P2', explain: 'e', steps: ['missing'] },
    ]);
    expect(paths).toHaveLength(1);
    expect(paths[0].guides.map((g) => g.slug)).toEqual(['b', 'a']);
  });
});

describe('guides index layout', () => {
  const a = guide();
  const b = guide({ slug: 'visa-flags', title: 'Visa flags', section: 'International students', formats: ['official', 'checklist'], readMinutes: 7, updated: '2026-10-01' });
  const paths = [{ id: 'visa', label: 'F-1 or OPT', explain: 'Work authorisation first.', steps: ['visa-flags', 'reading-a-posting'] }];
  const html = renderGuidesIndex([a, b], { siteUrl: SITE, paths });

  it('states counts computed from the guides, never a fixed number', () => {
    expect(html).toContain('2 guides · 2 sections · 1 reading path · last updated 2026-10-01');
    expect(html).toMatch(/data-count="all">2</);
  });

  it('renders each guide as a card with its formats, reading time and search text', () => {
    expect(html).toContain('<li class="card" data-guide="visa-flags" data-formats="official checklist"');
    expect(html).toContain('<span class="tag">OFFICIAL</span>');
    expect(html).toContain('7 min read');
    expect(html).toContain('href="../guides/visa-flags/"');
    expect(html).toContain('Reading a posting &lt;carefully&gt;');
    expect(html).not.toContain('<carefully>');
    expect(html).toMatch(/data-text="reading a posting &lt;carefully&gt; levels &amp; signals understanding jobs/);
  });

  it('reading paths work without JavaScript as an exclusive set of details', () => {
    expect(html).toContain('<details class="path" name="path" id="path-visa">');
    const path = html.slice(html.indexOf('id="path-visa"'), html.indexOf('</details>', html.indexOf('id="path-visa"')));
    expect(path.indexOf('visa-flags/')).toBeLessThan(path.indexOf('reading-a-posting/'));
    expect(path).toContain('Work authorisation first.');
  });

  it('keeps search, views and save controls hidden until the script runs, and links section anchors', () => {
    expect(html).toContain('<div class="toolbar" data-guides-toolbar hidden>');
    expect(html).toMatch(/<button type="button" class="star"[^>]* hidden>/);
    expect(html).toContain('href="#sec-understanding-jobs"');
    expect(html).toContain('id="sec-understanding-jobs"');
    expect(html).toContain('<option value="official">OFFICIAL</option>');
    expect(html).not.toContain('<option value="worksheet">');
  });

  it('loads one same-origin module script and nothing from other origins', () => {
    expect(html).toContain('<html lang="en" data-ngj-guides="index">');
    expect(html.match(/<script(?![^>]*ld\+json)[^>]*>/g)).toEqual(['<script type="module" src="guides.js">']);
    expect(html).not.toMatch(/https:\/\/(?:cdn|fonts)\./);
    expect(GUIDE_PAGE_CSP).toContain("script-src 'self'");
    expect(GUIDE_PAGE_CSP).not.toContain('unsafe-inline');
    expect(html).toContain(GUIDE_PAGE_CSP.replace(/'/g, '&#39;'));
  });
});

describe('guide page layout', () => {
  const prev = guide({ slug: 'prev-guide', title: 'Prev guide', order: 0 });
  const cur = guide();
  const next = guide({ slug: 'next-guide', title: 'Next guide', order: 2 });
  const html = renderGuidePage(cur, { siteUrl: SITE, siblings: [next, cur, prev] });

  it('shows the 30-second brief, escaped, with its lead words in bold', () => {
    expect(html).toContain('<aside class="brief" aria-label="30-second brief">');
    expect(html).toContain('<strong>Read this when</strong> a posting &lt;confuses&gt; you.');
    expect(html).toContain('<strong>You get</strong> the signals that matter.');
  });

  it('lists every second-level heading in "On this page", pointing at real ids', () => {
    for (const [text, id] of [['First part', 'first-part'], ['Second part', 'second-part'], ['Third &amp; last', 'third-last']]) {
      expect(html).toContain(`<a href="#${id}">${text}</a>`);
      expect(html).toContain(`id="${id}"`);
    }
    expect(html).toContain('<nav class="toc toc-side" aria-label="On this page">');
    expect(html).toContain('<details class="toc toc-inline">');
  });

  it('omits "On this page" for short guides', () => {
    const { html: body, headings } = renderMarkdown('## Only\n\nx\n');
    expect(renderGuidePage(guide({ html: body, headings }), { siteUrl: SITE, siblings: [] })).not.toContain('<nav class="toc');
  });

  it('links the previous and next guide in index order, with the section in the breadcrumb', () => {
    expect(html).toContain('<a rel="prev" href="../../guides/prev-guide/">');
    expect(html).toContain('<a rel="next" href="../../guides/next-guide/">');
    expect(html).toContain('<a href="../../guides/#sec-understanding-jobs">Understanding jobs</a>');
  });

  it('links the breadcrumb section only for sections the index has', () => {
    const odd = renderGuidePage(guide({ section: 'Typo section' }), { siteUrl: SITE, siblings: [] });
    expect(odd).not.toContain('#sec-typo-section');
  });

  it('section headings are real h2 elements, not inside a summary', () => {
    const index = renderGuidesIndex([cur], { siteUrl: SITE, paths: [] });
    expect(index).toContain('<h2>UNDERSTANDING JOBS <span class="n" data-section-count>(1)</span></h2>');
    expect(index).not.toContain('<summary><h2>');
  });

  it('shows formats, reading time and dates, and Article JSON-LD with published and modified dates', () => {
    expect(html).toContain('<span class="tag">CHECKLIST</span>');
    expect(html).toContain('4 min read');
    expect(html).toContain('Updated <time datetime="2026-09-30">2026-09-30</time>');
    const ld = JSON.parse(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/.exec(html)[1]);
    expect(ld).toMatchObject({ '@type': 'Article', datePublished: '2026-09-25', dateModified: '2026-09-30', articleSection: 'Understanding jobs', wordCount: 900 });
  });

  it('keeps Mark read and Save hidden until the script runs, and loads only the same-origin script', () => {
    expect(html).toContain('<div class="tools" data-guide-tools data-guide="reading-a-posting" hidden>');
    expect(html.match(/<script(?![^>]*ld\+json)[^>]*>/g)).toEqual(['<script type="module" src="../guides.js">']);
    expect(html).toContain('data-ngj-guides="page"');
  });
});

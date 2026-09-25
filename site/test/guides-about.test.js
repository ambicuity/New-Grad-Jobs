// Guides (Markdown → /guides/<slug>/) and the /about/ page (health.json → facts).
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { loadGuides, renderGuidePage, renderGuidesIndex } from '../scripts/seo/guides.mjs';
import { aboutFacts, renderAboutPage } from '../scripts/seo/about.mjs';
import { generateSeo } from '../scripts/seo/generate.mjs';
import { PRERENDER_MARKER } from '../scripts/seo/render.mjs';
import { escapeHtml } from '../scripts/seo/text.mjs';

const SITE = 'https://jobs.example.test';
const quiet = { log: () => {}, warn: () => {} };
const ldBlocks = (html) => [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const GUIDE = '---\ntitle: Reading a posting <carefully>\ndescription: Levels & signals\nupdated: 2026-09-25\n---\n# Reading a posting\n\nSome **bold** text and a [link](../../jobs/).\n\n## Levels\n\n- I and II\n';

describe('loadGuides', () => {
  let dir;
  beforeEach(async () => { dir = await mkdtemp(join(tmpdir(), 'ngj-guides-')); });
  afterEach(() => rm(dir, { recursive: true, force: true }));

  it('loads slug-named markdown files with a title, skipping the rest', async () => {
    await writeFile(join(dir, 'reading-a-posting.md'), GUIDE);
    await writeFile(join(dir, 'no-title.md'), '# Untitled\n');
    await writeFile(join(dir, 'Bad Name.md'), '---\ntitle: x\n---\n');
    await writeFile(join(dir, 'notes.txt'), 'ignored');
    const warnings = [];
    const guides = await loadGuides(dir, { warn: (m) => warnings.push(m) });
    expect(guides.map((g) => g.slug)).toEqual(['reading-a-posting']);
    expect(guides[0]).toMatchObject({ title: 'Reading a posting <carefully>', description: 'Levels & signals', updated: '2026-09-25' });
    expect(guides[0].headings).toEqual([{ level: 1, text: 'Reading a posting' }, { level: 2, text: 'Levels' }]);
    expect(warnings.join('\n')).toMatch(/no title/);
    expect(warnings.join('\n')).toMatch(/bad slug/);
  });

  it('returns nothing for a missing directory', async () => {
    expect(await loadGuides(join(dir, 'nope'), quiet)).toEqual([]);
  });
});

describe('guide rendering', () => {
  const guide = {
    slug: 'reading-a-posting', title: 'Reading a posting <carefully>', description: 'Levels & signals', updated: '2026-09-25',
    html: '<h1>x</h1>', headings: [],
  };
  const other = { ...guide, slug: 'visa-flags', title: 'Visa flags' };

  it('page has canonical, Article JSON-LD, escaped title, sibling links and no scripts', () => {
    const html = renderGuidePage(guide, { siteUrl: SITE, siblings: [guide, other] });
    expect(html).toContain(`<link rel="canonical" href="${SITE}/guides/reading-a-posting/">`);
    expect(html).toContain(escapeHtml(guide.title));
    expect(html).not.toContain('<carefully>');
    const [ld] = ldBlocks(html).map((b) => JSON.parse(b));
    expect(ld).toMatchObject({ '@type': 'Article', headline: guide.title, dateModified: '2026-09-25', url: `${SITE}/guides/reading-a-posting/` });
    expect(html).toContain('href="../../guides/visa-flags/"');
    expect(html).not.toContain('href="../../guides/reading-a-posting/"');
    expect(html.match(/<script/g)).toHaveLength(1);
    expect(html).toContain('Updated 2026-09-25');
  });

  it('index lists every guide with its description', () => {
    const html = renderGuidesIndex([guide, other], { siteUrl: SITE });
    expect(html).toContain(`<link rel="canonical" href="${SITE}/guides/">`);
    expect(html).toContain('href="../guides/reading-a-posting/"');
    expect(html).toContain('Levels &amp; signals');
    expect(html).toContain('href="../guides/visa-flags/"');
  });
});

describe('aboutFacts / renderAboutPage', () => {
  const health = {
    status: 'ok', last_run: '2026-09-25T17:32:40Z', total_jobs: 2064, configured_company_apis: 272, enabled_sources: 5,
    active_hiring_companies: 290, run_duration_seconds: 151.7, url_safety_blocked: 0, near_miss_jobs: 812, corpus_jobs: 53733,
    source_counts: { greenhouse: 19805, workday: 16941 },
    sources: {
      greenhouse: { raw_count: 19805, configured_units: 136, status: 'ok', errors: { failed_companies: [] } },
      workday: { raw_count: 23358, configured_units: 59, status: 'ok', errors: { failed_companies: ['Autodesk <x>'] } },
    },
  };

  it('derives every figure from health.json and the generated data', () => {
    const facts = aboutFacts(health, { totalJobs: 1847, generatedAt: new Date('2026-09-25T17:32:40.261Z') });
    expect(facts).toMatchObject({
      totalJobs: '1,847', generatedAt: '2026-09-25T17:32:40Z', status: 'ok', configuredCompanyApis: '272',
      activeHiringCompanies: '290', enabledSources: '5', runDurationSeconds: '151.7', urlSafetyBlocked: '0', nearMissJobs: '812', corpusJobs: '53,733',
    });
    expect(facts.rows.map((r) => [r.label, r.raw, r.configured, r.status, r.failed])).toEqual([
      ['Greenhouse', '19,805', '136', 'ok', []],
      ['Workday', '23,358', '59', 'ok', ['Autodesk <x>']],
    ]);
  });

  it('never invents a number when health.json is missing or partial', () => {
    const facts = aboutFacts(null, { totalJobs: 3, generatedAt: null });
    expect(facts).toMatchObject({ totalJobs: '3', generatedAt: '', configuredCompanyApis: null, rows: [] });
    const html = renderAboutPage(facts, { siteUrl: SITE });
    expect(html).toContain('not reported');
    expect(html).not.toMatch(/\b200\+|\b300\+/);
  });

  it('renders the source table with escaping and the data links', () => {
    const html = renderAboutPage(aboutFacts(health, { totalJobs: 1847, generatedAt: null }), { siteUrl: SITE });
    expect(html).toContain(`<link rel="canonical" href="${SITE}/about/">`);
    expect(html).toContain('<td>Workday</td><td>23,358</td><td>59</td><td>ok</td><td>Autodesk &lt;x&gt;</td>');
    expect(html).toContain('href="../jobs.json"');
    expect(html).toContain('href="../health.json"');
    expect(html).not.toContain('<script');
  });
});

describe('generateSeo writes guides, about and closed-job pages', () => {
  let root;
  let publicDir;
  let distDir;
  let guidesDir;
  beforeEach(async () => {
    root = await mkdtemp(join(tmpdir(), 'ngj-seo-extra-'));
    publicDir = join(root, 'public');
    distDir = join(root, 'dist');
    guidesDir = join(root, 'guides');
    await mkdir(publicDir, { recursive: true });
    await mkdir(distDir, { recursive: true });
    await mkdir(guidesDir, { recursive: true });
    await writeFile(join(distDir, 'index.html'), `<html><body><div id="root">${PRERENDER_MARKER}</div></body></html>`);
    await writeFile(join(guidesDir, 'reading-a-posting.md'), GUIDE);
  });
  afterEach(() => rm(root, { recursive: true, force: true }));

  const JOB = {
    job_id: 'job_open01', company: 'Acme', title: 'Software Engineer, New Grad', location: 'Austin, TX',
    url: 'https://boards.example.com/acme/1', posted_at: '2026-09-20T10:00:00Z', category: { id: 'software_engineering', name: 'Software Engineering' },
  };

  it('with data: about + guides in the sitemap, closed job gets a noindex page outside the sitemap', async () => {
    const jobs = [JOB, { ...JOB, job_id: 'job_closed1', is_closed: true, title: 'Gone Role' }];
    await writeFile(join(publicDir, 'jobs.json'), JSON.stringify({ meta: { generated_at: '2026-09-25T12:00:00Z' }, jobs }));
    await writeFile(join(publicDir, 'health.json'), JSON.stringify({ status: 'ok', configured_company_apis: 272 }));

    const stats = await generateSeo({ publicDir, distDir, siteUrl: SITE, guidesDir, log: quiet });

    expect(stats).toMatchObject({ jobPages: 1, closedPages: 1, guidePages: 1, aboutPage: true });
    // home + landing (hub, swe, new-this-week) + about + guides index + 1 guide + 1 open job
    expect(stats.sitemapUrls).toBe(1 + stats.landingPages + 1 + 2 + 1);
    const sitemap = await readFile(join(distDir, 'sitemap.xml'), 'utf8');
    expect(sitemap).toContain(`<loc>${SITE}/about/</loc>`);
    expect(sitemap).toContain(`<loc>${SITE}/guides/reading-a-posting/</loc>`);
    expect(sitemap).not.toContain('job_closed1');

    const closed = await readFile(join(distDir, 'job', 'job_closed1', 'index.html'), 'utf8');
    expect(closed).toContain('<meta name="robots" content="noindex">');
    expect(closed).toContain('marked CLOSED');
    expect(closed).toContain('VIEW CLOSED LISTING');
    expect(closed).not.toContain('application/ld+json');
    const open = await readFile(join(distDir, 'job', 'job_open01', 'index.html'), 'utf8');
    expect(open).toContain('confirmed open at the employer on 2026-09-25');
    expect(open).not.toContain('noindex');

    const about = await readFile(join(distDir, 'about', 'index.html'), 'utf8');
    expect(about).toContain('<dt>open roles</dt><dd>1</dd>');
    expect(about).toContain('272');
    expect(existsSync(join(distDir, 'guides', 'index.html'))).toBe(true);
    const index = await readFile(join(distDir, 'index.html'), 'utf8');
    expect(index).toContain('href="./guides/"');
    expect(index).toContain('href="./about/"');
    const hub = await readFile(join(distDir, 'jobs', 'index.html'), 'utf8');
    expect(hub).toContain('href="../guides/reading-a-posting/"');
  });

  it('without data: guides are still written and listed', async () => {
    const stats = await generateSeo({ publicDir, distDir, siteUrl: SITE, guidesDir, log: quiet });
    expect(stats).toMatchObject({ jobPages: 0, guidePages: 1, aboutPage: false, sitemapUrls: 3 });
    expect(existsSync(join(distDir, 'guides', 'reading-a-posting', 'index.html'))).toBe(true);
    expect(existsSync(join(distDir, 'about'))).toBe(false);
  });
});
